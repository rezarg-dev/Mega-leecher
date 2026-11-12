"""GitHub as file storage: the REST API for setup, plain git for the uploads."""

import asyncio
import os
import re
import shutil
import tempfile
import time

import httpx

from . import config
from .db import t
from .errors import Cancelled, UserError
from .ui import cancel_keyboard, edit
from .utils import bar, clip, last_line, plain, run

API = "https://api.github.com"
BRANCH = "main"
UPLOADS_DIR = "uploads"
REPO_PREFIX = "bot-cloud-"

# Tuned for a 1 GB server: git must never try to delta-compress a 95 MB blob.
GIT_CONFIG = (
    ("user.email", "bot@telegram.bot"),
    ("user.name", "Telegram Bot"),
    ("commit.gpgsign", "false"),
    ("gc.auto", "0"),
    ("pack.windowMemory", "10m"),
    ("pack.compression", "0"),
    ("pack.threads", "1"),
    ("core.bigFileThreshold", "1m"),
    ("push.negotiate", "false"),
)

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]{20,255}")
_locks = {}


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _remote(username, token, repo):
    return f"https://{username}:{token}@github.com/{username}/{repo}.git"


def _repo_lock(username, repo):
    """Two pushes to the same repository must not race each other."""
    return _locks.setdefault((username, repo), asyncio.Lock())


async def validate_token(token):
    """Return the login the token belongs to."""
    if not _TOKEN_RE.fullmatch(token):
        raise UserError("gh_token_invalid", code=401)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{API}/user", headers=_headers(token))
    if response.status_code != 200:
        raise UserError("gh_token_invalid", code=response.status_code)
    return response.json()["login"]


async def ensure_repos(token, username, on_step=None):
    """Create the storage repositories that do not exist yet; return the usable ones."""
    ready = []
    async with httpx.AsyncClient(timeout=30, headers=_headers(token)) as client:
        for i in range(1, config.GITHUB_MAX_REPOS + 1):
            name = f"{REPO_PREFIX}{i}"
            if on_step:
                await on_step(i)
            response = await client.get(f"{API}/repos/{username}/{name}")
            if response.status_code != 200:
                response = await client.post(f"{API}/user/repos", json={
                    "name": name, "private": False, "auto_init": True,
                    "description": "Telegram Bot Cloud Storage",
                })
                if response.status_code != 201:
                    continue
            ready.append(name)
    return ready


class _Git:
    def __init__(self, cwd, token):
        self.cwd = cwd
        self.token = token
        self.env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

    async def _run(self, args, cancel=None):
        code, out, err = await run(["git", *args], cwd=self.cwd, env=self.env, cancel=cancel)
        # The token is part of the remote URL; keep it out of anything we show or log.
        return code, out.replace(self.token, "***"), err.replace(self.token, "***")

    async def try_(self, *args, cancel=None):
        """Run a command that is allowed to fail; return (exit code, error text)."""
        code, out, err = await self._run(args, cancel)
        return code, last_line(err) or last_line(out)

    async def __call__(self, *args, cancel=None):
        """Run a command that has to succeed; return its output."""
        code, out, err = await self._run(args, cancel)
        if code != 0:
            raise RuntimeError(f"git {args[0]}: {clip(last_line(err) or last_line(out))}")
        return out.strip()

    async def init(self, remote):
        await self("init", "-q")
        await self("symbolic-ref", "HEAD", f"refs/heads/{BRANCH}")
        await self("remote", "add", "origin", remote)
        for key, value in GIT_CONFIG:
            await self("config", key, value)

    async def checkout_index(self, cancel=None):
        """Load the remote branch into the index without downloading any file.

        Returns the commit to build on, or None when the branch does not exist yet.
        """
        if not await self("ls-remote", "--heads", "origin", BRANCH, cancel=cancel):
            return None
        await self("fetch", "--depth=1", "--filter=blob:none", "origin", BRANCH, cancel=cancel)
        # The filter turned this into a partial clone. Undo that, or git would
        # go back to the server every time it meets an object it does not have.
        for key in ("remote.origin.promisor", "remote.origin.partialclonefilter", "extensions.partialclone"):
            await self.try_("config", "--unset", key)
        await self("read-tree", "FETCH_HEAD")
        return await self("rev-parse", "FETCH_HEAD")

    async def commit(self, parent, message):
        tree = await self("write-tree", "--missing-ok")
        args = ["commit-tree", tree, "-m", message]
        if parent:
            args += ["-p", parent]
        commit = await self(*args)
        await self("update-ref", f"refs/heads/{BRANCH}", commit)
        return commit


