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
# --- Main settings (loaded from config.env) ---
from config import (
    API_ID, API_HASH, BOT_TOKEN, ADMIN_ID, PURCHASE_USERNAME,
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, INSTALL_DIR
)
from lang import STRINGS, T as _T
DB_FILE = "users_db.json"
GITHUB_DB_FILE = "github_db.json"
COOKIES_FILE = "cookies.txt"
MAX_SIZE_LIMIT = 2 * 1024 * 1024 * 1024
YT_DAILY_LIMIT = 10
GITHUB_CHUNK_SIZE = 95 * 1024 * 1024   # 95MB — امن با git push (بدون base64)
GITHUB_REPO_MAX = 5 * 1024 * 1024 * 1024  # 5GB per repo
GITHUB_MAX_REPOS = 3

# ===== گوگل درایو =====
DRIVE_DB_FILE = "drive_db.json"
DRIVE_DAILY_LIMIT = 10
DRIVE_GLOBAL_SEM = asyncio.Semaphore(4)

TEMP_DIR = os.path.join(INSTALL_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# مسیر کامل yt-dlp در venv / Full path to yt-dlp in venv
YT_DLP = os.path.join(INSTALL_DIR, "venv", "bin", "yt-dlp")
DENO_PATH = os.path.expanduser("~/.deno/bin/deno")
YT_JS_RUNTIME = ["--js-runtimes", f"deno:{DENO_PATH}"] if os.path.exists(os.path.expanduser("~/.deno/bin/deno")) else []

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://google.com/"
}

app = Client("my_bot_pro", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
GITHUB_GLOBAL_SEM = asyncio.Semaphore(4)  # حداکثر ۴ آپلود گیتهاب همزمان در کل سرور
BOT_START_TIME = time.time()
BOT_START_DATETIME = datetime.now(timezone.utc)
user_states = {}
user_multi_tasks = {}
last_update_time = {}
cancel_flags = {}
user_semaphores = {}

# ================= دیتابیس کاربران =================
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

# ===== دیتابیس گوگل درایو =====
def load_drive_db():
    if os.path.exists(DRIVE_DB_FILE):
        with open(DRIVE_DB_FILE, 'r') as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_drive_db(d):
    with open(DRIVE_DB_FILE, 'w') as f: json.dump(d, f)

def init_databases():
    for db_file in [DB_FILE, GITHUB_DB_FILE, DRIVE_DB_FILE]:
        if not os.path.exists(db_file):
            with open(db_file, 'w') as f:
                json.dump({}, f)

init_databases()

# ================= مدیریت زبان / Language Management =================
def get_user_lang(user_id):
    # دریافت زبان کاربر از دیتابیس / Get user language from database
    users = load_users(); uid = str(user_id)
    d = users.get(uid, {})
    return d.get("lang", "fa") if isinstance(d, dict) else "fa"

def set_user_lang(user_id, lang):
    # ذخیره زبان کاربر در دیتابیس / Save user language to database
    users = load_users(); uid = str(user_id)
    if uid not in users: users[uid] = {"expire": 0, "lang": lang, "yt_history": []}
    elif isinstance(users[uid], dict): users[uid]["lang"] = lang
    save_users(users)

def T(user_id, key, **kwargs):
    # ترجمه رشته بر اساس زبان کاربر / Translate string based on user language
    return _T(get_user_lang(user_id), key, **kwargs)

def has_drive_connected(user_id):
    return str(user_id) in load_drive_db()

def check_drive_quota(user_id):
    if user_id == ADMIN_ID: return True, DRIVE_DAILY_LIMIT
    db = load_drive_db(); uid = str(user_id)
    if uid not in db: return False, 0
    now = time.time()
    history = [t for t in db[uid].get("drive_history", []) if now - t < 86400]
    return DRIVE_DAILY_LIMIT - len(history) > 0, DRIVE_DAILY_LIMIT - len(history)

def record_drive_upload(user_id):
    if user_id == ADMIN_ID: return
    db = load_drive_db(); uid = str(user_id)
    if uid not in db: return
    now = time.time()
    history = [t for t in db[uid].get("drive_history", []) if now - t < 86400]
    history.append(now)
    db[uid]["drive_history"] = history
    save_drive_db(db)

def get_drive_auth_url():
    params = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": "http://localhost",
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive.file",
        "access_type": "offline",
        "prompt": "consent"
    })
    return f"https://accounts.google.com/o/oauth2/auth?{params}"

async def exchange_drive_code(code):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post("https://oauth2.googleapis.com/token", data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code.strip(),
            "redirect_uri": "http://localhost",
            "grant_type": "authorization_code"
        })
        if r.status_code == 200:
            d = r.json()
            return d.get("access_token"), d.get("refresh_token"), time.time() + d.get("expires_in", 3600)
        raise Exception(f"کد نامعتبر است ({r.status_code}): {r.text[:100]}")

async def get_valid_drive_token(user_id):
    db = load_drive_db(); uid = str(user_id)
    if uid not in db: return None
    d = db[uid]
    if d.get("token_expiry", 0) - time.time() > 60:
        return d["access_token"]
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post("https://oauth2.googleapis.com/token", data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": d["refresh_token"],
            "grant_type": "refresh_token"
        })
        if r.status_code == 200:
            data = r.json()
            d["access_token"] = data["access_token"]
            d["token_expiry"] = time.time() + data.get("expires_in", 3600)
            db[uid] = d; save_drive_db(db)
            return d["access_token"]
    return None

async def drive_get_or_create_folder(token, name="Telegram Bot Uploads"):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get("https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                    "fields": "files(id)"})
        if r.status_code == 200 and r.json().get("files"):
            return r.json()["files"][0]["id"]
        r = await c.post("https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"name": name, "mimeType": "application/vnd.google-apps.folder"})
        if r.status_code == 200:
            return r.json()["id"]
        raise Exception(f"خطا در ساخت پوشه: {r.status_code}")

async def drive_upload_file_stream(token, file_path, file_name, folder_id, status_msg, chat_id):
    file_size = os.path.getsize(file_path)
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                     "X-Upload-Content-Type": "application/octet-stream",
                     "X-Upload-Content-Length": str(file_size)},
            json={"name": file_name, "parents": [folder_id]})
        if r.status_code != 200:
            raise Exception(T(chat_id,"gd_upload_start_error",code=r.status_code))
        upload_url = r.headers["Location"]
    last_t = [time.time()]; sent = [0]
    async def file_iter():
        with open(file_path, 'rb') as f:
            while True:
                if cancel_flags.get(chat_id): return
                chunk = f.read(512 * 1024)
                if not chunk: break
                sent[0] += len(chunk)
                now = time.time()
                if now - last_t[0] >= 5:
                    last_t[0] = now
                    pct = sent[0] * 100 // file_size
                    bar = "■"*(pct//10) + "□"*(10-pct//10)
                    await safe_edit(status_msg,
                        T(chat_id,"gd_uploading",bar=bar,pct=pct,sent=sent[0]/(1024*1024),total=file_size/(1024*1024)),
                        reply_markup=get_cancel_keyboard(status_msg.chat.id))
                yield chunk
    async with httpx.AsyncClient(timeout=3600) as c:
        r = await c.put(upload_url, content=file_iter(),
            headers={"Content-Length": str(file_size), "Content-Type": "application/octet-stream"})
        if r.status_code not in (200, 201):
            raise Exception(T(chat_id,"gd_upload_fail",code=r.status_code))
        file_id = r.json()["id"]
        await c.post(f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"role": "reader", "type": "anyone"})
    return file_id, f"https://drive.google.com/file/d/{file_id}/view?usp=sharing", \
           f"https://drive.google.com/uc?id={file_id}&export=download"

async def drive_get_space(token):
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get("https://www.googleapis.com/drive/v3/about",
            headers={"Authorization": f"Bearer {token}"},
            params={"fields": "storageQuota"})
        if r.status_code == 200:
            q = r.json()["storageQuota"]
            total = int(q.get("limit", 0)); used = int(q.get("usage", 0))
            return used, total, total - used
    return 0, 0, 0

async def drive_list_files(token, folder_id):
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get("https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": f"'{folder_id}' in parents and trashed=false", "fields": "files(id,name,size)"})
        if r.status_code == 200: return r.json().get("files", [])
    return []

async def drive_clear_all_files(token, folder_id, status_msg):
    files = await drive_list_files(token, folder_id)
    deleted = 0
    async with httpx.AsyncClient(timeout=30) as c:
        for f in files:
            r = await c.delete(f"https://www.googleapis.com/drive/v3/files/{f['id']}",
                headers={"Authorization": f"Bearer {token}"})
            if r.status_code == 204:
                deleted += 1
                await safe_edit(status_msg, T(status_msg.chat.id,"gd_clearing_file",deleted=deleted))
    return deleted

# ================= توابع دسترسی =================
def has_access(user_id):
    if user_id == ADMIN_ID: return True
    users = load_users(); uid = str(user_id)
    if uid in users:
        d = users[uid]
        if isinstance(d, dict):
            if time.time() < d.get("expire", 0) or time.time() < d.get("yt_expire", 0): return True
        else:
            if time.time() < d: return True
    return False

def has_yt_access(user_id):
    if user_id == ADMIN_ID: return True
    users = load_users(); uid = str(user_id)
    if uid in users:
        d = users[uid]
        if isinstance(d, dict) and time.time() < d.get("yt_expire", 0): return True
    return False

def has_github_token(user_id):
    return str(user_id) in load_github_db()

def check_size_limit(size, user_id):
    if user_id == ADMIN_ID: return True
    return size <= MAX_SIZE_LIMIT

def get_user_sem(user_id):
    if user_id not in user_semaphores: user_semaphores[user_id] = asyncio.Semaphore(1)
    return user_semaphores[user_id]

# ================= سهمیه یوتوب =================
def check_yt_quota(user_id):
    if user_id == ADMIN_ID: return True, YT_DAILY_LIMIT
    users = load_users(); uid = str(user_id)
    if uid not in users: return False, 0
    now = time.time()
    history = [t for t in users[uid].get("yt_history", []) if now - t < 86400]
    return YT_DAILY_LIMIT - len(history) > 0, YT_DAILY_LIMIT - len(history)

def record_yt_download(user_id):
    if user_id == ADMIN_ID: return
    users = load_users(); uid = str(user_id)
    if uid not in users: return
    now = time.time()
    history = [t for t in users[uid].get("yt_history", []) if now - t < 86400]
    history.append(now)
    users[uid]["yt_history"] = history
    save_users(users)

