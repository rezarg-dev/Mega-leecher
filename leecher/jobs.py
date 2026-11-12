"""The job pipeline: queueing, fetching the sources and delivering the result."""

import asyncio
import logging
import os
import shutil
import tempfile
import time
from contextlib import asynccontextmanager

import httpx
from pyrogram.errors import FloodWait

from . import archive, config, db, gdrive, github, media, net, state, torrent, youtube
from .db import t
from .errors import Cancelled, UserError
from .ui import Progress, action_keyboard, batch_keyboard, cancel_keyboard, edit, show
from .utils import bar, clip, list_files, natural_key, plain, require_space, unique_path

log = logging.getLogger(__name__)

TG_TEXT_LIMIT = 4000

_job_slots = asyncio.Semaphore(config.MAX_CONCURRENT_JOBS)
_github_slots = asyncio.Semaphore(4)
_drive_slots = asyncio.Semaphore(4)


# ── Queueing ─────────────────────────────────────────────────

@asynccontextmanager
async def _turn(client, uid):
    """Regular users run one job at a time, within the global limit; the admin never waits."""
    if db.is_admin(uid):
        yield
        return
    lock = state.user_lock(uid)
    if lock.locked() or _job_slots.locked():
        await _send(client, uid, t(uid, "queued"))
    async with lock:
        async with _job_slots:
            yield


@asynccontextmanager
async def _slot(semaphore, uid):
    if db.is_admin(uid):
        yield
        return
    async with semaphore:
        yield


async def _send(client, uid, text):
    for attempt in range(3):
        try:
            return await client.send_message(uid, text)
        except FloodWait as e:
            await asyncio.sleep(min(e.value, 60) + 1)
        except Exception as e:
            log.warning("could not message %s: %s", uid, e)
            return None
    return None


def _error_text(uid, error):
    return t(uid, "error_generic", e=plain(clip(str(error) or type(error).__name__)))


# ── Entry points ─────────────────────────────────────────────

async def offer(client, uid, message, item, text):
    """Put a ready item in front of the user: add it to the open batch or show the action menu."""
    batch = state.batches.get(uid)
    if batch is not None:
        batch.items.append(item)
        await show(client, message, t(uid, "file_added_multi", count=len(batch.items)), batch_keyboard(uid))
        return
    shown = await show(client, message, text, action_keyboard(uid))
    if shown is None:
        state.discard([item])
        return
    # Keyed by the message that carries the buttons.
    state.selections[(uid, shown.id)] = state.Selection([item])


def submit(client, uid, selection):
    job = state.Job(client, uid)
    job.items = selection.items
    state.spawn(_run(job, selection))


def submit_torrent(client, message, source, is_magnet):
    job = state.Job(client, message.from_user.id)
    state.spawn(_run_torrent(job, message, source, is_magnet))


async def _run(job, selection):
    done = False
    try:
        async with _turn(job.client, job.uid):
            done = await _process(job, selection)
    finally:
        job.close()
        item = selection.items[0]
        retry = (not done and selection.action != "multi"
                 and item.kind == "local" and os.path.exists(item.source))
        if not retry:
            state.discard(selection.items)
    if retry:
        # A finished torrent is expensive to redo; let the user pick another action.
        message = await _send(job.client, job.uid, t(job.uid, "torrent_ready"))
        if message is None:
            state.discard(selection.items)
        else:
            await offer(job.client, job.uid, message, item, t(job.uid, "torrent_ready"))


