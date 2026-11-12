import asyncio
import logging
import os

from pyrogram import idle

from . import config, state
from . import handlers  # noqa: F401  (importing registers the handlers)
from .client import app
from .utils import remove

log = logging.getLogger("leecher")


def _empty_temp():
    """Nothing in temp/ survives a restart: the state that referred to it is gone."""
    os.makedirs(config.TEMP_DIR, exist_ok=True)
    for name in os.listdir(config.TEMP_DIR):
        remove(os.path.join(config.TEMP_DIR, name))


async def _serve():
    await app.start()
    log.info("running as @%s", app.me.username)
    sweeper = asyncio.ensure_future(state.sweeper())
    try:
        await idle()
    finally:
        sweeper.cancel()
        await state.shutdown()
        await app.stop()


def run():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("pyrogram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    _empty_temp()
    app.run(_serve())
