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
info()    { echo -e "${CYAN}  -->  $1${RESET}"; }
success() { echo -e "${GREEN}  [OK] $1${RESET}"; }
warn()    { echo -e "${YELLOW}  [!!] $1${RESET}"; }
error()   { echo -e "${RED}  [ERR] $1${RESET}"; exit 1; }
section() { echo -e "\n${BOLD}${BLUE}---  $1  ---${RESET}\n"; }
ask()     { echo -e "${YELLOW}  [?]  ${BOLD}$1${RESET}"; }

confirm() {
    local prompt="$1" default="${2:-y}"
    local yn_hint; [[ $default == "y" ]] && yn_hint="[Y/n]" || yn_hint="[y/N]"
    ask "$prompt $yn_hint"
    read -r -p "      " reply
    reply="${reply:-$default}"
    [[ "$reply" =~ ^[Yy]$ ]]
}

read_val() {
    local prompt="$1" var_name="$2"
    ask "$prompt"
    read -r -p "      " "$var_name"
}

# ── Constants ─────────────────────────────────────────────────
INSTALL_DIR="/opt/mega-leecher"
SERVICE_NAME="mega-leecher"
CLI_PATH="/usr/local/bin/mega-leecher"

# =============================================================
#   STEP 0 — Pre-flight checks
# =============================================================
clear
print_logo
section "Pre-flight Checks"

[[ $EUID -ne 0 ]] && error "This script must be run as root.\nRun: sudo bash setup.sh"
success "Running as root"

if ! command -v apt-get &>/dev/null; then
    error "This script only supports Debian/Ubuntu systems."
fi
success "Compatible OS detected"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ ! -f "$SCRIPT_DIR/bot.py" ]]    && error "bot.py not found! Run setup.sh from the project directory."
[[ ! -f "$SCRIPT_DIR/config.py" ]] && error "config.py not found! Run setup.sh from the project directory."
success "Project files found"

# =============================================================
#   STEP 1 — System dependencies
# =============================================================
section "Installing System Dependencies"

info "Updating package lists..."
apt-get update -qq

info "Installing required packages..."
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3 python3-pip python3-venv python3-libtorrent \
    git curl ffmpeg rar unrar unzip zip p7zip-full \
    > /dev/null 2>&1
success "System packages installed"

info "Checking Node.js 20.x..."
if ! node --version 2>/dev/null | grep -q "v20"; then
    info "Installing Node.js 20.x..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs > /dev/null 2>&1
fi
NODE_VER=$(node --version 2>/dev/null || echo "not found")
success "Node.js $NODE_VER ready"

# =============================================================
#   STEP 2 — Install directory
# =============================================================
section "Setting Up Directory"

if [[ -d "$INSTALL_DIR" ]]; then
    warn "Directory $INSTALL_DIR already exists."
    if confirm "Remove existing installation and reinstall?" "n"; then
        systemctl stop "$SERVICE_NAME" 2>/dev/null || true
        # Keep config.env if it exists
        if [[ -f "$INSTALL_DIR/config.env" ]]; then
            cp "$INSTALL_DIR/config.env" /tmp/mega_leecher_config_backup.env
            info "Config backed up to /tmp/mega_leecher_config_backup.env"
        fi
        rm -rf "$INSTALL_DIR"
        info "Previous installation removed."
    fi
fi

mkdir -p "$INSTALL_DIR/temp"
success "Install directory ready: $INSTALL_DIR"

# Copy bot files
info "Copying bot files..."
cp "$SCRIPT_DIR/bot.py"    "$INSTALL_DIR/bot.py"
cp "$SCRIPT_DIR/config.py" "$INSTALL_DIR/config.py"
success "bot.py and config.py copied"

# Restore backed up config if exists
if [[ -f /tmp/mega_leecher_config_backup.env ]]; then
    cp /tmp/mega_leecher_config_backup.env "$INSTALL_DIR/config.env"
    rm /tmp/mega_leecher_config_backup.env
    success "Previous config.env restored"
fi

# Python venv
info "Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv" --system-site-packages > /dev/null 2>&1
success "Virtual environment created"

