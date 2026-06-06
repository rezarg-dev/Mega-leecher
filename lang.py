# ===============================================================
# lang.py — Bilingual strings for Mega Leecher Bot
# زبان‌ها: فارسی (fa) | انگلیسی (en)
# Languages: Persian (fa) | English (en)
# ===============================================================

STRINGS = {

    # ── زبان فارسی / Persian ──────────────────────────────────
    "fa": {

        # انتخاب زبان / Language selection
        "choose_language":
            "🌐 **زبان مورد نظر خود را انتخاب کنید:**\n\nPlease choose your language:",
        "lang_changed_fa":  "✅ زبان به **فارسی** تغییر یافت.",
        "lang_changed_en":  "✅ Language changed to **English**.",

        # خوش‌آمدگویی / Welcome
        "welcome":
            "👋 **خوش آمدید!**\n\n"
            "🤖 این ربات یک ابزار حرفه‌ای برای پردازش و مدیریت فایل است.\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📦 **قابلیت‌های پردازش فایل:**\n"
            "• تقسیم فایل به پارت‌های ۱۹، ۴۰ یا ۹۰۰ مگابایتی\n"
            "• فشرده‌سازی در قالب RAR با رمز عبور دلخواه\n"
            "• ارسال فایل خام بدون تغییر\n"
            "• پشتیبانی از فایل‌های فشرده رمزدار (بدون نیاز به رمز)\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "⬇️ **قابلیت‌های دانلود:**\n"
            "• دانلود از **لینک مستقیم**\n"
            "• دانلود از **تورنت** (مگنت یا فایل .torrent)\n"
            "• دانلود از **یوتوب** با کیفیت‌های مختلف تا 1080p\n"
            "• دانلود فقط صدا از یوتوب (MP3)\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "☁️ **فضای ابری رایگان:**\n"
            "• آپلود فایل‌ها به **گیتهاب** و دریافت لینک دانلود مستقیم\n"
            "• تا **۱۵ گیگابایت** فضای رایگان با توکن شخصی\n"
            "• آپلود فایل‌ها به **گوگل درایو** و دریافت لینک اشتراک‌گذاری\n"
            "• تا **۱۵ گیگابایت** فضای رایگان با حساب گوگل\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📋 برای شروع از منوی پایین استفاده کنید 👇",

        # دکمه‌های منوی اصلی / Main reply menu buttons
        "btn_direct_link":   "🌐 راهنمای لینک مستقیم",
        "btn_torrent":       "🧲 راهنمای تورنت",
        "btn_tg_files":      "📁 راهنمای کار با فایل‌های تلگرامی",
        "btn_youtube":       "🎬 راهنمای دانلود از یوتوب",
        "btn_github":        "☁️ اتصال به گیتهاب",
        "btn_drive":         "📂 اتصال به گوگل درایو",
        "btn_purchase":      "🛒 خرید / تمدید اشتراک",
        "btn_language":      "🌐 تغییر زبان",
        "menu_placeholder":  "انتخاب کنید...",

        # دکمه‌های ادمین / Admin buttons
        "btn_add_user":      "➕ افزودن کاربر",
        "btn_del_user":      "➖ حذف کاربر",
        "btn_add_yt_user":   "➕ افزودن کاربر یوتوب",
        "btn_user_list":     "📋 لیست کاربران",
        "btn_clean_bot":     "🧹 پاکسازی ربات",
        "btn_cancel_fa":     "انصراف",

        # دکمه‌های اینلاین / Inline keyboard buttons
        "btn_cancel_op":     "❌ لغو عملیات",
        "btn_raw":           "ارسال فایل خام (بدون تغییر)",
        "btn_full_rar":      "ارسال به صورت تک فایل RAR",
        "btn_multi_rar":     "ایجاد آرشیو چند فایلی",
        "btn_19mb":          "پارت‌های ۱۹ مگ",
        "btn_40mb":          "پارت‌های ۴۰ مگ",
        "btn_900mb":         "پارت‌های ۹۰۰ مگ",
        "btn_github_upload": "☁️ آپلود به گیتهاب",
        "btn_drive_upload":  "📂 آپلود به گوگل درایو",
        "btn_no_pass":       "بدون رمز",
        "btn_set_pass":      "تعیین رمز عبور",
        "btn_start_archive": "شروع آرشیو",
        "btn_start_op":      "شروع عملیات",

        # نوار پیشرفت / Progress bar
        "progress":
            "وضعیت: {action}\n[{bar}] {pct:.1f}%\nسرعت: {speed:.1f} KB/s\n"
            "حجم: {cur:.1f}MB از {total:.1f}MB",
        "progress_unknown_size":
            "وضعیت: {action}\n📥 {cur:.1f} MB دریافت شد...",

        # پیام‌های کنترل دسترسی / Access control messages
        "no_subscription":
            "⛔️ **شما هیچ اشتراک فعالی ندارید!**\n\nبرای خرید:\n👤 {purchase}\n🆔 `{uid}`",
        "feature_needs_sub":
            "⛔️ این قابلیت فقط برای کاربران دارای اشتراک است.\n👤 {purchase}",

        # پیام‌های عمومی / General messages
        "cancelled":         "🚫 عملیات لغو شد.",
        "size_limit":        "❌ فایل‌های بیشتر از 2 گیگابایت مجاز نیست.",
        "processing_start":  "در حال شروع پردازش...",
        "queued":            "⏳ درخواست در صف قرار گرفت...",
        "done":              "✅ عملیات با موفقیت تمام شد.",
        "error_generic":     "❌ خطا: `{e}`",

        # راهنمای لینک مستقیم / Direct link guide
        "guide_direct":
            "**🌐 راهنمای دانلود از لینک مستقیم:**\n\n"
            "کافیه لینک دانلود فایل رو مستقیم داخل چت بفرستید — ربات بقیه کار رو میکنه.\n\n"
            "📌 **چه لینک‌هایی پشتیبانی میشن؟**\n"
            "• هر لینکی که مستقیم به یه فایل اشاره کنه\n"
            "• ویدیو، موزیک، زیپ، PDF، APK، EXE و هر فرمت دیگه‌ای\n"
            "• حجم دانلود تا **۲ گیگابایت**\n\n"
            "⚙️ **بعد از دانلود چه کارهایی میشه کرد؟**\n"
            "• 📤 ارسال فایل خام (بدون هیچ تغییری)\n"
            "• 🗜 فشرده‌سازی در قالب **RAR** با یا بدون رمز عبور\n"
            "• ✂️ تقسیم به پارت‌های **۱۹، ۴۰ یا ۹۰۰ مگابایتی**\n"
            "• ☁️ آپلود به **گیتهاب** و دریافت لینک دانلود مستقیم\n\n"
            "💡 **نکته:** اگه چند فایل از چند لینک مختلف داری، میتونی همه رو بفرستی و در یک آرشیو RAR واحد تحویل بگیری.",

        # راهنمای تورنت / Torrent guide
        "guide_torrent":
            "**🧲 راهنمای دانلود تورنت:**\n\n"
            "دو روش برای ارسال تورنت وجود داره:\n\n"
            "1️⃣ **لینک مگنت** — لینکی که با `magnet:?xt=` شروع میشه رو مستقیم داخل چت بفرستید\n\n"
            "2️⃣ **فایل .torrent** — فایل تورنت رو آپلود کنید\n\n"
            "📌 **نکات مهم:**\n"
            "• ربات ابتدا متادیتا (اطلاعات فایل) رو دریافت میکنه، بعد دانلود شروع میشه\n"
            "• اگه تورنت سید نداشته باشه، دانلود ممکنه زمان ببره یا ناقص بمونه\n"
            "• حجم تا **۲ گیگابایت** برای کاربران عادی\n"
            "• اگه سرور شلوغ باشه، درخواست در صف قرار میگیره و نوبتی پردازش میشه\n\n"
            "⚙️ **بعد از دانلود چه کارهایی میشه کرد؟**\n"
            "• 📤 ارسال فایل خام (بدون تغییر)\n"
            "• 🗜 فشرده‌سازی **RAR** با رمز عبور دلخواه\n"
            "• ✂️ تقسیم به پارت‌های **۱۹، ۴۰ یا ۹۰۰ مگابایتی**\n"
            "• ☁️ آپلود به **گیتهاب** و دریافت لینک دانلود مستقیم",

        # راهنمای فایل‌های تلگرام / Telegram files guide
        "guide_tg_files":
            "**📁 راهنمای کار با فایل‌های تلگرامی:**\n\n"
            "فایل، ویدیو، موزیک یا هر محتوایی رو که در تلگرام دارید **فوروارد** کنید یا مستقیم **آپلود** کنید.\n\n"
            "📌 **چه فایل‌هایی پشتیبانی میشن؟**\n"
            "• تمام فرمت‌ها: ویدیو، صدا، زیپ، RAR، 7z، PDF و...\n"
            "• فایل‌های فشرده **رمزدار** — نیازی به وارد کردن رمز نیست، مستقیم پارت‌بندی میشن\n"
            "• چندین فایل مختلف رو میتونید یکجا بفرستید و در **یک آرشیو RAR** تحویل بگیرید\n"
            "• حجم تا **۲ گیگابایت** برای کاربران عادی\n\n"
            "⚙️ **بعد از دریافت چه کارهایی میشه کرد؟**\n"
            "• 📤 ارسال فایل خام (ویدیو به صورت استریم‌پذیر در تلگرام)\n"
            "• 🗜 فشرده‌سازی در قالب **RAR** با یا بدون رمز عبور\n"
            "• ✂️ تقسیم به پارت‌های **۱۹، ۴۰ یا ۹۰۰ مگابایتی**\n"
            "• 📦 ترکیب چند فایل در **یک آرشیو چندفایلی**\n"
            "• ☁️ آپلود به **گیتهاب** و دریافت لینک دانلود مستقیم",

        # راهنمای یوتوب / YouTube guide
        "guide_youtube":
            "**🎬 راهنمای دانلود از یوتوب:**\n\n"
            "کافیه لینک ویدیوی یوتوب رو مستقیم داخل چت بفرستید.\n\n"
            "📌 **کیفیت‌های قابل دانلود:**\n• 360p • 480p • 720p • 1080p • 🎵 فقط صدا\n\n"
            "⚡️ حجم تقریبی هر کیفیت نمایش داده میشه.\n"
            "🔢 سهمیه روزانه: **۱۰ ویدیو** در هر ۲۴ ساعت.",

        # اشتراک / Subscription
        "sub_active":        "✅ **شما دارای اشتراک فعال هستید.**\n\n⏳ روزهای باقیمانده: **{days} روز**",
        "sub_buy":           "⛔️ جهت خرید اشتراک به {purchase} پیام دهید.\n🆔 آیدی عددی شما: `{uid}`",
        "sub_renew":         "⛔️ جهت خرید یا تمدید به {purchase} پیام دهید.\n🆔 آیدی عددی شما: `{uid}`",
        "no_yt_sub":         "⛔️ شما اشتراک ویژه یوتوب ندارید.",
        "yt_quota_exceeded": "⛔️ **سهمیه روزانه تمام شده!**\nبه سقف ۱۰ ویدیو در ۲۴ ساعت رسیده‌اید.",

        # هندلر فایل‌ها / File handler
        "file_too_large":    "❌ فایل‌های بیشتر از 2 گیگابایت مجاز نیست.",
        "processing":        "⏳ در حال پردازش...",
        "file_added_multi":  "افزوده شد. (مجموع: {count})",
        "file_received":     "فایل دریافت شد: `{name}`",
        "file_expired":      "❌ فایل منقضی شده، دوباره ارسال کنید.",
        "ask_password":      "رمز گذاشته شود؟",
        "set_password":      "رمز را بفرستید:",
        "first_file_added":  "فایل اول اضافه شد. بعدی‌ها را فوروارد کنید.",

        # لینک مستقیم / Direct URL
        "extracting_link":   "⏳ در حال استخراج لینک...",
        "link_too_large":    "❌ حجم فایل بیشتر از 2 گیگابایت است.",
        "no_direct_link":    "❌ لینک مستقیم یافت نشد.",
        "file_name_prompt":  "نام فایل: `{name}`",

        # یوتوب / YouTube
        "yt_extracting":     "⏳ در حال استخراج اطلاعات...",
        "yt_quality_prompt": "🎬 **{title}**\n\n🔢 سهمیه باقیمانده: **{remaining} ویدیو**\n\nکیفیت را انتخاب کنید:",
        "yt_file_ready":     "فایل یوتوب: `{name}`\nکیفیت: **{quality}**",
        "yt_downloading":    "در حال دانلود ({quality})...",
        "yt_quota_exceeded_cb": "⛔️ سهمیه روزانه تمام شده!",
        "yt_request_expired": "❌ درخواست منقضی شده است.",

        # تورنت / Torrent
        "torrent_metadata":  "در حال دریافت متادیتا...",
        "torrent_cancelled": "🚫 لغو شد.",
        "torrent_too_large": "❌ حجم تورنت بیشتر از 2 گیگابایت است.",
        "torrent_progress":
            "وضعیت: دانلود تورنت\n[{bar}] {pct:.1f}%\n"
            "سرعت: {speed:.1f} KB/s\n"
            "حجم: {done:.1f}MB از {total:.1f}MB\n"
            "سید: {seeds} | پیر: {peers}",
        "torrent_ready":     "✅ آماده پردازش.",

        # core_processing
        "preparing_file":    "📦 در حال آماده‌سازی فایل...",
        "sending":           "در حال ارسال...",
        "compressing_rar":   "در حال بسته‌بندی RAR...",
        "sending_part":      "پارت {i} از {total}",
        "final_file":        "فایل نهایی",
        "yt_item_download":  "دانلود از یوتوب (آیتم {i})...",

        # گیتهاب — پیام‌های آپلود / GitHub upload messages
        "gh_preparing":      "☁️ در حال آماده‌سازی...",
        "gh_uploading":
            "☁️ **آپلود به گیتهاب...**\n[{bar}] {pct}%\nپارت {i} از {n}  ({mb:.1f} MB)",
        "gh_upload_done":    "✅ آپلود کامل شد!",
        "gh_queued":         "⏳ **صف آپلود گیتهاب**\n\nبه محض آزاد شدن، آپلود شروع می‌شود...",
        "gh_success_header":
            "✅ **آپلود به گیتهاب موفق بود!**\n\n"
            "📁 ریپازیتوری: `{repo}`\n"
            "🔢 تعداد پارت‌ها: {parts}\n{quota}",
        "gh_multipart_note":
            "\n📥 **نحوه استفاده:**\n"
            "۱. تمام پارت‌ها را دانلود کنید\n"
            "۲. همه را در یک پوشه قرار دهید\n"
            "۳. پارت اول را با 7-Zip باز کنید\n",
        "gh_links_header":   "🔗 **لینک‌های دانلود:**\n\n",
        "gh_part_link":      "📎 پارت {i}:\n`{url}`\n\n",
        "gh_links_file_cap": "📄 تمام لینک‌ها — برای وارد کردن به دانلود منیجر (ADM و...)",
        "gh_quota_line":     "🔢 سهمیه باقیمانده: **{remaining} آپلود**\n",
        "gh_full":           "❌ **فضای گیتهاب پر شده!**\n\nاز منوی ☁️ اتصال به گیتهاب، گزینه پاکسازی را بزنید.",
        "gh_no_token_core":  "❌ توکن گیتهاب تنظیم نشده.\nاز منوی ☁️ اتصال به گیتهاب توکن وارد کنید.",
        "gh_quota_core":     "⛔️ سهمیه روزانه آپلود به گیتهاب تمام شده!\nهر کاربر روزانه {limit} آپلود مجاز است.",
        "gh_clear_repo":     "🗑 در حال پاکسازی ریپازیتوری {i} از {total}...",

        # گیتهاب — منو / GitHub menu
        "gh_menu_title":
            "☁️ **مدیریت فضای ابری گیتهاب**\n\nوضعیت: {status}\n\n"
            "با اتصال به گیتهاب فایل‌ها را رایگان ذخیره کرده و لینک مستقیم دریافت کنید.\n\n"
            "📦 ظرفیت: تا **۱۵ گیگابایت** (۳ ریپازیتوری × ۵ گیگ)",
        "gh_connected":      "✅ متصل به اکانت `{username}`",
        "gh_not_connected":  "❌ توکن تنظیم نشده",
        "gh_btn_guide":      "📖 راهنمای گام به گام",
        "gh_btn_token":      "🔑 وارد کردن توکن",
        "gh_btn_token_change": "🔑 تغییر توکن",
        "gh_btn_space":      "📊 فضای باقیمانده",
        "gh_btn_clear":      "🗑 پاکسازی همه فایل‌ها",

        "gh_guide_text":
            "📖 **راهنمای دریافت توکن گیتهاب**\n\n"
            "**مرحله ۱ — ساخت حساب:**\n"
            "① به `github.com` بروید و ثبت‌نام کنید\n\n"
            "**مرحله ۲ — رفتن به تنظیمات:**\n"
            "① تصویر پروفایل → **Settings**\n"
            "② پایین صفحه → **Developer settings**\n"
            "③ **Personal access tokens** → **Fine-grained tokens**\n"
            "④ **Generate new token**\n\n"
            "**مرحله ۳ — تنظیمات توکن:**\n"
            "① نام دلخواه (مثلاً `mega-leecher`)\n"
            "② Expiration: **No expiration**\n"
            "③ Repository access: **All repositories**\n"
            "④ Permissions → Contents: **Read and write**\n\n"
            "⚠️ توکن فقط یک‌بار نمایش داده می‌شود — همین‌جا کپی کنید!",

        "gh_token_prompt":
            "🔑 لطفاً توکن GitHub خود را ارسال کنید\n(با `ghp_` یا `github_pat_` شروع میشه):",
        "gh_space_info":
            "📊 **فضای ابری گیتهاب:**\n\n"
            "👤 اکانت: `{username}`\n\n"
            "**وضعیت هر ریپازیتوری:**\n{repos_info}\n"
            "[{bar}] {pct:.1f}%\n"
            "📦 مصرف: {used:.2f} GB\n"
            "✅ باقیمانده: {free:.2f} GB از {total:.0f} GB\n\n"
            "🔢 سهمیه امروز: **{quota} از {limit}** باقی مانده",
        "gh_no_token_menu":   "❌ توکن تنظیم نشده.",
        "gh_warn_clear":
            "⚠️ **هشدار!**\nتمام فایل‌های آپلود شده در گیتهاب حذف می‌شوند. مطمئنید؟",
        "gh_btn_confirm_clear": "✅ بله، پاکسازی کن",
        "gh_btn_cancel":     "❌ انصراف",
        "gh_clearing":       "🗑 در حال پاکسازی...",
        "gh_clear_done":     "✅ **فضای گیتهاب پاکسازی شد!**\nاکنون می‌توانید فایل‌های جدید آپلود کنید.",
        "gh_clear_error":    "⚠️ پاکسازی با خطا مواجه شد:\n`{e}`",
        "gh_cancelled":      "❌ عملیات لغو شد.",
        "gh_verifying":      "⏳ در حال بررسی توکن...",
        "gh_invalid_token":  "❌ {err}\nلطفاً دوباره از منوی گیتهاب امتحان کنید.",
        "gh_creating_repos": "✅ توکن معتبر! اکانت: `{username}`\n⏳ در حال ایجاد ۳ ریپازیتوری...",
        "gh_creating_repo_i": "✅ توکن معتبر! اکانت: `{username}`\n⏳ ایجاد ریپازیتوری {i} از {total}...",
        "gh_repo_error":
            "❌ خطا در ایجاد ریپازیتوری.\nبررسی کنید permissions توکن شامل ۴ مجوز لازم باشد.",
        "gh_connect_success":
            "✅ **اتصال به گیتهاب برقرار شد!**\n\n"
            "👤 اکانت: `{username}`\n"
            "📁 ریپازیتوری‌ها: {repos} عدد\n"
            "💾 ظرفیت: تا {cap} گیگابایت\n\n"
            "گزینه **☁️ آپلود به گیتهاب** در منوی پردازش فایل نمایش داده می‌شود.",

        # گوگل درایو — منو / Drive menu
        "gd_menu_title":
            "📂 **مدیریت گوگل درایو**\n\nوضعیت: {status}\n\n"
            "با اتصال به گوگل درایو فایل‌ها را آپلود کرده و لینک دانلود مستقیم دریافت کنید.\n\n"
            "💾 ظرفیت رایگان: **۱۵ گیگابایت**\n"
            "🔢 سهمیه روزانه: **۱۰ آپلود**",
        "gd_connected":      "✅ متصل",
        "gd_not_connected":  "❌ متصل نشده",
        "gd_btn_guide":      "📖 راهنمای گام به گام",
        "gd_btn_dl_guide":   "📥 راهنمای دانلود لینک‌ها",
        "gd_btn_connect":    "🔗 اتصال حساب گوگل",
        "gd_btn_space":      "📊 فضای باقیمانده",
        "gd_btn_clear":      "🗑 پاکسازی فایل‌های آپلودشده",
        "gd_btn_disconnect": "❌ قطع اتصال",

        "gd_guide_text":
            "📖 **راهنمای اتصال به گوگل درایو**\n\n"
            "**مرحله ۱ — باز کردن لینک:**\n"
            "① روی **اتصال حساب گوگل** بزنید\n"
            "② لینک را **کپی** کنید\n"
            "③ در مرورگر Chrome یا Safari باز کنید\n"
            "   ⚠️ در مرورگر داخلی تلگرام باز **نکنید**\n\n"
            "**مرحله ۲ — ورود به گوگل:**\n"
            "① با حساب گوگل وارد شوید\n"
            "② روی **Allow** کلیک کنید\n\n"
            "**مرحله ۳ — دریافت کد:**\n"
            "① مرورگر صفحه خطا نشان می‌دهد — این **طبیعی** است\n"
            "② آدرس کامل صفحه را از نوار آدرس کپی کنید\n"
            "   مثال: `http://localhost/?code=4/0Ae...`\n"
            "③ آدرس را برای ربات **بفرستید**",

        "gd_dl_guide_text":
            "📥 **راهنمای دانلود از گوگل درایو**\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "**روش اول — مرورگر:**\n\n"
            "① لینک **دانلود مستقیم** را کپی کنید\n"
            "② در مرورگر Paste کنید\n"
            "③ اگر گوگل هشدار ویروس داد روی **Download anyway** کلیک کنید\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "**روش دوم — اپ اندروید (اگر روش اول کار نکرد):**\n\n"
            "① اپ MITM Drive Downloader را نصب کنید\n"
            "② اپ را باز کنید و روی **Start** بزنید\n"
            "③ لینک **دانلود مستقیم** را Paste کنید\n"
            "④ روی **Download** بزنید",

        "gd_connect_url":
            "🔗 **اتصال به گوگل درایو:**\n\n"
            "**مرحله ۱:** لینک زیر را در مرورگر باز کنید:\n{url}\n\n"
            "**مرحله ۲:** با حساب گوگل وارد شوید و دسترسی را تأیید کنید\n\n"
            "**مرحله ۳:** آدرس کامل صفحه خطا را کپی کرده و همین‌جا بفرستید\n\n"
            "مثال: `http://localhost/?code=4/xxxxx`",
        "gd_btn_cancel_connect": "❌ لغو اتصال",
        "gd_checking_space": "⏳ در حال بررسی فضا...",
        "gd_no_account":     "❌ حساب گوگل متصل نشده.",
        "gd_auth_error":     "❌ خطا در احراز هویت. دوباره متصل شوید.",
        "gd_space_info":
            "📊 **فضای گوگل درایو:**\n\n"
            "[{bar}] {pct:.1f}%\n"
            "📦 مصرف: {used:.2f} GB\n"
            "✅ باقیمانده: {free:.2f} GB از {total:.0f} GB\n\n"
            "🔢 سهمیه امروز: **{quota} از {limit}** باقی مانده",
        "gd_warn_clear":
            "⚠️ **هشدار!**\nتمام فایل‌های آپلودشده در گوگل درایو حذف می‌شوند. مطمئنید؟",
        "gd_btn_confirm_clear": "✅ بله، پاکسازی کن",
        "gd_no_account_short": "❌ حساب متصل نشده.",
        "gd_auth_error_short": "❌ خطا در احراز هویت.",
        "gd_no_folder":      "❌ پوشه‌ای یافت نشد.",
        "gd_clearing":       "🗑 در حال پاکسازی...",
        "gd_clear_done":     "✅ **پاکسازی انجام شد!**\n{count} فایل حذف شد.",
        "gd_clear_error":    "⚠️ خطا: `{e}`",
        "gd_cancelled":      "❌ عملیات اتصال لغو شد.",
        "gd_cancelled_short": "❌ عملیات لغو شد.",
        "gd_disconnected":   "✅ حساب گوگل قطع شد.",
        "gd_verifying":      "⏳ در حال بررسی کد...",
        "gd_invalid_code":   "❌ کد نامعتبر. دوباره از منوی گوگل درایو امتحان کنید.",
        "gd_creating_folder": "⏳ در حال ساخت پوشه...",
        "gd_oauth_not_configured":
            "❌ اطلاعات Google OAuth در config.env تنظیم نشده.\n"
            "مقادیر GOOGLE_CLIENT_ID و GOOGLE_CLIENT_SECRET را پر کنید.",
        "gd_connect_success":
            "✅ **اتصال به گوگل درایو موفق بود!**\n\n"
            "💾 ظرفیت رایگان: ۱۵ گیگابایت\n\n"
            "گزینه **📂 آپلود به گوگل درایو** در منوی پردازش فایل نمایش داده می‌شود.",
        "gd_code_error":     "❌ خطا: `{e}`",

        # گوگل درایو — آپلود / Drive upload
        "gd_uploading":
            "📂 **آپلود به گوگل درایو...**\n[{bar}] {pct}%\n"
            "{sent:.1f} MB از {total:.1f} MB",
        "gd_upload_start_error": "❌ خطا در شروع آپلود: {code}",
        "gd_upload_fail":    "❌ آپلود ناموفق: {code}",
        "gd_clearing_file":  "🗑 در حال پاکسازی... ({deleted} فایل حذف شد)",
        "gd_upload_done":    "✅ آپلود کامل شد!",
        "gd_quota_core":     "⛔️ سهمیه روزانه آپلود به گوگل درایو تمام شده!\nهر کاربر روزانه {limit} آپلود مجاز است.",
        "gd_no_account_core": "❌ حساب گوگل متصل نشده.\nاز منوی 📂 اتصال به گوگل درایو متصل شوید.",
        "gd_auth_error_core": "❌ خطا در احراز هویت گوگل. دوباره از منوی اتصال متصل شوید.",
        "gd_folder_error":   "❌ خطا در دسترسی به گوگل درایو.",
        "gd_queued":         "⏳ **صف آپلود گوگل درایو**\n\nبه محض آزاد شدن، آپلود شروع می‌شود...",
        "gd_success":
            "✅ **آپلود به گوگل درایو موفق بود!**\n\n"
            "📄 نام فایل: `{name}`\n"
            "{quota}"
            "\n🔗 **مشاهده فایل:**\n`{view}`\n\n"
            "⬇️ **دانلود مستقیم:**\n`{dl}`\n\n"
            "⚠️ برای فایل‌های بزرگ ممکن است گوگل نیاز به تأیید داشته باشد.",
        "gd_size_limit":     "❌ حجم فایل بیشتر از ۲ گیگابایت است ({size:.2f} GB)",
        "gd_quota_line":     "🔢 سهمیه باقیمانده امروز: **{remaining} آپلود**\n",
        "gd_folder_create_error": "خطا در ساخت پوشه: {code}",

        # پنل ادمین / Admin panel
        "admin_no_users":    "هیچ کاربر فعالی وجود ندارد.",
        "admin_user_list_title": "📋 **لیست کاربران** — صفحه {page} از {total_pages} (جمع: {total} نفر)\n",
        "admin_user_entry":  "**{i}.** 👤 {uname}\n  🆔 `{uid}`\n  ⏳ اشتراک: **{rd} روز**\n  🎬 یوتوب: **{ytd} روز**\n━━━━━━━━━━━━━━━━━\n",
        "admin_btn_prev":    "→ قبلی",
        "admin_btn_next":    "بعدی ←",
        "admin_ask_user_id": "آیدی عددی کاربر:",
        "admin_ask_yt_id":   "آیدی عددی کاربر یوتوب:",
        "admin_ask_days":    "تعداد روزهای اشتراک:",
        "admin_ask_yt_days": "تعداد روزهای اشتراک یوتوب:",
        "admin_ask_username": "آیدی نوشتاری:",
        "admin_cancel":      "انصراف",
        "admin_cancelled":   "لغو شد.",
        "admin_clean_done":  "✅ پاکسازی شد.",
        "admin_added":       "✅ اضافه شد. اعتبار: {days} روز.",
        "admin_yt_added":    "✅ دسترسی یوتوب. اعتبار: {days} روز.",
        "admin_deleted":     "✅ دسترسی لغو شد.",
        "admin_not_found":   "❌ یافت نشد.",

        # action texts در progress bar / progress bar action texts
        "receiving_file":    "دریافت فایل",
        "sending_video":     "ارسال ویدیو",
        "sending_audio":     "ارسال صدا",
        "sending_file":      "ارسال فایل",
        "btn_audio_only":    "🎵 فقط صدا ({size})",
        "audio_only_label":  "صدا",
        "torrent_dl_action": "دانلود تورنت",

        # اینستاگرام / Instagram
        "ig_received":       "📸 پست اینستاگرام دریافت شد.",
        "ig_select_action":  "📸 **پست اینستاگرام**\n\nنحوه ارسال را انتخاب کنید:",

        # MITM
        "mitm_caption":      "📲 **MITM Drive Downloader**\nاگر دانلود از مرورگر کار نکرد از این اپ استفاده کنید",
    },

    # ── زبان انگلیسی / English ────────────────────────────────
    "en": {

        # Language selection
        "choose_language":
            "🌐 **Please choose your language:**\n\nزبان مورد نظر خود را انتخاب کنید:",
        "lang_changed_fa":  "✅ Language changed to **Persian**.",
        "lang_changed_en":  "✅ Language changed to **English**.",

        # Welcome
        "welcome":
            "👋 **Welcome!**\n\n"
            "🤖 This bot is a professional tool for file processing and management.\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📦 **File Processing:**\n"
            "• Split files into 19MB, 40MB or 900MB parts\n"
            "• Compress into RAR archives with optional password\n"
            "• Send files raw without any modification\n"
            "• Password-protected archives supported (no password needed)\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "⬇️ **Download Features:**\n"
            "• Download from **direct links**\n"
            "• Download from **torrents** (magnet or .torrent file)\n"
            "• Download from **YouTube** up to 1080p\n"
            "• Audio-only download from YouTube (MP3)\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "☁️ **Free Cloud Storage:**\n"
            "• Upload to **GitHub** and get direct download links\n"
            "• Up to **15 GB** free with your personal token\n"
            "• Upload to **Google Drive** and get shareable links\n"
            "• Up to **15 GB** free with your Google account\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📋 Use the menu below to get started 👇",

        # Main reply menu buttons
        "btn_direct_link":   "🌐 Direct Link Guide",
        "btn_torrent":       "🧲 Torrent Guide",
        "btn_tg_files":      "📁 Telegram Files Guide",
        "btn_youtube":       "🎬 YouTube Download Guide",
        "btn_github":        "☁️ Connect GitHub",
        "btn_drive":         "📂 Connect Google Drive",
        "btn_purchase":      "🛒 Buy / Renew Subscription",
        "btn_language":      "🌐 Change Language",
        "menu_placeholder":  "Select an option...",

        # Admin buttons
        "btn_add_user":      "➕ Add User",
        "btn_del_user":      "➖ Remove User",
        "btn_add_yt_user":   "➕ Add YouTube User",
        "btn_user_list":     "📋 User List",
        "btn_clean_bot":     "🧹 Clean Bot",
        "btn_cancel_fa":     "Cancel",

        # Inline keyboard buttons
        "btn_cancel_op":     "❌ Cancel Operation",
        "btn_raw":           "Send Raw File (no changes)",
        "btn_full_rar":      "Send as Single RAR File",
        "btn_multi_rar":     "Create Multi-File Archive",
        "btn_19mb":          "19 MB Parts",
        "btn_40mb":          "40 MB Parts",
        "btn_900mb":         "900 MB Parts",
        "btn_github_upload": "☁️ Upload to GitHub",
        "btn_drive_upload":  "📂 Upload to Google Drive",
        "btn_no_pass":       "No Password",
        "btn_set_pass":      "Set Password",
        "btn_start_archive": "Start Archive",
        "btn_start_op":      "Start Operation",

        # Progress bar
        "progress":
            "Status: {action}\n[{bar}] {pct:.1f}%\nSpeed: {speed:.1f} KB/s\n"
            "Size: {cur:.1f}MB of {total:.1f}MB",
        "progress_unknown_size":
            "Status: {action}\n📥 Received {cur:.1f} MB...",

        # Access control
        "no_subscription":
            "⛔️ **You have no active subscription!**\n\nTo purchase:\n👤 {purchase}\n🆔 `{uid}`",
        "feature_needs_sub":
            "⛔️ This feature is only available for subscribed users.\n👤 {purchase}",

        # General messages
        "cancelled":         "🚫 Operation cancelled.",
        "size_limit":        "❌ Files larger than 2 GB are not allowed.",
        "processing_start":  "Starting processing...",
        "queued":            "⏳ Request added to queue...",
        "done":              "✅ Operation completed successfully.",
        "error_generic":     "❌ Error: `{e}`",

        # Direct link guide
        "guide_direct":
            "**🌐 Direct Link Download Guide:**\n\n"
            "Just send the download link directly in the chat — the bot handles the rest.\n\n"
            "📌 **What links are supported?**\n"
            "• Any link that points directly to a file\n"
            "• Video, music, zip, PDF, APK, EXE and any other format\n"
            "• Download size up to **2 GB**\n\n"
            "⚙️ **What can you do after downloading?**\n"
            "• 📤 Send raw file (without any changes)\n"
            "• 🗜 Compress into **RAR** with or without a password\n"
            "• ✂️ Split into **19, 40 or 900 MB** parts\n"
            "• ☁️ Upload to **GitHub** and get a direct download link\n\n"
            "💡 **Tip:** If you have multiple files from different links, send them all and receive them in a single RAR archive.",

        # Torrent guide
        "guide_torrent":
            "**🧲 Torrent Download Guide:**\n\n"
            "Two ways to send a torrent:\n\n"
            "1️⃣ **Magnet link** — send a link starting with `magnet:?xt=` directly in chat\n\n"
            "2️⃣ **.torrent file** — upload the torrent file\n\n"
            "📌 **Important notes:**\n"
            "• The bot first fetches metadata, then starts downloading\n"
            "• If the torrent has no seeds, download may be slow or incomplete\n"
            "• Size up to **2 GB** for regular users\n"
            "• If the server is busy, your request will be queued\n\n"
            "⚙️ **What can you do after downloading?**\n"
            "• 📤 Send raw file (without changes)\n"
            "• 🗜 **RAR** compression with optional password\n"
            "• ✂️ Split into **19, 40 or 900 MB** parts\n"
            "• ☁️ Upload to **GitHub** and get a direct download link",

        # Telegram files guide
        "guide_tg_files":
            "**📁 Telegram Files Guide:**\n\n"
            "**Forward** or directly **upload** any file, video, music or content from Telegram.\n\n"
            "📌 **What files are supported?**\n"
            "• All formats: video, audio, zip, RAR, 7z, PDF and more\n"
            "• **Password-protected** archives — no password needed, split directly\n"
            "• Send multiple files and receive them in a **single RAR archive**\n"
            "• Size up to **2 GB** for regular users\n\n"
            "⚙️ **What can you do after receiving?**\n"
            "• 📤 Send raw file (video as streamable in Telegram)\n"
            "• 🗜 Compress into **RAR** with or without a password\n"
            "• ✂️ Split into **19, 40 or 900 MB** parts\n"
            "• 📦 Combine multiple files into a **multi-file archive**\n"
            "• ☁️ Upload to **GitHub** and get a direct download link",

        # YouTube guide
        "guide_youtube":
            "**🎬 YouTube Download Guide:**\n\n"
            "Just send the YouTube video link directly in chat.\n\n"
            "📌 **Available qualities:**\n• 360p • 480p • 720p • 1080p • 🎵 Audio only\n\n"
            "⚡️ Approximate size for each quality is shown.\n"
            "🔢 Daily quota: **10 videos** per 24 hours.",

        # Subscription
        "sub_active":        "✅ **You have an active subscription.**\n\n⏳ Days remaining: **{days} days**",
        "sub_buy":           "⛔️ To purchase a subscription, message {purchase}.\n🆔 Your ID: `{uid}`",
        "sub_renew":         "⛔️ To buy or renew, message {purchase}.\n🆔 Your ID: `{uid}`",
        "no_yt_sub":         "⛔️ You don't have a YouTube subscription.",
        "yt_quota_exceeded": "⛔️ **Daily quota reached!**\nYou've hit the limit of 10 videos per 24 hours.",

        # File handler
        "file_too_large":    "❌ Files larger than 2 GB are not allowed.",
        "processing":        "⏳ Processing...",
        "file_added_multi":  "Added. (Total: {count})",
        "file_received":     "File received: `{name}`",
        "file_expired":      "❌ File expired, please send it again.",
        "ask_password":      "Add a password?",
        "set_password":      "Send the password:",
        "first_file_added":  "First file added. Forward the next ones.",

        # Direct URL
        "extracting_link":   "⏳ Extracting link...",
        "link_too_large":    "❌ File size exceeds 2 GB.",
        "no_direct_link":    "❌ No direct download link found.",
        "file_name_prompt":  "File name: `{name}`",

        # YouTube
        "yt_extracting":     "⏳ Extracting video info...",
        "yt_quality_prompt": "🎬 **{title}**\n\n🔢 Remaining quota: **{remaining} videos**\n\nChoose quality:",
        "yt_file_ready":     "YouTube file: `{name}`\nQuality: **{quality}**",
        "yt_downloading":    "Downloading ({quality})...",
        "yt_quota_exceeded_cb": "⛔️ Daily quota reached!",
        "yt_request_expired": "❌ Request expired.",

        # Torrent
        "torrent_metadata":  "Fetching metadata...",
        "torrent_cancelled": "🚫 Cancelled.",
        "torrent_too_large": "❌ Torrent size exceeds 2 GB.",
        "torrent_progress":
            "Status: Torrent download\n[{bar}] {pct:.1f}%\n"
            "Speed: {speed:.1f} KB/s\n"
            "Size: {done:.1f}MB of {total:.1f}MB\n"
            "Seeds: {seeds} | Peers: {peers}",
        "torrent_ready":     "✅ Ready to process.",

        # core_processing
        "preparing_file":    "📦 Preparing file...",
        "sending":           "Sending...",
        "compressing_rar":   "Compressing into RAR...",
        "sending_part":      "Part {i} of {total}",
        "final_file":        "Final file",
        "yt_item_download":  "Downloading from YouTube (item {i})...",

        # GitHub upload messages
        "gh_preparing":      "☁️ Preparing...",
        "gh_uploading":
            "☁️ **Uploading to GitHub...**\n[{bar}] {pct}%\nPart {i} of {n}  ({mb:.1f} MB)",
        "gh_upload_done":    "✅ Upload complete!",
        "gh_queued":         "⏳ **GitHub upload queue**\n\nUpload will start as soon as a slot is free...",
        "gh_success_header":
            "✅ **Upload to GitHub successful!**\n\n"
            "📁 Repository: `{repo}`\n"
            "🔢 Parts: {parts}\n{quota}",
        "gh_multipart_note":
            "\n📥 **How to use:**\n"
            "1. Download all parts\n"
            "2. Place them all in one folder\n"
            "3. Open the first part with 7-Zip\n",
        "gh_links_header":   "🔗 **Download Links:**\n\n",
        "gh_part_link":      "📎 Part {i}:\n`{url}`\n\n",
        "gh_links_file_cap": "📄 All links — for import into a download manager (ADM etc.)",
        "gh_quota_line":     "🔢 Remaining quota: **{remaining} uploads**\n",
        "gh_full":           "❌ **GitHub storage is full!**\n\nGo to ☁️ Connect GitHub menu and clear your files.",
        "gh_no_token_core":  "❌ GitHub token not set.\nPlease connect via the ☁️ Connect GitHub menu.",
        "gh_quota_core":     "⛔️ Daily GitHub upload quota reached!\nEach user is allowed {limit} uploads per day.",
        "gh_clear_repo":     "🗑 Clearing repository {i} of {total}...",

        # GitHub menu
        "gh_menu_title":
            "☁️ **GitHub Cloud Storage**\n\nStatus: {status}\n\n"
            "Connect your GitHub account to store files for free and get direct download links.\n\n"
            "📦 Capacity: up to **15 GB** (3 repositories × 5 GB)",
        "gh_connected":      "✅ Connected to `{username}`",
        "gh_not_connected":  "❌ Token not set",
        "gh_btn_guide":      "📖 Step-by-Step Guide",
        "gh_btn_token":      "🔑 Enter Token",
        "gh_btn_token_change": "🔑 Change Token",
        "gh_btn_space":      "📊 Storage Info",
        "gh_btn_clear":      "🗑 Clear All Files",

        "gh_guide_text":
            "📖 **How to Get a GitHub Token**\n\n"
            "**Step 1 — Create an account:**\n"
            "① Go to `github.com` and sign up\n\n"
            "**Step 2 — Go to settings:**\n"
            "① Profile picture → **Settings**\n"
            "② Scroll down → **Developer settings**\n"
            "③ **Personal access tokens** → **Fine-grained tokens**\n"
            "④ **Generate new token**\n\n"
            "**Step 3 — Token settings:**\n"
            "① Any name (e.g. `mega-leecher`)\n"
            "② Expiration: **No expiration**\n"
            "③ Repository access: **All repositories**\n"
            "④ Permissions → Contents: **Read and write**\n\n"
            "⚠️ The token is shown only once — copy it here!",

        "gh_token_prompt":
            "🔑 Please send your GitHub token\n(starts with `ghp_` or `github_pat_`):",
        "gh_space_info":
            "📊 **GitHub Cloud Storage:**\n\n"
            "👤 Account: `{username}`\n\n"
            "**Per-repository status:**\n{repos_info}\n"
            "[{bar}] {pct:.1f}%\n"
            "📦 Used: {used:.2f} GB\n"
            "✅ Free: {free:.2f} GB of {total:.0f} GB\n\n"
            "🔢 Today's quota: **{quota} of {limit}** remaining",
        "gh_no_token_menu":   "❌ Token not set.",
        "gh_warn_clear":
            "⚠️ **Warning!**\nAll uploaded files on GitHub will be deleted. Are you sure?",
        "gh_btn_confirm_clear": "✅ Yes, clear",
        "gh_btn_cancel":     "❌ Cancel",
        "gh_clearing":       "🗑 Clearing...",
        "gh_clear_done":     "✅ **GitHub storage cleared!**\nYou can now upload new files.",
        "gh_clear_error":    "⚠️ Clear failed:\n`{e}`",
        "gh_cancelled":      "❌ Operation cancelled.",
        "gh_verifying":      "⏳ Verifying token...",
        "gh_invalid_token":  "❌ {err}\nPlease try again from the GitHub menu.",
        "gh_creating_repos": "✅ Token valid! Account: `{username}`\n⏳ Creating 3 repositories...",
        "gh_creating_repo_i": "✅ Token valid! Account: `{username}`\n⏳ Creating repository {i} of {total}...",
        "gh_repo_error":
            "❌ Failed to create repository.\nPlease check that your token has the required 4 permissions.",
        "gh_connect_success":
            "✅ **Connected to GitHub successfully!**\n\n"
            "👤 Account: `{username}`\n"
            "📁 Repositories: {repos}\n"
            "💾 Capacity: up to {cap} GB\n\n"
            "The **☁️ Upload to GitHub** option will now appear in the file processing menu.",

        # Google Drive menu
        "gd_menu_title":
            "📂 **Google Drive Management**\n\nStatus: {status}\n\n"
            "Connect your Google account to upload files and get direct download links.\n\n"
            "💾 Free capacity: **15 GB**\n"
            "🔢 Daily quota: **10 uploads**",
        "gd_connected":      "✅ Connected",
        "gd_not_connected":  "❌ Not connected",
        "gd_btn_guide":      "📖 Step-by-Step Guide",
        "gd_btn_dl_guide":   "📥 Download Guide",
        "gd_btn_connect":    "🔗 Connect Google Account",
        "gd_btn_space":      "📊 Storage Info",
        "gd_btn_clear":      "🗑 Clear Uploaded Files",
        "gd_btn_disconnect": "❌ Disconnect",

        "gd_guide_text":
            "📖 **How to Connect Google Drive**\n\n"
            "**Step 1 — Open the link:**\n"
            "① Tap **Connect Google Account**\n"
            "② **Copy** the link\n"
            "③ Open it in Chrome or Safari\n"
            "   ⚠️ Do NOT open in Telegram's built-in browser\n\n"
            "**Step 2 — Sign in to Google:**\n"
            "① Sign in with your Google account\n"
            "② Click **Allow**\n\n"
            "**Step 3 — Get the code:**\n"
            "① The browser will show an error page — this is **normal**\n"
            "② Copy the full address from the address bar\n"
            "   Example: `http://localhost/?code=4/0Ae...`\n"
            "③ **Send** that address to the bot",

        "gd_dl_guide_text":
            "📥 **Google Drive Download Guide**\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "**Method 1 — Browser:**\n\n"
            "① Copy the **direct download** link\n"
            "② Paste it in your browser\n"
            "③ If Google shows a virus warning, click **Download anyway**\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "**Method 2 — Android app (if method 1 doesn't work):**\n\n"
            "① Install the MITM Drive Downloader app\n"
            "② Open the app and tap **Start**\n"
            "③ Paste the **direct download** link\n"
            "④ Tap **Download**",

        "gd_connect_url":
            "🔗 **Connect to Google Drive:**\n\n"
            "**Step 1:** Open this link in your browser:\n{url}\n\n"
            "**Step 2:** Sign in with your Google account and allow access\n\n"
            "**Step 3:** Copy the full address of the error page and send it here\n\n"
            "Example: `http://localhost/?code=4/xxxxx`",
        "gd_btn_cancel_connect": "❌ Cancel Connection",
        "gd_checking_space": "⏳ Checking storage...",
        "gd_no_account":     "❌ Google account not connected.",
        "gd_auth_error":     "❌ Authentication error. Please reconnect.",
        "gd_space_info":
            "📊 **Google Drive Storage:**\n\n"
            "[{bar}] {pct:.1f}%\n"
            "📦 Used: {used:.2f} GB\n"
            "✅ Free: {free:.2f} GB of {total:.0f} GB\n\n"
            "🔢 Today's quota: **{quota} of {limit}** remaining",
        "gd_warn_clear":
            "⚠️ **Warning!**\nAll uploaded files on Google Drive will be deleted. Are you sure?",
        "gd_btn_confirm_clear": "✅ Yes, clear",
        "gd_no_account_short": "❌ Account not connected.",
        "gd_auth_error_short": "❌ Authentication error.",
        "gd_no_folder":      "❌ Folder not found.",
        "gd_clearing":       "🗑 Clearing...",
        "gd_clear_done":     "✅ **Cleared!**\n{count} files deleted.",
        "gd_clear_error":    "⚠️ Error: `{e}`",
        "gd_cancelled":      "❌ Connection cancelled.",
        "gd_cancelled_short": "❌ Operation cancelled.",
        "gd_disconnected":   "✅ Google account disconnected.",
        "gd_verifying":      "⏳ Verifying code...",
        "gd_invalid_code":   "❌ Invalid code. Please try again from the Google Drive menu.",
        "gd_creating_folder": "⏳ Creating folder...",
        "gd_oauth_not_configured":
            "❌ Google OAuth credentials not set in config.env.\n"
            "Please fill in GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        "gd_connect_success":
            "✅ **Connected to Google Drive successfully!**\n\n"
            "💾 Free capacity: 15 GB\n\n"
            "The **📂 Upload to Google Drive** option will now appear in the file processing menu.",
        "gd_code_error":     "❌ Error: `{e}`",

        # Drive upload
        "gd_uploading":
            "📂 **Uploading to Google Drive...**\n[{bar}] {pct}%\n"
            "{sent:.1f} MB of {total:.1f} MB",
        "gd_upload_start_error": "❌ Upload initiation error: {code}",
        "gd_upload_fail":    "❌ Upload failed: {code}",
        "gd_clearing_file":  "🗑 Clearing... ({deleted} files deleted)",
        "gd_upload_done":    "✅ Upload complete!",
        "gd_quota_core":     "⛔️ Daily Google Drive upload quota reached!\nEach user is allowed {limit} uploads per day.",
        "gd_no_account_core": "❌ Google account not connected.\nPlease connect via the 📂 Connect Google Drive menu.",
        "gd_auth_error_core": "❌ Google authentication error. Please reconnect.",
        "gd_folder_error":   "❌ Error accessing Google Drive.",
        "gd_queued":         "⏳ **Google Drive upload queue**\n\nUpload will start as soon as a slot is free...",
        "gd_success":
            "✅ **Upload to Google Drive successful!**\n\n"
            "📄 File name: `{name}`\n"
            "{quota}"
            "\n🔗 **View file:**\n`{view}`\n\n"
            "⬇️ **Direct download:**\n`{dl}`\n\n"
            "⚠️ For large files, Google may require confirmation.",
        "gd_size_limit":     "❌ File size exceeds 2 GB ({size:.2f} GB)",
        "gd_quota_line":     "🔢 Remaining quota today: **{remaining} uploads**\n",
        "gd_folder_create_error": "Folder creation error: {code}",

        # Admin panel
        "admin_no_users":    "No active users found.",
        "admin_user_list_title": "📋 **User List** — Page {page} of {total_pages} (Total: {total})\n",
        "admin_user_entry":  "**{i}.** 👤 {uname}\n  🆔 `{uid}`\n  ⏳ Subscription: **{rd} days**\n  🎬 YouTube: **{ytd} days**\n━━━━━━━━━━━━━━━━━\n",
        "admin_btn_prev":    "→ Previous",
        "admin_btn_next":    "Next ←",
        "admin_ask_user_id": "User numeric ID:",
        "admin_ask_yt_id":   "YouTube user numeric ID:",
        "admin_ask_days":    "Number of subscription days:",
        "admin_ask_yt_days": "Number of YouTube subscription days:",
        "admin_ask_username": "Username:",
        "admin_cancel":      "Cancel",
        "admin_cancelled":   "Cancelled.",
        "admin_clean_done":  "✅ Cleaned.",
        "admin_added":       "✅ Added. Validity: {days} days.",
        "admin_yt_added":    "✅ YouTube access granted. Validity: {days} days.",
        "admin_deleted":     "✅ Access revoked.",
        "admin_not_found":   "❌ Not found.",

        # action texts in progress bar
        "receiving_file":    "Receiving file",
        "sending_video":     "Sending video",
        "sending_audio":     "Sending audio",
        "sending_file":      "Sending file",
        "btn_audio_only":    "🎵 Audio only ({size})",
        "audio_only_label":  "Audio",
        "torrent_dl_action": "Torrent download",

        # Instagram
        "ig_received":       "📸 Instagram post received.",
        "ig_select_action":  "📸 **Instagram Post**\n\nChoose how to send:",

        # MITM
        "mitm_caption":      "📲 **MITM Drive Downloader**\nUse this app if browser download doesn't work",
    }
}


def get_lang(user_id, users_db=None):
    # / دریافت زبان کاربر از دیتابیس — Get user language from database
    if users_db is None:
        return "fa"
    uid = str(user_id)
    d = users_db.get(uid, {})
    if isinstance(d, dict):
        return d.get("lang", "fa")
    return "fa"


def T(lang, key, **kwargs):
    # / ترجمه رشته بر اساس زبان — Translate string based on language
    text = STRINGS.get(lang, STRINGS["fa"]).get(key)
    if text is None:
        text = STRINGS["fa"].get(key, key)
    return text.format(**kwargs) if kwargs else text
