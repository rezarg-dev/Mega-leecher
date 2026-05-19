import os
import asyncio
import time
import aiohttp
import urllib.parse
import shutil
import json
import re
import base64
import httpx
import yt_dlp
import libtorrent as lt
from datetime import datetime, timezone
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply, ReplyKeyboardMarkup, KeyboardButton
from pyrogram.errors import FloodWait

# --- تنظیمات اصلی (از config.env خوانده می‌شوند) ---
from config import (
    API_ID, API_HASH, BOT_TOKEN, ADMIN_ID, PURCHASE_USERNAME,
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, INSTALL_DIR
)

# ── Constants ─────────────────────────────────────────────────────────────────
DB_FILE            = "users_db.json"
GITHUB_DB_FILE     = "github_db.json"
DRIVE_DB_FILE      = "drive_db.json"
COOKIES_FILE       = "cookies.txt"

MAX_SIZE_LIMIT     = 2 * 1024 * 1024 * 1024          # 2 GB
YT_DAILY_LIMIT     = 10
GITHUB_DAILY_LIMIT = 10
DRIVE_DAILY_LIMIT  = 10

GITHUB_CHUNK_SIZE  = 95 * 1024 * 1024                # 95 MB per chunk
GITHUB_REPO_MAX    = 5  * 1024 * 1024 * 1024         # 5 GB per repo
GITHUB_MAX_REPOS   = 3

TEMP_DIR = os.path.join(INSTALL_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://google.com/"
}

# ── Pyrogram client ───────────────────────────────────────────────────────────
app = Client("mega_leecher", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ── Semaphores & global state ─────────────────────────────────────────────────
GITHUB_GLOBAL_SEM = asyncio.Semaphore(4)
DRIVE_GLOBAL_SEM  = asyncio.Semaphore(4)

BOT_START_TIME     = time.time()
BOT_START_DATETIME = datetime.now(timezone.utc)

user_states      = {}
user_multi_tasks = {}
last_update_time = {}
cancel_flags     = {}
user_semaphores  = {}

# ── Database helpers ──────────────────────────────────────────────────────────
def load_users():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_users(d):
    with open(DB_FILE, 'w') as f: json.dump(d, f)

def load_github_db():
    if os.path.exists(GITHUB_DB_FILE):
        with open(GITHUB_DB_FILE, 'r') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_github_db(d):
    with open(GITHUB_DB_FILE, 'w') as f: json.dump(d, f)

def load_drive_db():
    if os.path.exists(DRIVE_DB_FILE):
        with open(DRIVE_DB_FILE, 'r') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_drive_db(d):
    with open(DRIVE_DB_FILE, 'w') as f: json.dump(d, f)

# ── Auto-create databases on first run ────────────────────────────────────────
def init_databases():
    for db_file in [DB_FILE, GITHUB_DB_FILE, DRIVE_DB_FILE]:
        if not os.path.exists(db_file):
            with open(db_file, 'w') as f:
                json.dump({}, f)

init_databases()

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run()
