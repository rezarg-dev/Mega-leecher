"""
Mega Leecher — Configuration Loader
Reads settings from config.env in the project root.
"""

import os
import sys


def _load(path="config.env"):
    cfg = {}
    if not os.path.exists(path):
        print(f"[ERROR] config.env not found. Copy config.env.example to config.env and fill in your values.")
        sys.exit(1)
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg


_cfg = _load()


def _require(key):
    val = _cfg.get(key, "")
    if not val or val.endswith("_here"):
        print(f"[ERROR] '{key}' is not set in config.env. Please fill in all required values.")
        sys.exit(1)
    return val


# ── Required ──────────────────────────────────────────
API_ID              = int(_require("API_ID"))
API_HASH            = _require("API_HASH")
BOT_TOKEN           = _require("BOT_TOKEN")
ADMIN_ID            = int(_require("ADMIN_ID"))
PURCHASE_USERNAME   = _require("PURCHASE_USERNAME")

# ── Optional (Google Drive) ───────────────────────────
GOOGLE_CLIENT_ID     = _cfg.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = _cfg.get("GOOGLE_CLIENT_SECRET", "")

# ── Paths ─────────────────────────────────────────────
INSTALL_DIR = _cfg.get("INSTALL_DIR", "/opt/mega-leecher")
