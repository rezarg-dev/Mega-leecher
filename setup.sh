#!/usr/bin/env bash
# ============================================================
#   Mega Leecher — install / upgrade script
#   https://github.com/rezarg-dev/Mega-leecher
#
#   bash setup.sh            full install or in-place upgrade
#   bash setup.sh --update   code + Python packages only (used by the CLI)
#
#   Running it again never touches config.env, the user databases,
#   cookies.txt or the Telegram session.
# ============================================================
set -euo pipefail

INSTALL_DIR="/opt/mega-leecher"
SERVICE_NAME="mega-leecher"
POT_SERVICE="bgutil-pot-provider"
POT_REPO="https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git"
NODE_MAJOR=22
CLI_PATH="/usr/local/bin/mega-leecher"
LOG_FILE="/tmp/mega-leecher-setup.log"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODE_FILES=(leecher bot.py broadcast.py requirements.txt)

# The token server must be the same version as the yt-dlp plugin pinned in
# requirements.txt; the plugin refuses to talk to any other major version.
POT_VERSION="$(sed -n 's/^bgutil-ytdlp-pot-provider==//p' "$SCRIPT_DIR/requirements.txt" 2>/dev/null | tr -d '[:space:]')"

MODE="install"
[[ "${1:-}" == "--update" ]] && MODE="update"