# ================= توابع گیتهاب =================
GH_HEADERS = lambda token: {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

async def gh_validate_token(token):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get("https://api.github.com/user", headers=GH_HEADERS(token))
        if r.status_code == 200: return r.json()["login"], None
        return None, f"توکن نامعتبر است (کد: {r.status_code})"

async def gh_create_repo(token, repo_name):
    async with httpx.AsyncClient(timeout=30) as c:
        # check exists
        r = await c.get(f"https://api.github.com/user", headers=GH_HEADERS(token))
        username = r.json()["login"]
        r = await c.get(f"https://api.github.com/repos/{username}/{repo_name}", headers=GH_HEADERS(token))
        if r.status_code == 200: return True, username
        r = await c.post("https://api.github.com/user/repos", headers=GH_HEADERS(token),
                         json={"name": repo_name, "private": False, "auto_init": True,
                               "description": "Telegram Bot Cloud Storage"})
        return r.status_code == 201, username

async def gh_get_repo_size(token, username, repo_name):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"https://api.github.com/repos/{username}/{repo_name}", headers=GH_HEADERS(token))
        if r.status_code == 200: return r.json().get("size", 0) * 1024  # KB to bytes
        return 0

async def gh_upload_chunk(token, username, repo, remote_path, chunk_bytes):
    content_b64 = base64.b64encode(chunk_bytes).decode()
    sha = None
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.get(f"https://api.github.com/repos/{username}/{repo}/contents/{remote_path}",
                        headers=GH_HEADERS(token))
        if r.status_code == 200: sha = r.json().get("sha")
    payload = {"message": f"upload {remote_path}", "content": content_b64}
    if sha: payload["sha"] = sha
    async with httpx.AsyncClient(timeout=300) as c:
        r = await c.put(f"https://api.github.com/repos/{username}/{repo}/contents/{remote_path}",
                        headers=GH_HEADERS(token), json=payload)
        if r.status_code in (200, 201):
            return f"https://raw.githubusercontent.com/{username}/{repo}/main/{remote_path}"
        raise Exception(f"آپلود chunk ناموفق: {r.status_code} - {r.text[:300]}")

async def gh_upload_file(token, username, repo, local_path, status_msg, chat_id):
    """هر chunk جداگانه commit+push — فایل‌ها در repo (نه releases)، فقط ۹۵MB RAM در هر push"""
    file_name = os.path.basename(local_path)
    safe_name = re.sub(r'[^\w.\-]', '_', file_name).strip('_')
    ts = int(time.time())
    folder_name = f"upload_{ts}"
    file_size = os.path.getsize(local_path)
    n_parts = max(1, (file_size + GITHUB_CHUNK_SIZE - 1) // GITHUB_CHUNK_SIZE)
    clone_dir = os.path.join(TEMP_DIR, f"gh_{chat_id}_{ts}")

    try:
        await safe_edit(status_msg, T(chat_id,"gh_preparing"), reply_markup=get_cancel_keyboard(chat_id))
        os.makedirs(clone_dir, exist_ok=True)
        clone_url = f"https://{username}:{token}@github.com/{username}/{repo}.git"
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

        async def git(*args):
            p = await asyncio.create_subprocess_exec("git", *args, cwd=clone_dir,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env)
            out, err = await p.communicate()
            return p.returncode, out.decode(), err.decode()

        await git("init")
        await git("remote", "add", "origin", clone_url)
        await git("config", "user.email", "bot@telegram.bot")
        await git("config", "user.name", "Telegram Bot")
        await git("config", "pack.windowMemory", "10m")
        await git("config", "pack.compression", "0")
        await git("config", "pack.threads", "1")
        await git("config", "core.bigFileThreshold", "1m")
        await git("fetch", "--depth=1", "origin", "main")
        await git("checkout", "-B", "main", "FETCH_HEAD")

        upload_dir = os.path.join(clone_dir, "uploads", folder_name)
        os.makedirs(upload_dir, exist_ok=True)
        links = []

        with open(local_path, 'rb') as f:
            for i in range(1, n_parts + 1):
                if cancel_flags.get(chat_id): raise ValueError("CANCELLED")
                chunk = f.read(GITHUB_CHUNK_SIZE)
                if not chunk: break
                ext = os.path.splitext(file_name)[1]  # پسوند اصلی فایل مثل .mp4 یا .exe
                chunk_name = f"Mega-Leecher{ext}.{i:03d}" if n_parts > 1 else f"Mega-Leecher{ext}"
                chunk_path = os.path.join(upload_dir, chunk_name)
                chunk_mb = len(chunk) / (1024 * 1024)

                bar = "■"*(i*10//n_parts) + "□"*(10-i*10//n_parts)
                bar = "■"*(i*10//n_parts) + "□"*(10-i*10//n_parts)
                await safe_edit(status_msg,
                    T(chat_id,"gh_uploading",bar=bar,pct=i*100//n_parts,i=i,n=n_parts,mb=chunk_mb),
                    reply_markup=get_cancel_keyboard(chat_id))

                with open(chunk_path, 'wb') as cf:
                    cf.write(chunk)
                del chunk

                # commit و push فقط همین یک فایل — pack-objects فقط ۹۵MB پردازش میکنه
                await git("add", f"uploads/{folder_name}/{chunk_name}")
                await git("commit", "-m", f"chunk {i}/{n_parts}: {chunk_name}")

                push_proc = await asyncio.create_subprocess_exec(
                    "git", "push", "origin", "main", "--force",
                    cwd=clone_dir, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE, env=env)
                while True:
                    try:
                        await asyncio.wait_for(push_proc.wait(), timeout=10.0)
                        break
                    except asyncio.TimeoutError:
                        if cancel_flags.get(chat_id):
                            push_proc.terminate()
                            raise ValueError("CANCELLED")
                if push_proc.returncode != 0:
                    err_out = await push_proc.stderr.read()
                    raise Exception(f"git push ناموفق پارت {i} (کد {push_proc.returncode}): {err_out.decode()[:150]}")

                links.append(f"https://raw.githubusercontent.com/{username}/{repo}/main/uploads/{folder_name}/{chunk_name}")

        return links, len(links)
    finally:
        shutil.rmtree(clone_dir, ignore_errors=True)

async def gh_list_folder(token, username, repo, path="uploads"):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"https://api.github.com/repos/{username}/{repo}/contents/{path}",
                        headers=GH_HEADERS(token))
        if r.status_code == 200: return r.json()
        return []

async def gh_delete_file(token, username, repo, path, sha):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.delete(f"https://api.github.com/repos/{username}/{repo}/contents/{path}",
                           headers=GH_HEADERS(token), json={"message": f"delete {path}", "sha": sha})
        return r.status_code == 200

async def gh_clear_all(token, username, repos, status_msg, chat_id=0):
    """پاکسازی با git — حذف پوشه uploads از ریپو"""
    for i, repo in enumerate(repos, 1):
        await safe_edit(status_msg, T(chat_id,"gh_clear_repo",i=i,total=len(repos)))
        clone_dir = os.path.join(TEMP_DIR, f"gh_clear_{int(time.time())}_{i}")
        try:
            os.makedirs(clone_dir, exist_ok=True)
            clone_url = f"https://{username}:{token}@github.com/{username}/{repo}.git"
            env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

            async def git(*args):
                p = await asyncio.create_subprocess_exec("git", *args, cwd=clone_dir,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env)
                await p.communicate()
                return p.returncode

            await git("init")
            await git("remote", "add", "origin", clone_url)
            await git("config", "user.email", "bot@telegram.bot")
            await git("config", "user.name", "Telegram Bot")
            await git("config", "pack.windowMemory", "10m")
            await git("config", "pack.compression", "0")
            await git("config", "pack.threads", "1")
            rc = await git("fetch", "--depth=1", "origin", "main")
            if rc != 0: continue
            await git("checkout", "-B", "main", "FETCH_HEAD")
            uploads_dir = os.path.join(clone_dir, "uploads")
            if os.path.exists(uploads_dir):
                shutil.rmtree(uploads_dir)
                await git("add", "-A")
                rc = await git("commit", "-m", "Clear all uploads")
                if rc == 0:
                    await git("push", "origin", "main", "--force")
        except Exception:
            pass
        finally:
            shutil.rmtree(clone_dir, ignore_errors=True)

async def gh_get_space_info(token, username, repos):
    """محاسبه حجم از db داخلی — realtime و بدون تأخیر GitHub"""
    db = load_github_db()
    uid = next((u for u, d in db.items() if d.get("username") == username), None)
    repo_sizes = db[uid].get("repo_sizes", {}) if uid else {}
    used = sum(repo_sizes.get(r, 0) for r in repos)
    total = GITHUB_REPO_MAX * len(repos)
    return used, total, total - used

GITHUB_DAILY_LIMIT = 10

def check_gh_quota(user_id):
    if user_id == ADMIN_ID: return True, GITHUB_DAILY_LIMIT
    db = load_github_db(); uid = str(user_id)
    if uid not in db: return False, 0
    now = time.time()
    history = [t for t in db[uid].get("gh_history", []) if now - t < 86400]
    remaining = GITHUB_DAILY_LIMIT - len(history)
    return remaining > 0, remaining

def record_gh_upload(user_id):
    if user_id == ADMIN_ID: return
    db = load_github_db(); uid = str(user_id)
    if uid not in db: return
    now = time.time()
    history = [t for t in db[uid].get("gh_history", []) if now - t < 86400]
    history.append(now)
    db[uid]["gh_history"] = history
    save_github_db(db)

def update_repo_size(username, repo_name, added_bytes):
    """ثبت حجم آپلود در db"""
    db = load_github_db()
    uid = next((u for u, d in db.items() if d.get("username") == username), None)
    if uid:
        if "repo_sizes" not in db[uid]:
            db[uid]["repo_sizes"] = {}
        db[uid]["repo_sizes"][repo_name] = db[uid]["repo_sizes"].get(repo_name, 0) + added_bytes
        save_github_db(db)

def reset_repo_sizes(username, repos):
    """صفر کردن حجم بعد از پاکسازی"""
    db = load_github_db()
    uid = next((u for u, d in db.items() if d.get("username") == username), None)
    if uid:
        db[uid]["repo_sizes"] = {r: 0 for r in repos}
        save_github_db(db)

def gh_find_repo(token, username, repos, file_size):
    """ریپوی مناسب از db داخلی"""
    db = load_github_db()
    uid = next((u for u, d in db.items() if d.get("username") == username), None)
    repo_sizes = db[uid].get("repo_sizes", {}) if uid else {}
    for repo in repos:
        used = repo_sizes.get(repo, 0)
        if GITHUB_REPO_MAX - used >= file_size:
            return repo
    return None

# ================= توابع حجم یوتوب =================
def get_quality_size(formats, max_height):
    vf = [f for f in formats if f.get('vcodec','none') != 'none' and f.get('acodec','none') == 'none' and 0 < (f.get('height') or 0) <= max_height]
    af = [f for f in formats if f.get('acodec','none') != 'none' and f.get('vcodec','none') == 'none']
    if not vf: return 0
    bv = max(vf, key=lambda f: (f.get('height',0), f.get('filesize') or f.get('filesize_approx') or 0))
    ba = max(af, key=lambda f: f.get('filesize') or f.get('filesize_approx') or 0) if af else None
    return (bv.get('filesize') or bv.get('filesize_approx') or 0) + ((ba.get('filesize') or ba.get('filesize_approx') or 0) if ba else 0)

def get_audio_size(formats):
    af = [f for f in formats if f.get('acodec','none') != 'none' and f.get('vcodec','none') == 'none']
    if not af: return 0
    b = max(af, key=lambda f: f.get('filesize') or f.get('filesize_approx') or 0)
    return b.get('filesize') or b.get('filesize_approx') or 0

def fmt_size(s):
    if not s: return "نامشخص"
    mb = s/(1024*1024)
    return f"{s//1024}KB" if mb < 1 else f"~{mb:.0f}MB"

# ================= توابع کمکی UI =================
async def safe_edit(msg, text, reply_markup=None):
    try: await msg.edit_text(text, reply_markup=reply_markup)
    except: pass

async def safe_final_edit(message, bot_msg, text, reply_markup=None):
    try: await bot_msg.edit_text(text, reply_markup=reply_markup)
    except:
        try: await message.reply(text, reply_markup=reply_markup)
        except: pass

def get_cancel_keyboard(user_id=0):
    # دکمه لغو عملیات / Cancel operation button
    return InlineKeyboardMarkup([[InlineKeyboardButton(T(user_id, "btn_cancel_op"), callback_data="cancel_task")]])

def get_main_keyboard(user_id=None):
    # منوی اینلاین پردازش فایل / Inline file processing menu
    uid = user_id or 0
    kb = [
        [InlineKeyboardButton(T(uid, "btn_raw"),       callback_data="size_raw")],
        [InlineKeyboardButton(T(uid, "btn_full_rar"),  callback_data="size_full")],
        [InlineKeyboardButton(T(uid, "btn_multi_rar"), callback_data="size_multi")],
        [InlineKeyboardButton(T(uid, "btn_split"),     callback_data="size_split")]
    ]
    if user_id and has_github_token(user_id):
        kb.append([InlineKeyboardButton(T(uid, "btn_github_upload"), callback_data="size_github")])
    if user_id and has_drive_connected(user_id):
        kb.append([InlineKeyboardButton(T(uid, "btn_drive_upload"), callback_data="size_gdrive")])
    return InlineKeyboardMarkup(kb)

async def progress_bar(current, total, status_msg, start_time, action_text, is_cancellable=False, user_id=0):
    # نوار پیشرفت دانلود/آپلود / Download/upload progress bar
    chat_id = status_msg.chat.id
    if is_cancellable and cancel_flags.get(chat_id): raise ValueError("CANCELLED")
    now = time.time()
    if now - last_update_time.get(status_msg.id, 0) < 5 and current != total: return
    last_update_time[status_msg.id] = now
    diff = now - start_time
    if diff <= 0: return
    pct = current*100/total if total > 0 else 0
    speed = current/diff/1024
    bar = "■"*int(pct/10) + "□"*(10-int(pct/10))
    await safe_edit(status_msg,
        T(user_id, "progress",
          action=action_text, bar=bar, pct=pct, speed=speed,
          cur=current/(1024*1024), total=total/(1024*1024)),
        get_cancel_keyboard(user_id) if is_cancellable else None)

def get_reply_menu(user_id):
    # منوی اصلی ربات / Main bot reply menu
    keyboard = [
        [KeyboardButton(T(user_id, "btn_direct_link")), KeyboardButton(T(user_id, "btn_torrent"))],
        [KeyboardButton(T(user_id, "btn_tg_files")),    KeyboardButton(T(user_id, "btn_youtube"))],
        [KeyboardButton(T(user_id, "btn_github")),      KeyboardButton(T(user_id, "btn_drive"))]
    ]
    if user_id == ADMIN_ID:
        keyboard += [
            [KeyboardButton(T(user_id, "btn_add_user")),    KeyboardButton(T(user_id, "btn_del_user"))],
            [KeyboardButton(T(user_id, "btn_add_yt_user")), KeyboardButton(T(user_id, "btn_user_list"))],
            [KeyboardButton(T(user_id, "btn_clean_bot"))]
        ]
    else:
        keyboard.append([KeyboardButton(T(user_id, "btn_purchase"))])
    keyboard.append([KeyboardButton(T(user_id, "btn_language"))])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, placeholder=T(user_id, "menu_placeholder"))

# ================= گارد محافظ =================
@app.on_message(filters.all & filters.incoming, group=-1)
async def access_checker_middleware(client, message):
    # محافظ دسترسی — بررسی اشتراک کاربر / Access guard — check user subscription
    if not message.from_user: return
    try:
        msg_ts = message.date.timestamp() if hasattr(message.date,'timestamp') else float(message.date)
    except: msg_ts = BOT_START_TIME + 1
    if msg_ts < BOT_START_TIME:
        message.stop_propagation(); return
    chat_id = message.chat.id; user_id = message.from_user.id; text = message.text or ""
    # دکمه‌های مجاز بدون نیاز به اشتراک (فارسی و انگلیسی) / Free buttons (Persian and English)
    free_fa = ["/start",
               STRINGS["fa"]["btn_direct_link"], STRINGS["fa"]["btn_torrent"],
               STRINGS["fa"]["btn_tg_files"],    STRINGS["fa"]["btn_youtube"],
               STRINGS["fa"]["btn_purchase"],    STRINGS["fa"]["btn_github"],
               STRINGS["fa"]["btn_drive"],       STRINGS["fa"]["btn_language"]]
    free_en = [STRINGS["en"]["btn_direct_link"], STRINGS["en"]["btn_torrent"],
               STRINGS["en"]["btn_tg_files"],    STRINGS["en"]["btn_youtube"],
               STRINGS["en"]["btn_purchase"],    STRINGS["en"]["btn_github"],
               STRINGS["en"]["btn_drive"],       STRINGS["en"]["btn_language"]]
    allowed = free_fa + free_en
    if chat_id in user_states and user_states[chat_id].get("admin_action"): return
    # اجازه ورود به کاربران در حین وارد کردن اندازه split / Allow during split size input
    if any(str(k).startswith(f"{chat_id}_") and v.get("awaiting_split_size")
           for k, v in user_states.items()): return
    if text in allowed: return
    if f"gh_{chat_id}" in user_states: return
    if f"gd_{chat_id}" in user_states: return
    if not has_access(user_id):
        await message.reply(T(user_id, "no_subscription", purchase=PURCHASE_USERNAME, uid=user_id))
        message.stop_propagation()

# ================= هندلرهای پیام =================
@app.on_message(filters.command("start"))
async def start(client, message):
    # نمایش انتخاب زبان هنگام شروع / Show language selection on start
    await message.reply(
        T(message.from_user.id, "choose_language"),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇮🇷 Persian (فارسی)", callback_data="setlang_fa"),
             InlineKeyboardButton("🇺🇸 English",          callback_data="setlang_en")]
        ])
    )

