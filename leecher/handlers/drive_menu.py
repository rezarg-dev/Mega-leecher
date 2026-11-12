"""The Google Drive menu: connecting an account, usage and cleanup."""

import logging
import os
import time

import httpx
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton as Button, InlineKeyboardMarkup

from .. import config, db, gdrive, state
from ..client import app
from ..db import t
from ..errors import UserError
from ..ui import ack, button, edit, show
from ..utils import bar, clip, plain
from .common import subscribers_only

log = logging.getLogger(__name__)


@app.on_message(filters.private & button("btn_drive"))
async def menu(client, message):
    uid = message.from_user.id
    if not db.has_access(uid):
        await message.reply(t(uid, "feature_needs_sub", purchase=config.PURCHASE_USERNAME))
        return
    connected = db.gd_account(uid) is not None
    rows = [
        [Button(t(uid, "gd_btn_guide"), callback_data="gd_guide")],
        [Button(t(uid, "gd_btn_dl_guide"), callback_data="gd_dl_guide")],
        [Button(t(uid, "gd_btn_connect"), callback_data="gd_connect")],
    ]
    if connected:
        rows.append([Button(t(uid, "gd_btn_space"), callback_data="gd_space")])
        rows.append([Button(t(uid, "gd_btn_clear"), callback_data="gd_clear")])
        rows.append([Button(t(uid, "gd_btn_disconnect"), callback_data="gd_disconnect")])
    status = t(uid, "gd_connected" if connected else "gd_not_connected")
    await message.reply(t(uid, "gd_menu_title", status=status), reply_markup=InlineKeyboardMarkup(rows))


async def _show_space(uid, message):
    await edit(message, t(uid, "gd_checking_space"))
    token = await gdrive.access_token(uid)
    if not token:
        await edit(message, t(uid, "gd_auth_error"))
        return
    used, total, free = await gdrive.space(token)
    percent = used / total * 100 if total else 0
    await edit(message, t(uid, "gd_space_info", bar=bar(percent), pct=percent,
                          used=used / config.GB, free=free / config.GB, total=total / config.GB,
                          quota=db.gd_remaining(uid), limit=config.DRIVE_DAILY_LIMIT))


async def _clear(uid, message):
    token = await gdrive.access_token(uid)
    if not token:
        await edit(message, t(uid, "gd_auth_error_short"))
        return
    folder = db.gd_account(uid).get("folder_id")
    if not folder:
        await edit(message, t(uid, "gd_no_folder"))
        return
    await edit(message, t(uid, "gd_clearing"))
    last = 0.0

    async def report(deleted):
        nonlocal last
        if time.monotonic() - last >= 3:
            last = time.monotonic()
            await edit(message, t(uid, "gd_clearing_file", deleted=deleted))

    count = await gdrive.clear(token, folder, report)
    await edit(message, t(uid, "gd_clear_done", count=count))


async def _guarded(uid, message, work, error_key):
    """Run a Drive operation in the background and report a failure in the menu message."""
    try:
        await work
    except Exception as e:
        log.warning("drive operation failed for %s: %s", uid, e)
        await edit(message, t(uid, error_key, e=plain(clip(str(e) or type(e).__name__))))


@app.on_callback_query(filters.regex("^gd_"))
@subscribers_only
async def callback(client, query):
    await ack(query)
    uid = query.from_user.id
    message = query.message
    action = query.data

    if action == "gd_guide":
        await edit(message, t(uid, "gd_guide_text"), InlineKeyboardMarkup([
            [Button(t(uid, "gd_btn_connect"), callback_data="gd_connect")],
        ]))

    elif action == "gd_dl_guide":
        await client.send_message(message.chat.id, t(uid, "gd_dl_guide_text"))
        if os.path.isfile(config.DRIVE_APK):
            await client.send_document(message.chat.id, config.DRIVE_APK, caption=t(uid, "mitm_caption"))

    elif action == "gd_connect":
        if not gdrive.is_configured():
            await edit(message, t(uid, "gd_oauth_not_configured"))
            return
        state.prompts[uid] = state.Prompt("gd_code")
        await client.send_message(
            message.chat.id, t(uid, "gd_connect_url", url=gdrive.auth_url()),
            reply_markup=InlineKeyboardMarkup([
                [Button(t(uid, "gd_btn_cancel_connect"), callback_data="gd_cancel_connect")],
            ]))

    elif action == "gd_cancel_connect":
        prompt = state.prompts.get(uid)
        if prompt is not None and prompt.kind == "gd_code":
            del state.prompts[uid]
        await edit(message, t(uid, "gd_cancelled"))

    elif action == "gd_space":
        if not db.gd_account(uid):
            await edit(message, t(uid, "gd_no_account"))
            return
        state.spawn(_guarded(uid, message, _show_space(uid, message), "gd_clear_error"))

    elif action == "gd_clear":
        await edit(message, t(uid, "gd_warn_clear"), InlineKeyboardMarkup([
            [Button(t(uid, "gd_btn_confirm_clear"), callback_data="gd_clear_ok")],
            [Button(t(uid, "gh_btn_cancel"), callback_data="gd_cancel")],
        ]))

    elif action == "gd_clear_ok":
        if not db.gd_account(uid):
            await edit(message, t(uid, "gd_no_account_short"))
            return
        state.spawn(_guarded(uid, message, _clear(uid, message), "gd_clear_error"))

    elif action == "gd_disconnect":
        db.gd_disconnect(uid)
        await edit(message, t(uid, "gd_disconnected"))

    elif action == "gd_cancel":
        await edit(message, t(uid, "gd_cancelled_short"))


async def on_code(client, message):
    """Called by the text router with the message that should contain the OAuth code."""
    uid = message.from_user.id
    state.prompts.pop(uid, None)
    code = gdrive.extract_code(message.text)
    status = await message.reply(t(uid, "gd_verifying"))
    try:
        access, refresh, expiry = await gdrive.exchange_code(code)
        if not access or not refresh:
            await show(client, status, t(uid, "gd_invalid_code"))
            return
        await edit(status, t(uid, "gd_creating_folder"))
        folder = await gdrive.ensure_folder(access)
    except UserError as e:
        await show(client, status, t(uid, "gd_code_error", e=plain(e.text(uid))))
        return
    except (httpx.HTTPError, KeyError, ValueError) as e:
        await show(client, status, t(uid, "gd_code_error", e=plain(clip(str(e) or type(e).__name__))))
        return
    db.gd_connect(uid, access, refresh, expiry, folder)
    await show(client, status, t(uid, "gd_connect_success"))
