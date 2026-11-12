"""Routes plain text: answers to open prompts first, then links."""

import re

from pyrogram import filters

from .. import db, state
from ..client import app
from ..ui import menu_button
from . import actions, admin, drive_menu, files, github_menu

LINK = re.compile(r"(https?://|magnet:\?xt=urn:btih:)\S+", re.IGNORECASE)


def _link(text):
    match = LINK.match(text)
    return match.group(0) if match else None


@app.on_message(filters.private & filters.text & ~filters.command("start") & ~menu_button)
async def on_text(client, message):
    uid = message.from_user.id
    text = message.text.strip()
    link = _link(text)
    prompt = state.prompts.get(uid)

    if prompt is not None:
        if prompt.kind == "admin" and db.is_admin(uid):
            await admin.on_input(client, message, prompt)
            return
        if prompt.kind == "gh_token":
            await github_menu.on_token(client, message)
            return
        if prompt.kind == "gd_code":
            await drive_menu.on_code(client, message)
            return
        # A link sent while we wait for a number or a password is a new file,
        # unless the user explicitly replied to the question with it.
        if link is None or message.reply_to_message is not None:
            if prompt.kind == "split":
                await actions.on_split_size(client, message, prompt)
            else:
                await actions.on_password(client, message, prompt)
            return

    if link is not None:
        await files.on_link(client, message, link)
