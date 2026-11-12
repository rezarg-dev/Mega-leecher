"""In-memory state: files waiting for a decision, open prompts and running jobs."""

import asyncio
import itertools
import logging
import shutil
import time
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

SELECTION_TTL = 24 * 3600
PROMPT_TTL = 3600


@dataclass
class Item:
    """One thing to fetch: a Telegram file, a URL, a video link or a local path."""
    kind: str                   # media | url | youtube | instagram | local
    source: object
    name: str
    quality: str = None
    size: int = 0
    cleanup: str = None         # directory to delete once the item is done with


@dataclass
class Selection:
    """Files waiting for the user to choose what happens to them."""
    items: list
    action: str = None          # raw | full | split | multi | github | gdrive
    split_mb: int = None
    password: str = None
    needs_quality: bool = False
    has_4k: bool = False
    created: float = field(default_factory=time.time)


@dataclass
class Batch:
    """Files being collected for a multi-file archive."""
    key: tuple
    items: list
    created: float = field(default_factory=time.time)


@dataclass
class Prompt:
    """The bot asked something and the next text message is the answer."""
    kind: str                   # gh_token | gd_code | split | password | admin
    key: tuple = None
    step: str = None
    data: dict = field(default_factory=dict)
    created: float = field(default_factory=time.time)


class Job:
    _ids = itertools.count(1)

    def __init__(self, client, uid):
        self.id = next(Job._ids)
        self.client = client
        self.uid = uid
        self.cancel = asyncio.Event()
        self.status = None      # the message that shows progress
        self.workdir = None
        self.items = []
        jobs[self.id] = self

    @property
    def cancelled(self):
        return self.cancel.is_set()

    def close(self):
        jobs.pop(self.id, None)


selections = {}     # (chat id, message id) -> Selection
batches = {}        # chat id -> Batch
prompts = {}        # chat id -> Prompt
jobs = {}           # job id -> Job
_locks = {}
_tasks = set()


def user_lock(uid):
    lock = _locks.get(uid)
    if lock is None:
        lock = _locks[uid] = asyncio.Lock()
    return lock


def spawn(coro):
    """Run a coroutine in the background and keep it alive until it is done."""
    task = asyncio.ensure_future(coro)
    _tasks.add(task)
    task.add_done_callback(_finished)
    return task


def _finished(task):
    _tasks.discard(task)
    if not task.cancelled() and task.exception() is not None:
        log.error("background task failed", exc_info=task.exception())


async def shutdown():
    """Cancel everything still running, so no child process outlives the bot."""
    tasks = list(_tasks)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


def discard(items):
    for item in items:
        if item.cleanup:
            shutil.rmtree(item.cleanup, ignore_errors=True)


def drop_selection(key):
    selection = selections.pop(key, None)
    if selection is not None:
        discard(selection.items)


def drop_batch(chat_id):
    batch = batches.pop(chat_id, None)
    if batch is not None:
        discard(batch.items)


def busy_dirs():
    """Directories under temp/ that still belong to something alive."""
    dirs = set()
    for job in jobs.values():
        if job.workdir:
            dirs.add(job.workdir)
        dirs.update(item.cleanup for item in job.items if item.cleanup)
    for holder in list(selections.values()) + list(batches.values()):
        dirs.update(item.cleanup for item in holder.items if item.cleanup)
    return dirs


def purge():
    now = time.time()
    for key in [k for k, s in selections.items() if now - s.created > SELECTION_TTL]:
        drop_selection(key)
    for chat_id in [c for c, b in batches.items() if now - b.created > SELECTION_TTL]:
        drop_batch(chat_id)
    for chat_id in [c for c, p in prompts.items() if now - p.created > PROMPT_TTL]:
        del prompts[chat_id]


async def sweeper(interval=600):
    while True:
        await asyncio.sleep(interval)
        try:
            purge()
        except Exception:
            log.exception("state cleanup failed")