info "Installing Python packages (this may take a few minutes)..."
"$INSTALL_DIR/venv/bin/pip" install -q --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -q pyrogram tgcrypto yt-dlp aiohttp httpx 2>/dev/null
success "Python packages installed"

# Verify key packages
info "Verifying packages..."
for pkg in pyrogram yt_dlp aiohttp httpx; do
    "$INSTALL_DIR/venv/bin/python" -c "import $pkg" 2>/dev/null \
        || error "Package '$pkg' failed to import. Check pip output above."
done
success "All packages verified"

# =============================================================
#   STEP 3 — Configuration
# =============================================================
# Skip config step if config.env already exists
if [[ -f "$INSTALL_DIR/config.env" ]]; then
    warn "Existing config.env found — skipping configuration step."
    warn "Edit it with: nano $INSTALL_DIR/config.env"
else

section "Bot Configuration"

echo -e "${DIM}  Get API_ID and API_HASH from: my.telegram.org/apps${RESET}\n"

read_val "API_ID (number):"                              BOT_API_ID
read_val "API_HASH:"                                     BOT_API_HASH
read_val "BOT_TOKEN (from @BotFather):"                  BOT_TOKEN
read_val "ADMIN_ID (your numeric Telegram user ID):"     BOT_ADMIN_ID
read_val "PURCHASE_USERNAME (e.g. @yourusername):"       BOT_PURCHASE_USER

[[ ! "$BOT_API_ID" =~ ^[0-9]+$ ]]   && error "API_ID must be a number."
[[ ! "$BOT_ADMIN_ID" =~ ^[0-9]+$ ]] && error "ADMIN_ID must be a number."
success "Configuration values accepted"

# =============================================================
#   STEP 4 — Google Drive (optional)
# =============================================================
section "Google Drive Integration (Optional)"

echo -e "${DIM}  Allows users to upload files to Google Drive and get download links.${RESET}\n"

GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""

if confirm "Do you want to enable Google Drive support?" "y"; then
    echo ""
    echo -e "${DIM}  How to get credentials:${RESET}"
    echo -e "${DIM}  1. Go to console.cloud.google.com${RESET}"
    echo -e "${DIM}  2. Create a project and enable Google Drive API${RESET}"
    echo -e "${DIM}  3. Create OAuth 2.0 Client ID (type: Web application)${RESET}"
    echo -e "${DIM}  4. Add redirect URI: http://localhost${RESET}\n"

    read_val "Google Client ID:" GOOGLE_CLIENT_ID
    read_val "Google Client Secret:" GOOGLE_CLIENT_SECRET

    if [[ -n "$GOOGLE_CLIENT_ID" && -n "$GOOGLE_CLIENT_SECRET" ]]; then
        success "Google Drive credentials saved"
    else
        warn "Values empty — Google Drive disabled. Enable later with: mega-leecher"
        GOOGLE_CLIENT_ID=""
        GOOGLE_CLIENT_SECRET=""
    fi
else
    info "Google Drive skipped. You can enable it later with: mega-leecher"
fi

# =============================================================
#   STEP 5 — Write config.env
# =============================================================
section "Writing Configuration File"

cat > "$INSTALL_DIR/config.env" << CONF
# Mega Leecher Configuration
# Generated: $(date)

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
success "config.env saved (permissions: 600)"

fi  # end of config skip block

# =============================================================
#   STEP 6 — Systemd service
# =============================================================
section "Installing Systemd Service"

cat > "/etc/systemd/system/${SERVICE_NAME}.service" << SVC
[Unit]
Description=Mega Leecher Telegram Bot
Documentation=https://github.com/rezarg-dev/Mega-leecher
After=network.target network-online.target
Wants=network-online.target

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

# =============================================================
#   STEP 7 — Install mega-leecher CLI
# =============================================================
section "Installing mega-leecher CLI"

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
        echo -e "${GREEN}${BOLD}  RUNNING${RESET}"
    else
        echo -e "${RED}${BOLD}  STOPPED${RESET}"
    fi
}

