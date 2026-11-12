#!/usr/bin/env bash
# Mega Leecher — management CLI (installed as /usr/local/bin/mega-leecher)

INSTALL_DIR="/opt/mega-leecher"
SERVICE_NAME="mega-leecher"
POT_SERVICE="bgutil-pot-provider"
REPO_URL="https://github.com/rezarg-dev/Mega-leecher.git"
CONFIG="$INSTALL_DIR/config.env"

RED='\033[0;31m';  GREEN='\033[0;32m';  YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m';   MAGENTA='\033[0;35m'
BOLD='\033[1m';    DIM='\033[2m';       RESET='\033[0m'

ok()   { echo -e "${GREEN}  [OK] $1${RESET}"; }
note() { echo -e "${YELLOW}  [!!] $1${RESET}"; }
fail() { echo -e "${RED}  [ERR] $1${RESET}"; }
step() { echo -e "${CYAN}  --> $1${RESET}"; }

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
    if [[ ! -f "$CONFIG" ]]; then
        echo -e "${DIM}  Unknown${RESET}"
    elif [[ -n "$(grep '^GOOGLE_CLIENT_ID=' "$CONFIG" | cut -d= -f2-)" ]]; then
        echo -e "${GREEN}  Enabled${RESET}"
    else
        echo -e "${DIM}  Disabled${RESET}"
    fi
}

