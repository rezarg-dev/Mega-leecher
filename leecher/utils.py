import asyncio
import os
import re
import shutil
import signal
import unicodedata

from . import config
from .errors import Cancelled, UserError

MAX_NAME_BYTES = 200


def safe_filename(name, default="file"):
    """Reduce an untrusted name to a plain file name that is safe to join to a directory."""
    # Header values can carry undecodable bytes (lone surrogates); drop them first.
    name = str(name or "").encode("utf-8", "replace").decode("utf-8")
    name = unicodedata.normalize("NFC", name)
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(ch for ch in name if unicodedata.category(ch) != "Cc")
    name = name.strip().lstrip(".").strip()
    if not name:
        return default
    root, ext = os.path.splitext(name)
    if len(ext.encode("utf-8")) > 20:
        root, ext = name, ""
    while root and len((root + ext).encode("utf-8")) > MAX_NAME_BYTES:
        root = root[:-1]
    return (root + ext) or default


def unique_path(directory, name):
    path = os.path.join(directory, name)
    root, ext = os.path.splitext(name)
    n = 2
    while os.path.lexists(path):
        path = os.path.join(directory, f"{root} ({n}){ext}")
        n += 1
    return path


def natural_key(text):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def list_files(path):
    """Every file below `path`, in a stable human-friendly order."""
    found = []
    for root, dirs, files in os.walk(path):
        dirs.sort(key=natural_key)
        found.extend(os.path.join(root, name) for name in sorted(files, key=natural_key))
    return found


def tree_size(path):
    if os.path.isfile(path):
        return os.path.getsize(path)
    return sum(os.path.getsize(f) for f in list_files(path))


def remove(path):
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path, ignore_errors=True)
    else:
        try:
            os.unlink(path)
        except OSError:
            pass


def require_space(nbytes):
    """Refuse early when a download would not fit next to its processed copy."""
    needed = 2 * nbytes + 512 * config.MB
    if shutil.disk_usage(config.TEMP_DIR).free < needed:
        raise UserError("no_disk_space")


def bar(percent):
    filled = max(0, min(10, int(percent // 10)))
    return "■" * filled + "□" * (10 - filled)


def clip(text, limit=200):
    text = str(text).strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def plain(text):
    """Make text safe to show inside a `code` span."""
    return str(text).replace("`", "'")


def inline(text):
    """Make text safe to show inside **bold** or other Markdown formatting."""
    text = plain(text)
    for mark in ("**", "__", "~~", "||"):
        while mark in text:
            text = text.replace(mark, mark[0] + "\u200b" + mark[1])
    return text


def last_line(text):
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _kill(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


async def run(cmd, cwd=None, env=None, cancel=None, timeout=None):
    """Run a command and return (exit code, stdout, stderr).

    The process gets its own group so that cancelling also takes down
    whatever it spawned (ffmpeg under yt-dlp, git's helpers, ...).
    """
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=cwd, env=env,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )
    output = asyncio.ensure_future(proc.communicate())
    waiting = {output}
    stop = None
    if cancel is not None:
        stop = asyncio.ensure_future(cancel.wait())
        waiting.add(stop)
    try:
        done, _ = await asyncio.wait(waiting, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
        if output not in done:
            _kill(proc)
            await output
            if stop is not None and stop in done:
                raise Cancelled()
            raise asyncio.TimeoutError()
        out, err = output.result()
        return proc.returncode, out.decode(errors="replace"), err.decode(errors="replace")
    finally:
        if stop is not None:
            stop.cancel()
        if not output.done():
            _kill(proc)
            output.cancel()
