"""Torrent downloads (magnet links and .torrent files) through libtorrent."""

import asyncio
import logging
import os
import time

import libtorrent as lt

from . import config, db
from .db import t
from .errors import Cancelled, UserError
from .ui import cancel_keyboard, edit
from .utils import bar, clip, plain, require_space

log = logging.getLogger(__name__)

METADATA_TIMEOUT = 600
MAX_TORRENT_FILE = 10 * config.MB


def _add(session, source, is_magnet, save_path):
    try:
        if is_magnet:
            params = lt.parse_magnet_uri(source)
        elif hasattr(lt, "add_torrent_params"):
            params = lt.add_torrent_params()
            params.ti = lt.torrent_info(source)
        else:
            params = {"ti": lt.torrent_info(source)}
        if isinstance(params, dict):            # libtorrent 1.1 only knows the dict form
            params["save_path"] = save_path
        else:
            params.save_path = save_path
        return session.add_torrent(params)
    except Exception as e:
        log.info("rejected torrent: %s", e)
        raise UserError("torrent_invalid")


def _error(status):
    code = getattr(status, "errc", None)
    if code is not None:
        try:
            return code.message() if code.value() else None
        except Exception:
            return None
    message = getattr(status, "error", "")      # libtorrent 1.1
    return message if isinstance(message, str) and message else None


async def _pause(job, seconds):
    """Sleep, but wake up at once when the job is cancelled."""
    try:
        await asyncio.wait_for(job.cancel.wait(), seconds)
    except asyncio.TimeoutError:
        return
    raise Cancelled()


async def download(job, source, is_magnet, save_path):
    """Download a torrent into `save_path`; return the path of what it contains."""
    uid = job.uid
    session = lt.session()
    handle = _add(session, source, is_magnet, save_path)
    try:
        deadline = time.monotonic() + METADATA_TIMEOUT
        while not handle.status().has_metadata:
            if time.monotonic() > deadline:
                raise UserError("torrent_metadata_timeout")
            await _pause(job, 1)

        total = handle.status().total_wanted
        if total > config.MAX_FILE_SIZE and not db.is_admin(uid):
            raise UserError("torrent_too_large")
        require_space(total)

        while True:
            status = handle.status()
            if status.is_seeding or status.is_finished:
                break
            failure = _error(status)
            if failure:
                raise UserError("error_generic", e=plain(clip(failure)))
            percent = status.progress * 100
            await edit(
                job.status,
                t(uid, "torrent_progress", bar=bar(percent), pct=percent,
                  speed=status.download_rate / 1024,
                  done=status.total_wanted_done / config.MB,
                  total=status.total_wanted / config.MB,
                  seeds=status.num_seeds, peers=status.num_peers),
                cancel_keyboard(uid, job.id),
            )
            await _pause(job, 5)
    finally:
        try:
            session.remove_torrent(handle)
        except Exception:
            pass
        # Tearing a session down can block for a moment; keep that off the event loop.
        holder = [session]
        del session, handle
        await asyncio.shield(asyncio.to_thread(holder.clear))

    entries = [name for name in os.listdir(save_path) if not name.startswith(".")]
    if not entries:
        raise UserError("error_generic", e="empty torrent")
    # A torrent is either a single file or a single top-level folder.
    return os.path.join(save_path, entries[0]) if len(entries) == 1 else save_path
