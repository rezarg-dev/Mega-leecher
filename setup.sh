#!/usr/bin/env bash
# ============================================================
#   Mega Leecher — Automated Install Script
#   https://github.com/rezarg-dev/Mega-leecher
# ============================================================
set -e

# ── Colors ───────────────────────────────────────────────────
RED='\033[0;31m';  GREEN='\033[0;32m';  YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m';   MAGENTA='\033[0;35m'
BOLD='\033[1m';    DIM='\033[2m';        RESET='\033[0m'

# ── Logo ─────────────────────────────────────────────────────
print_logo() {
    echo -e "${MAGENTA}${BOLD}"
    echo '  ███╗   ███╗███████╗ ██████╗  █████╗ '
    echo '  ████╗ ████║██╔════╝██╔════╝ ██╔══██╗'
    echo '  ██╔████╔██║█████╗  ██║  ███╗███████║'
    echo '  ██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║'
    echo '  ██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║'
    echo '  ╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝'
    echo -e "${CYAN}"
    echo '  ██╗     ███████╗███████╗ ██████╗██╗  ██╗███████╗██████╗ '
    echo '  ██║     ██╔════╝██╔════╝██╔════╝██║  ██║██╔════╝██╔══██╗'
    echo '  ██║     █████╗  █████╗  ██║     ███████║█████╗  ██████╔╝'
    echo '  ██║     ██╔══╝  ██╔══╝  ██║     ██╔══██║██╔══╝  ██╔══██╗'
    echo '  ███████╗███████╗███████╗╚██████╗██║  ██║███████╗██║  ██║'
    echo '  ╚══════╝╚══════╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝'
    echo -e "${DIM}${CYAN}                    Telegram File Manager Bot${RESET}"
    echo ""
}

# ── Helpers ───────────────────────────────────────────────────
info()    { echo -e "${CYAN}  ➜  $1${RESET}"; }
success() { echo -e "${GREEN}  ✔  $1${RESET}"; }
warn()    { echo -e "${YELLOW}  ⚠  $1${RESET}"; }
error()   { echo -e "${RED}  ✘  $1${RESET}"; exit 1; }
section() { echo -e "\n${BOLD}${BLUE}━━━  $1  ━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"; }
ask()     { echo -e "${YELLOW}  ?  ${BOLD}$1${RESET}"; }

confirm() {
    local prompt="$1" default="${2:-y}"
    local yn_hint; [[ $default == "y" ]] && yn_hint="[Y/n]" || yn_hint="[y/N]"
    ask "$prompt $yn_hint"
    read -r -p "      " reply
    reply="${reply:-$default}"
    [[ "$reply" =~ ^[Yy]$ ]]
}

read_val() {
    local prompt="$1" var_name="$2" secret="${3:-no}"
    ask "$prompt"
    if [[ $secret == "yes" ]]; then
        read -r -s -p "      " "$var_name"; echo ""
    else
        read -r -p "      " "$var_name"
    fi
}

# ── Constants ─────────────────────────────────────────────────
INSTALL_DIR="/opt/mega-leecher"
SERVICE_NAME="mega-leecher"
CLI_PATH="/usr/local/bin/mega-leecher"
REPO_URL="https://github.com/rezarg-dev/Mega-leecher"
PYTHON_MIN="3.9"

# ═══════════════════════════════════════════════════════════════
#   STEP 0 — Pre-flight checks
# ═══════════════════════════════════════════════════════════════
clear
print_logo
section "Pre-flight Checks"

[[ $EUID -ne 0 ]] && error "این اسکریپت باید با دسترسی root اجرا شود.\nدوباره با sudo bash setup.sh اجرا کنید."
success "Running as root"

if ! command -v apt-get &>/dev/null; then
    error "این اسکریپت فقط برای سیستم‌های Debian/Ubuntu طراحی شده است."
fi
success "Compatible OS detected"

# ═══════════════════════════════════════════════════════════════
#   STEP 1 — Install system dependencies
# ═══════════════════════════════════════════════════════════════
section "Installing System Dependencies"

info "Updating package lists..."
apt-get update -qq

info "Installing required packages..."
apt-get install -y -qq \
    python3 python3-pip python3-venv python3-libtorrent \
    git curl ffmpeg rar unrar unzip zip p7zip-full \
    > /dev/null 2>&1
success "System packages installed"

info "Installing Node.js 20.x..."
if ! node --version 2>/dev/null | grep -q "v20"; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs > /dev/null 2>&1
fi
NODE_VER=$(node --version 2>/dev/null || echo "not found")
success "Node.js $NODE_VER"

# ═══════════════════════════════════════════════════════════════
#   STEP 2 — Setup install directory
# ═══════════════════════════════════════════════════════════════
section "Setting Up Directory"

if [[ -d "$INSTALL_DIR" ]]; then
    warn "پوشه $INSTALL_DIR از قبل وجود دارد."
    if confirm "آیا می‌خواهید محتوای قبلی حذف و از نو نصب شود؟" "n"; then
        rm -rf "$INSTALL_DIR"
        info "پوشه قبلی حذف شد."
    fi
fi

mkdir -p "$INSTALL_DIR/temp"
success "Install directory: $INSTALL_DIR"

# ── Copy bot files ────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for f in bot.py config.py; do
    if [[ -f "$SCRIPT_DIR/$f" ]]; then
        cp "$SCRIPT_DIR/$f" "$INSTALL_DIR/$f"
    else
        error "فایل $f پیدا نشد! مطمئن شوید setup.sh را از پوشه پروژه اجرا می‌کنید."
    fi
done
success "Bot files copied"

# ── Python venv ───────────────────────────────────────────────
info "Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv" --system-site-packages > /dev/null 2>&1
success "Virtual environment created"

info "Installing Python packages (این ممکن است چند دقیقه طول بکشد)..."
"$INSTALL_DIR/venv/bin/pip" install -q --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -q \
    pyrogram tgcrypto yt-dlp aiohttp httpx
success "Python packages installed"

# ═══════════════════════════════════════════════════════════════
#   STEP 3 — Configuration
# ═══════════════════════════════════════════════════════════════
section "Bot Configuration"

echo -e "${DIM}  برای دریافت API_ID و API_HASH به my.telegram.org مراجعه کنید${RESET}\n"

read_val "API_ID (عدد):" BOT_API_ID
read_val "API_HASH:" BOT_API_HASH
read_val "BOT_TOKEN (از @BotFather):" BOT_TOKEN
read_val "ADMIN_ID (آیدی عددی تلگرام شما):" BOT_ADMIN_ID
read_val "PURCHASE_USERNAME (یوزرنیم برای خرید، مثال: @myuser):" BOT_PURCHASE_USER

# ── Validate numeric fields ───────────────────────────────────
[[ ! "$BOT_API_ID" =~ ^[0-9]+$ ]]   && error "API_ID باید عدد باشد."
[[ ! "$BOT_ADMIN_ID" =~ ^[0-9]+$ ]] && error "ADMIN_ID باید عدد باشد."
success "Configuration values accepted"

# ═══════════════════════════════════════════════════════════════
#   STEP 4 — Google Drive (optional)
# ═══════════════════════════════════════════════════════════════
section "Google Drive Integration (Optional)"

echo -e "${DIM}  قابلیت آپلود فایل به گوگل درایو و دریافت لینک دانلود مستقیم${RESET}\n"

GDRIVE_ENABLED=false
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""

if confirm "آیا می‌خواهید پشتیبانی از گوگل درایو را فعال کنید؟" "y"; then
    echo ""
    echo -e "${DIM}  برای دریافت credentials:${RESET}"
    echo -e "${DIM}  1. به console.cloud.google.com بروید${RESET}"
    echo -e "${DIM}  2. یک پروژه بسازید و Google Drive API را فعال کنید${RESET}"
    echo -e "${DIM}  3. OAuth 2.0 Client ID بسازید (نوع: Web application)${RESET}"
    echo -e "${DIM}  4. Redirect URI اضافه کنید: http://localhost${RESET}\n"

    read_val "Google Client ID:" GOOGLE_CLIENT_ID
    read_val "Google Client Secret:" GOOGLE_CLIENT_SECRET

    if [[ -n "$GOOGLE_CLIENT_ID" && -n "$GOOGLE_CLIENT_SECRET" ]]; then
        GDRIVE_ENABLED=true
        success "Google Drive فعال شد"
    else
        warn "مقادیر وارد نشد — گوگل درایو غیرفعال ماند"
    fi
else
    info "گوگل درایو رد شد — بعداً می‌توانید با دستور mega-leecher فعال کنید"
fi

# ═══════════════════════════════════════════════════════════════
#   STEP 5 — Write config.env
# ═══════════════════════════════════════════════════════════════
section "Writing Configuration File"

cat > "$INSTALL_DIR/config.env" << CONF
# Mega Leecher — Configuration
# Generated by setup.sh on $(date)

API_ID=${BOT_API_ID}
API_HASH=${BOT_API_HASH}
BOT_TOKEN=${BOT_TOKEN}
ADMIN_ID=${BOT_ADMIN_ID}
PURCHASE_USERNAME=${BOT_PURCHASE_USER}

GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}

