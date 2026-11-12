"""Keyboards, message helpers and the progress display."""

import asyncio
import logging
import time

from pyrogram import filters
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.types import (
    InlineKeyboardButton as Button,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from . import config, db
from .db import t
from .lang import variants
from .utils import bar

log = logging.getLogger(__name__)

# Menu buttons that work without a subscription.
FREE_KEYS = (
    "btn_direct_link", "btn_torrent", "btn_tg_files", "btn_youtube",
    "btn_purchase", "btn_github", "btn_drive", "btn_language",
)
ADMIN_KEYS = ("btn_add_user", "btn_del_user", "btn_add_yt_user", "btn_user_list", "btn_clean_bot")


def labels(*keys):
    found = set()
    for key in keys:
        found |= variants(key)
    return found


FREE_BUTTONS = labels(*FREE_KEYS)
MENU_BUTTONS = FREE_BUTTONS | labels(*ADMIN_KEYS)


def button(*keys):
    """Filter: the message is one of these menu buttons, in any language."""
    wanted = labels(*keys)
    return filters.create(lambda _, __, message: bool(message.text) and message.text in wanted)


menu_button = filters.create(lambda _, __, message: bool(message.text) and message.text in MENU_BUTTONS)


# ── Keyboards ────────────────────────────────────────────────

def language_keyboard():
    return InlineKeyboardMarkup([[
        Button("🇮🇷 Persian (فارسی)", callback_data="setlang_fa"),
        Button("🇺🇸 English", callback_data="setlang_en"),
    ]])


def cancel_keyboard(uid, job_id):
    return InlineKeyboardMarkup([[Button(t(uid, "btn_cancel_op"), callback_data=f"cancel_{job_id}")]])


def action_keyboard(uid):
    rows = [
        [Button(t(uid, "btn_raw"), callback_data="size_raw")],
        [Button(t(uid, "btn_full_rar"), callback_data="size_full")],
        [Button(t(uid, "btn_multi_rar"), callback_data="size_multi")],
        [Button(t(uid, "btn_split"), callback_data="size_split")],
    ]
    if db.gh_account(uid):
        rows.append([Button(t(uid, "btn_github_upload"), callback_data="size_github")])
    if db.gd_account(uid):
        rows.append([Button(t(uid, "btn_drive_upload"), callback_data="size_gdrive")])
    return InlineKeyboardMarkup(rows)


def password_keyboard(uid, message_id):
    return InlineKeyboardMarkup([
        [Button(t(uid, "btn_no_pass"), callback_data=f"pass_none_{message_id}")],
        [Button(t(uid, "btn_set_pass"), callback_data=f"pass_set_{message_id}")],
    ])


def batch_keyboard(uid, first=False):
    start = "btn_start_archive" if first else "btn_start_op"
    return InlineKeyboardMarkup([
        [Button(t(uid, start), callback_data="multi_start")],
        [Button(t(uid, "btn_cancel_op"), callback_data="multi_cancel")],
    ])


def reply_menu(uid):
    rows = [
        [KeyboardButton(t(uid, "btn_direct_link")), KeyboardButton(t(uid, "btn_torrent"))],
        [KeyboardButton(t(uid, "btn_tg_files")), KeyboardButton(t(uid, "btn_youtube"))],
        [KeyboardButton(t(uid, "btn_github")), KeyboardButton(t(uid, "btn_drive"))],
    ]
    if db.is_admin(uid):
        rows += [
            [KeyboardButton(t(uid, "btn_add_user")), KeyboardButton(t(uid, "btn_del_user"))],
            [KeyboardButton(t(uid, "btn_add_yt_user")), KeyboardButton(t(uid, "btn_user_list"))],
            [KeyboardButton(t(uid, "btn_clean_bot"))],
        ]
    else:
        rows.append([KeyboardButton(t(uid, "btn_purchase"))])
    rows.append([KeyboardButton(t(uid, "btn_language"))])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, placeholder=t(uid, "menu_placeholder"))


# ── Messages ─────────────────────────────────────────────────

async def edit(message, text, markup=None):
    """Best-effort edit, used for progress updates. Never raises."""
    try:
        await message.edit_text(text, reply_markup=markup)
        return True
    except MessageNotModified:
        return True
    except FloodWait:
        return False
    except Exception as e:
        log.debug("edit failed: %s", e)
        return False


async def show(client, message, text, markup=None):
    """Edit a message with something the user must see; send it anew if editing fails.

    Returns the message that now carries the text, or None if nothing got through.
    """
    for _ in range(2):
        try:
            await message.edit_text(text, reply_markup=markup)
            return message
        except MessageNotModified:
            return message
        except FloodWait as e:
            await asyncio.sleep(min(e.value, 60) + 1)
        except Exception:
            break
    try:
        return await client.send_message(message.chat.id, text, reply_markup=markup)
    except Exception as e:
        log.warning("could not deliver a message to %s: %s", message.chat.id, e)
        return None


async def ack(query, text=None, alert=False):
    try:
        await query.answer(text, show_alert=alert)
    except Exception:
        pass


async def strip_buttons(message):
    try:
        await message.edit_reply_markup(None)
    except Exception:
        pass


# ── Progress ─────────────────────────────────────────────────

class Progress:
    """Throttled progress display on a job's status message."""

    INTERVAL = 5

    def __init__(self, job, label, telegram=False):
        self.job = job
        self.label = label
        self.telegram = telegram
        self.started = time.monotonic()
        self.last = self.started - self.INTERVAL

    async def update(self, current, total):
        job = self.job
        if self.telegram and job.cancelled:
            # The only way to abort a transfer that Pyrogram is running.
            job.client.stop_transmission()
        now = time.monotonic()
        if now - self.last < self.INTERVAL and current != total:
            return
        self.last = now
        elapsed = now - self.started
        if elapsed <= 0:
            return
        uid = job.uid
        if total:
            percent = current * 100 / total
            text = t(uid, "progress", action=self.label, bar=bar(percent), pct=percent,
                     speed=current / elapsed / 1024,
                     cur=current / config.MB, total=total / config.MB)
        else:
            text = t(uid, "progress_unknown_size", action=self.label, cur=current / config.MB)
        await edit(job.status, text, cancel_keyboard(uid, job.id))