@app.on_callback_query(filters.regex("^setlang_"))
async def setlang_callback(client, cq):
    # پردازش انتخاب زبان / Process language selection
    await cq.answer()
    lang = cq.data.split("_")[1]
    user_id = cq.from_user.id
    set_user_lang(user_id, lang)
    confirm_key = "lang_changed_en" if lang == "en" else "lang_changed_fa"
    await safe_edit(cq.message, T(user_id, confirm_key))
    await client.send_message(cq.message.chat.id, T(user_id, "welcome"),
                               reply_markup=get_reply_menu(user_id))

@app.on_message(filters.text & filters.regex(
    "^(🌐 راهنمای لینک مستقیم|🌐 Direct Link Guide"
    "|🧲 راهنمای تورنت|🧲 Torrent Guide"
    "|📁 راهنمای کار با فایل‌های تلگرامی|📁 Telegram Files Guide"
    "|🎬 راهنمای دانلود از یوتوب|🎬 YouTube Download Guide"
    "|🛒 خرید / تمدید اشتراک|🛒 Buy / Renew Subscription"
    "|🌐 تغییر زبان|🌐 Change Language)$"))
async def handle_user_menus(client, message):
    t = message.text; uid = message.from_user.id
    if "لینک مستقیم" in t or "Direct Link Guide" in t:
        await message.reply(T(uid, "guide_direct"))
    elif "تورنت" in t or "Torrent Guide" in t:
        await message.reply(T(uid, "guide_torrent"))
    elif "فایل‌های تلگرامی" in t or "Telegram Files Guide" in t:
        await message.reply(T(uid, "guide_tg_files"))
    elif "یوتوب" in t or "YouTube Download Guide" in t:
        await message.reply(T(uid, "guide_youtube"))
    elif "خرید" in t or "Buy / Renew Subscription" in t:
        users = load_users()
        uid_str = str(uid)
        if has_access(uid) and uid_str in users and isinstance(users[uid_str], dict):
            expire = users[uid_str].get("expire", 0)
            if expire > time.time():
                rem_days = int((expire - time.time()) // 86400)
                await message.reply(T(uid, "sub_active", days=rem_days))
            else:
                await message.reply(T(uid, "sub_renew", purchase=PURCHASE_USERNAME, uid=uid))
        else:
            await message.reply(T(uid, "sub_buy", purchase=PURCHASE_USERNAME, uid=uid))
    elif "تغییر زبان" in t or "Change Language" in t:
        await message.reply(
            T(uid, "choose_language"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🇮🇷 Persian (فارسی)", callback_data="setlang_fa"),
                 InlineKeyboardButton("🇺🇸 English",          callback_data="setlang_en")]
            ])
        )

# ================= منوی گیتهاب =================
@app.on_message(filters.text & filters.regex("^(📂 اتصال به گوگل درایو|📂 Connect Google Drive)$"))
async def drive_menu(client, message):
    user_id = message.from_user.id
    if not has_access(user_id):
        await message.reply(T(user_id, "feature_needs_sub", purchase=PURCHASE_USERNAME))
        return
    db = load_drive_db(); uid = str(user_id); has_d = uid in db
    status = T(user_id, "gd_connected") if has_d else T(user_id, "gd_not_connected")
    buttons = [
        [InlineKeyboardButton(T(user_id,"gd_btn_guide"), callback_data="gd_guide")],
        [InlineKeyboardButton(T(user_id,"gd_btn_dl_guide"), callback_data="gd_dl_guide")],
        [InlineKeyboardButton(T(user_id,"gd_btn_connect"), callback_data="gd_connect")]
    ]
    if has_d:
        buttons.append([InlineKeyboardButton(T(user_id,"gd_btn_space"), callback_data="gd_space")])
        buttons.append([InlineKeyboardButton(T(user_id,"gd_btn_clear"), callback_data="gd_clear")])
        buttons.append([InlineKeyboardButton(T(user_id,"gd_btn_disconnect"), callback_data="gd_disconnect")])
    await message.reply(
        T(user_id,"gd_menu_title",status=status),
        reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex("^gd_"))