get_gdrive_status() {
    local cfg="$INSTALL_DIR/config.env"
    if [[ -f "$cfg" ]]; then
        local cid; cid=$(grep "^GOOGLE_CLIENT_ID=" "$cfg" | cut -d= -f2)
        [[ -n "$cid" ]] && echo -e "${GREEN}  Enabled${RESET}" || echo -e "${DIM}  Disabled${RESET}"
    else
        echo -e "${DIM}  Unknown${RESET}"
    fi
}

print_status_bar() {
    echo -e "  ${DIM}Bot status:${RESET}     $(get_status)"
    echo -e "  ${DIM}Google Drive:${RESET}   $(get_gdrive_status)"
    echo -e "  ${DIM}Install path:${RESET}   ${DIM}$INSTALL_DIR${RESET}"
    echo ""
    echo -e "  ${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
}

print_menu() {
    echo -e "  ${BOLD}Service:${RESET}"
    echo -e "  ${CYAN}  1)${RESET}  Start bot"
    echo -e "  ${CYAN}  2)${RESET}  Stop bot"
    echo -e "  ${CYAN}  3)${RESET}  Restart bot"
    echo -e "  ${CYAN}  4)${RESET}  View live logs"
    echo ""
    echo -e "  ${BOLD}Configuration:${RESET}"
    echo -e "  ${CYAN}  5)${RESET}  Edit config.env"
    echo -e "  ${CYAN}  6)${RESET}  Setup Google Drive"
    echo -e "  ${CYAN}  7)${RESET}  Disable Google Drive"
    echo ""
    echo -e "  ${BOLD}Maintenance:${RESET}"
    echo -e "  ${CYAN}  8)${RESET}  Clean temp files"
    echo -e "  ${CYAN}  9)${RESET}  Update from GitHub"
    echo -e "  ${CYAN} 10)${RESET}  Reinstall"
    echo -e "  ${RED}  11)${RESET}  Uninstall completely"
    echo ""
    echo -e "  ${CYAN}  0)${RESET}  Exit"
    echo ""
    echo -e "  ${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "  Select option: \c"
}

do_start() {
    systemctl start "$SERVICE_NAME"
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}  [OK] Bot started successfully${RESET}"
    else
        echo -e "${RED}  [ERR] Bot failed to start. Last log lines:${RESET}"
        journalctl -u "$SERVICE_NAME" -n 20 --no-pager
    fi
}

do_stop() {
    systemctl stop "$SERVICE_NAME" \
        && echo -e "${GREEN}  [OK] Bot stopped${RESET}" \
        || echo -e "${RED}  [ERR] Failed to stop${RESET}"
}

do_restart() {
    systemctl restart "$SERVICE_NAME"
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}  [OK] Bot restarted${RESET}"
    else
        echo -e "${RED}  [ERR] Bot failed to restart. Last log lines:${RESET}"
        journalctl -u "$SERVICE_NAME" -n 20 --no-pager
    fi
}

do_logs()    { journalctl -u "$SERVICE_NAME" -f --no-pager; }

do_edit_config() {
    local editor="${EDITOR:-nano}"
    $editor "$INSTALL_DIR/config.env"
    echo -e "${YELLOW}  [!!] Restart the bot to apply changes (option 3)${RESET}"
}

do_setup_gdrive() {
    echo ""
    echo -e "${CYAN}  Get credentials from: console.cloud.google.com${RESET}"
    echo -e "${DIM}  Type: Web application | Redirect URI: http://localhost${RESET}\n"
    echo -e "${YELLOW}  [?]  ${BOLD}Google Client ID:${RESET}"; read -r -p "      " gcid
    echo -e "${YELLOW}  [?]  ${BOLD}Google Client Secret:${RESET}"; read -r -p "      " gcsecret
    if [[ -z "$gcid" || -z "$gcsecret" ]]; then
        echo -e "${RED}  [ERR] Empty values — cancelled${RESET}"; return
    fi
    if grep -q "^GOOGLE_CLIENT_ID=" "$INSTALL_DIR/config.env"; then
        sed -i "s|^GOOGLE_CLIENT_ID=.*|GOOGLE_CLIENT_ID=$gcid|" "$INSTALL_DIR/config.env"
        sed -i "s|^GOOGLE_CLIENT_SECRET=.*|GOOGLE_CLIENT_SECRET=$gcsecret|" "$INSTALL_DIR/config.env"
    else
        echo "GOOGLE_CLIENT_ID=$gcid"     >> "$INSTALL_DIR/config.env"
        echo "GOOGLE_CLIENT_SECRET=$gcsecret" >> "$INSTALL_DIR/config.env"
    fi
    echo -e "${GREEN}  [OK] Google Drive enabled — restart bot to apply (option 3)${RESET}"
}

