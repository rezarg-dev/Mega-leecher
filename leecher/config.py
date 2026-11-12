"""Settings read from config.env, plus the limits shared across the bot."""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# In a container the data lives in a mounted volume, away from the code.
DATA_DIR = os.environ.get("MEGA_LEECHER_DATA") or BASE_DIR
CONFIG_FILE = os.environ.get("MEGA_LEECHER_CONFIG") or os.path.join(DATA_DIR, "config.env")
os.makedirs(DATA_DIR, exist_ok=True)


def _fail(message):
    print(f"[ERROR] {message}", file=sys.stderr)
    sys.exit(1)


def _read_env(path):
    values = {}
    if not os.path.isfile(path):
        return values
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[key.strip()] = value
    return values


_cfg = _read_env(CONFIG_FILE)


def _get(key):
    """Environment variables win over config.env."""
    return os.environ.get(key) or _cfg.get(key, "")


def _required(key):
    value = _get(key)
    if not value or value.endswith("_here"):
        _fail(f"'{key}' is not set. Put it in config.env or pass it as an environment variable.")
    return value


def _required_int(key):
    value = _required(key)
    try:
        return int(value)
    except ValueError:
        _fail(f"'{key}' must be a number.")


def _optional_int(key, default, minimum=1):
    value = _get(key)
    if not value:
        return default
    try:
        return max(minimum, int(value))
    except ValueError:
        _fail(f"'{key}' must be a number.")


# Telegram
API_ID = _required_int("API_ID")
API_HASH = _required("API_HASH")
BOT_TOKEN = _required("BOT_TOKEN")
ADMIN_ID = _required_int("ADMIN_ID")
PURCHASE_USERNAME = _required("PURCHASE_USERNAME")

# Google Drive (optional)
GOOGLE_CLIENT_ID = _get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = _get("GOOGLE_CLIENT_SECRET")

# How many jobs of regular users may run at the same time.
MAX_CONCURRENT_JOBS = _optional_int("MAX_CONCURRENT_JOBS", 4)

# Paths
TEMP_DIR = os.path.join(DATA_DIR, "temp")
USERS_DB = os.path.join(DATA_DIR, "users_db.json")
GITHUB_DB = os.path.join(DATA_DIR, "github_db.json")
DRIVE_DB = os.path.join(DATA_DIR, "drive_db.json")
COOKIES_FILE = os.path.join(DATA_DIR, "cookies.txt")
DRIVE_APK = os.path.join(DATA_DIR, "MITM.Drive.Downloader.v1-android.apk")

# Limits
MB = 1024 * 1024
GB = 1024 * MB
DAY = 86400

MAX_FILE_SIZE = 2 * GB            # per file, for everyone except the admin
TG_UPLOAD_LIMIT = 2000 * MB       # Telegram refuses anything bigger from a bot

SPLIT_MIN_MB = 19
SPLIT_MAX_MB = 900

YT_DAILY_LIMIT = 10
GITHUB_DAILY_LIMIT = 10
DRIVE_DAILY_LIMIT = 10

GITHUB_CHUNK_SIZE = 95 * MB       # GitHub rejects files over 100 MB
GITHUB_REPO_MAX = 5 * GB
GITHUB_MAX_REPOS = 3
