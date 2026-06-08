<div align="center">

```
███╗   ███╗███████╗ ██████╗  █████╗     ██╗     ███████╗███████╗ ██████╗██╗  ██╗███████╗██████╗
████╗ ████║██╔════╝██╔════╝ ██╔══██╗    ██║     ██╔════╝██╔════╝██╔════╝██║  ██║██╔════╝██╔══██╗
██╔████╔██║█████╗  ██║  ███╗███████║    ██║     █████╗  █████╗  ██║     ███████║█████╗  ██████╔╝
██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║    ██║     ██╔══╝  ██╔══╝  ██║     ██╔══██║██╔══╝  ██╔══██╗
██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║    ███████╗███████╗███████╗╚██████╗██║  ██║███████╗██║  ██║
╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝    ╚══════╝╚══════╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
```

**A powerful Telegram bot for downloading, processing and managing files**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-2.x-blue?style=flat-square)](https://pyrogram.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux-orange?style=flat-square&logo=linux)](https://linux.org)

</div>

---

## Support the Project

If Mega Leecher has been useful to you, consider supporting its development:

| Network | Address |
|---------|---------|
| **USDT (BEP20)** | `0x8F540B43cC82d765bfe33c7B3da042B11708eCD1` |
| **USDT (TRC20)** | `TGHxjiBeBkdJ7v2Vc4gqE9FYp7Nj1sgDkJ` |
| **Litecoin (LTC)** | `ltc1q28g9qzpjs22x2uvds5tqp60w250fvjf2te234l` |

Every contribution, no matter the size, helps keep this project alive. ❤️

---

## ✨ Features

### 📦 File Processing
- **Split** files into 19MB, 40MB or 900MB parts
- **Compress** into RAR archives with optional password protection
- **Send raw** files without any modification
- **Multi-file archives** — combine multiple files into one RAR

### ⬇️ Downloading
- **Direct links** — any HTTP/HTTPS download link up to 2GB
- **Torrents** — magnet links or `.torrent` files
- **YouTube** — download videos up to 1080p or audio-only (MP3)

### ☁️ Cloud Storage
- **GitHub** — upload files and get direct download links (up to 15GB free with your own token)
- **Google Drive** — upload files and get shareable links (up to 15GB free with your Google account)

### 🔐 Access Control
- Subscription-based access with expiry dates
- Separate YouTube subscription tier
- Daily upload quotas per user
- Admin panel for user management

---

## 📋 Requirements

| Requirement | Version |
|-------------|---------|
| OS | Ubuntu 20.04+ / Debian 11+ |
| Python | 3.9+ |
| Node.js | 20.x |
| RAM | 1GB minimum (2GB recommended) |
| Root access | Required |

---

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/rezarg-dev/Mega-leecher.git
cd Mega-leecher

# Run the installer
bash setup.sh
```

The installer will automatically:
1. Install all system dependencies (apt packages, Node.js, Python packages)
2. Ask for your Telegram bot credentials
3. Optionally configure Google Drive support
4. Set up a systemd service that starts automatically on boot
5. Install the `mega-leecher` management command

---

## ⚙️ Configuration

After installation your config is stored at `/opt/mega-leecher/config.env`.

Copy the example file to get started:
```bash
cp config.env.example config.env
nano config.env
```

| Variable | Description |
|----------|-------------|
| `API_ID` | Telegram API ID — get from [my.telegram.org](https://my.telegram.org/apps) |
| `API_HASH` | Telegram API Hash — get from [my.telegram.org](https://my.telegram.org/apps) |
| `BOT_TOKEN` | Bot token — get from [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID` | Your Telegram numeric user ID |
| `PURCHASE_USERNAME` | Telegram username shown for subscription purchases |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID (optional) |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret (optional) |
| `INSTALL_DIR` | Installation directory (default: `/opt/mega-leecher`) |

> ⚠️ `config.env` is listed in `.gitignore` — never commit it to version control.

---

## 🔧 Management

Use the `mega-leecher` command from anywhere on your server:

```bash
mega-leecher
```

This opens an interactive management panel with a colored menu:

| Option | Action |
|--------|--------|
| 1 | Start bot |
| 2 | Stop bot |
| 3 | Restart bot |
| 4 | View live logs |
| 5 | Edit config.env |
| 6 | Setup Google Drive |
| 7 | Disable Google Drive |
| 8 | Clean temp files |
| 9 | Update from GitHub |
| 10 | Reinstall |
| 11 | Uninstall completely |

---

## 🔗 GitHub Cloud Storage Setup

GitHub is a free online service that provides cloud storage for your files.

### Step 1 — Create an Account
1. Open your browser and go to [github.com](https://github.com)
2. Click **Sign up** and enter your email, password and a username
3. Complete the email verification steps

> If you already have an account, just sign in.

### Step 2 — Go to Settings
1. Click your **profile picture** (top-right corner)
2. Select **Settings** from the dropdown menu

### Step 3 — Go to Developer Settings
1. In Settings, scroll down to the bottom of the left sidebar
2. Click **Developer settings** (last option)

### Step 4 — Create a Token
1. Click **Personal access tokens**
2. Select **Fine-grained tokens**
3. Click the green **Generate new token** button

### Step 5 — Configure the Token
| Field | Value |
|-------|-------|
| **Token name** | Any name, e.g. `mega-leecher` |
| **Expiration** | No expiration |
| **Repository access** | All repositories |

### Step 6 — Set Permissions
Scroll to **Repository permissions** and set the following to **Read and write**:

- ✅ **Actions**
- ✅ **Administration**
- ✅ **Contents**
- ✅ **Workflows**

> If you don't see all permissions, click **Show more**.

### Step 7 — Generate and Copy
1. Scroll back to the top and click the green **Generate token** button
2. **Copy the token immediately** — it is shown only once!
3. Send the token to the bot via the **☁️ Connect GitHub** menu

The bot will automatically create 3 repositories giving you **15GB total** free storage.

---

## 📂 Google Drive Setup

### Step 1 — Get OAuth Credentials
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project
3. Enable the **Google Drive API**
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Add Authorized redirect URI: `http://localhost`
7. Copy your **Client ID** and **Client Secret**

### Step 2 — Add to Config
Run `mega-leecher` and choose option **6 (Setup Google Drive)**, or edit `config.env` directly:
```env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
```
Then restart the bot (option 3).

### Step 3 — Connect in Telegram
Send **📂 اتصال به گوگل درایو** to the bot and follow the step-by-step guide inside.

---

## 🎬 YouTube Cookies (Optional)

To download age-restricted or member-only videos, you need to provide a `cookies.txt` file from a logged-in YouTube session.

### Step 1 — Browse YouTube first
Open Firefox, log in to your Google account, and browse YouTube for a few minutes. This ensures fresh, valid session cookies are stored in your browser.

### Step 2 — Install the extension
Install the **"Get cookies.txt LOCALLY"** extension from the Firefox Add-ons store.

> ⚠️ Make sure to use Firefox, not Chrome. The extension works more reliably with YouTube on Firefox.

### Step 3 — Export cookies
1. Go to [youtube.com](https://youtube.com) while logged in
2. Click the extension icon in the toolbar
3. Set **Export Format** to `Netscape`
4. Click **Export As** and save the file
5. Rename the saved file to `cookies.txt`

### Step 4 — Place the file on your server
```bash
cp cookies.txt /opt/mega-leecher/cookies.txt
systemctl restart mega-leecher
```

---

## 📁 Project Structure

```
Mega-leecher/
├── bot.py                  # Main bot — handlers, processing, cloud upload
├── config.py               # Configuration loader (reads config.env)
├── config.env.example      # Configuration template
├── setup.sh                # Automated install & management script
├── mega-leecher.service    # Systemd service unit file
├── .gitignore              # Git ignore rules
└── README.md
```

---

## 🛠️ Manual Installation (Advanced)

If you prefer to install manually without the setup script:

```bash
# 1. Install system packages
apt update && apt install -y python3 python3-pip python3-venv python3-libtorrent \
    git ffmpeg rar unrar unzip zip p7zip-full

# 2. Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# 3. Create directory and venv
mkdir -p /opt/mega-leecher
cd /opt/mega-leecher
python3 -m venv venv --system-site-packages

# 4. Install Python dependencies
./venv/bin/pip install pyrogram tgcrypto yt-dlp aiohttp httpx

# 5. Configure
cp config.env.example config.env
nano config.env

# 6. Run
./venv/bin/python bot.py
```

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create your feature branch: `git checkout -b feat/amazing-feature`
3. Commit your changes: `git commit -m 'feat: add amazing feature'`
4. Push to the branch: `git push origin feat/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

<div align="center">
<sub>Built with ❤️ — Self-hosted, open source, and free forever</sub>
</div>