async def drive_callback(client, cq):
    await cq.answer()
    chat_id = cq.message.chat.id; user_id = cq.from_user.id; action = cq.data

    if action == "gd_guide":
        await safe_edit(cq.message,
            T(user_id,"gd_guide_text"),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(T(user_id,"gd_btn_connect"), callback_data="gd_connect")]]))

    elif action == "gd_connect":
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            await safe_edit(cq.message, T(user_id,"gd_oauth_not_configured")); return
        auth_url = get_drive_auth_url()
        user_states[f"gd_{chat_id}"] = {"type": "awaiting_drive_code"}
        await client.send_message(chat_id,
            T(user_id,"gd_connect_url",url=auth_url),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(T(user_id,"gd_btn_cancel_connect"), callback_data="gd_cancel")]]))

    elif action == "gd_space":
        db = load_drive_db(); uid = str(user_id)
        if uid not in db: await safe_edit(cq.message, T(user_id,"gd_no_account")); return
        await safe_edit(cq.message, T(user_id,"gd_checking_space"))
        token = await get_valid_drive_token(user_id)
        if not token: await safe_edit(cq.message, T(user_id,"gd_auth_error")); return
        used, total, remaining = await drive_get_space(token)
        pct = (used/total*100) if total > 0 else 0
        bar = "■"*int(pct/10) + "□"*(10-int(pct/10))
        _, quota_left = check_drive_quota(user_id)
        await safe_edit(cq.message,
            T(user_id,"gd_space_info", bar=bar, pct=pct,
              used=used/(1024**3), free=remaining/(1024**3),
              total=total/(1024**3), quota=quota_left, limit=DRIVE_DAILY_LIMIT))

    elif action == "gd_clear":
        await safe_edit(cq.message, T(user_id,"gd_warn_clear"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(T(user_id,"gd_btn_confirm_clear"), callback_data="gd_clear_ok")],
                [InlineKeyboardButton(T(user_id,"gh_btn_cancel"),          callback_data="gd_cancel")]]))

    elif action == "gd_clear_ok":
        db = load_drive_db(); uid = str(user_id)
        if uid not in db: await safe_edit(cq.message, T(user_id,"gd_no_account_short")); return
        token = await get_valid_drive_token(user_id)
        if not token: await safe_edit(cq.message, T(user_id,"gd_auth_error_short")); return
        folder_id = db[uid].get("folder_id")
        if not folder_id: await safe_edit(cq.message, T(user_id,"gd_no_folder")); return
        await safe_edit(cq.message, T(user_id,"gd_clearing"))
        try:
            count = await drive_clear_all_files(token, folder_id, cq.message)
            await safe_edit(cq.message, T(user_id,"gd_clear_done",count=count))
        except Exception as e:
            await safe_edit(cq.message, T(user_id,"gd_clear_error",e=e))

    elif action == "gd_dl_guide":
        await client.send_message(chat_id, T(user_id,"gd_dl_guide_text"))
        apk_path = os.path.join(INSTALL_DIR, "MITM.Drive.Downloader.v1-android.apk")
        if os.path.exists(apk_path):
            await client.send_document(chat_id, apk_path,
                caption=T(user_id,"mitm_caption"))
        user_states.pop(f"gd_{chat_id}", None)
        await safe_edit(cq.message, T(user_id,"gd_cancelled"))

    elif action == "gd_disconnect":
        db = load_drive_db(); uid = str(user_id)
        if uid in db: del db[uid]; save_drive_db(db)
        await safe_edit(cq.message, T(user_id,"gd_disconnected"))

    elif action == "gd_cancel":
        await safe_edit(cq.message, T(user_id,"gd_cancelled_short"))

@app.on_message(filters.text, group=1)
async def handle_drive_code_input(client, message):
    chat_id = message.chat.id
    sk = f"gd_{chat_id}"
    if sk not in user_states or user_states[sk].get("type") != "awaiting_drive_code": return
    code = message.text.strip()
    # استخراج کد از URL کامل در صورتی که کاربر URL رو paste کرده
    if "code=" in code:
        match = re.search(r'[?&]code=([^&\s]+)', code)
        if match:
            code = urllib.parse.unquote(match.group(1))
    del user_states[sk]
    status_msg = await message.reply(T(message.from_user.id,"gd_verifying"))
    try:
        access_token, refresh_token, expiry = await exchange_drive_code(code)
        if not refresh_token:
            await safe_final_edit(message, status_msg, T(message.from_user.id,"gd_invalid_code")); return
        await safe_edit(status_msg, T(message.from_user.id,"gd_creating_folder"))
        folder_id = await drive_get_or_create_folder(access_token)
        db = load_drive_db()
        db[str(chat_id)] = {
            "access_token": access_token, "refresh_token": refresh_token,
            "token_expiry": expiry, "folder_id": folder_id,
            "drive_history": []
        }
        save_drive_db(db)
        await safe_final_edit(message, status_msg,
            T(message.from_user.id,"gd_connect_success"))
    except Exception as e:
        await safe_final_edit(message, status_msg, T(message.from_user.id,"gd_code_error",e=e))


@app.on_message(filters.text & filters.regex("^(☁️ اتصال به گیتهاب|☁️ Connect GitHub)$"))
async def github_menu(client, message):
    user_id = message.from_user.id

    if not has_access(user_id):
        await message.reply(T(user_id,"feature_needs_sub",purchase=PURCHASE_USERNAME))
        return
        return

    db = load_github_db(); uid = str(user_id); has_t = uid in db
    username = db[uid]["username"] if has_t else None
    status = T(user_id, "gh_connected", username=username) if has_t else T(user_id, "gh_not_connected")
    buttons = [
        [InlineKeyboardButton(T(user_id,"gh_btn_guide"), callback_data="gh_guide")],
        [InlineKeyboardButton(T(user_id,"gh_btn_token_change") if has_t else T(user_id,"gh_btn_token"), callback_data="gh_set_token")]
    ]
    if has_t:
        buttons.append([InlineKeyboardButton(T(user_id,"gh_btn_space"), callback_data="gh_space")])
        buttons.append([InlineKeyboardButton(T(user_id,"gh_btn_clear"), callback_data="gh_clear")])
    await message.reply(
        T(user_id,"gh_menu_title",status=status),
        reply_markup=InlineKeyboardMarkup(buttons))

def _gh_guide_kb(user_id, page):
    # صفحه‌بندی راهنمای گیتهاب / GitHub guide pagination keyboard
    total = 4
    row = []
    if page > 1:
        row.append(InlineKeyboardButton(
            T(user_id,"gh_guide_prev"), callback_data=f"gh_guide_p{page-1}"))
    if page < total:
        row.append(InlineKeyboardButton(
            T(user_id,"gh_guide_next"), callback_data=f"gh_guide_p{page+1}"))
    else:
        row.append(InlineKeyboardButton(
            T(user_id,"gh_btn_token"), callback_data="gh_set_token"))
    nav = [InlineKeyboardButton(
        T(user_id,"gh_guide_page_num",page=page,total=total),
        callback_data="noop")]
    return InlineKeyboardMarkup([row, nav])

@app.on_callback_query(filters.regex("^noop$"))
async def noop_callback(client, cq):
    await cq.answer()

@app.on_callback_query(filters.regex("^gh_"))
async def github_callback(client, cq):
    await cq.answer()
    chat_id = cq.message.chat.id; user_id = cq.from_user.id; action = cq.data

    if action == "gh_guide":
        await safe_edit(cq.message, T(user_id,"gh_guide_page1"),
            reply_markup=_gh_guide_kb(user_id, 1))

    elif action.startswith("gh_guide_p"):
        page = int(action.split("gh_guide_p")[1])
        pages = {1:"gh_guide_page1", 2:"gh_guide_page2",
                 3:"gh_guide_page3", 4:"gh_guide_page4"}
        await safe_edit(cq.message, T(user_id, pages[page]),
            reply_markup=_gh_guide_kb(user_id, page))

    elif action == "gh_set_token":
        user_states[f"gh_{chat_id}"] = {"type": "awaiting_gh_token"}
        await client.send_message(chat_id, T(user_id,"gh_token_prompt"),
                                  reply_markup=ForceReply(selective=True))

    elif action == "gh_space":
        db = load_github_db(); uid = str(user_id)
        if uid not in db: await safe_edit(cq.message, T(user_id,"gh_no_token_menu")); return
        d = db[uid]
        repos = d.get("repos", [])
        repo_sizes = d.get("repo_sizes", {})
        repo_lines = ""
        total_used = 0
        for r in repos:
            sz = repo_sizes.get(r, 0)
            total_used += sz
            pr = sz / GITHUB_REPO_MAX * 100
            bar_r = "■"*int(pr/10) + "□"*(10-int(pr/10))
            repo_lines += f"  📁 `{r}`: {sz/(1024**3):.2f}GB [{bar_r}]\n"
        total_cap = GITHUB_REPO_MAX * len(repos)
        pct = (total_used / total_cap * 100) if total_cap > 0 else 0
        bar = "■"*int(pct/10) + "□"*(10-int(pct/10))
        _, remaining_quota = check_gh_quota(user_id)
        await safe_edit(cq.message,
            T(user_id,"gh_space_info",
              username=d["username"], repos_info=repo_lines, bar=bar, pct=pct,
              used=total_used/(1024**3), free=(total_cap-total_used)/(1024**3),
              total=total_cap/(1024**3), quota=remaining_quota, limit=GITHUB_DAILY_LIMIT))

    elif action == "gh_clear":
        await safe_edit(cq.message, T(user_id,"gh_warn_clear"),
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton(T(user_id,"gh_btn_confirm_clear"), callback_data="gh_clear_ok")],
                            [InlineKeyboardButton(T(user_id,"gh_btn_cancel"), callback_data="gh_cancel")]]))

    elif action == "gh_clear_ok":
        db = load_github_db(); uid = str(user_id)
        if uid not in db: await safe_edit(cq.message, T(user_id,"gh_no_token_menu")); return
        d = db[uid]
        await safe_edit(cq.message, T(user_id,"gh_clearing"))
        try:
            await gh_clear_all(d["token"], d["username"], d.get("repos",[]), cq.message, user_id)
            reset_repo_sizes(d["username"], d.get("repos", []))
            await safe_edit(cq.message, T(user_id,"gh_clear_done"))
        except Exception as e:
            await safe_edit(cq.message, T(user_id,"gh_clear_error",e=e))

    elif action == "gh_cancel":
        await safe_edit(cq.message, T(user_id,"gh_cancelled"))