# ── Output helpers ───────────────────────────────────────────
RED='\033[0;31m';  GREEN='\033[0;32m';  YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m';   MAGENTA='\033[0;35m'
BOLD='\033[1m';    DIM='\033[2m';       RESET='\033[0m'

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

info()    { echo -e "${CYAN}  -->  $1${RESET}"; }
success() { echo -e "${GREEN}  [OK] $1${RESET}"; }
warn()    { echo -e "${YELLOW}  [!!] $1${RESET}"; }
error()   { echo -e "${RED}  [ERR] $1${RESET}"; exit 1; }
section() { echo -e "\n${BOLD}${BLUE}---  $1  ---${RESET}\n"; }
ask()     { echo -e "${YELLOW}  [?]  ${BOLD}$1${RESET}"; }

confirm() {
    local prompt="$1" default="${2:-y}" hint reply
    [[ $default == "y" ]] && hint="[Y/n]" || hint="[y/N]"
    ask "$prompt $hint"
    read -r -p "      " reply
    reply="${reply:-$default}"
    [[ "$reply" =~ ^[Yy]$ ]]
}

read_val() {
    ask "$1"
    read -r -p "      " "$2"
}

# Run a noisy command quietly; show its output only if it fails.
quiet() {
    if ! "$@" >> "$LOG_FILE" 2>&1; then
        echo -e "${RED}  [ERR] Command failed: $*${RESET}"
        echo -e "${DIM}  Last lines of $LOG_FILE:${RESET}"
        tail -n 25 "$LOG_FILE" | sed 's/^/      /'
        exit 1
    fi
}

# ── Steps ────────────────────────────────────────────────────

preflight() {
    section "Pre-flight Checks"
    [[ $EUID -eq 0 ]] || error "This script must be run as root.\n        Run: sudo bash setup.sh"
    success "Running as root"
    command -v apt-get &>/dev/null || error "This script only supports Debian/Ubuntu systems."
    success "Compatible OS detected"
    check_sources
    success "Project files found"
}

check_sources() {
    local f
    for f in "${CODE_FILES[@]}" mega-leecher.sh; do
        [[ -e "$SCRIPT_DIR/$f" ]] || error "$f not found! Run setup.sh from the project directory."
    done
}

install_system_packages() {
    section "Installing System Dependencies"
    export DEBIAN_FRONTEND=noninteractive

    info "Updating package lists..."
    quiet apt-get update

    info "Installing required packages..."
    quiet apt-get install -y \
        python3 python3-pip python3-venv python3-libtorrent \
        git curl ffmpeg rar unrar unzip zip p7zip-full
    local tool
    for tool in python3 git curl ffmpeg ffprobe rar zip; do
        command -v "$tool" &>/dev/null || error "'$tool' is still missing after installation. See $LOG_FILE"
    done
    success "System packages installed"

    info "Checking Node.js ($NODE_MAJOR or newer)..."
    if [[ "$(node_major)" -lt "$NODE_MAJOR" ]]; then
        info "Installing Node.js $NODE_MAJOR.x..."
        curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" -o /tmp/nodesource_setup.sh
        quiet bash /tmp/nodesource_setup.sh
        quiet apt-get install -y nodejs
        rm -f /tmp/nodesource_setup.sh
    fi
    success "Node.js $(node --version) ready"

    info "Checking Deno (required for YouTube downloads)..."
    if ! command -v deno &>/dev/null && [[ ! -x "$HOME/.deno/bin/deno" ]]; then
        info "Installing Deno..."
        # No terminal on stdin, so the installer does not stop to ask questions.
        curl -fsSL https://deno.land/install.sh 2>> "$LOG_FILE" | sh >> "$LOG_FILE" 2>&1 || true
    fi
    if command -v deno &>/dev/null || [[ -x "$HOME/.deno/bin/deno" ]]; then
        success "Deno ready"
    else
        warn "Deno could not be installed — YouTube downloads may fail until it is."
    fi
}

node_major() {
    local version
    version=$(node --version 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/' || true)
    echo "${version:-0}"
}

# YouTube hides sizes and 4K formats from clients that cannot present a PO token.
install_pot_provider() {
    local dir="$INSTALL_DIR/pot-provider" built
    [[ -n "$POT_VERSION" ]] || { warn "No PO Token provider version pinned in requirements.txt"; return 1; }
    built=$(git -C "$dir" describe --tags --exact-match 2>/dev/null || true)
    if [[ "$built" == "$POT_VERSION" && -f "$dir/server/build/main.js" ]]; then
        success "PO Token provider $POT_VERSION already built"
        return 0
    fi
    if [[ "$(node_major)" -lt "$NODE_MAJOR" ]]; then
        warn "PO Token provider $POT_VERSION needs Node.js $NODE_MAJOR+. Run a full install: bash setup.sh"
        return 1
    fi
    info "Building the YouTube PO Token provider ($POT_VERSION)..."
    # Build next to the old copy and swap only on success.
    rm -rf "$dir.new"
    if git clone --quiet --single-branch --branch "$POT_VERSION" "$POT_REPO" "$dir.new" >> "$LOG_FILE" 2>&1 \
        && (cd "$dir.new/server" && npm ci --silent && npx tsc) >> "$LOG_FILE" 2>&1; then
        rm -rf "$dir"
        mv "$dir.new" "$dir"
        success "PO Token provider built"
        return 0
    fi
    rm -rf "$dir.new"
    warn "PO Token provider could not be built — quality sizes and 4K may be missing. See $LOG_FILE"
    return 1
}

# Copy the code into place. Data files in INSTALL_DIR are never touched.
install_code() {
    local f
    mkdir -p "$INSTALL_DIR/temp"
    if [[ -d "$INSTALL_DIR/leecher" || -f "$INSTALL_DIR/bot.py" ]]; then
        rm -rf "$INSTALL_DIR/.backup"
        mkdir -p "$INSTALL_DIR/.backup"
        for f in "${CODE_FILES[@]}" config.py lang.py .version; do
            [[ -e "$INSTALL_DIR/$f" ]] && cp -a "$INSTALL_DIR/$f" "$INSTALL_DIR/.backup/"
        done
    fi
    if [[ "$SCRIPT_DIR" != "$INSTALL_DIR" ]]; then
        for f in "${CODE_FILES[@]}"; do
            rm -rf "${INSTALL_DIR:?}/$f"
            cp -a "$SCRIPT_DIR/$f" "$INSTALL_DIR/$f"
        done
    fi
    # Left over from the single-file versions of the bot.
    rm -f "$INSTALL_DIR/config.py" "$INSTALL_DIR/lang.py"
    find "$INSTALL_DIR/leecher" -name '__pycache__' -type d -prune -exec rm -rf {} +
    git -C "$SCRIPT_DIR" rev-parse --short HEAD > "$INSTALL_DIR/.version" 2>/dev/null \
        || rm -f "$INSTALL_DIR/.version"
}

restore_backup() {
    local f
    [[ -d "$INSTALL_DIR/.backup" ]] || return 1
    for f in "${CODE_FILES[@]}"; do
        rm -rf "${INSTALL_DIR:?}/$f"
    done
    cp -a "$INSTALL_DIR/.backup/." "$INSTALL_DIR/"
}

install_python_packages() {
    local py="$INSTALL_DIR/venv/bin/python" want have=""
    want=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
    if [[ -f "$INSTALL_DIR/venv/pyvenv.cfg" ]]; then
        have=$(grep -E '^version' "$INSTALL_DIR/venv/pyvenv.cfg" | grep -oE '[0-9]+\.[0-9]+' | head -n 1 || true)
    fi
    # Rebuild on a full install, and whenever the venv belongs to another
    # Python (it stops working after a distribution upgrade).
    if [[ "$MODE" == "install" || "$have" != "$want" || ! -x "$py" ]]; then
        info "Creating Python virtual environment..."
        rm -rf "$INSTALL_DIR/venv"
        # System site packages are needed for python3-libtorrent.
        quiet python3 -m venv "$INSTALL_DIR/venv" --system-site-packages
    fi
    info "Installing Python packages (this may take a few minutes)..."
    quiet "$py" -m pip install --upgrade pip
    quiet "$py" -m pip install --upgrade -r "$INSTALL_DIR/requirements.txt"

    local pkg
    for pkg in pyrogram tgcrypto aiohttp httpx yt_dlp libtorrent; do
        "$py" -c "import $pkg" >> "$LOG_FILE" 2>&1 \
            || error "Python package '$pkg' cannot be imported. See $LOG_FILE"
    done
    success "Python packages installed and verified"
}

# True when the installed code loads with the current configuration.
code_loads() {
    (cd "$INSTALL_DIR" && ./venv/bin/python -m compileall -q leecher bot.py broadcast.py \
        && ./venv/bin/python -c "import leecher.main") >> "$LOG_FILE" 2>&1
}

write_config() {
    if [[ -f "$INSTALL_DIR/config.env" ]]; then
        warn "Existing config.env found — keeping it."
        warn "Edit it with: nano $INSTALL_DIR/config.env"
        return
    fi

    section "Bot Configuration"
    echo -e "${DIM}  Get API_ID and API_HASH from: my.telegram.org/apps${RESET}\n"
    local api_id api_hash bot_token admin_id purchase gcid="" gcsecret=""
    read_val "API_ID (number):"                              api_id
    read_val "API_HASH:"                                     api_hash
    read_val "BOT_TOKEN (from @BotFather):"                  bot_token
    read_val "ADMIN_ID (your numeric Telegram user ID):"     admin_id
    read_val "PURCHASE_USERNAME (e.g. @yourusername):"       purchase

    [[ "$api_id" =~ ^[0-9]+$ ]]   || error "API_ID must be a number."
    [[ "$admin_id" =~ ^[0-9]+$ ]] || error "ADMIN_ID must be a number."
    [[ -n "$api_hash" && -n "$bot_token" && -n "$purchase" ]] || error "All values are required."
    success "Configuration values accepted"

    section "Google Drive Integration (Optional)"
    echo -e "${DIM}  Allows users to upload files to Google Drive and get download links.${RESET}\n"
    if confirm "Do you want to enable Google Drive support?" "y"; then
        echo ""
        echo -e "${DIM}  How to get credentials:${RESET}"
        echo -e "${DIM}  1. Go to console.cloud.google.com${RESET}"
        echo -e "${DIM}  2. Create a project and enable Google Drive API${RESET}"
        echo -e "${DIM}  3. Create OAuth 2.0 Client ID (type: Web application)${RESET}"
        echo -e "${DIM}  4. Add redirect URI: http://localhost${RESET}\n"
        read_val "Google Client ID:"     gcid
        read_val "Google Client Secret:" gcsecret
        if [[ -n "$gcid" && -n "$gcsecret" ]]; then
            success "Google Drive credentials saved"
        else
            warn "Values empty — Google Drive disabled. Enable later with: mega-leecher"
            gcid=""; gcsecret=""
        fi
    else
        info "Google Drive skipped. You can enable it later with: mega-leecher"
    fi

    cat > "$INSTALL_DIR/config.env" << CONF
# Mega Leecher Configuration
# Generated: $(date)

API_ID=${api_id}
API_HASH=${api_hash}
BOT_TOKEN=${bot_token}
ADMIN_ID=${admin_id}
PURCHASE_USERNAME=${purchase}

GOOGLE_CLIENT_ID=${gcid}
GOOGLE_CLIENT_SECRET=${gcsecret}
CONF
    chmod 600 "$INSTALL_DIR/config.env"
    success "config.env saved (permissions: 600)"
}

install_services() {
    section "Installing Systemd Services"
    local with_pot="$1"

    if [[ "$with_pot" == "yes" ]]; then
        cat > "/etc/systemd/system/${POT_SERVICE}.service" << UNIT
[Unit]
Description=BgUtils PO Token Provider for yt-dlp
Documentation=https://github.com/Brainicism/bgutil-ytdlp-pot-provider
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}/pot-provider/server
ExecStart=$(command -v node) build/main.js
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT
        systemctl daemon-reload
        systemctl enable "$POT_SERVICE" > /dev/null 2>&1
        if systemctl restart "$POT_SERVICE"; then
            success "PO Token provider service running (port 4416)"
        else
            warn "PO Token provider service did not start. Check: journalctl -u $POT_SERVICE"
        fi
    fi

    # Wants, not Requires: the bot is still useful when the token provider is down.
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << UNIT
[Unit]
Description=Mega Leecher Telegram Bot
Documentation=https://github.com/rezarg-dev/Mega-leecher
After=network-online.target ${POT_SERVICE}.service
Wants=network-online.target ${POT_SERVICE}.service

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
UNIT
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME" > /dev/null 2>&1
    success "Bot service installed and enabled"
}

install_cli() {
    install -m 755 "$SCRIPT_DIR/mega-leecher.sh" "$CLI_PATH"
    success "mega-leecher command installed at $CLI_PATH"
}

start_bot() {
    info "Starting service..."
    systemctl restart "$SERVICE_NAME"
    sleep 3
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        success "Bot is running!"
    else
        warn "Bot failed to start. Last 30 log lines:"
        echo ""
        journalctl -u "$SERVICE_NAME" -n 30 --no-pager || true
        echo ""
        warn "Fix the issue and use 'mega-leecher' to start the bot."
    fi
}

# ── Update mode: code and Python packages only ───────────────
run_update() {
    [[ $EUID -eq 0 ]] || error "This script must be run as root."
    [[ -f "$INSTALL_DIR/config.env" ]] || error "No installation found in $INSTALL_DIR. Run: bash setup.sh"
    check_sources
    : > "$LOG_FILE"

    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    install_code
    install_python_packages
    if ! code_loads; then
        warn "The new version does not load — restoring the previous one."
        tail -n 15 "$LOG_FILE" | sed 's/^/      /'
        restore_backup || error "No backup to restore. See $LOG_FILE"
        systemctl start "$SERVICE_NAME" 2>/dev/null || true
        error "Update aborted; the previous version is running again."
    fi
    local with_pot="no"
    install_pot_provider && with_pot="yes"
    install_services "$with_pot"
    install_cli
    start_bot
}

# ── Full install ─────────────────────────────────────────────
run_install() {
    clear 2>/dev/null || true
    print_logo
    : > "$LOG_FILE"
    preflight
    install_system_packages

    section "Installing Mega Leecher"
    if [[ -d "$INSTALL_DIR" ]]; then
        warn "$INSTALL_DIR already exists — upgrading in place (settings and data are kept)."
        systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    fi
    install_code
    success "Bot files copied to $INSTALL_DIR"
    install_python_packages

    local with_pot="no"
    install_pot_provider && with_pot="yes"

    write_config
    install_services "$with_pot"

    section "Installing mega-leecher CLI"
    install_cli

    section "Starting Mega Leecher"
    if code_loads; then
        success "Code and configuration load correctly"
    else
        tail -n 15 "$LOG_FILE" | sed 's/^/      /'
        error "The bot does not load. Check $INSTALL_DIR/config.env and run setup.sh again."
    fi
    start_bot

    echo ""
    echo -e "${BOLD}${GREEN}  +------------------------------------------+${RESET}"
    echo -e "${BOLD}${GREEN}  |   Mega Leecher installation complete!    |${RESET}"
    echo -e "${BOLD}${GREEN}  +------------------------------------------+${RESET}"
    echo ""
    echo -e "  ${CYAN}Manage the bot anytime with:${RESET}"
    echo -e "  ${BOLD}    mega-leecher${RESET}"
    echo ""
}

if [[ "$MODE" == "update" ]]; then
    run_update
else
    run_install
fi