def _copy_chunk(source, destination, limit):
    written = 0
    with open(destination, "wb") as out:
        while written < limit:
            block = source.read(min(config.MB, limit - written))
            if not block:
                break
            out.write(block)
            written += len(block)
    return written


async def upload(job, account, repo, path, on_pushed):
    """Push a file to the repository in chunks; return the raw download links.

    Every chunk is its own commit and push, so git never holds more than one
    chunk in memory. `on_pushed(nbytes)` is called after each successful push.
    """
    uid = job.uid
    username, token = account["username"], account["token"]
    parts = max(1, -(-os.path.getsize(path) // config.GITHUB_CHUNK_SIZE))
    ext = os.path.splitext(path)[1]
    folder = f"upload_{int(time.time())}"
    workdir = tempfile.mkdtemp(prefix="git_", dir=job.workdir)
    git = _Git(workdir, token)
    links = []

    async with _repo_lock(username, repo):
        try:
            await edit(job.status, t(uid, "gh_preparing"), cancel_keyboard(uid, job.id))
            await git.init(_remote(username, token, repo))
            parent = await git.checkout_index(cancel=job.cancel)
            # Two uploads in the same second must not land in the same folder.
            while parent and await git("ls-tree", parent, f"{UPLOADS_DIR}/{folder}"):
                folder += "_"

            chunk = os.path.join(workdir, "chunk")
            packs = os.path.join(workdir, ".git", "objects", "pack")
            with open(path, "rb") as source:
                for i in range(1, parts + 1):
                    if job.cancelled:
                        raise Cancelled()
                    name = f"Mega-Leecher{ext}.{i:03d}" if parts > 1 else f"Mega-Leecher{ext}"
                    relative = f"{UPLOADS_DIR}/{folder}/{name}"
                    written = await asyncio.to_thread(_copy_chunk, source, chunk, config.GITHUB_CHUNK_SIZE)

                    percent = i * 100 // parts
                    await edit(job.status,
                               t(uid, "gh_uploading", bar=bar(percent), pct=percent, i=i, n=parts,
                                 mb=written / config.MB),
                               cancel_keyboard(uid, job.id))

                    # Plumbing instead of add/commit: those inspect the working
                    # tree, which here holds none of the files already uploaded.
                    before = set(os.listdir(packs))
                    blob = await git("hash-object", "-w", "--", chunk)
                    os.unlink(chunk)
                    await git("update-index", "--add", "--cacheinfo", f"100644,{blob},{relative}")
                    parent = await git.commit(parent, f"chunk {i}/{parts}: {name}")

                    code, error = await git.try_("push", "--no-thin", "origin", BRANCH, cancel=job.cancel)
                    if code != 0:
                        raise UserError("gh_push_failed", i=i, code=code, err=plain(clip(error, 150)))
                    # GitHub has the chunk now; drop the local pack that holds it so
                    # a 2 GB upload does not need another 2 GB of disk.
                    for pack in set(os.listdir(packs)) - before:
                        os.unlink(os.path.join(packs, pack))
                    on_pushed(written)
                    links.append(f"https://raw.githubusercontent.com/{username}/{repo}/{BRANCH}/{relative}")
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
    return links


async def clear(account, repo):
    """Replace the repository's history with a single empty commit.

    Deleting the files in a new commit would leave them in the history and
    the space would never be released, hence the fresh root commit.
    """
    username, token = account["username"], account["token"]
    workdir = tempfile.mkdtemp(prefix="gh_clear_", dir=config.TEMP_DIR)
    git = _Git(workdir, token)
    async with _repo_lock(username, repo):
        try:
            await git.init(_remote(username, token, repo))
            with open(os.path.join(workdir, "README.md"), "w", encoding="utf-8") as f:
                f.write("# Cloud storage\n\nFiles in this repository are managed by a Telegram bot.\n")
            await git("add", "README.md")
            await git("commit", "-q", "-m", "Clear all uploads")
            await git("push", "--force", "origin", BRANCH)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