print_status_bar() {
    local version="unknown"
    [[ -f "$INSTALL_DIR/.version" ]] && version=$(cat "$INSTALL_DIR/.version")
    echo -e "  ${DIM}Bot status:${RESET}     $(get_status)"
    echo -e "  ${DIM}Google Drive:${RESET}   $(get_gdrive_status)"
    echo -e "  ${DIM}Version:${RESET}        ${DIM}  $version${RESET}"
    echo -e "  ${DIM}Install path:${RESET}   ${DIM}  $INSTALL_DIR${RESET}"
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

report_running() {
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        ok "$1"
    else
        fail "Bot is not running. Last log lines:"
        journalctl -u "$SERVICE_NAME" -n 20 --no-pager
    fi
}

do_start()   { systemctl start "$SERVICE_NAME";   report_running "Bot started successfully"; }
do_restart() { systemctl restart "$SERVICE_NAME"; report_running "Bot restarted"; }

do_stop() {
    if systemctl stop "$SERVICE_NAME"; then ok "Bot stopped"; else fail "Failed to stop"; fi
}

do_logs() {
    echo -e "${DIM}  Press Ctrl+C to return to the menu${RESET}\n"
    # Ctrl+C should end journalctl, not this menu.
    trap : INT
    journalctl -u "$SERVICE_NAME" -f --no-pager
    trap - INT
}

do_edit_config() {
    "${EDITOR:-nano}" "$CONFIG"
    note "Restart the bot to apply changes (option 3)"
}

# Replace (or add) one KEY=VALUE line in config.env, whatever characters the value holds.
set_config() {
    local key="$1" value="$2" tmp
    tmp=$(mktemp)
    grep -v "^${key}=" "$CONFIG" > "$tmp" || true
    echo "${key}=${value}" >> "$tmp"
    cat "$tmp" > "$CONFIG"
    rm -f "$tmp"
}

do_setup_gdrive() {
    local gcid gcsecret
    echo ""
    echo -e "${CYAN}  Get credentials from: console.cloud.google.com${RESET}"
    echo -e "${DIM}  Type: Web application | Redirect URI: http://localhost${RESET}\n"
    echo -e "${YELLOW}  [?]  ${BOLD}Google Client ID:${RESET}";     read -r -p "      " gcid
    echo -e "${YELLOW}  [?]  ${BOLD}Google Client Secret:${RESET}"; read -r -p "      " gcsecret
    if [[ -z "$gcid" || -z "$gcsecret" ]]; then
        fail "Empty values — cancelled"
        return
    fi
    set_config GOOGLE_CLIENT_ID "$gcid"
    set_config GOOGLE_CLIENT_SECRET "$gcsecret"
    ok "Google Drive enabled — restart bot to apply (option 3)"
}

do_disable_gdrive() {
    set_config GOOGLE_CLIENT_ID ""
    set_config GOOGLE_CLIENT_SECRET ""
    ok "Google Drive disabled — restart bot to apply (option 3)"
}

do_clean_temp() {
    local count
    count=$(find "$INSTALL_DIR/temp" -mindepth 1 -maxdepth 1 2>/dev/null | wc -l)
    find "$INSTALL_DIR/temp" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null
    ok "Removed $count temp files/folders"
}

# Clone the latest code and hand over to its setup.sh.
run_setup_from_github() {
    local tmp status
    tmp=$(mktemp -d)
    step "Downloading the latest version..."
    if ! git clone --quiet --depth=1 "$REPO_URL" "$tmp/Mega-leecher"; then
        fail "Could not reach GitHub. Check your internet connection."
        rm -rf "$tmp"
        return 1
    fi
    bash "$tmp/Mega-leecher/setup.sh" "$@"
    status=$?
    rm -rf "$tmp"
    return $status
}

do_update() {
    local latest current=""
    step "Checking latest commit on GitHub..."
    latest=$(git ls-remote "$REPO_URL" HEAD 2>/dev/null | cut -f1)
    if [[ -z "$latest" ]]; then
        fail "Could not reach GitHub. Check your internet connection."
        return
    fi
    [[ -f "$INSTALL_DIR/.version" ]] && current=$(cat "$INSTALL_DIR/.version")
    if [[ -n "$current" && "$latest" == "$current"* ]]; then
        ok "Already up to date (commit: $current)"
        return
    fi
    step "Updating to commit: ${BOLD}${latest:0:7}"
    echo -e "${DIM}  Preserving: config.env, databases, cookies, session${RESET}\n"
    run_setup_from_github --update
}

do_reinstall() {
    local reply
    note "This reinstalls the bot and its dependencies. Settings and user data are preserved."
    echo -e "  Continue? [y/N] \c"; read -r reply
    [[ "$reply" =~ ^[Yy]$ ]] || return
    run_setup_from_github
}

do_uninstall() {
    local confirm_text backup
    echo ""
    echo -e "${RED}${BOLD}  WARNING: All bot files and settings will be deleted!${RESET}"
    echo -e "  Type ${BOLD}UNINSTALL${RESET} to confirm: \c"
    read -r confirm_text
    if [[ "$confirm_text" != "UNINSTALL" ]]; then
        echo -e "${CYAN}  Cancelled${RESET}"
        return
    fi
    systemctl stop    "$SERVICE_NAME" "$POT_SERVICE" 2>/dev/null || true
    systemctl disable "$SERVICE_NAME" "$POT_SERVICE" 2>/dev/null || true

    # One last copy of the things that cannot be recreated.
    backup="/root/mega-leecher-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    if (cd "$INSTALL_DIR" 2>/dev/null && tar -czf "$backup" --ignore-failed-read \
            config.env users_db.json github_db.json drive_db.json cookies.txt 2>/dev/null); then
        ok "Settings and user data saved to $backup"
    fi

    rm -f "/etc/systemd/system/${SERVICE_NAME}.service" "/etc/systemd/system/${POT_SERVICE}.service"
    systemctl daemon-reload
    rm -rf "$INSTALL_DIR"
    rm -f "/usr/local/bin/mega-leecher"
    ok "Mega Leecher has been completely removed"
    exit 0
}

if [[ $EUID -ne 0 ]]; then
    fail "Run as root: sudo mega-leecher"
    exit 1
fi

while true; do
    print_logo
    print_status_bar
    print_menu
    read -r choice || exit 0
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
        *)  fail "Invalid option" ;;
    esac
    echo ""
    echo -e "  ${DIM}Press Enter to return to menu...${RESET}"
    read -r || exit 0
done
