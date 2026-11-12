"""/start, language selection, the guide buttons and the subscription button."""

import time

from pyrogram import filters

from .. import config, db
from ..client import app
from ..db import t
from ..lang import LANGS, variants
from ..ui import ack, button, edit, language_keyboard, reply_menu

GUIDES = {
    "btn_direct_link": "guide_direct",
    "btn_torrent": "guide_torrent",
    "btn_tg_files": "guide_tg_files",
    "btn_youtube": "guide_youtube",
}
_GUIDE_FOR = {label: guide for key, guide in GUIDES.items() for label in variants(key)}


@app.on_message(filters.private & filters.command("start"))
async def start(client, message):
    await message.reply(t(message.from_user.id, "choose_language"), reply_markup=language_keyboard())


@app.on_message(filters.private & button("btn_language"))
async def change_language(client, message):
    await message.reply(t(message.from_user.id, "choose_language"), reply_markup=language_keyboard())


@app.on_callback_query(filters.regex(rf"^setlang_({'|'.join(LANGS)})$"))
async def set_language(client, query):
    await ack(query)
    uid = query.from_user.id
    lang = query.data.split("_")[1]
    db.set_lang(uid, lang)
    if query.message is None:
        return
    await edit(query.message, t(uid, f"lang_changed_{lang}"))
    await client.send_message(query.message.chat.id, t(uid, "welcome"), reply_markup=reply_menu(uid))


@app.on_message(filters.private & button(*GUIDES))
async def guide(client, message):
    await message.reply(t(message.from_user.id, _GUIDE_FOR[message.text]))


@app.on_message(filters.private & button("btn_purchase"))
async def purchase(client, message):
    uid = message.from_user.id
    known, expire = db.subscription(uid)
    contact = {"purchase": config.PURCHASE_USERNAME, "uid": uid}
    if not (known and db.has_access(uid)):
        text = t(uid, "sub_buy", **contact)
    elif expire > time.time():
        text = t(uid, "sub_active", days=db.days_left(expire))
    else:
        text = t(uid, "sub_renew", **contact)
    await message.reply(text)


@app.on_callback_query(filters.regex("^noop$"))
async def noop(client, query):
    await ack(query)
