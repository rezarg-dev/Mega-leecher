#!/usr/bin/env python3
"""Send an announcement to every user in users_db.json.

Edit MESSAGES below, then run (from the install directory):

    ./venv/bin/python broadcast.py

Each user gets the text in the language they picked in the bot. The script
uses its own Telegram session, so the bot can keep running meanwhile.
"""

import asyncio
import sys

from pyrogram import Client
from pyrogram.errors import (
    FloodWait, InputUserDeactivated, PeerIdInvalid, UserDeactivatedBan, UserIsBlocked,
)

from leecher import config, db

MESSAGES = {
    "fa": """
🆕 **قابلیت جدید: تقسیم‌بندی با حجم دلخواه**

از این پس می‌توانید فایل‌های خود را با هر اندازه‌ای که می‌خواهید تقسیم کنید!

✂️ **نحوه استفاده:**
۱. فایل را به ربات بفرستید
۲. گزینه **تقسیم‌بندی دلخواه** را انتخاب کنید
۳. اندازه هر پارت را به مگابایت وارد کنید (بین ۱۹ تا ۹۰۰)
۴. در صورت نیاز رمز عبور تعیین کنید

برای استفاده از این قابلیت یک بار /start را تایپ کنید و ارسال کنید

📌 این قابلیت برای تمام منابع دانلود پشتیبانی می‌شود:
• لینک مستقیم
• فایل‌های تلگرامی
• تورنت
• یوتوب
""",
    "en": """
🆕 **New feature: custom split size**

You can now split your files into parts of any size you like!

✂️ **How to use:**
1. Send a file to the bot
2. Choose **Custom Split**
3. Enter the size of each part in megabytes (between 19 and 900)
4. Set a password if you need one

To use this feature, send /start once

📌 This feature works with every download source:
• Direct links
• Telegram files
• Torrents
• YouTube
""",
}

GONE = (UserIsBlocked, InputUserDeactivated, UserDeactivatedBan, PeerIdInvalid)


async def deliver(app, uid):
    text = MESSAGES.get(db.get_lang(uid)) or MESSAGES["fa"]
    try:
        await app.send_message(uid, text)
    except FloodWait as e:
        print(f"    flood wait, sleeping {e.value}s")
        await asyncio.sleep(e.value + 1)
        await app.send_message(uid, text)


async def broadcast(user_ids):
    sent = skipped = failed = 0
    total = len(user_ids)
    async with Client("broadcast_session", api_id=config.API_ID, api_hash=config.API_HASH,
                      bot_token=config.BOT_TOKEN, workdir=config.BASE_DIR) as app:
        for n, uid in enumerate(user_ids, 1):
            try:
                await deliver(app, uid)
                sent += 1
                print(f"[{n}/{total}] sent to {uid}")
            except GONE:
                skipped += 1
                print(f"[{n}/{total}] skipped {uid} (blocked or deleted)")
            except Exception as e:
                failed += 1
                print(f"[{n}/{total}] failed {uid}: {e}")
            await asyncio.sleep(0.1)

    print(f"\nSent: {sent}   Skipped: {skipped}   Failed: {failed}   Total: {total}")


def main():
    user_ids = db.all_user_ids()
    if not user_ids:
        print("No users found in users_db.json")
        return
    if "--yes" not in sys.argv:
        answer = input(f"Send the announcement to {len(user_ids)} users? [y/N] ")
        if answer.strip().lower() != "y":
            print("Cancelled.")
            return
    asyncio.run(broadcast(user_ids))


if __name__ == "__main__":
    main()
