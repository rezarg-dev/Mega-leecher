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

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://python.org)
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
- **Split** files into RAR parts of any size between 19 MB and 900 MB
- **Compress** into RAR archives with optional password protection
- **Send raw** files without any modification (videos are sent streamable, with a thumbnail)
- **Multi-file archives** — combine several files, links and videos into one RAR

### ⬇️ Downloading
- **Direct links** — any HTTP/HTTPS download link up to 2GB
- **Torrents** — magnet links or `.torrent` files
- **YouTube** — videos from 360p up to 4K, or audio-only (MP3), with the size of each quality shown up front
- **Instagram** — public posts and reels

### ☁️ Cloud Storage
- **GitHub** — upload files and get direct download links (up to 15GB free with your own token)
- **Google Drive** — upload files and get shareable links (up to 15GB free with your Google account)

### 🔐 Access Control
- Subscription-based access with expiry dates
- Separate YouTube subscription tier
- Daily quotas for YouTube downloads and cloud uploads
- Admin panel for user management
- Persian and English interface, chosen per user

### ⚙️ Under the Hood
- Every job runs in the background and can be cancelled at any stage
- One job at a time per user, with a server-wide limit so a small VPS is not overwhelmed
- Temporary files are removed after every job and on every start

---

## 📋 Requirements

| Requirement | Version |
|-------------|---------|
| OS | Ubuntu 22.04+ / Debian 12+ |
| Python | 3.10+ |
| Node.js | 22.x (installed automatically, used by the YouTube token provider) |
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
1. Install all system dependencies (apt packages, Node.js, Deno, Python packages)
2. Build the YouTube PO Token provider and run it as a service
3. Ask for your Telegram bot credentials
4. Optionally configure Google Drive support
5. Set up a systemd service that starts automatically on boot
6. Install the `mega-leecher` management command

### Upgrading an existing installation

Run the same two commands again on the server. The installer upgrades in place:
`config.env`, the user databases, `cookies.txt` and the Telegram session are never touched.

```bash
git clone https://github.com/rezarg-dev/Mega-leecher.git
bash Mega-leecher/setup.sh
```

> ⚠️ Coming from version 1.x (the single `bot.py`)? Upgrade with the commands above, **not** with
> option 9 of the old `mega-leecher` menu — the old updater only knows about three files.

---

## ⚙️ Configuration

After installation your config is stored at `/opt/mega-leecher/config.env`.

For a manual setup, copy the example file to get started:
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
| `MAX_CONCURRENT_JOBS` | How many jobs of regular users run at once (optional, default `4`) |

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
| 9 | Update from GitHub (rolls back by itself if the new version does not start) |
| 10 | Reinstall (settings and user data are kept) |
| 11 | Uninstall completely (a backup of your settings and data is saved to `/root` first) |

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
```

No restart is needed: the file is read for every download.

---

## 📣 Broadcasting an Announcement

`broadcast.py` sends a message to every user in the database, each in the language they chose.
Edit the `MESSAGES` texts at the top of the file, then run it from the install directory:

```bash
cd /opt/mega-leecher
./venv/bin/python broadcast.py
```

The script uses its own Telegram session, so the bot keeps running while it works.

---

## 📁 Project Structure

```
Mega-leecher/
├── bot.py                  # Entry point
├── broadcast.py            # Send an announcement to all users
├── leecher/
│   ├── main.py             # Startup and shutdown
│   ├── client.py           # The Pyrogram client
│   ├── config.py           # Settings (reads config.env) and limits
│   ├── lang.py             # Every user-facing text, Persian and English
│   ├── db.py               # Users, GitHub and Drive accounts (JSON files)
│   ├── state.py            # Pending files, open prompts, running jobs
│   ├── jobs.py             # The pipeline: queue → fetch → deliver
│   ├── net.py              # Direct-link downloads
│   ├── youtube.py          # YouTube / Instagram through yt-dlp
│   ├── torrent.py          # Torrents through libtorrent
│   ├── archive.py          # RAR and ZIP packaging
│   ├── media.py            # Sending files back to Telegram
│   ├── github.py           # GitHub storage (REST API + git)
│   ├── gdrive.py           # Google Drive (OAuth + resumable upload)
│   ├── ui.py               # Keyboards, message helpers, progress
│   ├── utils.py            # File names, subprocesses, formatting
│   └── handlers/           # Telegram handlers, one module per area
├── setup.sh                # Automated install / upgrade script
├── mega-leecher.sh         # Management CLI (installed as `mega-leecher`)
├── mega-leecher.service    # Systemd unit for manual installs
├── config.env.example      # Configuration template
├── requirements.txt
└── README.md
```

Runtime files — `config.env`, `users_db.json`, `github_db.json`, `drive_db.json`, `cookies.txt`,
the session file and `temp/` — live next to `bot.py` and are ignored by git.

---

## 🛠️ Manual Installation (Advanced)

If you prefer to install manually without the setup script:

```bash
# 1. Install system packages
apt update && apt install -y python3 python3-pip python3-venv python3-libtorrent \
    git ffmpeg rar unrar unzip zip p7zip-full

# 2. Get the code
git clone https://github.com/rezarg-dev/Mega-leecher.git /opt/mega-leecher
cd /opt/mega-leecher

# 3. Create the venv (system packages are needed for libtorrent)
python3 -m venv venv --system-site-packages
./venv/bin/pip install -r requirements.txt

# 4. Configure
cp config.env.example config.env
nano config.env

# 5. Run
./venv/bin/python bot.py
```

YouTube also needs [Deno](https://deno.com) and the
[PO Token provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider) server, in the same
version as the `bgutil-ytdlp-pot-provider` line in `requirements.txt`. `setup.sh` takes care of both.

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
