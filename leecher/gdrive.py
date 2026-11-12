"""Google Drive: OAuth, resumable uploads and storage housekeeping."""

import asyncio
import logging
import os
import re
import time
import urllib.parse

import httpx

from . import config, db
from .errors import Cancelled, UserError
from .utils import clip, plain

log = logging.getLogger(__name__)

AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/drive/v3"
UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable"

REDIRECT_URI = "http://localhost"
SCOPE = "https://www.googleapis.com/auth/drive.file"
FOLDER_NAME = "Telegram Bot Uploads"
FOLDER_MIME = "application/vnd.google-apps.folder"

CHUNK_SIZE = 8 * config.MB      # Drive wants multiples of 256 KB
MAX_RETRIES = 5


class FolderMissing(Exception):
    """The upload folder stored for the user no longer exists."""


def is_configured():
    return bool(config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET)


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def auth_url():
    query = urllib.parse.urlencode({
        "client_id": config.GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    })
    return f"{AUTH_URL}?{query}"


def extract_code(text):
    """Users paste either the bare code or the whole http://localhost/?code=... address."""
    text = text.strip()
    match = re.search(r"[?&]code=([^&\s]+)", text)
    return urllib.parse.unquote(match.group(1)) if match else text


async def exchange_code(code):
    """Trade an authorization code for (access token, refresh token, expiry)."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(TOKEN_URL, data={
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        })
    if response.status_code != 200:
        raise UserError("gd_code_rejected", code=response.status_code,
                        detail=plain(clip(response.text, 100)))
    data = response.json()
    expiry = time.time() + data.get("expires_in", 3600)
    return data.get("access_token"), data.get("refresh_token"), expiry


async def access_token(uid):
    """A token that is valid for at least another minute, or None."""
    account = db.gd_account(uid)
    if not account:
        return None
    if account.get("token_expiry", 0) - time.time() > 60 and account.get("access_token"):
        return account["access_token"]
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(TOKEN_URL, data={
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "refresh_token": account["refresh_token"],
                "grant_type": "refresh_token",
            })
    except httpx.HTTPError as e:
        log.warning("token refresh failed for %s: %s", uid, e)
        return None
    if response.status_code != 200:
        return None
    data = response.json()
    db.gd_update(uid, access_token=data["access_token"],
                 token_expiry=time.time() + data.get("expires_in", 3600))
    return data["access_token"]


async def ensure_folder(token):
    """Find the bot's upload folder, creating it on first use."""
    query = f"name='{FOLDER_NAME}' and mimeType='{FOLDER_MIME}' and trashed=false"
    async with httpx.AsyncClient(timeout=30, headers=_bearer(token)) as client:
        response = await client.get(f"{API}/files", params={"q": query, "fields": "files(id)"})
        if response.status_code == 200 and response.json().get("files"):
            return response.json()["files"][0]["id"]
        response = await client.post(f"{API}/files", json={"name": FOLDER_NAME, "mimeType": FOLDER_MIME})
    if response.status_code != 200:
        raise UserError("gd_folder_create_error", code=response.status_code)
    return response.json()["id"]


def _next_offset(response):
    """Where Drive wants the upload to continue, from a 308 response."""
    match = re.fullmatch(r"bytes=0-(\d+)", response.headers.get("Range", ""))
    return int(match.group(1)) + 1 if match else 0


async def upload(token, path, name, folder_id, cancel, on_progress):
    """Upload a file in chunks and return its Drive id.

    A chunk that fails is retried from wherever Drive says it got to, so a
    hiccup in the connection does not throw away a multi-gigabyte upload.
    """
    size = os.path.getsize(path)
    timeout = httpx.Timeout(120, connect=30)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            UPLOAD_URL,
            headers={**_bearer(token),
                     "X-Upload-Content-Type": "application/octet-stream",
                     "X-Upload-Content-Length": str(size)},
            json={"name": name, "parents": [folder_id]},
        )
        if response.status_code == 404:
            raise FolderMissing()
        if response.status_code != 200 or "Location" not in response.headers:
            raise UserError("gd_upload_start_error", code=response.status_code)
        session_url = response.headers["Location"]

        offset = 0
        failures = 0
        with open(path, "rb") as f:
            while True:
                if cancel.is_set():
                    raise Cancelled()
                f.seek(offset)
                chunk = f.read(CHUNK_SIZE)
                last = offset + len(chunk) - 1
                content_range = f"bytes {offset}-{last}/{size}" if chunk else f"bytes */{size}"
                try:
                    response = await client.put(session_url, content=chunk,
                                                headers={"Content-Range": content_range})
                    status = response.status_code
                except httpx.TransportError as e:
                    log.info("drive upload interrupted at %s: %s", offset, e)
                    response, status = None, 0

                if status in (200, 201):
                    return response.json()["id"]
                if status == 308:
                    resume = _next_offset(response)
                    if resume > offset:
                        failures = 0
                    else:
                        failures += 1
                        if failures > MAX_RETRIES:
                            raise UserError("gd_upload_fail", code=status)
                    offset = resume
                    await on_progress(offset, size)
                    continue
                if status and status < 500 and status != 429:
                    raise UserError("gd_upload_fail", code=status)

                failures += 1
                if failures > MAX_RETRIES:
                    raise UserError("gd_upload_fail", code=status or "network")
                await asyncio.sleep(min(2 ** failures, 30))
                # Ask how much arrived before sending anything again.
                try:
                    response = await client.put(session_url, headers={"Content-Range": f"bytes */{size}"})
                except httpx.TransportError:
                    continue
                if response.status_code in (200, 201):
                    return response.json()["id"]
                if response.status_code == 308:
                    offset = _next_offset(response)


async def share(token, file_id):
    """Make the file readable by anyone with the link; return (view URL, download URL)."""
    async with httpx.AsyncClient(timeout=30, headers=_bearer(token)) as client:
        response = await client.post(f"{API}/files/{file_id}/permissions",
                                     json={"role": "reader", "type": "anyone"})
    if response.status_code != 200:
        raise UserError("gd_upload_fail", code=response.status_code)
    return (f"https://drive.google.com/file/d/{file_id}/view?usp=sharing",
            f"https://drive.google.com/uc?id={file_id}&export=download")


async def space(token):
    """(used, total, free) in bytes; all zero when Drive does not answer."""
    async with httpx.AsyncClient(timeout=15, headers=_bearer(token)) as client:
        response = await client.get(f"{API}/about", params={"fields": "storageQuota"})
    if response.status_code != 200:
        return 0, 0, 0
    quota = response.json().get("storageQuota", {})
    total, used = int(quota.get("limit", 0)), int(quota.get("usage", 0))
    return used, total, max(0, total - used)


async def clear(token, folder_id, on_deleted=None):
    """Delete every file in the upload folder; return how many were removed."""
    deleted = 0
    params = {"q": f"'{folder_id}' in parents and trashed=false", "fields": "files(id)", "pageSize": 1000}
    async with httpx.AsyncClient(timeout=30, headers=_bearer(token)) as client:
        while True:
            response = await client.get(f"{API}/files", params=params)
            if response.status_code != 200:
                break
            files = response.json().get("files", [])
            removed = 0
            for entry in files:
                result = await client.delete(f"{API}/files/{entry['id']}")
                if result.status_code == 204:
                    removed += 1
                    deleted += 1
                    if on_deleted:
                        await on_deleted(deleted)
            # A full page means there may be more; list again until it runs dry.
            if len(files) < params["pageSize"] or not removed:
                break
    return deleted