do_disable_gdrive() {
    sed -i "s|^GOOGLE_CLIENT_ID=.*|GOOGLE_CLIENT_ID=|"         "$INSTALL_DIR/config.env"
    sed -i "s|^GOOGLE_CLIENT_SECRET=.*|GOOGLE_CLIENT_SECRET=|" "$INSTALL_DIR/config.env"
    echo -e "${GREEN}  [OK] Google Drive disabled — restart bot to apply (option 3)${RESET}"
}

do_clean_temp() {
    local count; count=$(find "$INSTALL_DIR/temp" -mindepth 1 2>/dev/null | wc -l)
    rm -rf "${INSTALL_DIR:?}/temp/"*
    echo -e "${GREEN}  [OK] Removed $count temp files/folders${RESET}"
}

do_update() {
    local REPO_RAW="https://raw.githubusercontent.com/rezarg-dev/Mega-leecher/main"
    local FILES_TO_UPDATE=("bot.py" "config.py")
    local PRESERVE=("config.env" "users_db.json" "github_db.json" "drive_db.json" "cookies.txt" "temp")

    echo -e "${CYAN}  --> Checking latest commit on GitHub...${RESET}"

    # Get latest commit SHA
    local LATEST_SHA
    LATEST_SHA=$(curl -sf "https://api.github.com/repos/rezarg-dev/Mega-leecher/commits/main" \
        | grep '"sha"' | head -1 | cut -d'"' -f4 | cut -c1-7)

    if [[ -z "$LATEST_SHA" ]]; then
        echo -e "${RED}  [ERR] Could not reach GitHub. Check your internet connection.${RESET}"
        return
    fi

    # Check current version
    local CURRENT_SHA=""
    [[ -f "$INSTALL_DIR/.version" ]] && CURRENT_SHA=$(cat "$INSTALL_DIR/.version")

    if [[ "$CURRENT_SHA" == "$LATEST_SHA" ]]; then
        echo -e "${GREEN}  [OK] Already up to date (commit: $LATEST_SHA)${RESET}"
        return
    fi

    echo -e "${CYAN}  --> Updating to commit: ${BOLD}$LATEST_SHA${RESET}"
    echo -e "${DIM}  Preserving: config.env, databases, cookies, temp files${RESET}\n"

    # Stop bot
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true

    # Download updated files only
    local failed=0
    for f in "${FILES_TO_UPDATE[@]}"; do
        echo -e "${CYAN}  --> Downloading $f...${RESET}"
        if curl -sf "$REPO_RAW/$f" -o "$INSTALL_DIR/$f.tmp"; then
            mv "$INSTALL_DIR/$f.tmp" "$INSTALL_DIR/$f"
            echo -e "${GREEN}  [OK] $f updated${RESET}"
        else
            rm -f "$INSTALL_DIR/$f.tmp"
            echo -e "${RED}  [ERR] Failed to download $f${RESET}"
            failed=1
        fi
    done

    if [[ $failed -eq 1 ]]; then
        echo -e "${RED}  [ERR] Update incomplete. Starting bot with previous version.${RESET}"
        systemctl start "$SERVICE_NAME" 2>/dev/null || true
        return
    fi

    # Validate syntax before restarting
    if ! "$INSTALL_DIR/venv/bin/python" -m py_compile "$INSTALL_DIR/bot.py" 2>/dev/null; then
        echo -e "${RED}  [ERR] bot.py syntax check failed. Rolling back is not possible.${RESET}"
        echo -e "${YELLOW}  [!!] Bot will not start until the issue is resolved.${RESET}"
        return
    fi

    # Save current version
    echo "$LATEST_SHA" > "$INSTALL_DIR/.version"

    # Restart bot
    systemctl start "$SERVICE_NAME"
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}  [OK] Bot updated and restarted successfully!${RESET}"
        echo -e "${DIM}  Version: $LATEST_SHA${RESET}"
    else
        echo -e "${RED}  [ERR] Bot failed to start after update. Check logs (option 4).${RESET}"
    fi
}