@app.on_message(filters.text)
async def handle_github_token_input(client, message):
    chat_id = message.chat.id
    sk = f"gh_{chat_id}"
    if sk not in user_states or user_states[sk].get("type") != "awaiting_gh_token":
        message.continue_propagation(); return
    token = message.text.strip()
    del user_states[sk]
    status_msg = await message.reply(T(message.from_user.id,"gh_verifying"))
    username, err = await gh_validate_token(token)
    if err:
        await safe_final_edit(message, status_msg, T(message.from_user.id,"gh_invalid_token",err=err)); return
    await safe_edit(status_msg, T(message.from_user.id,"gh_creating_repos",username=username))
    repos = []
    for i in range(1, GITHUB_MAX_REPOS + 1):
        repo_name = f"bot-cloud-{i}"
        await safe_edit(status_msg, T(message.from_user.id,"gh_creating_repo_i",username=username,i=i,total=GITHUB_MAX_REPOS))
        ok, _ = await gh_create_repo(token, repo_name)
        if ok:
            repos.append(repo_name)
    if not repos:
        await safe_final_edit(message, status_msg, T(message.from_user.id,"gh_repo_error")); return
    db = load_github_db()
    db[str(chat_id)] = {"token": token, "username": username, "repos": repos}
    save_github_db(db)
    await safe_final_edit(message, status_msg,
        T(chat_id,"gh_connect_success",username=username,repos=len(repos),cap=len(repos)*5))

@app.on_callback_query(filters.regex("^cancel_task$"))
async def cancel_callback(client, cq):
    cancel_flags[cq.message.chat.id] = True
    await cq.answer("⚠️ درخواست لغو ثبت شد." if get_user_lang(cq.from_user.id)=="fa" else "⚠️ Cancellation requested.", show_alert=True)

# ================= بخش مدیریت ادمین =================
USERS_PER_PAGE = 5

async def send_user_list_page(chat_id, active_users, page, client, send_new=False, message_id=None):
    # نمایش لیست کاربران با صفحه‌بندی / Display paginated user list
    lang = get_user_lang(ADMIN_ID)
    total = len(active_users)
    total_pages = (total + USERS_PER_PAGE - 1) // USERS_PER_PAGE
    start = page * USERS_PER_PAGE
    end = min(start + USERS_PER_PAGE, total)
    page_users = active_users[start:end]

    text = _T(lang, "admin_user_list_title", page=page+1, total_pages=total_pages, total=total)
    text += "━━━━━━━━━━━━━━━━━\n\n"
    for i, u in enumerate(page_users, start + 1):
        text += _T(lang, "admin_user_entry", i=i, uname=u['uname'], uid=u['uid'], rd=u['rd'], ytd=u['ytd'])

    buttons = []
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(_T(lang,"admin_btn_prev"), callback_data=f"ulist_{page-1}"))
    if page < total_pages - 1:
        row.append(InlineKeyboardButton(_T(lang,"admin_btn_next"), callback_data=f"ulist_{page+1}"))
    if row: buttons.append(row)
    kb = InlineKeyboardMarkup(buttons) if buttons else None

    if send_new:
        await client.send_message(chat_id, text, reply_markup=kb)
    else:
        await client.edit_message_text(chat_id, message_id, text, reply_markup=kb)

