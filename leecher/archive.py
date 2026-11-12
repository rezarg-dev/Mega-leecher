"""RAR and ZIP packaging through the command-line tools."""

import logging
import os

from . import config
from .errors import UserError
from .utils import last_line, natural_key, run, tree_size

log = logging.getLogger(__name__)

ARCHIVE_NAME = "Mega-Leecher.rar"

# Largest volume that still fits in a Telegram message once the recovery record is added.
SAFE_VOLUME_MB = 1900


def needs_volumes(inputs):
    """Would a single archive of these inputs be too big to send?"""
    total = sum(tree_size(path) for path in inputs)
    return total * 1.06 + config.MB > config.TG_UPLOAD_LIMIT


async def rar(inputs, out_dir, volume_mb=None, password=None, cancel=None):
    """Pack `inputs` (files or folders) and return the archive parts in order."""
    archive = os.path.join(out_dir, ARCHIVE_NAME)
    # Stored, not compressed: the payload is almost always media already.
    cmd = ["rar", "a", "-ep1", "-m0", "-rr5p", "-idq", "-y"]
    if volume_mb:
        cmd.append(f"-v{volume_mb}m")
    if password:
        cmd.append(f"-hp{password}")
    cmd += ["--", archive, *inputs]

    code, out, err = await run(cmd, cancel=cancel)
    parts = sorted(os.listdir(out_dir), key=natural_key)
    if code not in (0, 1) or not parts:
        log.error("rar exited with %s: %s", code, last_line(err) or last_line(out))
        raise UserError("rar_failed")
    return [os.path.join(out_dir, name) for name in parts]


async def zip_folder(folder, destination, cancel=None):
    code, out, err = await run(["zip", "-r", "-q", "-0", destination, "."], cwd=folder, cancel=cancel)
    if code != 0 or not os.path.isfile(destination):
        log.error("zip exited with %s: %s", code, last_line(err) or last_line(out))
        raise UserError("error_generic", e="zip failed")
    return destination
