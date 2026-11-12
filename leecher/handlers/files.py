"""Intake: Telegram files, links, torrents and the YouTube quality menu."""

import logging
import time

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton as Button, InlineKeyboardMarkup

from .. import config, db, jobs, net, state, torrent, youtube
from ..client import app
from ..db import t
from ..errors import UserError
from ..ui import ack, action_keyboard, batch_keyboard, edit, show
from ..utils import clip, inline, plain, safe_filename
from .common import subscribers_only

log = logging.getLogger(__name__)

# Media types we accept, with the extension to use when Telegram gives no file name.
MEDIA_TYPES = {
    "document": "", "video": ".mp4", "audio": ".mp3", "voice": ".ogg",
    "animation": ".mp4", "video_note": ".mp4", "photo": ".jpg",
}
MEDIA = (filters.document | filters.video | filters.audio | filters.voice
         | filters.animation | filters.video_note | filters.photo)


def _media(message):
    """The media object of a message and a safe file name for it."""
    for kind, extension in MEDIA_TYPES.items():
        media = getattr(message, kind, None)
        if media is not None:
            name = getattr(media, "file_name", None)
            return media, safe_filename(name) if name else f"file_{int(time.time())}{extension}"
    return None, None


@app.on_message(filters.private & MEDIA)
async def on_media(client, message):
    uid = message.from_user.id
    media, name = _media(message)
    if media is None:
        return
    size = getattr(media, "file_size", 0) or 0
    if size > config.MAX_FILE_SIZE and not db.is_admin(uid):
        await message.reply(t(uid, "file_too_large"))
        return

    if name.lower().endswith(".torrent"):
        if size > torrent.MAX_TORRENT_FILE:
            await message.reply(t(uid, "torrent_invalid"))
            return
        jobs.submit_torrent(client, message, None, is_magnet=False)
        return

    reply = await message.reply(t(uid, "processing"), quote=True)
    item = state.Item("media", message, name, size=size)
    await jobs.offer(client, uid, reply, item, t(uid, "file_received", name=plain(name)))


async def on_link(client, message, url):
    """Called by the text router for http(s) and magnet links."""
    uid = message.from_user.id
    if url.lower().startswith("magnet:"):
        jobs.submit_torrent(client, message, url, is_magnet=True)
        return

    if youtube.is_instagram(url):
        reply = await message.reply(t(uid, "ig_received"), quote=True)
        item = state.Item("instagram", url, f"instagram_{int(time.time())}", quality="best")
        await jobs.offer(client, uid, reply, item, t(uid, "ig_select_action"))
        return

    if youtube.is_youtube(url):
        if not db.has_yt_access(uid):
            await message.reply(t(uid, "no_yt_sub"))
            return
        remaining = db.yt_remaining(uid)
        if remaining <= 0:
            await message.reply(t(uid, "yt_quota_exceeded"))
            return
        reply = await message.reply(t(uid, "yt_extracting"), quote=True)
        state.spawn(_youtube_menu(client, uid, reply, url, remaining))
        return

    reply = await message.reply(t(uid, "extracting_link"), quote=True)
    state.spawn(_direct_link(client, uid, reply, url))


async def _direct_link(client, uid, reply, url):
    try:
        name, size, is_html = await net.probe(url)
    except UserError as e:
        await show(client, reply, e.text(uid))
        return
    if size > config.MAX_FILE_SIZE and not db.is_admin(uid):
        await show(client, reply, t(uid, "link_too_large"))
        return
    if is_html:
        await show(client, reply, t(uid, "no_direct_link"))
        return
    name = name or f"file_{int(time.time())}.dat"
    item = state.Item("url", url, name, size=size)
    await jobs.offer(client, uid, reply, item, t(uid, "file_name_prompt", name=plain(name)))


async def _youtube_menu(client, uid, reply, url, remaining):
    try:
        title, duration, formats = await youtube.fetch_info(url)
    except UserError as e:
        await show(client, reply, e.text(uid))
        return
    except Exception as e:
        log.exception("could not read video info for %s", url)
        await show(client, reply, t(uid, "error_generic", e=plain(clip(str(e) or type(e).__name__))))
        return

    sizes = youtube.sizes(formats, duration)
    unknown = t(uid, "unknown")
    has_4k = sizes["2160"] is not None

    def video(quality):
        size = youtube.format_size(sizes[quality], unknown)
        return Button(f"🎥 {quality}p ({size})", callback_data=f"ytqual_{quality}")

    size_4k = youtube.format_size(sizes["2160"], unknown) if has_4k else t(uid, "quality_not_available")
    audio = youtube.format_size(sizes["mp3"], unknown)
    keyboard = InlineKeyboardMarkup([
        [video("360"), video("480")],
        [video("720"), video("1080")],
        [Button(f"🎥 4K ({size_4k})", callback_data="ytqual_2160")],
        [Button(t(uid, "btn_audio_only", size=audio), callback_data="ytqual_mp3")],
    ])
    shown = await show(client, reply, t(uid, "yt_quality_prompt", title=inline(title), remaining=remaining),
                       keyboard)
    if shown is not None:
        item = state.Item("youtube", url, youtube.file_stem(title))
        state.selections[(uid, shown.id)] = state.Selection([item], needs_quality=True, has_4k=has_4k)


@app.on_callback_query(filters.regex(r"^ytqual_(360|480|720|1080|2160|mp3)$"))
@subscribers_only
async def choose_quality(client, query):
    uid = query.from_user.id
    message = query.message
    key = (message.chat.id, message.id)
    quality = query.data.split("_")[1]

    selection = state.selections.get(key)
    if selection is None or not selection.needs_quality:
        await ack(query)
        await edit(message, t(uid, "yt_request_expired"))
        return
    if quality == "2160" and not selection.has_4k:
        await ack(query, t(uid, "quality_not_available"), alert=True)
        return
    await ack(query)
    if db.yt_remaining(uid) <= 0:
        state.drop_selection(key)
        await edit(message, t(uid, "yt_quota_exceeded_cb"))
        return

    item = selection.items[0]
    item.quality = quality
    selection.needs_quality = False

    batch = state.batches.get(uid)
    if batch is not None:
        del state.selections[key]
        batch.items.append(item)
        await edit(message, t(uid, "file_added_multi", count=len(batch.items)), batch_keyboard(uid))
        return
    label = t(uid, "audio_only_label") if quality == "mp3" else f"{quality}p"
    await edit(message, t(uid, "yt_file_ready", name=plain(item.name), quality=label), action_keyboard(uid))