INSTALL_DIR=${INSTALL_DIR}
CONF

chmod 600 "$INSTALL_DIR/config.env"
success "config.env ذخیره شد (chmod 600)"

# ═══════════════════════════════════════════════════════════════
#   STEP 6 — Systemd service
# ═══════════════════════════════════════════════════════════════
section "Installing Systemd Service"

cat > "/etc/systemd/system/${SERVICE_NAME}.service" << SVC
[Unit]
Description=Mega Leecher Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/python bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVC

systemctl daemon-reload
systemctl enable "$SERVICE_NAME" > /dev/null 2>&1
success "Systemd service installed and enabled"

# ═══════════════════════════════════════════════════════════════
#   STEP 7 — Install mega-leecher CLI
# ═══════════════════════════════════════════════════════════════
section "Installing mega-leecher Command"

cat > "$CLI_PATH" << 'CLI_EOF'
#!/usr/bin/env bash
# Mega Leecher — Management CLI

RED='\033[0;31m';  GREEN='\033[0;32m';  YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m';   MAGENTA='\033[0;35m'
BOLD='\033[1m';    DIM='\033[2m';        RESET='\033[0m'

INSTALL_DIR="/opt/mega-leecher"
SERVICE_NAME="mega-leecher"

print_logo() {
    clear
    echo -e "${MAGENTA}${BOLD}"
    echo '  ███╗   ███╗███████╗ ██████╗  █████╗ '
    echo '  ████╗ ████║██╔════╝██╔════╝ ██╔══██╗'
    echo '  ██╔████╔██║█████╗  ██║  ███╗███████║'
    echo '  ██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║'
    echo '  ██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║'
    echo '  ╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝'
    echo -e "${CYAN}"
    echo '  ██╗     ███████╗███████╗ ██████╗██╗  ██╗███████╗██████╗ '
    echo '  ██║     ██╔════╝██╔════╝██╔════╝██║  ██║██╔════╝██╔══██╗'
    echo '  ██║     █████╗  █████╗  ██║     ███████║█████╗  ██████╔╝'
    echo '  ██║     ██╔══╝  ██╔══╝  ██║     ██╔══██║██╔══╝  ██╔══██╗'
    echo '  ███████╗███████╗███████╗╚██████╗██║  ██║███████╗██║  ██║'
    echo '  ╚══════╝╚══════╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝'
    echo -e "${DIM}${CYAN}                    Telegram File Manager Bot${RESET}"
    echo ""
}

get_status() {
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        echo -e "${GREEN}${BOLD}● RUNNING${RESET}"
    else
        echo -e "${RED}${BOLD}● STOPPED${RESET}"
    fi
}

get_gdrive_status() {
    local cfg="$INSTALL_DIR/config.env"
    if [[ -f "$cfg" ]]; then
        local cid; cid=$(grep "^GOOGLE_CLIENT_ID=" "$cfg" | cut -d= -f2)
        [[ -n "$cid" ]] && echo -e "${GREEN}فعال${RESET}" || echo -e "${DIM}غیرفعال${RESET}"
    else
        echo -e "${DIM}نامشخص${RESET}"
    fi
}

print_status_bar() {
    local status; status=$(get_status)
    local gdrive; gdrive=$(get_gdrive_status)
    echo -e "  ${DIM}وضعیت ربات:${RESET}      $status"
    echo -e "  ${DIM}گوگل درایو:${RESET}      $gdrive"
    echo -e "  ${DIM}مسیر نصب:${RESET}        ${DIM}$INSTALL_DIR${RESET}"
    echo ""
    echo -e "  ${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
}

print_menu() {
    echo -e "  ${BOLD}مدیریت سرویس:${RESET}"
    echo -e "  ${CYAN}  1)${RESET}  شروع ربات"
    echo -e "  ${CYAN}  2)${RESET}  توقف ربات"
    echo -e "  ${CYAN}  3)${RESET}  ری‌استارت ربات"
    echo -e "  ${CYAN}  4)${RESET}  مشاهده لاگ زنده"
    echo ""
    echo -e "  ${BOLD}پیکربندی:${RESET}"
    echo -e "  ${CYAN}  5)${RESET}  ویرایش config.env"
    echo -e "  ${CYAN}  6)${RESET}  راه‌اندازی گوگل درایو"
    echo -e "  ${CYAN}  7)${RESET}  غیرفعال کردن گوگل درایو"
    echo ""
    echo -e "  ${BOLD}نگهداری:${RESET}"
    echo -e "  ${CYAN}  8)${RESET}  پاکسازی فایل‌های موقت"
    echo -e "  ${CYAN}  9)${RESET}  آپدیت ربات از گیتهاب"
    echo -e "  ${CYAN} 10)${RESET}  نصب مجدد (Reinstall)"
    echo -e "  ${RED}  11)${RESET}  حذف کامل (Uninstall)"
    echo ""
    echo -e "  ${CYAN}  0)${RESET}  خروج"
    echo ""
    echo -e "  ${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "  انتخاب کنید: \c"
}

do_start()   { systemctl start   "$SERVICE_NAME" && echo -e "${GREEN}  ✔ ربات شروع شد${RESET}" || echo -e "${RED}  ✘ خطا در شروع${RESET}"; }
do_stop()    { systemctl stop    "$SERVICE_NAME" && echo -e "${GREEN}  ✔ ربات متوقف شد${RESET}" || echo -e "${RED}  ✘ خطا${RESET}"; }
do_restart() { systemctl restart "$SERVICE_NAME" && echo -e "${GREEN}  ✔ ری‌استارت شد${RESET}" || echo -e "${RED}  ✘ خطا${RESET}"; }
do_logs()    { journalctl -u "$SERVICE_NAME" -f --no-pager; }

do_edit_config() {
    local editor="${EDITOR:-nano}"
    $editor "$INSTALL_DIR/config.env"
    echo -e "${YELLOW}  ⚠  برای اعمال تغییرات ربات را ری‌استارت کنید (گزینه 3)${RESET}"
}

do_setup_gdrive() {
    echo ""
    echo -e "${CYAN}  برای دریافت credentials به console.cloud.google.com بروید${RESET}"
    echo -e "${DIM}  نوع: Web application | Redirect URI: http://localhost${RESET}\n"
    echo -e "${YELLOW}  ?  ${BOLD}Google Client ID:${RESET}"; read -r -p "      " gcid
    echo -e "${YELLOW}  ?  ${BOLD}Google Client Secret:${RESET}"; read -r -p "      " gcsecret
    if [[ -z "$gcid" || -z "$gcsecret" ]]; then
        echo -e "${RED}  ✘  مقادیر خالی — لغو شد${RESET}"; return
    fi
    sed -i "s|^GOOGLE_CLIENT_ID=.*|GOOGLE_CLIENT_ID=$gcid|" "$INSTALL_DIR/config.env"
    sed -i "s|^GOOGLE_CLIENT_SECRET=.*|GOOGLE_CLIENT_SECRET=$gcsecret|" "$INSTALL_DIR/config.env"
    echo -e "${GREEN}  ✔  گوگل درایو فعال شد — ربات را ری‌استارت کنید (گزینه 3)${RESET}"
}

do_disable_gdrive() {
    sed -i "s|^GOOGLE_CLIENT_ID=.*|GOOGLE_CLIENT_ID=|" "$INSTALL_DIR/config.env"
    sed -i "s|^GOOGLE_CLIENT_SECRET=.*|GOOGLE_CLIENT_SECRET=|" "$INSTALL_DIR/config.env"
    echo -e "${GREEN}  ✔  گوگل درایو غیرفعال شد — ربات را ری‌استارت کنید (گزینه 3)${RESET}"
}

do_clean_temp() {
    local temp_dir="$INSTALL_DIR/temp"
    local count; count=$(find "$temp_dir" -mindepth 1 | wc -l)
    rm -rf "${temp_dir:?}"/*
    echo -e "${GREEN}  ✔  $count فایل/پوشه موقت حذف شد${RESET}"
}

do_update() {
    echo -e "${CYAN}  ➜  در حال آپدیت از گیتهاب...${RESET}"
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    cd "$INSTALL_DIR"
    if [[ -d ".git" ]]; then
        git pull origin main
    else
        echo -e "${YELLOW}  ⚠  این نصب از git clone نیست — آپدیت دستی لازم است${RESET}"
        systemctl start "$SERVICE_NAME"; return
    fi
    systemctl start "$SERVICE_NAME"
    echo -e "${GREEN}  ✔  آپدیت انجام شد و ربات شروع شد${RESET}"
}

do_reinstall() {
    echo -e "${YELLOW}  ⚠  این عملیات config.env را حذف نمی‌کند${RESET}"
    echo -e "  ادامه می‌دهید؟ [y/N] \c"; read -r reply
    [[ ! "$reply" =~ ^[Yy]$ ]] && return
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    local cfg_backup; cfg_backup=$(cat "$INSTALL_DIR/config.env" 2>/dev/null || echo "")
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    bash "$SCRIPT_DIR/setup.sh"
}

do_uninstall() {
    echo ""
    echo -e "${RED}${BOLD}  ⚠  هشدار: تمام فایل‌های ربات و تنظیمات حذف می‌شوند!${RESET}"
    echo -e "  برای تأیید عبارت ${BOLD}UNINSTALL${RESET} را تایپ کنید: \c"
    read -r confirm_text
    [[ "$confirm_text" != "UNINSTALL" ]] && echo -e "${CYAN}  لغو شد${RESET}" && return
    systemctl stop    "$SERVICE_NAME" 2>/dev/null || true
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    systemctl daemon-reload
    rm -rf "$INSTALL_DIR"
    rm -f "/usr/local/bin/mega-leecher"
    echo -e "${GREEN}  ✔  Mega Leecher کاملاً حذف شد${RESET}"
    exit 0
}

# ── Main loop ─────────────────────────────────────────────────
while true; do
    print_logo
    print_status_bar
    print_menu
    read -r choice
    echo ""
    case "$choice" in
        1)  do_start ;;
        2)  do_stop ;;
        3)  do_restart ;;
        4)  do_logs ;;
        5)  do_edit_config ;;
        6)  do_setup_gdrive ;;
        7)  do_disable_gdrive ;;
        8)  do_clean_temp ;;
        9)  do_update ;;
        10) do_reinstall ;;
        11) do_uninstall ;;
        0)  echo -e "${DIM}  خروج...${RESET}\n"; exit 0 ;;
        *)  echo -e "${RED}  ✘  گزینه نامعتبر${RESET}" ;;
    esac
    echo ""
    echo -e "  ${DIM}برای بازگشت به منو Enter بزنید...${RESET}"
    read -r
done
CLI_EOF

chmod +x "$CLI_PATH"
success "دستور mega-leecher نصب شد در $CLI_PATH"

# ═══════════════════════════════════════════════════════════════
#   STEP 8 — Start the bot
# ═══════════════════════════════════════════════════════════════
section "Starting Mega Leecher"

systemctl start "$SERVICE_NAME"
sleep 2
if systemctl is-active --quiet "$SERVICE_NAME"; then
    success "ربات با موفقیت شروع شد! ✨"
else
    warn "سرویس شروع نشد — با دستور mega-leecher → گزینه 4 لاگ را بررسی کنید"
fi

# ═══════════════════════════════════════════════════════════════
#   Done
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}${GREEN}  ╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}  ║     نصب Mega Leecher تکمیل شد! 🎉      ║${RESET}"
echo -e "${BOLD}${GREEN}  ╚══════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${CYAN}برای مدیریت ربات دستور زیر را بزنید:${RESET}"
echo -e "  ${BOLD}  mega-leecher${RESET}"
echo ""
