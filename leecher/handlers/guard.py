import time

from pyrogram import filters

from .. import config, db, state
from ..client import app
from ..db import t
from ..ui import FREE_BUTTONS, MENU_BUTTONS

STARTED = time.time()


@app.on_message(filters.private & filters.incoming, group=-1)
async def guard(client, message):
    """Runs before every other handler: drops stale updates and enforces the subscription."""
    user = message.from_user
    if user is None:
        message.stop_propagation()
    # Whatever piled up while the bot was offline is not worth acting on.
    if message.date is not None and message.date.timestamp() < STARTED:
        message.stop_propagation()

    text = message.text or ""
    is_start = text.startswith("/start")
    if is_start or text in MENU_BUTTONS:
        # Going back to the menu abandons whatever question was still open.
        state.prompts.pop(user.id, None)
    if is_start or text in FREE_BUTTONS:
        return
    if not db.has_access(user.id):
        await message.reply(t(user.id, "no_subscription", purchase=config.PURCHASE_USERNAME, uid=user.id))
        message.stop_propagation()