async def _run_torrent(job, message, source, is_magnet):
    uid, client = job.uid, job.client
    job.workdir = tempfile.mkdtemp(prefix=f"torrent_{uid}_", dir=config.TEMP_DIR)
    failure = None
    try:
        job.status = await message.reply(t(uid, "torrent_metadata"),
                                         reply_markup=cancel_keyboard(uid, job.id), quote=True)
        async with _turn(client, uid):
            if job.cancelled:
                raise Cancelled()
            if not is_magnet:
                source = await client.download_media(
                    message, file_name=os.path.join(job.workdir, "task.torrent"))
                if not source:
                    raise UserError("torrent_invalid")
            data_dir = os.path.join(job.workdir, "data")
            os.mkdir(data_dir)
            path = await torrent.download(job, source, is_magnet, data_dir)
    except Cancelled:
        failure = t(uid, "torrent_cancelled")
    except UserError as e:
        failure = e.text(uid)
    except Exception as e:
        log.exception("torrent job %s failed", job.id)
        failure = _error_text(uid, e)
    finally:
        job.close()

    if failure is not None:
        shutil.rmtree(job.workdir, ignore_errors=True)
        if job.status is not None:
            await show(client, job.status, failure)
        return
    item = state.Item("local", path, os.path.basename(path), cleanup=job.workdir)
    await offer(client, uid, job.status, item, t(uid, "torrent_ready"))


# ── Processing ───────────────────────────────────────────────

def _check_github(uid):
    if not db.gh_account(uid):
        raise UserError("gh_no_token_core")
    if db.gh_remaining(uid) <= 0:
        raise UserError("gh_quota_core", limit=config.GITHUB_DAILY_LIMIT)


def _check_drive(uid):
    if not db.gd_account(uid):
        raise UserError("gd_no_account_core")
    if db.gd_remaining(uid) <= 0:
        raise UserError("gd_quota_core", limit=config.DRIVE_DAILY_LIMIT)


def _youtube_count(items):
    return sum(1 for item in items if item.kind == "youtube")


async def _process(job, selection):
    """Run one job from start to finish. Returns True when everything was delivered."""
    uid, client = job.uid, job.client
    job.status = await _send(client, uid, t(uid, "processing_start"))
    if job.status is None:
        return False
    job.workdir = tempfile.mkdtemp(prefix=f"{uid}_", dir=config.TEMP_DIR)
    in_dir = os.path.join(job.workdir, "in")
    out_dir = os.path.join(job.workdir, "out")
    os.mkdir(in_dir)
    os.mkdir(out_dir)
    action = selection.action
    try:
        # Fail on quota and connection problems before downloading anything.
        if action == "github":
            _check_github(uid)
        elif action == "gdrive":
            _check_drive(uid)
        videos = _youtube_count(selection.items)
        if videos and not db.is_admin(uid) and db.yt_remaining(uid) < videos:
            raise UserError("yt_quota_exceeded")

        target = await _fetch(job, selection, in_dir)

        if action == "raw":
            await _send_raw(job, target)
        elif action == "github":
            await _to_github(job, target)
        elif action == "gdrive":
            await _to_drive(job, target)
        else:
            await _send_archive(job, selection, target, in_dir, out_dir)

        if videos:
            db.record_yt(uid, videos)
        await show(client, job.status, t(uid, "done"))
        return True
    except Cancelled:
        await show(client, job.status, t(uid, "cancelled"))
    except UserError as e:
        await show(client, job.status, e.text(uid))
    except Exception as e:
        log.exception("job %s failed", job.id)
        await show(client, job.status, _error_text(uid, e))
    finally:
        shutil.rmtree(job.workdir, ignore_errors=True)
    return False


# ── Fetching ─────────────────────────────────────────────────

async def _fetch(job, selection, in_dir):
    """Bring every item to disk; return the file or directory to deliver."""
    items = selection.items
    if selection.action != "multi":
        item = items[0]
        if item.kind == "local":
            return item.source
        return await _fetch_item(job, item, in_dir)
    for index, item in enumerate(items, 1):
        await _fetch_item(job, item, in_dir, index)
    return in_dir


def _quality_label(uid, item):
    if item.kind == "instagram":
        return "Instagram"
    if item.quality == "mp3":
        return t(uid, "audio_only_label")
    return f"{item.quality}p"


