"""What to do with a received file: the action menu, passwords, batches and cancelling."""

from pyrogram import filters
from pyrogram.types import ForceReply

from .. import config, jobs, state
from ..client import app
from ..db import t
from ..ui import ack, batch_keyboard, edit, password_keyboard, strip_buttons
from .common import subscribers_only

ARCHIVE_ACTIONS = ("full", "split", "multi")


@app.on_callback_query(filters.regex(r"^size_(raw|full|multi|split|github|gdrive)$"))
@subscribers_only
async def choose_action(client, query):
    await ack(query)
    uid = query.from_user.id
    message = query.message
    key = (message.chat.id, message.id)
    action = query.data.split("_")[1]

    selection = state.selections.get(key)
    if selection is None or selection.needs_quality:
        await edit(message, t(uid, "file_expired"))
        return

    if action in ("raw", "github", "gdrive"):
        del state.selections[key]
        selection.action = action
        await strip_buttons(message)
        jobs.submit(client, uid, selection)

    elif action == "full":
        selection.action = action
        await edit(message, t(uid, "ask_password"), password_keyboard(uid, message.id))

    elif action == "split":
        selection.action = action
        state.prompts[uid] = state.Prompt("split", key=key)
        await edit(message, t(uid, "ask_split_size"))

    else:
        del state.selections[key]
        batch = state.batches.get(uid)
        if batch is None:
            state.batches[uid] = state.Batch(key, selection.items)
            await edit(message, t(uid, "first_file_added"), batch_keyboard(uid, first=True))
        else:
            batch.items.extend(selection.items)
            await edit(message, t(uid, "file_added_multi", count=len(batch.items)), batch_keyboard(uid))


@app.on_callback_query(filters.regex("^multi_start$"))
@subscribers_only
async def start_batch(client, query):
    await ack(query)
    uid = query.from_user.id
    batch = state.batches.pop(uid, None)
    if batch is None:
        await edit(query.message, t(uid, "file_expired"))
        return
    state.selections[batch.key] = state.Selection(batch.items, action="multi")
    await edit(query.message, t(uid, "ask_password"), password_keyboard(uid, batch.key[1]))


@app.on_callback_query(filters.regex("^multi_cancel$"))
async def cancel_batch(client, query):
    await ack(query)
    uid = query.from_user.id
    state.drop_batch(uid)
    if query.message is not None:
        await edit(query.message, t(uid, "cancelled"))


@app.on_callback_query(filters.regex(r"^pass_(none|set)_\d+$"))
@subscribers_only
async def choose_password(client, query):
    await ack(query)
    uid = query.from_user.id
    message = query.message
    _, mode, message_id = query.data.split("_")
    key = (message.chat.id, int(message_id))

    selection = state.selections.get(key)
    if selection is None or selection.action not in ARCHIVE_ACTIONS:
        await edit(message, t(uid, "file_expired"))
        return

    if mode == "set":
        state.prompts[uid] = state.Prompt("password", key=key)
        await client.send_message(message.chat.id, t(uid, "set_password"),
                                  reply_markup=ForceReply(selective=True))
        return

    del state.selections[key]
    prompt = state.prompts.get(uid)
    if prompt is not None and prompt.key == key:
        del state.prompts[uid]
    await strip_buttons(message)
    jobs.submit(client, uid, selection)


async def on_split_size(client, message, prompt):
    """Called by the text router with the answer to "how big should each part be?"."""
    uid = message.from_user.id
    selection = state.selections.get(prompt.key)
    if selection is None:
        state.prompts.pop(uid, None)
        await message.reply(t(uid, "file_expired"))
        return
    try:
        size = int(message.text.strip())
    except ValueError:
        size = 0
    if not config.SPLIT_MIN_MB <= size <= config.SPLIT_MAX_MB:
        await message.reply(t(uid, "split_invalid"))
        return
    state.prompts.pop(uid, None)
    selection.split_mb = size
    await message.reply(t(uid, "split_ready", size=size) + "\n\n" + t(uid, "ask_password"),
                        reply_markup=password_keyboard(uid, prompt.key[1]))


async def on_password(client, message, prompt):
    uid = message.from_user.id
    state.prompts.pop(uid, None)
    selection = state.selections.pop(prompt.key, None)
    if selection is None:
        await message.reply(t(uid, "file_expired"))
        return
    selection.password = message.text
    jobs.submit(client, uid, selection)


@app.on_callback_query(filters.regex(r"^cancel_(\d+|task)$"))
async def cancel_job(client, query):
    uid = query.from_user.id
    job_id = query.data.split("_")[1]
    job = state.jobs.get(int(job_id)) if job_id.isdigit() else None
    # Buttons from before a restart point at jobs that no longer exist.
    if job is None or job.uid != uid:
        await ack(query)
        return
    job.cancel.set()
    await ack(query, t(uid, "cancel_requested"), alert=True)