@app.on_callback_query(filters.regex(r"^ulist_\d+$") & filters.user(ADMIN_ID))
async def user_list_page_callback(client, cq):
    await cq.answer()
    page = int(cq.data.split("_")[1])
    users = load_users()
    active = []
    for uid, d in users.items():
        if isinstance(d, dict):
            exp = d.get("expire", 0); yt_exp = d.get("yt_expire", 0)
            rd = int((exp - time.time()) // 86400) if exp > time.time() else 0
            ytd = int((yt_exp - time.time()) // 86400) if yt_exp > time.time() else 0
            if rd > 0 or ytd > 0:
                active.append({"uid": uid, "uname": d.get("username","نامشخص"), "rd": rd, "ytd": ytd})
    await send_user_list_page(cq.message.chat.id, active, page, client,
                              send_new=False, message_id=cq.message.id)


@app.on_message(filters.text & filters.regex("^(➕ افزودن کاربر|➕ Add User|➕ افزودن کاربر یوتوب|➕ Add YouTube User|📋 لیست کاربران|📋 User List|➖ حذف کاربر|➖ Remove User|🧹 پاکسازی ربات|🧹 Clean Bot)$") & filters.user(ADMIN_ID))
async def admin_menu_handler(client, message):
    t = message.text; chat_id = message.chat.id; user_id = message.from_user.id
    if t in ("📋 لیست کاربران", "📋 User List"):
        users = load_users()
        active = []
        for uid, d in users.items():
            if isinstance(d, dict):
                exp = d.get("expire", 0); yt_exp = d.get("yt_expire", 0)
                rd = int((exp - time.time()) // 86400) if exp > time.time() else 0
                ytd = int((yt_exp - time.time()) // 86400) if yt_exp > time.time() else 0
                if rd > 0 or ytd > 0:
                    active.append({"uid": uid, "uname": d.get("username","نامشخص"), "rd": rd, "ytd": ytd})
        if not active:
            await message.reply(T(user_id,"admin_no_users")); return
        await send_user_list_page(message.chat.id, active, page=0, client=client, send_new=True)
    elif t in ("➕ افزودن کاربر", "➕ Add User"):
        user_states[chat_id] = {"admin_action": "wait_for_user_id"}
        await message.reply(T(user_id,"admin_ask_user_id"),
            reply_markup=ReplyKeyboardMarkup([[T(user_id,"admin_cancel")]], resize_keyboard=True))
    elif t in ("➕ افزودن کاربر یوتوب", "➕ Add YouTube User"):
        user_states[chat_id] = {"admin_action": "wait_for_yt_user_id"}
        await message.reply(T(user_id,"admin_ask_yt_id"),
            reply_markup=ReplyKeyboardMarkup([[T(user_id,"admin_cancel")]], resize_keyboard=True))
    elif t in ("➖ حذف کاربر", "➖ Remove User"):
        user_states[chat_id] = {"admin_action": "wait_for_delete_id"}
        await message.reply(T(user_id,"admin_ask_user_id"),
            reply_markup=ReplyKeyboardMarkup([[T(user_id,"admin_cancel")]], resize_keyboard=True))
    elif t in ("🧹 پاکسازی ربات", "🧹 Clean Bot"):
        for f in os.listdir(TEMP_DIR):
            fp = os.path.join(TEMP_DIR, f)
            try:
                if os.path.isfile(fp): os.unlink(fp)
                elif os.path.isdir(fp): shutil.rmtree(fp)
            except: pass
        await message.reply(T(user_id,"admin_clean_done"), reply_markup=get_reply_menu(ADMIN_ID))

@app.on_message(filters.text & filters.user(ADMIN_ID))
async def admin_states_handler(client, message):
    # پردازش مرحله‌ای مدیریت کاربران / Step-by-step user management processing
    chat_id = message.chat.id
    user_id = message.from_user.id  # ← کلید: user_id برای T() / key: user_id for T()
    t = message.text
    state = user_states.get(chat_id, {}).get("admin_action")

    cancel_words = (T(user_id,"admin_cancel"),)
    if t in cancel_words and state:
        user_states.pop(chat_id, None)
        await message.reply(T(user_id,"admin_cancelled"), reply_markup=get_reply_menu(ADMIN_ID))
        return

    if state == "wait_for_user_id":
        user_states[chat_id]["target_user_id"] = t
        user_states[chat_id]["admin_action"] = "wait_for_days"
        await message.reply(T(user_id,"admin_ask_days"))

    elif state == "wait_for_days":
        try:
            days = int(t)
        except ValueError:
            await message.reply("❌" if get_user_lang(user_id) == "en" else "❌ عدد وارد کنید."); return
        user_states[chat_id]["target_days"] = days
        user_states[chat_id]["admin_action"] = "wait_for_username"
        await message.reply(T(user_id,"admin_ask_username"))

    elif state == "wait_for_username":
        tid = user_states[chat_id]["target_user_id"]
        days = user_states[chat_id]["target_days"]
        exp = time.time() + days * 86400
        users = load_users()
        if tid not in users:
            users[tid] = {"expire": exp, "username": t, "yt_expire": 0, "lang": "fa"}
        else:
            users[tid]["expire"] = exp
            users[tid]["username"] = t
        save_users(users)
        user_states.pop(chat_id, None)
        await message.reply(T(user_id,"admin_added", days=days), reply_markup=get_reply_menu(ADMIN_ID))

    elif state == "wait_for_yt_user_id":
        user_states[chat_id]["target_user_id"] = t
        user_states[chat_id]["admin_action"] = "wait_for_yt_days"
        await message.reply(T(user_id,"admin_ask_yt_days"))

    elif state == "wait_for_yt_days":
        try:
            days = int(t)
        except ValueError:
            await message.reply("❌"); return
        user_states[chat_id]["target_days"] = days
        user_states[chat_id]["admin_action"] = "wait_for_yt_username"
        await message.reply(T(user_id,"admin_ask_username"))

    elif state == "wait_for_yt_username":
        tid = user_states[chat_id]["target_user_id"]
        days = user_states[chat_id]["target_days"]
        exp = time.time() + days * 86400
        users = load_users()
        if tid not in users:
            users[tid] = {"expire": 0, "username": t, "yt_expire": exp, "lang": "fa"}
        else:
            users[tid]["yt_expire"] = exp
            users[tid]["username"] = t
        save_users(users)
        user_states.pop(chat_id, None)
        await message.reply(T(user_id,"admin_yt_added", days=days), reply_markup=get_reply_menu(ADMIN_ID))

    elif state == "wait_for_delete_id":
        tid = t.strip()
        users = load_users()
        if tid in users:
            # حفظ تنظیمات زبان بعد از حذف اشتراک / Preserve lang setting on delete
            saved_lang = users[tid].get("lang", "fa") if isinstance(users.get(tid), dict) else "fa"
            del users[tid]
            users[tid] = {"expire": 0, "yt_expire": 0, "lang": saved_lang}
            save_users(users)
            user_states.pop(chat_id, None)
            await message.reply(T(user_id,"admin_deleted"), reply_markup=get_reply_menu(ADMIN_ID))
        else:
            user_states.pop(chat_id, None)
            await message.reply(T(user_id,"admin_not_found"), reply_markup=get_reply_menu(ADMIN_ID))

    else:
        message.continue_propagation()

# ================= هندلرهای پردازش =================
@app.on_message(filters.text & filters.regex(r"^https?://|^magnet:\?xt=urn:btih:"))
async def handle_text_links(client, message):
    chat_id = message.chat.id; user_id = message.from_user.id; text = message.text.strip()
    if text.startswith("magnet:"):
        await handle_torrent_download(client, message, text, is_magnet=True); return

    # نادیده گرفتن localhost (کد OAuth گوگل درایو)
    if "localhost" in text.lower():
        return

    is_youtube = "youtube.com" in text.lower() or "youtu.be" in text.lower()
    is_instagram = "instagram.com" in text.lower()

    if is_instagram:
        bot_msg = await message.reply("📸 پست اینستاگرام دریافت شد.", quote=True)
        ts = int(time.time())
        file_name = f"instagram_{ts}"
        state_key = f"{chat_id}_{bot_msg.id}"
        user_states[state_key] = {"type": "youtube", "source": text, "file_name": file_name, "yt_quality": "best"}
        await safe_final_edit(message, bot_msg, "📸 **پست اینستاگرام**\n\nنحوه ارسال را انتخاب کنید:", get_main_keyboard(user_id))
        return

    if is_youtube:
        if not has_yt_access(user_id):
            await message.reply(T(user_id,"no_yt_sub")); return
        allowed, remaining = check_yt_quota(user_id)
        if not allowed:
            await message.reply(T(user_id,"yt_quota_exceeded")); return
        bot_msg = await message.reply(T(user_id,"yt_extracting"), quote=True)
        try:
            async def extract_info():
                # فقط فیلدهای مورد نیاز — بسیار سبک‌تر از --dump-json
                cmd = [YT_DLP,
                       "--print", "%(title)s",
                       "--print", "%(formats.:.{height,filesize,filesize_approx,vcodec,acodec})j",
                       *YT_JS_RUNTIME,"-q","--no-warnings"]
                if os.path.exists(COOKIES_FILE): cmd += ["--cookies", COOKIES_FILE]
                cmd.append(text)
                proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                try:
                    out, err = await asyncio.wait_for(proc.communicate(), timeout=60)
                except asyncio.TimeoutError:
                    proc.kill()
                    raise Exception("timeout")
                if proc.returncode != 0: raise Exception(err.decode()[:200])
                lines = out.decode().strip().split('\n')
                title = lines[0] if lines else 'youtube_video'
                formats = json.loads(lines[1]) if len(lines) > 1 else []
                return title, formats

            title, formats = await extract_info()
            file_name = "".join(c for c in title if c.isalnum() or c in (' ','.','_','-')).strip()
            s360=fmt_size(get_quality_size(formats,360)); s480=fmt_size(get_quality_size(formats,480))
            s720=fmt_size(get_quality_size(formats,720)); s1080=fmt_size(get_quality_size(formats,1080))
            saudio=fmt_size(get_audio_size(formats))
            del formats  # آزاد کردن حافظه
            state_key = f"{chat_id}_{bot_msg.id}"
            user_states[state_key] = {"type":"youtube_pending","source":text,"file_name":file_name}
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🎥 360p ({s360})",callback_data="ytqual_360"),
                 InlineKeyboardButton(f"🎥 480p ({s480})",callback_data="ytqual_480")],
                [InlineKeyboardButton(f"🎥 720p ({s720})",callback_data="ytqual_720"),
                 InlineKeyboardButton(f"🎥 1080p ({s1080})",callback_data="ytqual_1080")],
                [InlineKeyboardButton(T(user_id,"btn_audio_only",size=saudio),callback_data="ytqual_mp3")]
            ])
            await safe_final_edit(message, bot_msg,
                T(user_id,"yt_quality_prompt",title=title,remaining=remaining), kb)
        except Exception as e:
            await safe_final_edit(message, bot_msg, f"❌ خطا: `{e}`")
        return

    bot_msg = await message.reply(T(user_id,"extracting_link"), quote=True)
    file_name = f"file_{int(time.time())}.dat"; final_url = text; is_html = False
    try:
        async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as s:
            async with s.head(final_url, allow_redirects=True) as r:
                size = int(r.headers.get('Content-Length',0))
                if size > 0 and not check_size_limit(size, chat_id):
                    await safe_final_edit(message, bot_msg, T(user_id,"link_too_large")); return
                if 'text/html' in r.headers.get('Content-Type',''): is_html = True
                cd = r.headers.get('Content-Disposition','')
                if cd:
                    m = re.search(r'filename\*?=(?:UTF-8\'\')?([^;]+)', cd, re.IGNORECASE)
                    if m: file_name = urllib.parse.unquote(m.group(1).strip('"\''))
                if file_name.startswith("file_") and not is_html:
                    en = urllib.parse.unquote(os.path.basename(urllib.parse.urlparse(final_url).path))
                    if en: file_name = en
    except: pass
    if is_html:
        await safe_final_edit(message, bot_msg, T(user_id,"no_direct_link")); return
    if chat_id in user_multi_tasks:
        user_multi_tasks[chat_id]["items"].append({"type":"url","source":final_url,"file_name":file_name})
        await safe_final_edit(message, bot_msg, T(user_id,"file_added_multi",count=len(user_multi_tasks[chat_id]['items'])),
                              InlineKeyboardMarkup([[InlineKeyboardButton(T(user_id,"btn_start_op"),callback_data="multi_start")]])); return
    await safe_final_edit(message, bot_msg, T(user_id,"file_name_prompt",name=file_name), get_main_keyboard(user_id))
    user_states[f"{chat_id}_{bot_msg.id}"] = {"type":"url","source":final_url,"file_name":file_name}

@app.on_callback_query(filters.regex("^ytqual_"))
async def yt_quality_callback(client, cq):
    await cq.answer()
    chat_id = cq.message.chat.id; user_id = cq.from_user.id
    quality = cq.data.split("_")[1]; state_key = f"{chat_id}_{cq.message.id}"
    if state_key not in user_states or user_states[state_key].get("type") != "youtube_pending":
        await safe_edit(cq.message, T(user_id,"yt_request_expired")); return
    allowed, _ = check_yt_quota(user_id)
    if not allowed:
        await safe_edit(cq.message, T(user_id,"yt_quota_exceeded_cb")); return
    user_states[state_key]["type"] = "youtube"; user_states[state_key]["yt_quality"] = quality
    file_name = user_states[state_key]["file_name"]
    if chat_id in user_multi_tasks:
        user_multi_tasks[chat_id]["items"].append(user_states.pop(state_key))
        await safe_edit(cq.message, T(user_id,"file_added_multi",count=len(user_multi_tasks[chat_id]['items'])),
                        InlineKeyboardMarkup([[InlineKeyboardButton(T(user_id,"btn_start_op"),callback_data="multi_start")]])); return
    label = T(cq.from_user.id,"audio_only_label") if quality == "mp3" else f"{quality}p"
    await safe_edit(cq.message, T(user_id,"yt_file_ready",name=file_name,quality=label), get_main_keyboard(user_id))

@app.on_message(filters.document | filters.video | filters.audio | filters.voice)
async def handle_media(client, message):
    chat_id = message.chat.id; user_id = message.from_user.id
    media = message.document or message.video or message.audio or message.voice
    if not check_size_limit(getattr(media,"file_size",0), chat_id):
        await message.reply(T(user_id,"file_too_large")); return
    file_name = getattr(media,"file_name",None) or f"file_{int(time.time())}"
    if file_name.lower().endswith(".torrent"):
        await handle_torrent_download(client, message, message, is_magnet=False); return
    bot_msg = await message.reply(T(user_id,"processing"), quote=True)
    if chat_id in user_multi_tasks:
        user_multi_tasks[chat_id]["items"].append({"type":"media","source":message,"file_name":file_name})
        await safe_final_edit(message, bot_msg, T(user_id,"file_added_multi",count=len(user_multi_tasks[chat_id]['items'])),
                              InlineKeyboardMarkup([[InlineKeyboardButton(T(user_id,"btn_start_op"),callback_data="multi_start")]])); return
    await safe_final_edit(message, bot_msg, T(user_id,"file_received",name=file_name), get_main_keyboard(user_id))
    user_states[f"{chat_id}_{bot_msg.id}"] = {"type":"media","source":message,"file_name":file_name}

# ================= هندلر تورنت =================
async def handle_torrent_download(client, message, source, is_magnet=True):
    chat_id = message.chat.id; user_id = message.from_user.id
    sem = get_user_sem(chat_id)
    status_msg = await message.reply(T(user_id,"torrent_metadata"), reply_markup=get_cancel_keyboard(user_id), quote=True)
    if chat_id == ADMIN_ID: await _execute_torrent(client, message, source, is_magnet, status_msg)
    else:
        async with sem:
            await safe_edit(status_msg, T(user_id,"torrent_metadata"), reply_markup=get_cancel_keyboard(user_id))
            await _execute_torrent(client, message, source, is_magnet, status_msg)

async def _execute_torrent(client, message, source, is_magnet, status_msg):
    chat_id = message.chat.id; user_id = message.from_user.id
    cancel_flags[chat_id] = False
    chat_temp_dir = os.path.join(TEMP_DIR, f"torrent_{chat_id}_{int(time.time())}")
    os.makedirs(chat_temp_dir, exist_ok=True)
    ses = lt.session()
    if is_magnet: handle = lt.add_magnet_uri(ses, source, {"save_path": chat_temp_dir})
    else:
        tp = await message.download(file_name=os.path.join(chat_temp_dir,"task.torrent"))
        handle = ses.add_torrent({'ti': lt.torrent_info(tp), 'save_path': chat_temp_dir})
    while not handle.status().has_metadata:
        if cancel_flags.get(chat_id):
            ses.remove_torrent(handle); shutil.rmtree(chat_temp_dir, ignore_errors=True)
            await safe_edit(status_msg, T(user_id,"torrent_cancelled")); return
        await asyncio.sleep(1)
    if not check_size_limit(handle.status().total_wanted, chat_id):
        ses.remove_torrent(handle); shutil.rmtree(chat_temp_dir, ignore_errors=True)
        await safe_edit(status_msg, T(user_id,"torrent_too_large")); return
    while not handle.status().is_seeding:
        if cancel_flags.get(chat_id):
            ses.remove_torrent(handle); shutil.rmtree(chat_temp_dir, ignore_errors=True)
            await safe_edit(status_msg, T(user_id,"torrent_cancelled")); return
        s = handle.status(); pct = s.progress*100
        bar = "■"*int(pct/10)+"□"*(10-int(pct/10))
        await safe_edit(status_msg,
            T(chat_id,"torrent_progress",bar=bar,pct=s.progress*100,
              speed=s.download_rate/1024,done=s.total_wanted_done/(1024*1024),
              total=s.total_wanted/(1024*1024),seeds=s.num_seeds,peers=s.num_peers),
            reply_markup=get_cancel_keyboard(chat_id))
        await asyncio.sleep(5)
    items = [f for f in os.listdir(chat_temp_dir) if f != "task.torrent"]
    final_path = os.path.join(chat_temp_dir, items[0])
    state_key = f"{chat_id}_{status_msg.id}"
    user_states[state_key] = {"type":"local_path","source":final_path,"file_name":items[0],"chat_temp_dir":chat_temp_dir}
    await safe_final_edit(message, status_msg, T(user_id,"torrent_ready"), get_main_keyboard(user_id))

# ================= کال‌بک‌ها =================
@app.on_callback_query(filters.regex("^size_"))
async def size_callback(client, cq):
    await cq.answer()
    chat_id = cq.message.chat.id; user_id = cq.from_user.id; action = cq.data.split("_")[1]
    state_key = f"{chat_id}_{cq.message.id}"
    if state_key not in user_states:
        await safe_edit(cq.message, T(user_id,"file_expired")); return
    user_states[state_key]["action"] = action
    if action == "raw": await execute_with_queue(client, chat_id, state_key)
    elif action == "github": await execute_with_queue(client, chat_id, state_key)
    elif action == "gdrive": await execute_with_queue(client, chat_id, state_key)
    elif action == "split":
        user_states[state_key]["action"] = "split"
        user_states[state_key]["awaiting_split_size"] = True
        await safe_edit(cq.message, T(user_id,"ask_split_size"))
    elif action == "multi":
        user_multi_tasks[chat_id] = {"state_key": state_key, "items": [user_states.pop(state_key)]}
        await safe_edit(cq.message, T(user_id,"first_file_added"),
                        InlineKeyboardMarkup([[InlineKeyboardButton(T(user_id,"btn_start_archive"),callback_data="multi_start")]]))
    else:
        await safe_edit(cq.message, T(user_id,"ask_password"), InlineKeyboardMarkup([
            [InlineKeyboardButton(T(user_id,"btn_no_pass"),callback_data=f"pass_none_{cq.message.id}")],
            [InlineKeyboardButton(T(user_id,"btn_set_pass"),callback_data=f"pass_set_{cq.message.id}")]
        ]))

@app.on_callback_query(filters.regex("^multi_start$"))
async def multi_start_callback(client, cq):
    await cq.answer()
    chat_id = cq.message.chat.id; user_id = cq.from_user.id
    if chat_id not in user_multi_tasks: return
    state_key = user_multi_tasks[chat_id]["state_key"]
    orig_msg_id = state_key.split(f"{chat_id}_", 1)[1]
    user_states[state_key] = {"action":"multi","multi_items":user_multi_tasks[chat_id]["items"]}
    del user_multi_tasks[chat_id]
    await safe_edit(cq.message, T(user_id,"ask_password"), InlineKeyboardMarkup([
        [InlineKeyboardButton(T(user_id,"btn_no_pass"), callback_data=f"pass_none_{orig_msg_id}")],
        [InlineKeyboardButton(T(user_id,"btn_set_pass"), callback_data=f"pass_set_{orig_msg_id}")]
    ]))

@app.on_callback_query(filters.regex("^pass_"))
async def password_callback(client, cq):
    await cq.answer()
    chat_id = cq.message.chat.id; user_id = cq.from_user.id
    parts = cq.data.split("_"); action = parts[1]; msg_id = parts[2]
    state_key = f"{chat_id}_{msg_id}"
    if state_key not in user_states: return
    if action == "none":
        user_states[state_key]["password"] = None; await execute_with_queue(client, chat_id, state_key)
    else:
        user_states[state_key]["awaiting_password"] = True
        await client.send_message(chat_id, T(user_id,"set_password"), reply_markup=ForceReply(selective=True))

@app.on_message(filters.text)
async def get_split_size_input(client, message):
    # دریافت اندازه split از کاربر / Receive split size from user
    chat_id = message.chat.id; user_id = message.from_user.id
    for key, data in list(user_states.items()):
        if str(key).startswith(f"{chat_id}_") and data.get("awaiting_split_size"):
            t = message.text.strip()
            try:
                size = int(t)
                if not (19 <= size <= 900):
                    raise ValueError
            except ValueError:
                await message.reply(T(user_id,"split_invalid"))
                return
            data["awaiting_split_size"] = False
            data["split_size"] = size
            # نمایش منوی رمز عبور / Show password menu
            msg_id = str(key).split(f"{chat_id}_", 1)[1]
            await message.reply(
                T(user_id,"split_ready",size=size) + "\n\n" + T(user_id,"ask_password"),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(T(user_id,"btn_no_pass"),  callback_data=f"pass_none_{msg_id}")],
                    [InlineKeyboardButton(T(user_id,"btn_set_pass"), callback_data=f"pass_set_{msg_id}")]
                ])
            )
            return
    message.continue_propagation()