async def _fetch_item(job, item, directory, index=None):
    uid, client = job.uid, job.client
    limit = None if db.is_admin(uid) else config.MAX_FILE_SIZE
    if job.cancelled:
        raise Cancelled()

    if item.kind == "local":
        path = unique_path(directory, os.path.basename(item.source))
        shutil.move(item.source, path)
        return path

    if item.kind == "media":
        path = unique_path(directory, item.name)
        require_space(item.size)
        progress = Progress(job, t(uid, "receiving_file"), telegram=True)
        result = await client.download_media(item.source, file_name=path, progress=progress.update)
        if job.cancelled:
            raise Cancelled()
        # Pyrogram swallows transfer errors and hands back a truncated file, so check the size.
        if not result or not os.path.isfile(path) or (item.size and os.path.getsize(path) != item.size):
            raise UserError("tg_download_failed")
        return path

    if item.kind == "url":
        label = t(uid, "receiving_link", i=index) if index else t(uid, "receiving_file")
        return await net.download(job, item.source, unique_path(directory, item.name), label, limit)

    if index:
        text = t(uid, "yt_item_download", i=index)
    else:
        text = t(uid, "yt_downloading", quality=_quality_label(uid, item))
    await edit(job.status, text, cancel_keyboard(uid, job.id))
    scratch = tempfile.mkdtemp(prefix="yt_", dir=job.workdir)
    produced = await youtube.download(job, item, scratch, item.name)
    if limit and os.path.getsize(produced) > limit:
        raise UserError("size_limit")
    path = unique_path(directory, os.path.basename(produced))
    os.rename(produced, path)
    shutil.rmtree(scratch, ignore_errors=True)
    return path


# ── Delivery ─────────────────────────────────────────────────

async def _send_raw(job, target):
    files = [target] if os.path.isfile(target) else list_files(target)
    if not files:
        raise UserError("empty_file")
    await edit(job.status, t(job.uid, "sending"))
    for path in files:
        await media.send(job, path)


async def _send_archive(job, selection, target, in_dir, out_dir):
    uid = job.uid
    await edit(job.status, t(uid, "compressing_rar"), cancel_keyboard(uid, job.id))
    if selection.action == "multi":
        inputs = [os.path.join(in_dir, name) for name in sorted(os.listdir(in_dir), key=natural_key)]
    else:
        inputs = [target]
    if selection.action == "split":
        volume = selection.split_mb
    else:
        volume = archive.SAFE_VOLUME_MB if archive.needs_volumes(inputs) else None

    parts = await archive.rar(inputs, out_dir, volume, selection.password, job.cancel)
    total = len(parts)
    for i, path in enumerate(parts, 1):
        label = t(uid, "sending_part", i=i, total=total)
        caption = label if total > 1 else t(uid, "final_file")
        await media.send(job, path, caption=caption, label=label, as_document=True)
        os.unlink(path)


async def _single_file(job, target):
    """Cloud uploads take one file; a folder (multi-file torrent) is zipped first."""
    if os.path.isfile(target):
        return target
    uid = job.uid
    await edit(job.status, t(uid, "preparing_file"), cancel_keyboard(uid, job.id))
    name = os.path.basename(os.path.normpath(target)) + ".zip"
    return await archive.zip_folder(target, os.path.join(job.workdir, name), job.cancel)


def _link_messages(uid, links):
    """Split the link list over as many messages as Telegram's length limit needs."""
    messages = []
    current = t(uid, "gh_links_header")
    for i, url in enumerate(links, 1):
        line = t(uid, "gh_part_link", i=i, url=url)
        if len(current) + len(line) > TG_TEXT_LIMIT:
            messages.append(current.strip())
            current = line
        else:
            current += line
    if current.strip():
        messages.append(current.strip())
    return messages


