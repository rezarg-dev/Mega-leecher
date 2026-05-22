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

MAX_SIZE_LIMIT     = 2 * 1024 * 1024 * 1024
YT_DAILY_LIMIT     = 10
GITHUB_DAILY_LIMIT = 10
DRIVE_DAILY_LIMIT  = 10

GITHUB_CHUNK_SIZE  = 95 * 1024 * 1024
GITHUB_REPO_MAX    = 5  * 1024 * 1024 * 1024
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

def init_databases():
    for db_file in [DB_FILE, GITHUB_DB_FILE, DRIVE_DB_FILE]:
        if not os.path.exists(db_file):
            with open(db_file, 'w') as f:
                json.dump({}, f)

init_databases()

# ── Access control ────────────────────────────────────────────────────────────
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

def has_drive_connected(user_id):
    return str(user_id) in load_drive_db()

def check_size_limit(size, user_id):
    if user_id == ADMIN_ID: return True
    return size <= MAX_SIZE_LIMIT

def get_user_sem(user_id):
    if user_id not in user_semaphores: user_semaphores[user_id] = asyncio.Semaphore(1)
    return user_semaphores[user_id]

# ── YouTube quota ─────────────────────────────────────────────────────────────
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

# ── UI helpers ────────────────────────────────────────────────────────────────
async def safe_edit(msg, text, reply_markup=None):
    try: await msg.edit_text(text, reply_markup=reply_markup)
    except: pass

async def safe_final_edit(message, bot_msg, text, reply_markup=None):
    try: await bot_msg.edit_text(text, reply_markup=reply_markup)
    except:
        try: await message.reply(text, reply_markup=reply_markup)
        except: pass

def get_cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو عملیات", callback_data="cancel_task")]])

def get_main_keyboard(user_id=None):
    kb = [
        [InlineKeyboardButton("ارسال فایل خام (بدون تغییر)", callback_data="size_raw")],
        [InlineKeyboardButton("ارسال به صورت تک فایل RAR", callback_data="size_full")],
        [InlineKeyboardButton("ایجاد آرشیو چند فایلی", callback_data="size_multi")],
        [InlineKeyboardButton("پارت‌های ۱۹ مگ", callback_data="size_19"),
         InlineKeyboardButton("پارت‌های ۴۰ مگ", callback_data="size_40"),
         InlineKeyboardButton("پارت‌های ۹۰۰ مگ", callback_data="size_900")]
    ]
    if user_id and has_github_token(user_id):
        kb.append([InlineKeyboardButton("☁️ آپلود به گیتهاب", callback_data="size_github")])
    if user_id and has_drive_connected(user_id):
        kb.append([InlineKeyboardButton("📂 آپلود به گوگل درایو", callback_data="size_gdrive")])
    return InlineKeyboardMarkup(kb)

def get_reply_menu(user_id):
    keyboard = [
        [KeyboardButton("🌐 راهنمای لینک مستقیم"), KeyboardButton("🧲 راهنمای تورنت")],
        [KeyboardButton("📁 راهنمای کار با فایل‌های تلگرامی"), KeyboardButton("🎬 راهنمای دانلود از یوتوب")],
        [KeyboardButton("☁️ اتصال به گیتهاب"), KeyboardButton("📂 اتصال به گوگل درایو")]
    ]
    if user_id == ADMIN_ID:
        keyboard += [[KeyboardButton("➕ افزودن کاربر"), KeyboardButton("➖ حذف کاربر")],
                     [KeyboardButton("➕ افزودن کاربر یوتوب"), KeyboardButton("📋 لیست کاربران")],
                     [KeyboardButton("🧹 پاکسازی ربات")]]
    else:
        keyboard.append([KeyboardButton("🛒 خرید / تمدید اشتراک")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, placeholder="انتخاب کنید...")

async def progress_bar(current, total, status_msg, start_time, action_text, is_cancellable=False):
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
        f"وضعیت: {action_text}\n[{bar}] {pct:.1f}%\nسرعت: {speed:.1f} KB/s\n"
        f"حجم: {current/(1024*1024):.1f}MB از {total/(1024*1024):.1f}MB",
        get_cancel_keyboard() if is_cancellable else None)

# ── Access guard middleware ────────────────────────────────────────────────────
@app.on_message(filters.all & filters.incoming, group=-1)
async def access_checker_middleware(client, message):
    if not message.from_user: return
    try:
        msg_ts = message.date.timestamp() if hasattr(message.date,'timestamp') else float(message.date)
    except: msg_ts = BOT_START_TIME + 1
    if msg_ts < BOT_START_TIME:
        message.stop_propagation(); return
    chat_id = message.chat.id; user_id = message.from_user.id; text = message.text or ""
    allowed = ["/start","🌐 راهنمای لینک مستقیم","🧲 راهنمای تورنت","📁 راهنمای کار با فایل‌های تلگرامی",
               "🎬 راهنمای دانلود از یوتوب","🛒 خرید / تمدید اشتراک","☁️ اتصال به گیتهاب","📂 اتصال به گوگل درایو"]
    if chat_id in user_states and user_states[chat_id].get("admin_action"): return
    if text in allowed: return
    if f"gh_{chat_id}" in user_states: return
    if f"gd_{chat_id}" in user_states: return
    if not has_access(user_id):
        await message.reply(f"⛔️ **شما هیچ اشتراک فعالی ندارید!**\n\nبرای خرید:\n👤 {PURCHASE_USERNAME}\n🆔 `{user_id}`")
        message.stop_propagation()

