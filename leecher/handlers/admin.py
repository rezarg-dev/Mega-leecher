"""The admin panel: subscriptions, the user list and temp cleanup."""

import os
import time

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton as Button, InlineKeyboardMarkup, ReplyKeyboardMarkup

from .. import config, db, state
from ..client import app
from ..db import t
from ..lang import variants
from ..ui import ack, button, edit, reply_menu
from ..utils import inline, remove

USERS_PER_PAGE = 5
KEEP_RECENT = 600       # seconds; never clean up what a running task may have just created

admin_only = filters.private & filters.user(config.ADMIN_ID)

# button -> (flow, first question)
FLOWS = {
    "btn_add_user": ("add", "admin_ask_user_id"),
    "btn_add_yt_user": ("add_yt", "admin_ask_yt_id"),
    "btn_del_user": ("delete", "admin_ask_user_id"),
}
_FLOW_FOR = {label: flow for key, flow in FLOWS.items() for label in variants(key)}


def _cancel_menu(uid):
    return ReplyKeyboardMarkup([[t(uid, "admin_cancel")]], resize_keyboard=True)


# ── User list ────────────────────────────────────────────────

def _user_page(uid, users, page):
    pages = (len(users) + USERS_PER_PAGE - 1) // USERS_PER_PAGE
    page = max(0, min(page, pages - 1))
    first = page * USERS_PER_PAGE

    text = t(uid, "admin_user_list_title", page=page + 1, total_pages=pages, total=len(users))
    text += "━━━━━━━━━━━━━━━━━\n\n"
    for i, user in enumerate(users[first:first + USERS_PER_PAGE], first + 1):
        text += t(uid, "admin_user_entry", i=i, uname=inline(user["uname"] or t(uid, "unknown")),
                  uid=user["uid"], rd=user["rd"], ytd=user["ytd"])

    row = []
    if page > 0:
        row.append(Button(t(uid, "admin_btn_prev"), callback_data=f"ulist_{page - 1}"))
    if page < pages - 1:
        row.append(Button(t(uid, "admin_btn_next"), callback_data=f"ulist_{page + 1}"))
    return text, InlineKeyboardMarkup([row]) if row else None


@app.on_message(admin_only & button("btn_user_list"))
async def user_list(client, message):
    uid = message.from_user.id
    users = db.active_users()
    if not users:
        await message.reply(t(uid, "admin_no_users"))
        return
    text, markup = _user_page(uid, users, 0)
    await message.reply(text, reply_markup=markup)


@app.on_callback_query(filters.regex(r"^ulist_\d+$") & filters.user(config.ADMIN_ID))
async def user_list_page(client, query):
    await ack(query)
    if query.message is None:
        return
    uid = query.from_user.id
    users = db.active_users()
    if not users:
        await edit(query.message, t(uid, "admin_no_users"))
        return
    text, markup = _user_page(uid, users, int(query.data.split("_")[1]))
    await edit(query.message, text, markup)


# ── Add / remove users ───────────────────────────────────────

@app.on_message(admin_only & button(*FLOWS))
async def begin(client, message):
    uid = message.from_user.id
    flow, question = _FLOW_FOR[message.text]
    state.prompts[uid] = state.Prompt("admin", step="id", data={"flow": flow})
    await message.reply(t(uid, question), reply_markup=_cancel_menu(uid))


def _positive_int(text):
    try:
        value = int(text)
    except ValueError:
        return None
    return value if value > 0 else None


async def on_input(client, message, prompt):
    """Called by the text router while the admin is in the middle of a flow."""
    uid = message.from_user.id
    text = message.text.strip()
    flow = prompt.data["flow"]
    menu = reply_menu(uid)

    if text in variants("admin_cancel"):
        state.prompts.pop(uid, None)
        await message.reply(t(uid, "admin_cancelled"), reply_markup=menu)
        return
    prompt.created = time.time()

    if prompt.step == "id":
        target = _positive_int(text)
        if target is None:
            await message.reply(t(uid, "admin_invalid_number"))
            return
        if flow == "delete":
            state.prompts.pop(uid, None)
            result = "admin_deleted" if db.revoke(target) else "admin_not_found"
            await message.reply(t(uid, result), reply_markup=menu)
            return
        prompt.data["target"] = target
        prompt.step = "days"
        await message.reply(t(uid, "admin_ask_yt_days" if flow == "add_yt" else "admin_ask_days"))

    elif prompt.step == "days":
        days = _positive_int(text)
        if days is None:
            await message.reply(t(uid, "admin_invalid_number"))
            return
        prompt.data["days"] = days
        prompt.step = "username"
        await message.reply(t(uid, "admin_ask_username"))

    else:
        state.prompts.pop(uid, None)
        youtube = flow == "add_yt"
        days = prompt.data["days"]
        db.grant(prompt.data["target"], days, text, youtube=youtube)
        await message.reply(t(uid, "admin_yt_added" if youtube else "admin_added", days=days),
                            reply_markup=menu)


# ── Cleanup ──────────────────────────────────────────────────

@app.on_message(admin_only & button("btn_clean_bot"))
async def clean(client, message):
    uid = message.from_user.id
    busy = state.busy_dirs()
    now = time.time()
    for name in os.listdir(config.TEMP_DIR):
        path = os.path.join(config.TEMP_DIR, name)
        try:
            recent = now - os.path.getmtime(path) < KEEP_RECENT
        except OSError:
            continue
        if path not in busy and not recent:
            remove(path)
    await message.reply(t(uid, "admin_clean_done"), reply_markup=reply_menu(uid))
