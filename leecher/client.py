from pyrogram import Client, enums

from . import config

app = Client(
    "mega_leecher",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    workdir=config.DATA_DIR,
    # Plain Markdown: file names and titles must never be parsed as HTML.
    parse_mode=enums.ParseMode.MARKDOWN,
)
