"""YouTube and Instagram downloads through yt-dlp."""

import asyncio
import json
import logging
import os
import shutil
import sys
import tempfile
import urllib.parse

from . import config
from .errors import UserError
from .utils import clip, last_line, plain, run, safe_filename

log = logging.getLogger(__name__)

# Run yt-dlp as a module of our own interpreter: no dependency on where
# (or whether) pip dropped the `yt-dlp` launcher script.
YT_DLP = [sys.executable, "-m", "yt_dlp"]

# Several player clients: if YouTube blocks one, the next is tried.
CLIENT_ARGS = ["--extractor-args", "youtube:player_client=tv,web,mweb"]
INSTAGRAM_ARGS = ["--extractor-args", "instagram:direct=1;app_id=936619743392459"]

INFO_TIMEOUT = 180
QUALITIES = ("360", "480", "720", "1080")

# Each yt-dlp process is heavy; do not let a burst of links exhaust the RAM.
_info_slots = asyncio.Semaphore(2)


def _host(url):
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def is_youtube(url):
    host = _host(url)
    return host == "youtu.be" or host.endswith(("youtube.com", "youtube-nocookie.com"))


def is_instagram(url):
    host = _host(url)
    return host == "instagram.com" or host.endswith(".instagram.com")


def _js_runtime():
    deno = shutil.which("deno") or os.path.expanduser("~/.deno/bin/deno")
    return ["--js-runtimes", f"deno:{deno}"] if os.path.exists(deno) else []


def _cookies(workdir):
    """yt-dlp rewrites the cookie file on exit, so every run gets its own copy."""
    if not os.path.isfile(config.COOKIES_FILE):
        return []
    copy = os.path.join(workdir, ".cookies.txt")
    shutil.copyfile(config.COOKIES_FILE, copy)
    return ["--cookies", copy]


# ── Size estimates ───────────────────────────────────────────

def _has(fmt, field):
    return fmt.get(field, "none") != "none"


def _bytes(fmt, duration):
    # Fall back to bitrate × duration when the exact size is not published.
    size = fmt.get("filesize") or fmt.get("filesize_approx")
    if size:
        return size
    tbr = fmt.get("tbr")
    return int(tbr * 1000 / 8 * duration) if tbr and duration else 0


def _audio_size(formats, duration):
    audio = [f for f in formats if _has(f, "acodec") and not _has(f, "vcodec")]
    return max((_bytes(f, duration) for f in audio), default=0)


def _video_size(formats, duration, wanted):
    video = [f for f in formats
             if _has(f, "vcodec") and not _has(f, "acodec") and wanted(f.get("height") or 0)]
    if not video:
        return None
    best = max(video, key=lambda f: (f.get("height") or 0, _bytes(f, duration)))
    return _bytes(best, duration) + _audio_size(formats, duration)


def sizes(formats, duration):
    """Estimated download size per quality button; None means not available."""
    result = {q: _video_size(formats, duration, lambda h, q=int(q): 0 < h <= q) or 0
              for q in QUALITIES}
    result["2160"] = _video_size(formats, duration, lambda h: h >= 2000)
    result["mp3"] = _audio_size(formats, duration)
    return result


def format_size(size, unknown):
    if not size:
        return unknown
    mb = size / config.MB
    return f"{size // 1024}KB" if mb < 1 else f"~{mb:.0f}MB"


# ── yt-dlp ───────────────────────────────────────────────────

def _parse(line, fallback):
    try:
        return json.loads(line)
    except ValueError:
        return fallback


async def fetch_info(url):
    """Return (title, duration in seconds, list of format dicts)."""
    workdir = tempfile.mkdtemp(prefix="info_", dir=config.TEMP_DIR)
    # Printing only the fields we need is far lighter than --dump-json.
    cmd = [
        *YT_DLP,
        "--print", "%(title)j",
        "--print", "%(duration)j",
        "--print", "%(formats.:.{height,filesize,filesize_approx,tbr,vcodec,acodec})j",
        "--no-playlist", *CLIENT_ARGS, *_js_runtime(), "-q", "--no-warnings",
        *_cookies(workdir), url,
    ]
    try:
        async with _info_slots:
            code, out, err = await run(cmd, timeout=INFO_TIMEOUT)
    except asyncio.TimeoutError:
        raise UserError("error_generic", e="timeout")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    if code != 0:
        raise UserError("error_generic", e=plain(clip(last_line(err) or f"yt-dlp exited with {code}")))

    lines = out.strip().split("\n")
    title = _parse(lines[0], lines[0]) if lines and lines[0] else None
    duration = _parse(lines[1], 0) if len(lines) > 1 else 0
    formats = _parse(lines[2], []) if len(lines) > 2 else []
    return (
        title if isinstance(title, str) and title else "youtube_video",
        duration if isinstance(duration, (int, float)) else 0,
        [f for f in formats if isinstance(f, dict)] if isinstance(formats, list) else [],
    )


def file_stem(title):
    stem = "".join(c for c in title if c.isalnum() or c in " ._-").strip()
    return safe_filename(stem, "youtube_video")


def _format_args(item):
    if item.kind == "instagram":
        return ["-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4",
                *_js_runtime(), *INSTAGRAM_ARGS]
    if item.quality == "mp3":
        # "worst" as the fallback: never pull a full video just to throw the picture away.
        selection = ["-f", "bestaudio/worst", "-x", "--audio-format", "mp3"]
    else:
        video = "bestvideo[height>=2000]" if item.quality == "2160" else f"bestvideo[height<={item.quality}]"
        selection = ["-f", f"{video}+bestaudio/bestvideo+bestaudio/best", "--merge-output-format", "mp4"]
    return [*selection, "--no-playlist", *CLIENT_ARGS, *_js_runtime()]


async def download(job, item, directory, stem):
    """Download one video or audio track into `directory`; return the file path."""
    template = os.path.join(directory, stem.replace("%", "%%") + ".%(ext)s")
    cmd = [*YT_DLP, *_format_args(item), "--no-progress", "--no-warnings",
           "-o", template, *_cookies(directory), item.source]
    try:
        code, _, err = await run(cmd, cancel=job.cancel)
    finally:
        try:
            os.unlink(os.path.join(directory, ".cookies.txt"))
        except OSError:
            pass
    failure = "ig_download_failed" if item.kind == "instagram" else "yt_download_failed"
    if code != 0:
        log.warning("yt-dlp failed for %s: %s", item.source, last_line(err))
        raise UserError(failure)

    wanted = ".mp3" if item.quality == "mp3" else ".mp4"
    produced = [name for name in os.listdir(directory)
                if name.startswith(stem + ".") and not name.endswith((".part", ".ytdl"))]
    produced.sort(key=lambda name: (not name.endswith(wanted), name))
    if not produced:
        raise UserError(failure)
    return os.path.join(directory, produced[0])
