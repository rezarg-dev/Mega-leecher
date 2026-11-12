"""JSON-backed storage: users, GitHub accounts and Google Drive accounts."""

import json
import logging
import os
import tempfile
import time

from . import config
from .lang import DEFAULT_LANG, LANGS, tr

log = logging.getLogger(__name__)


class JsonStore:
    """A dict persisted to a JSON file.

    The data is kept in memory. The file is read again only when something
    else (an editor, another script) has changed it behind our back.
    """

    def __init__(self, path):
        self.path = path
        self._data = {}
        self._mtime = None
        self._next_check = 0.0
        self._load()
        if self._mtime is None:
            self.save()

    def _stat(self):
        try:
            return os.stat(self.path).st_mtime_ns
        except OSError:
            return None

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("top-level value is not an object")
        except FileNotFoundError:
            data = {}
        except (ValueError, OSError) as e:
            # Never overwrite a file we could not parse: move it aside first.
            backup = f"{self.path}.broken-{int(time.time())}"
            log.error("%s is unreadable (%s), moved to %s", self.path, e, backup)
            try:
                os.replace(self.path, backup)
            except OSError:
                pass
            data = {}
        self._data = data
        self._mtime = self._stat()

    @property
    def data(self):
        now = time.monotonic()
        if now >= self._next_check:
            self._next_check = now + 1.0
            mtime = self._stat()
            if mtime is not None and mtime != self._mtime:
                self._load()
        return self._data

    def save(self):
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path), prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._data, f)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        self._mtime = self._stat()


users = JsonStore(config.USERS_DB)
github = JsonStore(config.GITHUB_DB)
drive = JsonStore(config.DRIVE_DB)


def is_admin(uid):
    return uid == config.ADMIN_ID


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _recent(history):
    now = time.time()
    if not isinstance(history, list):
        return []
    return [ts for ts in history if now - _number(ts) < config.DAY]


