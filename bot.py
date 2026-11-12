#!/usr/bin/env python3
"""Mega Leecher - entry point. Run with: python bot.py"""

import sys

try:
    from leecher.main import run
except ModuleNotFoundError as e:
    if e.name != "leecher":
        raise
    # Updating a 1.x installation file by file leaves bot.py without its package.
    sys.exit("The 'leecher' package is missing next to bot.py.\n"
             "Get the full project and run its installer (your data is kept):\n"
             "  git clone https://github.com/rezarg-dev/Mega-leecher.git && bash Mega-leecher/setup.sh")

if __name__ == "__main__":
    run()