do_reinstall() {
    echo -e "${YELLOW}  [!!] This will reinstall the bot. config.env will be preserved.${RESET}"
    echo -e "  Continue? [y/N] \c"; read -r reply
    [[ ! "$reply" =~ ^[Yy]$ ]] && return
    local setup_script
    setup_script="$(find / -name 'setup.sh' -path '*/Mega-leecher/*' 2>/dev/null | head -1)"
    if [[ -z "$setup_script" ]]; then
        echo -e "${YELLOW}  [!!] setup.sh not found. Clone the repo and run setup.sh manually.${RESET}"
        return
    fi
    bash "$setup_script"
}

do_uninstall() {
    echo ""
    echo -e "${RED}${BOLD}  WARNING: All bot files and settings will be deleted!${RESET}"
    echo -e "  Type ${BOLD}UNINSTALL${RESET} to confirm: \c"
    read -r confirm_text
    [[ "$confirm_text" != "UNINSTALL" ]] && echo -e "${CYAN}  Cancelled${RESET}" && return
    systemctl stop    "$SERVICE_NAME" 2>/dev/null || true
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    systemctl daemon-reload
    rm -rf "$INSTALL_DIR"
    rm -f "/usr/local/bin/mega-leecher"
    echo -e "${GREEN}  [OK] Mega Leecher has been completely removed${RESET}"
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
        0)  echo -e "${DIM}  Exiting...${RESET}\n"; exit 0 ;;
        *)  echo -e "${RED}  [ERR] Invalid option${RESET}" ;;
    esac
    echo ""
    echo -e "  ${DIM}Press Enter to return to menu...${RESET}"
    read -r
done
CLI_EOF

chmod +x "$CLI_PATH"
success "mega-leecher command installed at $CLI_PATH"

# =============================================================
#   STEP 8 — Test run & start service
# =============================================================
section "Starting Mega Leecher"

info "Testing bot.py syntax..."
if "$INSTALL_DIR/venv/bin/python" -m py_compile "$INSTALL_DIR/bot.py" 2>/dev/null; then
    success "bot.py syntax OK"
else
    error "bot.py has syntax errors. Check the file and reinstall."
fi

info "Testing config.py import..."
cd "$INSTALL_DIR"
if "$INSTALL_DIR/venv/bin/python" -c "import config" 2>/dev/null; then
    success "config.py loaded OK"
else
    echo -e "${RED}  [ERR] config.py failed to load. Check config.env values:${RESET}"
    cd "$INSTALL_DIR" && "$INSTALL_DIR/venv/bin/python" -c "import config" 2>&1 || true
    error "Fix config.env and re-run setup.sh"
fi

info "Starting service..."
systemctl start "$SERVICE_NAME"
sleep 3

if systemctl is-active --quiet "$SERVICE_NAME"; then
    success "Bot is running!"
else
    warn "Bot failed to start. Last 30 log lines:"
    echo ""
    journalctl -u "$SERVICE_NAME" -n 30 --no-pager
    echo ""
    warn "Fix the issue and use 'mega-leecher' to start the bot."
fi

# =============================================================
#   Done
# =============================================================
echo ""
echo -e "${BOLD}${GREEN}  +------------------------------------------+${RESET}"
echo -e "${BOLD}${GREEN}  |   Mega Leecher installation complete!    |${RESET}"
echo -e "${BOLD}${GREEN}  +------------------------------------------+${RESET}"
echo ""
echo -e "  ${CYAN}Manage the bot anytime with:${RESET}"
echo -e "  ${BOLD}    mega-leecher${RESET}"
echo ""