async def _to_github(job, target):
    uid, client = job.uid, job.client
    admin = db.is_admin(uid)
    if not admin and _github_slots.locked():
        await edit(job.status, t(uid, "gh_queued"), cancel_keyboard(uid, job.id))
    async with _slot(_github_slots, uid):
        if job.cancelled:
            raise Cancelled()
        path = await _single_file(job, target)
        size = os.path.getsize(path)
        if size == 0:
            raise UserError("empty_file")
        if size > config.MAX_FILE_SIZE and not admin:
            raise UserError("gh_size_limit", size=size / config.GB)
        _check_github(uid)
        repo = db.gh_pick_repo(uid, size)
        if not repo:
            raise UserError("gh_full")
        remaining = db.gh_remaining(uid)
        links = await github.upload(job, db.gh_account(uid), repo, path,
                                    lambda nbytes: db.gh_add_usage(uid, repo, nbytes))
    db.gh_record(uid)

    await edit(job.status, t(uid, "gh_upload_done"))
    quota = "" if admin else t(uid, "gh_quota_line", remaining=remaining - 1)
    header = t(uid, "gh_success_header", repo=repo, parts=len(links), quota=quota)
    if len(links) > 1:
        header += t(uid, "gh_multipart_note")
    await _send(client, uid, header)
    for text in _link_messages(uid, links):
        await _send(client, uid, text)

    # The same links as a text file, ready to import into a download manager.
    listing = os.path.join(job.workdir, f"links_{uid}_{int(time.time())}.txt")
    with open(listing, "w", encoding="utf-8") as f:
        f.write("\n".join(links))
    try:
        await client.send_document(uid, listing, caption=t(uid, "gh_links_file_cap"))
    except Exception as e:
        log.warning("could not send the link list to %s: %s", uid, e)


async def _drive_folder(uid, token, renew=False):
    folder = None if renew else db.gd_account(uid).get("folder_id")
    if not folder:
        try:
            folder = await gdrive.ensure_folder(token)
        except (UserError, httpx.HTTPError):
            raise UserError("gd_folder_error")
        db.gd_update(uid, folder_id=folder)
    return folder


def _drive_progress(job):
    uid = job.uid
    last = 0.0

    async def report(sent, total):
        nonlocal last
        now = time.monotonic()
        if now - last < Progress.INTERVAL and sent != total:
            return
        last = now
        percent = sent * 100 // total if total else 100
        await edit(job.status,
                   t(uid, "gd_uploading", bar=bar(percent), pct=percent,
                     sent=sent / config.MB, total=total / config.MB),
                   cancel_keyboard(uid, job.id))

    return report


async def _to_drive(job, target):
    uid, client = job.uid, job.client
    admin = db.is_admin(uid)
    if not admin and _drive_slots.locked():
        await edit(job.status, t(uid, "gd_queued"), cancel_keyboard(uid, job.id))
    async with _slot(_drive_slots, uid):
        if job.cancelled:
            raise Cancelled()
        path = await _single_file(job, target)
        size = os.path.getsize(path)
        if size == 0:
            raise UserError("empty_file")
        if size > config.MAX_FILE_SIZE and not admin:
            raise UserError("gd_size_limit", size=size / config.GB)
        _check_drive(uid)
        token = await gdrive.access_token(uid)
        if not token:
            raise UserError("gd_auth_error_core")
        remaining = db.gd_remaining(uid)
        name = os.path.basename(path)
        report = _drive_progress(job)

        folder = await _drive_folder(uid, token)
        try:
            file_id = await gdrive.upload(token, path, name, folder, job.cancel, report)
        except gdrive.FolderMissing:
            # The user deleted our folder from their Drive; make a new one and go again.
            folder = await _drive_folder(uid, token, renew=True)
            try:
                file_id = await gdrive.upload(token, path, name, folder, job.cancel, report)
            except gdrive.FolderMissing:
                raise UserError("gd_folder_error")

        # A long upload can outlive the token it started with.
        token = await gdrive.access_token(uid) or token
        view_url, download_url = await gdrive.share(token, file_id)
    db.gd_record(uid)

    await edit(job.status, t(uid, "gd_upload_done"))
    quota = "" if admin else t(uid, "gd_quota_line", remaining=remaining - 1)
    await _send(client, uid, t(uid, "gd_success", name=plain(name), quota=quota,
                               view=view_url, dl=download_url))