# ── /start ────────────────────────────────────────────────────────────────────
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply(
        "👋 **خوش آمدید به Mega Leecher!**\n\n"
        "🤖 ابزار حرفه‌ای برای دانلود، پردازش و مدیریت فایل در تلگرام\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "📦 **پردازش فایل:**\n"
        "• تقسیم به پارت‌های ۱۹، ۴۰ یا ۹۰۰ مگابایتی\n"
        "• فشرده‌سازی RAR با رمز عبور دلخواه\n"
        "• ارسال فایل خام بدون تغییر\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "⬇️ **دانلود:**\n"
        "• دانلود از لینک مستقیم\n"
        "• دانلود از تورنت (مگنت یا .torrent)\n"
        "• دانلود از یوتوب تا کیفیت 1080p\n"
        "• دانلود فقط صدا (MP3)\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "☁️ **فضای ابری رایگان:**\n"
        "• آپلود به گیتهاب — تا ۱۵ گیگابایت\n"
        "• آپلود به گوگل درایو — تا ۱۵ گیگابایت\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "📋 از منوی پایین استفاده کنید 👇",
        reply_markup=get_reply_menu(message.from_user.id)
    )

# ── User menus ────────────────────────────────────────────────────────────────
@app.on_message(filters.text & filters.regex("^(🌐 راهنمای لینک مستقیم|🧲 راهنمای تورنت|📁 راهنمای کار با فایل‌های تلگرامی|🎬 راهنمای دانلود از یوتوب|🛒 خرید / تمدید اشتراک)$"))
async def handle_user_menus(client, message):
    t = message.text; uid = message.from_user.id
    if "لینک مستقیم" in t:
        await message.reply(
            "**🌐 راهنمای دانلود از لینک مستقیم:**\n\n"
            "کافیه لینک دانلود فایل رو مستقیم داخل چت بفرستید.\n\n"
            "📌 **چه لینک‌هایی پشتیبانی میشن؟**\n"
            "• هر لینکی که مستقیم به یه فایل اشاره کنه\n"
            "• ویدیو، موزیک، زیپ، PDF، APK، EXE و هر فرمت دیگه‌ای\n"
            "• حجم دانلود تا **۲ گیگابایت**\n\n"
            "⚙️ **بعد از دانلود:**\n"
            "• 📤 ارسال فایل خام\n"
            "• 🗜 فشرده‌سازی RAR با یا بدون رمز\n"
            "• ✂️ تقسیم به پارت‌های ۱۹، ۴۰ یا ۹۰۰ مگابایتی\n"
            "• ☁️ آپلود به گیتهاب یا گوگل درایو"
        )
    elif "تورنت" in t:
        await message.reply(
            "**🧲 راهنمای دانلود تورنت:**\n\n"
            "۱. **لینک مگنت** — لینکی که با `magnet:?xt=` شروع میشه رو بفرستید\n"
            "۲. **فایل .torrent** — فایل رو آپلود کنید\n\n"
            "📌 **نکات:**\n"
            "• اگه تورنت سید نداشته باشه دانلود کند یا ناقص میشه\n"
            "• حجم تا **۲ گیگابایت**\n"
            "• درخواست‌ها به صورت صف پردازش میشن"
        )
    elif "فایل‌های تلگرامی" in t:
        await message.reply(
            "**📁 راهنمای کار با فایل‌های تلگرامی:**\n\n"
            "فایل رو **فوروارد** کنید یا مستقیم **آپلود** کنید.\n\n"
            "📌 **قابلیت‌ها:**\n"
            "• تمام فرمت‌ها پشتیبانی میشن\n"
            "• فایل‌های فشرده رمزدار بدون نیاز به رمز پارت‌بندی میشن\n"
            "• چند فایل رو میتونید در یک آرشیو RAR دریافت کنید\n"
            "• حجم تا **۲ گیگابایت**"
        )
    elif "یوتوب" in t:
        await message.reply(
            "**🎬 راهنمای دانلود از یوتوب:**\n\n"
            "لینک ویدیو رو مستقیم بفرستید.\n\n"
            "📌 **کیفیت‌ها:** 360p • 480p • 720p • 1080p • 🎵 فقط صدا\n\n"
            "🔢 سهمیه روزانه: **۱۰ ویدیو** در هر ۲۴ ساعت"
        )
    elif "خرید" in t:
        users = load_users()
        uid_str = str(uid)
        if has_access(uid) and uid_str in users and isinstance(users[uid_str], dict):
            expire = users[uid_str].get("expire", 0)
            if expire > time.time():
                rem_days = int((expire - time.time()) // 86400)
                await message.reply(f"✅ **اشتراک فعال**\n\n⏳ روزهای باقیمانده: **{rem_days} روز**")
            else:
                await message.reply(f"⛔️ جهت تمدید به {PURCHASE_USERNAME} پیام دهید.\n🆔 `{uid}`")
        else:
            await message.reply(f"⛔️ جهت خرید اشتراک به {PURCHASE_USERNAME} پیام دهید.\n🆔 `{uid}`")

# ── Cancel callback ───────────────────────────────────────────────────────────
@app.on_callback_query(filters.regex("^cancel_task$"))
async def cancel_callback(client, cq):
    cancel_flags[cq.message.chat.id] = True
    await cq.answer("⚠️ درخواست لغو ثبت شد.", show_alert=True)

# ── Admin panel ───────────────────────────────────────────────────────────────
USERS_PER_PAGE = 5

async def send_user_list_page(chat_id, active_users, page, client, send_new=False, message_id=None):
    total = len(active_users)
    total_pages = (total + USERS_PER_PAGE - 1) // USERS_PER_PAGE
    start = page * USERS_PER_PAGE
    end = min(start + USERS_PER_PAGE, total)
    page_users = active_users[start:end]
    text = f"📋 **لیست کاربران** — صفحه {page+1} از {total_pages} (جمع: {total} نفر)\n"
    text += "━━━━━━━━━━━━━━━━━\n\n"
    for i, u in enumerate(page_users, start + 1):
        text += (
            f"**{i}.** 👤 {u['uname']}\n"
            f"  🆔 `{u['uid']}`\n"
            f"  ⏳ اشتراک: **{u['rd']} روز**\n"
            f"  🎬 یوتوب: **{u['ytd']} روز**\n"
            f"━━━━━━━━━━━━━━━━━\n"
        )
    buttons = []
    row = []
    if page > 0:
        row.append(InlineKeyboardButton("→ قبلی", callback_data=f"ulist_{page-1}"))
    if page < total_pages - 1:
        row.append(InlineKeyboardButton("بعدی ←", callback_data=f"ulist_{page+1}"))
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

@app.on_message(filters.text & filters.regex("^(➕ افزودن کاربر|➕ افزودن کاربر یوتوب|📋 لیست کاربران|➖ حذف کاربر|🧹 پاکسازی ربات)$") & filters.user(ADMIN_ID))
async def admin_menu_handler(client, message):
    t = message.text; chat_id = message.chat.id
    if t == "📋 لیست کاربران":
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
            await message.reply("هیچ کاربر فعالی وجود ندارد."); return
        await send_user_list_page(message.chat.id, active, page=0, client=client, send_new=True)
    elif t == "➕ افزودن کاربر":
        user_states[chat_id] = {"admin_action": "wait_for_user_id"}
        await message.reply("آیدی عددی کاربر:", reply_markup=ReplyKeyboardMarkup([["انصراف"]], resize_keyboard=True))
    elif t == "➕ افزودن کاربر یوتوب":
        user_states[chat_id] = {"admin_action": "wait_for_yt_user_id"}
        await message.reply("آیدی عددی کاربر یوتوب:", reply_markup=ReplyKeyboardMarkup([["انصراف"]], resize_keyboard=True))
    elif t == "➖ حذف کاربر":
        user_states[chat_id] = {"admin_action": "wait_for_delete_id"}
        await message.reply("آیدی عددی کاربر:", reply_markup=ReplyKeyboardMarkup([["انصراف"]], resize_keyboard=True))
    elif t == "🧹 پاکسازی ربات":
        for f in os.listdir(TEMP_DIR):
            fp = os.path.join(TEMP_DIR, f)
            try:
                if os.path.isfile(fp): os.unlink(fp)
                elif os.path.isdir(fp): shutil.rmtree(fp)
            except: pass
        await message.reply("✅ پاکسازی شد.", reply_markup=get_reply_menu(ADMIN_ID))

@app.on_message(filters.text & filters.user(ADMIN_ID))
async def admin_states_handler(client, message):
    chat_id = message.chat.id; t = message.text
    state = user_states.get(chat_id, {}).get("admin_action")
    if t == "انصراف" and state:
        user_states.pop(chat_id, None); await message.reply("لغو شد.", reply_markup=get_reply_menu(ADMIN_ID)); return
    if state == "wait_for_user_id":
        user_states[chat_id]["target_user_id"] = t; user_states[chat_id]["admin_action"] = "wait_for_days"
        await message.reply("تعداد روزهای اشتراک:")
    elif state == "wait_for_days":
        user_states[chat_id]["target_days"] = int(t); user_states[chat_id]["admin_action"] = "wait_for_username"
        await message.reply("آیدی نوشتاری:")
    elif state == "wait_for_username":
        tid = user_states[chat_id]["target_user_id"]; days = user_states[chat_id]["target_days"]
        exp = time.time()+days*86400; users = load_users()
        if tid not in users: users[tid] = {"expire":exp,"username":t,"yt_expire":0}
        else: users[tid]["expire"]=exp; users[tid]["username"]=t
        save_users(users); user_states.pop(chat_id, None)
        await message.reply(f"✅ اضافه شد. اعتبار: {days} روز.", reply_markup=get_reply_menu(ADMIN_ID))
    elif state == "wait_for_yt_user_id":
        user_states[chat_id]["target_user_id"] = t; user_states[chat_id]["admin_action"] = "wait_for_yt_days"
        await message.reply("تعداد روزهای اشتراک یوتوب:")
    elif state == "wait_for_yt_days":
        user_states[chat_id]["target_days"] = int(t); user_states[chat_id]["admin_action"] = "wait_for_yt_username"
        await message.reply("آیدی نوشتاری:")
    elif state == "wait_for_yt_username":
        tid = user_states[chat_id]["target_user_id"]; days = user_states[chat_id]["target_days"]
        exp = time.time()+days*86400; users = load_users()
        if tid not in users: users[tid] = {"expire":0,"username":t,"yt_expire":exp}
        else: users[tid]["yt_expire"]=exp; users[tid]["username"]=t
        save_users(users); user_states.pop(chat_id, None)
        await message.reply(f"✅ دسترسی یوتوب. اعتبار: {days} روز.", reply_markup=get_reply_menu(ADMIN_ID))
    elif state == "wait_for_delete_id":
        tid = t.strip(); users = load_users()
        if tid in users:
            del users[tid]; save_users(users); user_states.pop(chat_id, None)
            await message.reply("✅ دسترسی لغو شد.", reply_markup=get_reply_menu(ADMIN_ID))
        else:
            user_states.pop(chat_id, None); await message.reply("❌ یافت نشد.", reply_markup=get_reply_menu(ADMIN_ID))
    else: message.continue_propagation()


# ── File size helpers ─────────────────────────────────────────────────────────
def fmt_size(s):
    if not s: return "نامشخص"
    mb = s/(1024*1024)
    return f"{s//1024}KB" if mb < 1 else f"~{mb:.0f}MB"

# ── Media handler ─────────────────────────────────────────────────────────────
@app.on_message(filters.document | filters.video | filters.audio | filters.voice)
async def handle_media(client, message):
    chat_id = message.chat.id; user_id = message.from_user.id
    media = message.document or message.video or message.audio or message.voice
    if not check_size_limit(getattr(media, "file_size", 0), chat_id):
        await message.reply("❌ فایل‌های بیشتر از 2 گیگابایت مجاز نیست."); return
    file_name = getattr(media, "file_name", None) or f"file_{int(time.time())}"
    if file_name.lower().endswith(".torrent"):
        await handle_torrent_download(client, message, message, is_magnet=False); return
    bot_msg = await message.reply("⏳ در حال پردازش...", quote=True)
    if chat_id in user_multi_tasks:
        user_multi_tasks[chat_id]["items"].append({"type": "media", "source": message, "file_name": file_name})
        await safe_final_edit(message, bot_msg,
            f"افزوده شد. (مجموع: {len(user_multi_tasks[chat_id]['items'])})",
            InlineKeyboardMarkup([[InlineKeyboardButton("شروع عملیات", callback_data="multi_start")]])); return
    await safe_final_edit(message, bot_msg, f"فایل دریافت شد: `{file_name}`", get_main_keyboard(user_id))
    user_states[f"{chat_id}_{bot_msg.id}"] = {"type": "media", "source": message, "file_name": file_name}

# ── Size callback ─────────────────────────────────────────────────────────────
@app.on_callback_query(filters.regex("^size_"))
async def size_callback(client, cq):
    await cq.answer()
    chat_id = cq.message.chat.id; action = cq.data.split("_")[1]
    state_key = f"{chat_id}_{cq.message.id}"
    if state_key not in user_states:
        await safe_edit(cq.message, "❌ فایل منقضی شده، دوباره ارسال کنید."); return
    user_states[state_key]["action"] = action
    if action == "raw":
        await execute_with_queue(client, chat_id, state_key)
    elif action == "github":
        await execute_with_queue(client, chat_id, state_key)
    elif action == "gdrive":
        await execute_with_queue(client, chat_id, state_key)
    elif action == "multi":
        user_multi_tasks[chat_id] = {"state_key": state_key, "items": [user_states.pop(state_key)]}
        await safe_edit(cq.message, "فایل اول اضافه شد. بعدی‌ها را فوروارد کنید.",
            InlineKeyboardMarkup([[InlineKeyboardButton("شروع آرشیو", callback_data="multi_start")]]))
    else:
        await safe_edit(cq.message, "رمز گذاشته شود؟", InlineKeyboardMarkup([
            [InlineKeyboardButton("بدون رمز", callback_data=f"pass_none_{cq.message.id}")],
            [InlineKeyboardButton("تعیین رمز عبور", callback_data=f"pass_set_{cq.message.id}")]
        ]))

@app.on_callback_query(filters.regex("^multi_start$"))
async def multi_start_callback(client, cq):
    await cq.answer()
    chat_id = cq.message.chat.id
    if chat_id not in user_multi_tasks: return
    state_key = user_multi_tasks[chat_id]["state_key"]
    user_states[state_key] = {"action": "multi", "multi_items": user_multi_tasks[chat_id]["items"]}
    del user_multi_tasks[chat_id]
    await safe_edit(cq.message, "رمز عبور؟", InlineKeyboardMarkup([
        [InlineKeyboardButton("بدون رمز", callback_data=f"pass_none_{cq.message.id}")],
        [InlineKeyboardButton("تعیین رمز", callback_data=f"pass_set_{cq.message.id}")]
    ]))

@app.on_callback_query(filters.regex("^pass_"))
async def password_callback(client, cq):
    await cq.answer()
    chat_id = cq.message.chat.id
    parts = cq.data.split("_"); action = parts[1]; msg_id = parts[2]
    state_key = f"{chat_id}_{msg_id}"
    if state_key not in user_states: return
    if action == "none":
        user_states[state_key]["password"] = None
        await execute_with_queue(client, chat_id, state_key)
    else:
        user_states[state_key]["awaiting_password"] = True
        await client.send_message(chat_id, "رمز را بفرستید:", reply_markup=ForceReply(selective=True))

@app.on_message(filters.text & filters.reply)
async def get_password_input(client, message):
    chat_id = message.chat.id
    for key, data in user_states.items():
        if str(key).startswith(f"{chat_id}_") and data.get("awaiting_password"):
            data["password"] = message.text; data["awaiting_password"] = False
            await execute_with_queue(client, chat_id, key); break

# ── Queue & processing ────────────────────────────────────────────────────────
async def execute_with_queue(client, chat_id, state_key):
    data = user_states.pop(state_key, None)
    if not data: return
    sem = get_user_sem(chat_id)
    if sem.locked() and chat_id != ADMIN_ID:
        await client.send_message(chat_id, "⏳ درخواست در صف قرار گرفت...")
    if chat_id == ADMIN_ID:
        asyncio.create_task(core_processing(client, chat_id, data))
    else:
        async with sem:
            await core_processing(client, chat_id, data)

async def core_processing(client, chat_id, data):
    action = data.get("action"); password = data.get("password")
    chat_base = os.path.join(TEMP_DIR, f"{chat_id}_{int(time.time())}")
    in_dir = os.path.join(chat_base, "in"); out_dir = os.path.join(chat_base, "out")
    os.makedirs(in_dir, exist_ok=True); os.makedirs(out_dir, exist_ok=True)
    status_msg = await client.send_message(chat_id, "در حال شروع پردازش...")
    cancel_flags[chat_id] = False; uploaded_ok = False

    try:
        target_path = ""

        # ── بررسی سهمیه قبل از دانلود ────────────────────────────────────────────
        if action == "gdrive":
            db = load_drive_db(); uid = str(chat_id)
            if uid not in db:
                await safe_edit(status_msg, "❌ حساب گوگل متصل نشده.
از منوی 📂 اتصال به گوگل درایو متصل شوید."); return
            allowed_d, remaining_d = check_drive_quota(chat_id)
            if not allowed_d:
                await safe_edit(status_msg,
                    f"⛔️ **سهمیه روزانه آپلود به گوگل درایو تمام شده!**
"
                    f"هر کاربر روزانه {DRIVE_DAILY_LIMIT} آپلود مجاز است."); return
        elif action == "github":
            db = load_github_db(); uid = str(chat_id)
            if uid not in db:
                await safe_edit(status_msg, "❌ توکن گیتهاب تنظیم نشده.
از منوی ☁️ اتصال به گیتهاب توکن وارد کنید."); return
            allowed_gh, remaining_gh = check_gh_quota(chat_id)
            if not allowed_gh:
                await safe_edit(status_msg,
                    f"⛔️ **سهمیه روزانه آپلود به گیتهاب تمام شده!**
"
                    f"هر کاربر روزانه {GITHUB_DAILY_LIMIT} آپلود مجاز است.
"
                    "سهمیه به صورت rolling در ۲۴ ساعت تجدید می‌شود."); return

        # ── دریافت فایل ──────────────────────────────────────────────────────────
        if data["type"] == "local_path":
            target_path = data["source"]
        elif data["type"] == "media":
            target_path = os.path.join(in_dir, data["file_name"])
            await client.download_media(data["source"], file_name=target_path,
                progress=progress_bar, progress_args=(status_msg, time.time(), "دریافت فایل", True))
        elif data["type"] == "url":
            target_path = os.path.join(in_dir, data["file_name"])
            async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as s:
                async with s.get(data["source"], allow_redirects=True) as r:
                    r.raise_for_status()
                    total = int(r.headers.get('content-length', 0))
                    if not check_size_limit(total, chat_id): raise ValueError("SIZE_LIMIT")
                    cur = 0; st = time.time()
                    with open(target_path, 'wb') as f:
                        async for c in r.content.iter_chunked(1024 * 1024):
                            if cancel_flags.get(chat_id): raise ValueError("CANCELLED")
                            cur += len(c)
                            if not check_size_limit(cur, chat_id): raise ValueError("SIZE_LIMIT")
                            f.write(c)
                            if total > 0:
                                await progress_bar(cur, total, status_msg, st, "دریافت فایل", True)
        elif data["type"] == "youtube":
            yt_quality = data.get("yt_quality", "720")
            is_audio   = yt_quality == "mp3"
            label      = "صدا" if is_audio else f"{yt_quality}p"
            await safe_edit(status_msg, f"در حال دانلود ({label})...", reply_markup=get_cancel_keyboard())
            if is_audio:
                target_path = os.path.join(in_dir, data["file_name"] + ".m4a")
                cmd = ["yt-dlp", "-f", "bestaudio[ext=m4a]/bestaudio", "-o", target_path]
            else:
                target_path = os.path.join(in_dir, data["file_name"] + ".mp4")
                cmd = ["yt-dlp", "-f",
                       f"bestvideo[height<={yt_quality}]+bestaudio/bestvideo+bestaudio/best",
                       "--merge-output-format", "mp4", "-o", target_path]
            if os.path.exists(COOKIES_FILE): cmd += ["--cookies", COOKIES_FILE]
            cmd.append(data["source"])
            if await run_yt_cmd(cmd, chat_id) != 0:
                raise ValueError("YOUTUBE_DOWNLOAD_FAILED")
            if os.path.exists(target_path) and not check_size_limit(os.path.getsize(target_path), chat_id):
                raise ValueError("SIZE_LIMIT")

        # ── ارسال ────────────────────────────────────────────────────────────
        if action == "raw":
            ext = os.path.splitext(target_path)[1].lower()
            await safe_edit(status_msg, "در حال ارسال...")
            if ext in ('.mp4', '.mkv', '.mov', '.avi', '.webm'):
                await client.send_video(chat_id, target_path, progress=progress_bar,
                    progress_args=(status_msg, time.time(), "ارسال ویدیو", False))
            elif ext in ('.mp3', '.m4a', '.ogg', '.opus', '.flac', '.wav'):
                await client.send_audio(chat_id, target_path, progress=progress_bar,
                    progress_args=(status_msg, time.time(), "ارسال صدا", False))
            else:
                await client.send_document(chat_id, target_path, progress=progress_bar,
                    progress_args=(status_msg, time.time(), "ارسال فایل", False))
            uploaded_ok = True

        elif action not in ("github", "gdrive"):
            final_source = target_path
            await safe_edit(status_msg, "در حال بسته‌بندی RAR...")
            archive_path = os.path.join(out_dir, "Mega-Leecher.rar")
            cmd = ["rar", "a", "-ep1", "-m0", "-rr5p", archive_path]
            if action not in ["full", "multi"]: cmd.append(f"-v{action}m")
            if password: cmd.append(f"-hp{password}")
            if action == "multi":
                cmd += [os.path.join(in_dir, f) for f in os.listdir(in_dir)]
            elif os.path.isdir(final_source):
                cmd.append(f"{final_source}/*")
            else:
                cmd.append(final_source)
            proc = await asyncio.create_subprocess_exec(*cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc.communicate()
            parts = sorted([os.path.join(out_dir, f) for f in os.listdir(out_dir)])
            for i, p in enumerate(parts, 1):
                cap = f"پارت {i} از {len(parts)}" if len(parts) > 1 else "فایل نهایی"
                await client.send_document(chat_id, p, caption=cap, progress=progress_bar,
                    progress_args=(status_msg, time.time(), f"ارسال {i}/{len(parts)}", False))
            uploaded_ok = True

        if uploaded_ok and data.get("type") == "youtube":
            record_yt_download(chat_id)
        await safe_final_edit(status_msg, status_msg, "✅ عملیات با موفقیت تمام شد.")

    except ValueError as e:
        msgs = {
            "CANCELLED":              "🚫 عملیات لغو شد.",
            "SIZE_LIMIT":             "❌ فایل بیشتر از 2 گیگابایت است.",
            "YOUTUBE_DOWNLOAD_FAILED":"❌ دانلود از یوتوب با خطا مواجه شد."
        }
        await safe_edit(status_msg, msgs.get(str(e), f"❌ خطا: {e}"))
    except Exception as e:
        await client.send_message(chat_id, f"❌ خطا: `{e}`")
    finally:
        shutil.rmtree(chat_base, ignore_errors=True)
        if "chat_temp_dir" in data:
            shutil.rmtree(data["chat_temp_dir"], ignore_errors=True)

# ── Direct link download ──────────────────────────────────────────────────────
@app.on_message(filters.text & filters.regex(r"^https?://|^magnet:\?xt=urn:btih:"))
async def handle_text_links(client, message):
    chat_id = message.chat.id; user_id = message.from_user.id
    text = message.text.strip()

    # نادیده گرفتن localhost (کد OAuth گوگل درایو)
    if "localhost" in text.lower():
        return

    is_youtube  = "youtube.com" in text.lower() or "youtu.be" in text.lower()
    is_torrent  = text.startswith("magnet:")

    if is_torrent:
        await handle_torrent_download(client, message, text, is_magnet=True); return


    if is_youtube:
        if not has_yt_access(user_id):
            await message.reply("⛔️ شما اشتراک ویژه یوتوب ندارید."); return
        allowed, remaining = check_yt_quota(user_id)
        if not allowed:
            await message.reply("⛔️ **سهمیه روزانه تمام شده!**\nبه سقف ۱۰ ویدیو در ۲۴ ساعت رسیده‌اید."); return
        bot_msg = await message.reply("⏳ در حال استخراج اطلاعات...", quote=True)
        try:
            async def extract_info():
                cmd = ["yt-dlp",
                       "--print", "%(title)s",
                       "--print", "%(formats.:.{height,filesize,filesize_approx,vcodec,acodec})j",
                       "-q", "--no-warnings"]
                if os.path.exists(COOKIES_FILE): cmd += ["--cookies", COOKIES_FILE]
                cmd.append(text)
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                try:
                    out, err = await asyncio.wait_for(proc.communicate(), timeout=60)
                except asyncio.TimeoutError:
                    proc.kill(); raise Exception("timeout")
                if proc.returncode != 0: raise Exception(err.decode()[:200])
                lines = out.decode().strip().split("\n")
                title   = lines[0] if lines else "youtube_video"
                formats = json.loads(lines[1]) if len(lines) > 1 else []
                return title, formats
            title, formats = await extract_info()
            file_name = "".join(c for c in title if c.isalnum() or c in (" ", ".", "_", "-")).strip()
            s360  = fmt_size(get_quality_size(formats, 360))
            s480  = fmt_size(get_quality_size(formats, 480))
            s720  = fmt_size(get_quality_size(formats, 720))
            s1080 = fmt_size(get_quality_size(formats, 1080))
            saudio= fmt_size(get_audio_size(formats))
            del formats
            state_key = f"{chat_id}_{bot_msg.id}"
            user_states[state_key] = {"type": "youtube_pending", "source": text, "file_name": file_name}
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🎥 360p ({s360})",  callback_data="ytqual_360"),
                 InlineKeyboardButton(f"🎥 480p ({s480})",  callback_data="ytqual_480")],
                [InlineKeyboardButton(f"🎥 720p ({s720})",  callback_data="ytqual_720"),
                 InlineKeyboardButton(f"🎥 1080p ({s1080})",callback_data="ytqual_1080")],
                [InlineKeyboardButton(f"🎵 فقط صدا ({saudio})", callback_data="ytqual_mp3")]
            ])
            await safe_final_edit(message, bot_msg,
                f"🎬 **{title}**\n\n🔢 سهمیه باقیمانده: **{remaining} ویدیو**\n\nکیفیت را انتخاب کنید:", kb)
        except Exception as e:
            await safe_final_edit(message, bot_msg, f"❌ خطا: `{e}`")
        return

    bot_msg = await message.reply("⏳ در حال استخراج لینک...", quote=True)
    file_name = f"file_{int(time.time())}.dat"
    final_url  = text
    is_html    = False

    try:
        async with aiohttp.ClientSession(headers=BROWSER_HEADERS) as s:
            async with s.head(final_url, allow_redirects=True) as r:
                size = int(r.headers.get('Content-Length', 0))
                if size > 0 and not check_size_limit(size, chat_id):
                    await safe_final_edit(message, bot_msg,
                        "❌ حجم فایل بیشتر از 2 گیگابایت است."); return
                if 'text/html' in r.headers.get('Content-Type', ''):
                    is_html = True
                cd = r.headers.get('Content-Disposition', '')
                if cd:
                    m = re.search(r'filename\*?=(?:UTF-8\'\')?([^;]+)', cd, re.IGNORECASE)
                    if m: file_name = urllib.parse.unquote(m.group(1).strip('"\''))
                if file_name.startswith("file_") and not is_html:
                    en = urllib.parse.unquote(
                        os.path.basename(urllib.parse.urlparse(final_url).path))
                    if en: file_name = en
    except: pass

    if is_html:
        await safe_final_edit(message, bot_msg, "❌ لینک مستقیم یافت نشد."); return

    if chat_id in user_multi_tasks:
        user_multi_tasks[chat_id]["items"].append(
            {"type": "url", "source": final_url, "file_name": file_name})
        await safe_final_edit(message, bot_msg,
            f"افزوده شد. (مجموع: {len(user_multi_tasks[chat_id]['items'])})",
            InlineKeyboardMarkup([[InlineKeyboardButton(
                "شروع عملیات", callback_data="multi_start")]])); return

    await safe_final_edit(message, bot_msg,
        f"نام فایل: `{file_name}`", get_main_keyboard(user_id))
    user_states[f"{chat_id}_{bot_msg.id}"] = {
        "type": "url", "source": final_url, "file_name": file_name}

# ── Torrent download ──────────────────────────────────────────────────────────
async def handle_torrent_download(client, message, source, is_magnet=True):
    chat_id = message.chat.id
    sem = get_user_sem(chat_id)
    status_msg = await message.reply("در حال دریافت متادیتا...",
        reply_markup=get_cancel_keyboard(), quote=True)
    if chat_id == ADMIN_ID:
        await _execute_torrent(client, message, source, is_magnet, status_msg)
    else:
        async with sem:
            await safe_edit(status_msg, "در حال دریافت متادیتا...",
                reply_markup=get_cancel_keyboard())
            await _execute_torrent(client, message, source, is_magnet, status_msg)

async def _execute_torrent(client, message, source, is_magnet, status_msg):
    chat_id = message.chat.id; user_id = message.from_user.id
    cancel_flags[chat_id] = False
    chat_temp_dir = os.path.join(TEMP_DIR, f"torrent_{chat_id}_{int(time.time())}")
    os.makedirs(chat_temp_dir, exist_ok=True)
    ses = lt.session()

    if is_magnet:
        handle = lt.add_magnet_uri(ses, source, {"save_path": chat_temp_dir})
    else:
        tp = await message.download(
            file_name=os.path.join(chat_temp_dir, "task.torrent"))
        handle = ses.add_torrent(
            {'ti': lt.torrent_info(tp), 'save_path': chat_temp_dir})

    # انتظار برای دریافت متادیتا
    while not handle.status().has_metadata:
        if cancel_flags.get(chat_id):
            ses.remove_torrent(handle)
            shutil.rmtree(chat_temp_dir, ignore_errors=True)
            await safe_edit(status_msg, "🚫 لغو شد."); return
        await asyncio.sleep(1)

    if not check_size_limit(handle.status().total_wanted, chat_id):
        ses.remove_torrent(handle)
        shutil.rmtree(chat_temp_dir, ignore_errors=True)
        await safe_edit(status_msg, "❌ حجم تورنت بیشتر از 2 گیگابایت است."); return

    # دانلود
    while not handle.status().is_seeding:
        if cancel_flags.get(chat_id):
            ses.remove_torrent(handle)
            shutil.rmtree(chat_temp_dir, ignore_errors=True)
            await safe_edit(status_msg, "🚫 لغو شد."); return
        s = handle.status(); pct = s.progress * 100
        bar = "■"*int(pct/10) + "□"*(10-int(pct/10))
        await safe_edit(status_msg,
            f"وضعیت: دانلود تورنت\n[{bar}] {pct:.1f}%\n"
            f"سرعت: {s.download_rate/1024:.1f} KB/s\n"
            f"حجم: {s.total_wanted_done/(1024*1024):.1f}MB از "
            f"{s.total_wanted/(1024*1024):.1f}MB\n"
            f"سید: {s.num_seeds} | پیر: {s.num_peers}",
            reply_markup=get_cancel_keyboard())
        await asyncio.sleep(5)

    items = [f for f in os.listdir(chat_temp_dir) if f != "task.torrent"]
    final_path = os.path.join(chat_temp_dir, items[0])
    state_key = f"{chat_id}_{status_msg.id}"
    user_states[state_key] = {
        "type": "local_path", "source": final_path,
        "file_name": items[0], "chat_temp_dir": chat_temp_dir
    }
    await safe_final_edit(message, status_msg,
        "✅ آماده پردازش.", get_main_keyboard(user_id))

# ── YouTube quality helpers ───────────────────────────────────────────────────
def get_quality_size(formats, max_height):
    vf = [f for f in formats if f.get('vcodec','none') != 'none'
          and f.get('acodec','none') == 'none' and 0 < (f.get('height') or 0) <= max_height]
    af = [f for f in formats if f.get('acodec','none') != 'none'
          and f.get('vcodec','none') == 'none']
    if not vf: return 0
    bv = max(vf, key=lambda f: (f.get('height',0),
             f.get('filesize') or f.get('filesize_approx') or 0))
    ba = max(af, key=lambda f: f.get('filesize') or f.get('filesize_approx') or 0) if af else None
    return ((bv.get('filesize') or bv.get('filesize_approx') or 0) +
            ((ba.get('filesize') or ba.get('filesize_approx') or 0) if ba else 0))

def get_audio_size(formats):
    af = [f for f in formats if f.get('acodec','none') != 'none'
          and f.get('vcodec','none') == 'none']
    if not af: return 0
    b = max(af, key=lambda f: f.get('filesize') or f.get('filesize_approx') or 0)
    return b.get('filesize') or b.get('filesize_approx') or 0

# ── YouTube quality callback ──────────────────────────────────────────────────
@app.on_callback_query(filters.regex("^ytqual_"))
async def yt_quality_callback(client, cq):
    await cq.answer()
    chat_id = cq.message.chat.id; user_id = cq.from_user.id
    quality   = cq.data.split("_")[1]
    state_key = f"{chat_id}_{cq.message.id}"
    if state_key not in user_states or user_states[state_key].get("type") != "youtube_pending":
        await safe_edit(cq.message, "❌ درخواست منقضی شده است."); return
    allowed, _ = check_yt_quota(user_id)
    if not allowed:
        await safe_edit(cq.message, "⛔️ سهمیه روزانه تمام شده!"); return
    user_states[state_key]["type"]       = "youtube"
    user_states[state_key]["yt_quality"] = quality
    file_name = user_states[state_key]["file_name"]
    if chat_id in user_multi_tasks:
        user_multi_tasks[chat_id]["items"].append(user_states.pop(state_key))
        await safe_edit(cq.message,
            f"افزوده شد. (مجموع: {len(user_multi_tasks[chat_id]['items'])})",
            InlineKeyboardMarkup([[InlineKeyboardButton(
                "شروع عملیات", callback_data="multi_start")]])); return
    label = "صدا" if quality == "mp3" else f"{quality}p"
    await safe_edit(cq.message,
        f"فایل یوتوب: `{file_name}`\nکیفیت: **{label}**", get_main_keyboard(user_id))

# ── yt-dlp runner ─────────────────────────────────────────────────────────────
async def run_yt_cmd(cmd, chat_id):
    proc = await asyncio.create_subprocess_exec(*cmd)
    while True:
        try:
            await asyncio.wait_for(proc.wait(), timeout=2.0); break
        except asyncio.TimeoutError:
            if cancel_flags.get(chat_id): proc.terminate(); raise ValueError("CANCELLED")
    return proc.returncode

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run()
