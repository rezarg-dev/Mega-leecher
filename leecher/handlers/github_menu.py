"""The GitHub storage menu: connecting an account, usage and cleanup."""

import logging

import httpx
from pyrogram import filters
from pyrogram.types import ForceReply, InlineKeyboardButton as Button, InlineKeyboardMarkup

from .. import config, db, github, state
from ..client import app
from ..db import t
from ..errors import UserError
from ..ui import ack, button, edit, show
from ..utils import bar, clip, plain
from .common import subscribers_only

log = logging.getLogger(__name__)

GUIDE_PAGES = 4


@app.on_message(filters.private & button("btn_github"))
async def menu(client, message):
    uid = message.from_user.id
    if not db.has_access(uid):
        await message.reply(t(uid, "feature_needs_sub", purchase=config.PURCHASE_USERNAME))
        return
    account = db.gh_account(uid)
    if account:
        status = t(uid, "gh_connected", username=account["username"])
    else:
        status = t(uid, "gh_not_connected")
    rows = [
        [Button(t(uid, "gh_btn_guide"), callback_data="gh_guide")],
        [Button(t(uid, "gh_btn_token_change" if account else "gh_btn_token"), callback_data="gh_set_token")],
    ]
    if account:
        rows.append([Button(t(uid, "gh_btn_space"), callback_data="gh_space")])
        rows.append([Button(t(uid, "gh_btn_clear"), callback_data="gh_clear")])
    await message.reply(t(uid, "gh_menu_title", status=status), reply_markup=InlineKeyboardMarkup(rows))


def _guide_keyboard(uid, page):
    row = []
    if page > 1:
        row.append(Button(t(uid, "gh_guide_prev"), callback_data=f"gh_guide_p{page - 1}"))
    if page < GUIDE_PAGES:
        row.append(Button(t(uid, "gh_guide_next"), callback_data=f"gh_guide_p{page + 1}"))
    else:
        row.append(Button(t(uid, "gh_btn_token"), callback_data="gh_set_token"))
    counter = Button(t(uid, "gh_guide_page_num", page=page, total=GUIDE_PAGES), callback_data="noop")
    return InlineKeyboardMarkup([row, [counter]])


def _space_text(uid, account):
    repos = account.get("repos", [])
    usage = db.gh_usage(uid)
    lines = ""
    used = 0
    for repo in repos:
        size = usage.get(repo, 0)
        used += size
        lines += f"  📁 `{repo}`: {size / config.GB:.2f}GB [{bar(size / config.GITHUB_REPO_MAX * 100)}]\n"
    capacity = config.GITHUB_REPO_MAX * len(repos)
    percent = used / capacity * 100 if capacity else 0
    return t(uid, "gh_space_info",
             username=account["username"], repos_info=lines, bar=bar(percent), pct=percent,
             used=used / config.GB, free=(capacity - used) / config.GB, total=capacity / config.GB,
             quota=db.gh_remaining(uid), limit=config.GITHUB_DAILY_LIMIT)


async def _clear(uid, message, account):
    repos = account.get("repos", [])
    failure = None
    for i, repo in enumerate(repos, 1):
        await edit(message, t(uid, "gh_clear_repo", i=i, total=len(repos)))
        try:
            await github.clear(account, repo)
            db.gh_reset_usage(uid, [repo])
        except Exception as e:
            log.warning("clearing %s/%s failed: %s", account["username"], repo, e)
            failure = e
    if failure is None:
        await edit(message, t(uid, "gh_clear_done"))
    else:
        await edit(message, t(uid, "gh_clear_error", e=plain(clip(failure))))


@app.on_callback_query(filters.regex("^gh_"))
@subscribers_only
async def callback(client, query):
    await ack(query)
    uid = query.from_user.id
    message = query.message
    action = query.data

    if action == "gh_guide":
        await edit(message, t(uid, "gh_guide_page1"), _guide_keyboard(uid, 1))

    elif action.startswith("gh_guide_p"):
        page = action[len("gh_guide_p"):]
        if page.isdigit() and 1 <= int(page) <= GUIDE_PAGES:
            await edit(message, t(uid, f"gh_guide_page{int(page)}"), _guide_keyboard(uid, int(page)))

    elif action == "gh_set_token":
        state.prompts[uid] = state.Prompt("gh_token")
        await client.send_message(message.chat.id, t(uid, "gh_token_prompt"),
                                  reply_markup=ForceReply(selective=True))

    elif action == "gh_space":
        account = db.gh_account(uid)
        if not account:
            await edit(message, t(uid, "gh_no_token_menu"))
            return
        await edit(message, _space_text(uid, account))

    elif action == "gh_clear":
        await edit(message, t(uid, "gh_warn_clear"), InlineKeyboardMarkup([
            [Button(t(uid, "gh_btn_confirm_clear"), callback_data="gh_clear_ok")],
            [Button(t(uid, "gh_btn_cancel"), callback_data="gh_cancel")],
        ]))

    elif action == "gh_clear_ok":
        account = db.gh_account(uid)
        if not account:
            await edit(message, t(uid, "gh_no_token_menu"))
            return
        await edit(message, t(uid, "gh_clearing"))
        state.spawn(_clear(uid, message, account))

    elif action == "gh_cancel":
        await edit(message, t(uid, "gh_cancelled"))


async def on_token(client, message):
    """Called by the text router with the message that should contain the token."""
    uid = message.from_user.id
    token = message.text.strip()
    state.prompts.pop(uid, None)
    try:
        # A personal access token has no business staying in the chat history.
        await message.delete()
    except Exception:
        pass
    status = await client.send_message(message.chat.id, t(uid, "gh_verifying"))

    async def step(i):
        await edit(status, t(uid, "gh_creating_repo_i", username=username, i=i, total=config.GITHUB_MAX_REPOS))

    try:
        username = await github.validate_token(token)
        await edit(status, t(uid, "gh_creating_repos", username=username))
        repos = await github.ensure_repos(token, username, step)
    except UserError as e:
        await show(client, status, t(uid, "gh_invalid_token", err=e.text(uid)))
        return
    except (httpx.HTTPError, KeyError, ValueError) as e:
        await show(client, status, t(uid, "error_generic", e=plain(clip(str(e) or type(e).__name__))))
        return
    if not repos:
        await show(client, status, t(uid, "gh_repo_error"))
        return

    db.gh_connect(uid, token, username, repos)
    await show(client, status, t(uid, "gh_connect_success", username=username, repos=len(repos),
                                 cap=len(repos) * config.GITHUB_REPO_MAX // config.GB))
