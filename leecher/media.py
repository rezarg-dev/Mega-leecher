"""Sending files back to the user."""

import asyncio
import json
import os
import tempfile

from pyrogram.errors import FloodWait

from . import config
from .db import t
from .errors import Cancelled, UserError
from .ui import Progress
from .utils import remove, run

VIDEO_EXT = (".mp4", ".mkv", ".mov", ".avi", ".webm")
AUDIO_EXT = (".mp3", ".m4a", ".ogg", ".opus", ".flac", ".wav")

_LABELS = {"video": "sending_video", "audio": "sending_audio", "document": "sending_file"}


async def _probe(path):
    """Duration, dimensions and tags, as far as ffprobe can tell."""
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path]
    try:
        code, out, _ = await run(cmd, timeout=30)
        data = json.loads(out) if code == 0 else {}
    except (asyncio.TimeoutError, ValueError, OSError):
        data = {}

    info = {"duration": 0, "width": 0, "height": 0, "title": None, "performer": None}
    fmt = data.get("format") or {}
    try:
        info["duration"] = int(float(fmt.get("duration") or 0))
    except ValueError:
        pass
    tags = {str(k).lower(): v for k, v in (fmt.get("tags") or {}).items()}
    info["title"] = tags.get("title")
    info["performer"] = tags.get("artist")
    for stream in data.get("streams") or []:
        is_cover = (stream.get("disposition") or {}).get("attached_pic")
        if stream.get("codec_type") == "video" and not is_cover:
            info["width"] = int(stream.get("width") or 0)
            info["height"] = int(stream.get("height") or 0)
            break
    return info


async def _thumbnail(path, duration):
    fd, thumb = tempfile.mkstemp(suffix=".jpg", dir=config.TEMP_DIR)
    os.close(fd)
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", str(min(duration // 2, 10)), "-i", path,
           "-frames:v", "1", "-vf", "scale=320:-2", "-q:v", "5", thumb]
    try:
        code, _, _ = await run(cmd, timeout=30)
    except (asyncio.TimeoutError, OSError):
        code = 1
    if code == 0 and os.path.getsize(thumb) > 0:
        return thumb
    remove(thumb)
    return None


def _kind(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    return "document"


async def send(job, path, caption="", label=None, as_document=False):
    """Upload one file to the user's chat, with progress and cancel support."""
    uid, client = job.uid, job.client
    size = os.path.getsize(path)
    if size == 0:
        raise UserError("empty_file")
    if size > config.TG_UPLOAD_LIMIT:
        raise UserError("tg_too_large")

    kind = "document" if as_document else _kind(path)
    progress = Progress(job, label or t(uid, _LABELS[kind]), telegram=True)
    options = {"caption": caption, "progress": progress.update}
    thumb = None
    if kind == "video":
        info = await _probe(path)
        thumb = await _thumbnail(path, info["duration"])
        options.update(duration=info["duration"], width=info["width"], height=info["height"],
                       thumb=thumb, supports_streaming=True)
        method = client.send_video
    elif kind == "audio":
        info = await _probe(path)
        options.update(duration=info["duration"], title=info["title"], performer=info["performer"])
        method = client.send_audio
    else:
        method = client.send_document

    try:
        for attempt in range(3):
            try:
                message = await method(uid, path, **options)
                break
            except FloodWait as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(e.value + 1)
    finally:
        if thumb:
            remove(thumb)

    # Pyrogram returns None when the transfer was stopped from the progress callback.
    if message is None:
        if job.cancelled:
            raise Cancelled()
        raise UserError("error_generic", e="upload failed")
    return message