def days_left(expire):
    remaining = _number(expire) - time.time()
    return int(remaining // config.DAY) if remaining > 0 else 0


# ── Users ────────────────────────────────────────────────────

def _user(uid, create=False):
    data = users.data
    key = str(uid)
    entry = data.get(key)
    if isinstance(entry, dict):
        return entry
    if entry is not None:
        # Very old databases stored only the expiry timestamp.
        entry = data[key] = {"expire": _number(entry)}
        return entry
    if create:
        entry = data[key] = {"expire": 0, "lang": DEFAULT_LANG, "yt_history": []}
        return entry
    return None


def get_lang(uid):
    entry = _user(uid)
    lang = entry.get("lang") if entry else None
    return lang if lang in LANGS else DEFAULT_LANG


def set_lang(uid, lang):
    _user(uid, create=True)["lang"] = lang
    users.save()


def t(uid, key, /, **params):
    return tr(get_lang(uid), key, **params)


def has_access(uid):
    if is_admin(uid):
        return True
    entry = _user(uid)
    if not entry:
        return False
    now = time.time()
    return now < _number(entry.get("expire")) or now < _number(entry.get("yt_expire"))


def has_yt_access(uid):
    if is_admin(uid):
        return True
    entry = _user(uid)
    return bool(entry) and time.time() < _number(entry.get("yt_expire"))


def subscription(uid):
    """(is the user known, expiry timestamp of the main subscription)."""
    entry = _user(uid)
    if not entry:
        return False, 0.0
    return True, _number(entry.get("expire"))


def yt_remaining(uid):
    if is_admin(uid):
        return config.YT_DAILY_LIMIT
    entry = _user(uid)
    if not entry:
        return 0
    return max(0, config.YT_DAILY_LIMIT - len(_recent(entry.get("yt_history"))))


def record_yt(uid, count=1):
    if is_admin(uid):
        return
    entry = _user(uid)
    if not entry:
        return
    entry["yt_history"] = _recent(entry.get("yt_history")) + [time.time()] * count
    users.save()


def grant(target, days, username, youtube=False):
    field = "yt_expire" if youtube else "expire"
    expire = time.time() + days * config.DAY
    entry = _user(target)
    if entry is None:
        entry = users.data[str(target)] = {
            "expire": 0, "username": username, "yt_expire": 0, "lang": DEFAULT_LANG,
        }
    entry[field] = expire
    entry["username"] = username
    users.save()


def revoke(target):
    entry = _user(target)
    if entry is None:
        return False
    # The language choice survives so the user is not thrown back to Persian.
    users.data[str(target)] = {"expire": 0, "yt_expire": 0, "lang": entry.get("lang", DEFAULT_LANG)}
    users.save()
    return True


def active_users():
    now = time.time()
    result = []
    for uid, entry in users.data.items():
        if not isinstance(entry, dict):
            continue
        expire, yt_expire = _number(entry.get("expire")), _number(entry.get("yt_expire"))
        if expire > now or yt_expire > now:
            result.append({
                "uid": uid,
                "uname": entry.get("username"),
                "rd": days_left(expire),
                "ytd": days_left(yt_expire),
            })
    return result


def all_user_ids():
    return [int(uid) for uid in users.data if uid.lstrip("-").isdigit()]


# ── GitHub ───────────────────────────────────────────────────

def gh_account(uid):
    entry = github.data.get(str(uid))
    if isinstance(entry, dict) and entry.get("token"):
        return entry
    return None


def gh_connect(uid, token, username, repos):
    old = github.data.get(str(uid))
    old = old if isinstance(old, dict) else {}
    entry = {"token": token, "username": username, "repos": repos}
    history = _recent(old.get("gh_history"))
    if history:
        entry["gh_history"] = history
    # Same account, same repositories: what is stored there has not changed.
    if old.get("username") == username and isinstance(old.get("repo_sizes"), dict):
        entry["repo_sizes"] = {r: s for r, s in old["repo_sizes"].items() if r in repos}
    github.data[str(uid)] = entry
    github.save()


def gh_remaining(uid):
    if is_admin(uid):
        return config.GITHUB_DAILY_LIMIT
    entry = gh_account(uid)
    if not entry:
        return 0
    return max(0, config.GITHUB_DAILY_LIMIT - len(_recent(entry.get("gh_history"))))


def gh_record(uid):
    entry = gh_account(uid)
    if is_admin(uid) or not entry:
        return
    entry["gh_history"] = _recent(entry.get("gh_history")) + [time.time()]
    github.save()


def gh_usage(uid):
    entry = gh_account(uid)
    sizes = entry.get("repo_sizes") if entry else None
    return sizes if isinstance(sizes, dict) else {}


def gh_add_usage(uid, repo, nbytes):
    entry = gh_account(uid)
    if not entry:
        return
    sizes = entry.get("repo_sizes")
    if not isinstance(sizes, dict):
        sizes = entry["repo_sizes"] = {}
    sizes[repo] = _number(sizes.get(repo)) + nbytes
    github.save()


def gh_reset_usage(uid, repos):
    entry = gh_account(uid)
    if not entry:
        return
    sizes = entry.get("repo_sizes")
    if not isinstance(sizes, dict):
        sizes = entry["repo_sizes"] = {}
    for repo in repos:
        sizes[repo] = 0
    github.save()


def gh_pick_repo(uid, size):
    """First repository that still has room for `size` bytes."""
    entry = gh_account(uid)
    if not entry:
        return None
    usage = gh_usage(uid)
    for repo in entry.get("repos", []):
        if config.GITHUB_REPO_MAX - _number(usage.get(repo)) >= size:
            return repo
    return None


# ── Google Drive ─────────────────────────────────────────────

def gd_account(uid):
    entry = drive.data.get(str(uid))
    if isinstance(entry, dict) and entry.get("refresh_token"):
        return entry
    return None


def gd_connect(uid, access_token, refresh_token, expiry, folder_id):
    old = drive.data.get(str(uid))
    history = _recent(old.get("drive_history")) if isinstance(old, dict) else []
    drive.data[str(uid)] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expiry": expiry,
        "folder_id": folder_id,
        "drive_history": history,
    }
    drive.save()


def gd_update(uid, **fields):
    entry = gd_account(uid)
    if not entry:
        return
    entry.update(fields)
    drive.save()


def gd_disconnect(uid):
    key = str(uid)
    entry = drive.data.get(key)
    if entry is None:
        return
    # Keep today's upload count, otherwise reconnecting would reset the quota.
    history = _recent(entry.get("drive_history")) if isinstance(entry, dict) else []
    if history:
        drive.data[key] = {"drive_history": history}
    else:
        del drive.data[key]
    drive.save()


def gd_remaining(uid):
    if is_admin(uid):
        return config.DRIVE_DAILY_LIMIT
    entry = gd_account(uid)
    if not entry:
        return 0
    return max(0, config.DRIVE_DAILY_LIMIT - len(_recent(entry.get("drive_history"))))


def gd_record(uid):
    entry = gd_account(uid)
    if is_admin(uid) or not entry:
        return
    entry["drive_history"] = _recent(entry.get("drive_history")) + [time.time()]
    drive.save()