@app.on_message(filters.text & filters.reply)
async def get_password_input(client, message):
    chat_id = message.chat.id
    for key, data in user_states.items():
        if str(key).startswith(f"{chat_id}_") and data.get("awaiting_password"):
            data["password"] = message.text; data["awaiting_password"] = False
            await execute_with_queue(client, chat_id, key); break

# ================= پردازش نهایی =================
async def execute_with_queue(client, chat_id, state_key):
    data = user_states.pop(state_key, None)
    if not data: return
    sem = get_user_sem(chat_id)
    if sem.locked() and chat_id != ADMIN_ID:
        await client.send_message(chat_id, T(user_id,"queued"))
    if chat_id == ADMIN_ID: asyncio.create_task(core_processing(client, chat_id, data))
    else:
        async with sem: await core_processing(client, chat_id, data)

async def run_yt_cmd(cmd, chat_id):
    proc = await asyncio.create_subprocess_exec(*cmd)
    while True:
        try: await asyncio.wait_for(proc.wait(), timeout=2.0); break
        except asyncio.TimeoutError:
            if cancel_flags.get(chat_id): proc.terminate(); raise ValueError("CANCELLED")
    return proc.returncode

async def _do_github_upload(client, chat_id, data, target_path, chat_base, token, username, repos, remaining_gh, status_msg):
    """منطق اصلی آپلود گیتهاب — فراخوانده میشه از داخل semaphore یا مستقیم برای ادمین"""
    upload_path = target_path

    # اگه target_path دایرکتوری بود (multi) اول zip بساز
    if os.path.isdir(target_path):
        await safe_edit(status_msg, T(chat_id,"preparing_file"))
        zip_path = os.path.join(chat_base, "github_upload.zip")
        proc = await asyncio.create_subprocess_exec(
            "zip", "-r", zip_path, "-j", target_path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()
        upload_path = zip_path

    file_size = os.path.getsize(upload_path)

    # محدودیت ۲ گیگ (ادمین استثناست)
    if file_size > MAX_SIZE_LIMIT and chat_id != ADMIN_ID:
        await safe_edit(status_msg,
            f"❌ **حجم فایل بیشتر از ۲ گیگابایت است ({file_size/(1024**3):.2f} GB)**\n"
            "آپلود به گیتهاب برای فایل‌های تا ۲ گیگابایت مجاز است.")
        return

    repo_name = gh_find_repo(token, username, repos, file_size)
    if not repo_name:
        await safe_edit(status_msg, T(chat_id,"gh_full"))
        return

    links, n_parts = await gh_upload_file(token, username, repo_name, upload_path, status_msg, chat_id)

    # پاکسازی فایل zip موقت
    if upload_path != target_path and os.path.exists(upload_path):
        os.unlink(upload_path)

    quota_line = "" if chat_id == ADMIN_ID else T(chat_id,"gh_quota_line",remaining=remaining_gh-1)

    await safe_edit(status_msg, T(chat_id,"gh_upload_done"))

    # پیام اصلی
    header = T(chat_id,"gh_success_header",repo=repo_name,parts=n_parts,quota=quota_line)
    if n_parts > 1:
        header += T(chat_id,"gh_multipart_note")
    await client.send_message(chat_id, header)

    # ارسال لینک‌ها در پیام‌های جداگانه (محدودیت ۴۰۹۶ کاراکتر تلگرام)
    TG_LIMIT = 4000
    current_msg = T(chat_id,"gh_links_header")
    for idx, link in enumerate(links, 1):
        line = T(chat_id,"gh_part_link",i=idx,url=link)
        if len(current_msg) + len(line) > TG_LIMIT:
            await client.send_message(chat_id, current_msg.strip())
            current_msg = line
        else:
            current_msg += line
    if current_msg.strip():
        await client.send_message(chat_id, current_msg.strip())

    # فایل txt با تمام لینک‌ها برای دانلود منیجر
    txt_path = os.path.join(TEMP_DIR, f"links_{chat_id}_{int(time.time())}.txt")
    with open(txt_path, 'w') as f:
        f.write("\n".join(links))
    await client.send_document(chat_id, txt_path,
        caption=T(chat_id,"gh_links_file_cap"))
    os.unlink(txt_path)

    record_gh_upload(chat_id)
    update_repo_size(username, repo_name, file_size)


async def _do_drive_upload(client, chat_id, data, target_path, chat_base, token, folder_id, remaining_quota, status_msg):
    upload_path = target_path
    if os.path.isdir(target_path):
        await safe_edit(status_msg, T(chat_id,"preparing_file"))
        zip_path = os.path.join(chat_base, "drive_upload.zip")
        proc = await asyncio.create_subprocess_exec("zip", "-r", zip_path, "-j", target_path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()
        upload_path = zip_path
    file_size = os.path.getsize(upload_path)
    if file_size > MAX_SIZE_LIMIT and chat_id != ADMIN_ID:
        await safe_edit(status_msg, T(chat_id,"gd_size_limit",size=file_size/(1024**3))); return
    file_name = os.path.basename(upload_path)
    try:
        file_id, view_url, download_url = await drive_upload_file_stream(
            token, upload_path, file_name, folder_id, status_msg, chat_id)
    finally:
        if upload_path != target_path and os.path.exists(upload_path):
            os.unlink(upload_path)
    if cancel_flags.get(chat_id): raise ValueError("CANCELLED")
    quota_line = "" if chat_id == ADMIN_ID else T(chat_id,"gd_quota_line",remaining=remaining_quota-1)
    result_msg = T(chat_id,"gd_success",name=file_name,quota=quota_line,view=view_url,dl=download_url)
    await safe_edit(status_msg, T(chat_id,"gd_upload_done"))
    await client.send_message(chat_id, result_msg)
    record_drive_upload(chat_id)


async def core_processing(client, chat_id, data):
    action = data.get("action"); password = data.get("password")
    chat_base = os.path.join(TEMP_DIR, f"{chat_id}_{int(time.time())}")
    in_dir = os.path.join(chat_base,"in"); out_dir = os.path.join(chat_base,"out")
    os.makedirs(in_dir, exist_ok=True); os.makedirs(out_dir, exist_ok=True)
    status_msg = await client.send_message(chat_id, T(chat_id,"processing_start"))
    cancel_flags[chat_id] = False; uploaded_ok = False

    try:
        # بررسی سهمیه و اتصال قبل از شروع دانلود
        if action == "gdrive":
            db = load_drive_db(); uid = str(chat_id)
            if uid not in db:
                await safe_edit(status_msg, T(chat_id,"gd_no_account_core")); return
            allowed_d, remaining_d = check_drive_quota(chat_id)
            if not allowed_d:
                await safe_edit(status_msg,
                    T(chat_id,"gd_quota_core",limit=DRIVE_DAILY_LIMIT)); return
        elif action == "github":
            db = load_github_db(); uid = str(chat_id)
            if uid not in db:
                await safe_edit(status_msg, T(chat_id,"gh_no_token_core")); return
            allowed_gh, remaining_gh = check_gh_quota(chat_id)
            if not allowed_gh:
                await safe_edit(status_msg,
                    T(chat_id,"gh_quota_core",limit=GITHUB_DAILY_LIMIT)); return

        target_path = ""
        data_type = data.get("type", "")
        if data_type == "local_path":
            target_path = data["source"]
        elif action == "multi":
            for i, item in enumerate(data["multi_items"], 1):
                p = os.path.join(in_dir, item["file_name"])
                if item["type"] == "media":
                    await client.download_media(item["source"], file_name=p, progress=progress_bar,
                                                progress_args=(status_msg,time.time(),T(chat_id,"receiving_file"),True,chat_id))
                elif item["type"] == "youtube":
                    await safe_edit(status_msg, T(chat_id,"yt_item_download",i=i), reply_markup=get_cancel_keyboard(chat_id))
                    qual = item.get("yt_quality","720")
                    if qual == "mp3":
                        cmd = [YT_DLP,"-f","bestaudio[ext=m4a]/bestaudio",*YT_JS_RUNTIME,"-o",p+".m4a"]
                    else:
                        cmd = [YT_DLP,"-f",f"bestvideo[height<={qual}]+bestaudio/bestvideo+bestaudio/best","--merge-output-format","mp4",*YT_JS_RUNTIME,"-o",p+".mp4"]
                    if os.path.exists(COOKIES_FILE): cmd += ["--cookies",COOKIES_FILE]
                    cmd.append(item["source"])
                    if await run_yt_cmd(cmd, chat_id) != 0: raise ValueError("YOUTUBE_DOWNLOAD_FAILED")
                else:
                    async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as s:
                        async with s.get(item["source"], allow_redirects=True) as r:
                            r.raise_for_status()
                            total = int(r.headers.get('content-length',0))
                            if not check_size_limit(total, chat_id): raise ValueError("SIZE_LIMIT")
                            cur = 0; st = time.time()
                            with open(p,'wb') as f:
                                async for c in r.content.iter_chunked(1024*1024):
                                    if cancel_flags.get(chat_id): raise ValueError("CANCELLED")
                                    cur += len(c)
                                    if not check_size_limit(cur, chat_id): raise ValueError("SIZE_LIMIT")
                                    f.write(c)
                                    if total > 0: await progress_bar(cur,total,status_msg,st,f"دریافت لینک {i}",True)
            target_path = in_dir
        else:
            yt_quality = data.get("yt_quality","720")
            is_yt = data_type == "youtube"
            is_audio = is_yt and yt_quality == "mp3"
            is_best = is_yt and yt_quality == "best"  # اینستاگرام
            if data_type == "media":
                target_path = os.path.join(in_dir, data["file_name"])
                await client.download_media(data["source"], file_name=target_path, progress=progress_bar,
                                            progress_args=(status_msg,time.time(),T(chat_id,"receiving_file"),True,chat_id))
            elif is_yt:
                label = T(chat_id,"audio_only_label") if is_audio else f"{yt_quality}p"
                await safe_edit(status_msg, T(chat_id,"yt_downloading",quality=label), reply_markup=get_cancel_keyboard(chat_id))
                if is_audio:
                    target_path = os.path.join(in_dir, data["file_name"]+".m4a")
                    cmd = [YT_DLP,"-f","bestaudio[ext=m4a]/bestaudio",*YT_JS_RUNTIME,"-o",target_path]
                elif is_best:
                    target_path = os.path.join(in_dir, data["file_name"]+".mp4")
                    cmd = [YT_DLP,"-f","bestvideo+bestaudio/best","--merge-output-format","mp4",*YT_JS_RUNTIME,
                           "--extractor-args","instagram:direct=1;app_id=936619743392459",
                           "-o",target_path]
                else:
                    target_path = os.path.join(in_dir, data["file_name"]+".mp4")
                    cmd = [YT_DLP,"-f",f"bestvideo[height<={yt_quality}]+bestaudio/bestvideo+bestaudio/best","--merge-output-format","mp4",*YT_JS_RUNTIME,"-o",target_path]
                if os.path.exists(COOKIES_FILE): cmd += ["--cookies",COOKIES_FILE]
                cmd.append(data["source"])
                if await run_yt_cmd(cmd, chat_id) != 0:
                    if is_best:
                        raise ValueError("INSTAGRAM_FAILED")
                    raise ValueError("YOUTUBE_DOWNLOAD_FAILED")
                    cands = [os.path.join(in_dir,f) for f in os.listdir(in_dir)]
                    if cands: target_path = cands[0]
                if os.path.exists(target_path) and not check_size_limit(os.path.getsize(target_path), chat_id):
                    raise ValueError("SIZE_LIMIT")
            else:
                target_path = os.path.join(in_dir, data["file_name"])
                async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as s:
                    async with s.get(data["source"], allow_redirects=True) as r:
                        r.raise_for_status()
                        total = int(r.headers.get('content-length',0))
                        if not check_size_limit(total, chat_id): raise ValueError("SIZE_LIMIT")
                        cur = 0; st = time.time()
                        with open(target_path,'wb') as f:
                            async for c in r.content.iter_chunked(1024*1024):
                                if cancel_flags.get(chat_id): raise ValueError("CANCELLED")
                                cur += len(c)
                                if not check_size_limit(cur, chat_id): raise ValueError("SIZE_LIMIT")
                                f.write(c)
                                if total > 0: await progress_bar(cur,total,status_msg,st,T(chat_id,"receiving_file"),True,chat_id)

        # ================= ارسال =================
        if action == "github":
            db = load_github_db(); uid = str(chat_id)
            if uid not in db:
                await safe_edit(status_msg, T(chat_id,"gh_no_token_core")); return
            gh = db[uid]; token = gh["token"]; username = gh["username"]; repos = gh.get("repos",[])

            # بررسی سهمیه روزانه
            allowed_gh, remaining_gh = check_gh_quota(chat_id)
            if not allowed_gh:
                await safe_edit(status_msg,
                    T(chat_id,"gh_quota_core",limit=GITHUB_DAILY_LIMIT)); return

            # صف جهانی گیتهاب — حداکثر ۴ آپلود همزمان (ادمین بدون محدودیت)
            if chat_id != ADMIN_ID:
                if GITHUB_GLOBAL_SEM.locked():
                    await safe_edit(status_msg,
                        T(chat_id,"gh_queued"),
                        reply_markup=get_cancel_keyboard(chat_id))
                async with GITHUB_GLOBAL_SEM:
                    await _do_github_upload(
                        client, chat_id, data, target_path, chat_base,
                        token, username, repos, remaining_gh, status_msg)
                    uploaded_ok = True
            else:
                await _do_github_upload(
                    client, chat_id, data, target_path, chat_base,
                    token, username, repos, remaining_gh, status_msg)
                uploaded_ok = True

        elif action == "gdrive":
            db = load_drive_db(); uid = str(chat_id)
            if uid not in db:
                await safe_edit(status_msg, T(chat_id,"gd_no_account_core")); return
            allowed_d, remaining_d = check_drive_quota(chat_id)
            if not allowed_d:
                await safe_edit(status_msg,
                    T(chat_id,"gd_quota_core",limit=DRIVE_DAILY_LIMIT)); return
            token = await get_valid_drive_token(chat_id)
            if not token:
                await safe_edit(status_msg, T(chat_id,"gd_auth_error_core")); return
            folder_id = db[uid].get("folder_id")
            if not folder_id:
                try:
                    folder_id = await drive_get_or_create_folder(token)
                    db[uid]["folder_id"] = folder_id; save_drive_db(db)
                except:
                    await safe_edit(status_msg, T(chat_id,"gd_folder_error")); return
            if chat_id != ADMIN_ID:
                if DRIVE_GLOBAL_SEM.locked():
                    await safe_edit(status_msg,
                        T(chat_id,"gd_queued"),
                        reply_markup=get_cancel_keyboard(chat_id))
                async with DRIVE_GLOBAL_SEM:
                    await _do_drive_upload(client, chat_id, data, target_path, chat_base,
                                           token, folder_id, remaining_d, status_msg)
                    uploaded_ok = True
            else:
                await _do_drive_upload(client, chat_id, data, target_path, chat_base,
                                       token, folder_id, remaining_d, status_msg)
                uploaded_ok = True

        elif action == "raw":
            ext = os.path.splitext(target_path)[1].lower()
            await safe_edit(status_msg, T(chat_id,"sending"))
            if ext in ('.mp4','.mkv','.mov','.avi','.webm'):
                await client.send_video(chat_id, target_path, progress=progress_bar,
                                        progress_args=(status_msg,time.time(),T(chat_id,"sending_video"),False,chat_id))
            elif ext in ('.mp3','.m4a','.ogg','.opus','.flac','.wav'):
                await client.send_audio(chat_id, target_path, progress=progress_bar,
                                        progress_args=(status_msg,time.time(),T(chat_id,"sending_audio"),False,chat_id))
            else:
                await client.send_document(chat_id, target_path, progress=progress_bar,
                                           progress_args=(status_msg,time.time(),T(chat_id,"sending_file"),False,chat_id))
            uploaded_ok = True
        else:
            final_source = target_path
            await safe_edit(status_msg, T(chat_id,"compressing_rar"))
            archive_path = os.path.join(out_dir,"Mega-Leecher.rar")
            cmd = ["rar","a","-ep1","-m0","-rr5p",archive_path]
            if action == "split":
                cmd.append(f"-v{data.get('split_size',100)}m")
            elif action not in ["full","multi"]: cmd.append(f"-v{action}m")
            if password: cmd.append(f"-hp{password}")
            if action == "multi": cmd += [os.path.join(in_dir,f) for f in os.listdir(in_dir)]
            elif os.path.isdir(final_source): cmd.append(f"{final_source}/*")
            else: cmd.append(final_source)
            proc = await asyncio.create_subprocess_exec(*cmd, stdin=asyncio.subprocess.DEVNULL,
                                                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc.communicate()
            parts = sorted([os.path.join(out_dir,f) for f in os.listdir(out_dir)])
            for i, p in enumerate(parts,1):
                cap = T(chat_id,"sending_part",i=i,total=len(parts)) if len(parts) > 1 else T(chat_id,"final_file")
                await client.send_document(chat_id, p, caption=cap, progress=progress_bar,
                                           progress_args=(status_msg,time.time(),T(chat_id,"sending_part",i=i,total=len(parts)),False,chat_id))
            uploaded_ok = True

        if uploaded_ok and data_type == "youtube":
            record_yt_download(chat_id)

        await safe_final_edit(status_msg, status_msg, T(chat_id,"done"))

    except ValueError as e:
        msgs = {
            "CANCELLED": T(chat_id,"cancelled"),
            "SIZE_LIMIT": T(chat_id,"size_limit"),
            "YOUTUBE_DOWNLOAD_FAILED": T(chat_id,"error_generic",e="YouTube download failed")
        }
        await client.send_message(chat_id, T(chat_id,"error_generic",e=e))
    finally:
        shutil.rmtree(chat_base, ignore_errors=True)
        if "chat_temp_dir" in data: shutil.rmtree(data["chat_temp_dir"], ignore_errors=True)

if __name__ == "__main__":
    app.run()
