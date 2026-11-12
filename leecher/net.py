"""Direct-link downloads."""

import asyncio
import ipaddress
import os
import socket
import urllib.parse

import aiohttp
from aiohttp.abc import AbstractResolver
from aiohttp.resolver import DefaultResolver

from . import config
from .errors import Cancelled, UserError
from .ui import Progress
from .utils import require_space, safe_filename

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://google.com/",
}

# No overall limit: a 2 GB file on a slow mirror can legitimately take hours.
DOWNLOAD_TIMEOUT = aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=120)
PROBE_TIMEOUT = aiohttp.ClientTimeout(total=30)


def _is_public(address):
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    if getattr(ip, "ipv4_mapped", None):
        ip = ip.ipv4_mapped
    return ip.is_global


def _check_host(host):
    """Reject links that point at this server or its private network."""
    if not host:
        raise UserError("url_not_allowed")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return                      # a name: the resolver below takes care of it
    if not _is_public(host):
        raise UserError("url_not_allowed")


class _PublicResolver(AbstractResolver):
    def __init__(self):
        self._inner = DefaultResolver()

    async def resolve(self, host, port=0, family=socket.AF_INET):
        found = await self._inner.resolve(host, port, family)
        public = [entry for entry in found if _is_public(entry["host"])]
        if not public:
            raise UserError("url_not_allowed")
        return public

    async def close(self):
        await self._inner.close()


async def _on_start(session, context, params):
    _check_host(params.url.host)


async def _on_redirect(session, context, params):
    location = params.response.headers.get("Location")
    if location:
        target = urllib.parse.urljoin(str(params.url), location)
        _check_host(urllib.parse.urlsplit(target).hostname)


def _session(timeout):
    trace = aiohttp.TraceConfig()
    trace.on_request_start.append(_on_start)
    trace.on_request_redirect.append(_on_redirect)
    return aiohttp.ClientSession(
        headers=BROWSER_HEADERS,
        timeout=timeout,
        connector=aiohttp.TCPConnector(resolver=_PublicResolver()),
        trace_configs=[trace],
    )


def _total_size(response):
    if response.status == 206:
        total = response.headers.get("Content-Range", "").rpartition("/")[2]
        return int(total) if total.isdigit() else 0
    return response.content_length or 0


def _file_name(response):
    try:
        disposition = response.content_disposition
    except Exception:
        disposition = None
    if disposition is not None and disposition.filename:
        # Many servers percent-encode the plain filename= value as well.
        return urllib.parse.unquote(disposition.filename)
    return urllib.parse.unquote(os.path.basename(response.url.path))


async def probe(url):
    """Look at a link without downloading it.

    Returns (file name or None, size or 0, is it an HTML page). All three are
    empty-handed when the server would not talk to us; the download itself
    will then report what went wrong.
    """
    async with _session(PROBE_TIMEOUT) as session:
        # Plenty of file hosts reject HEAD, so fall back to a one-byte GET.
        for method, headers in (("HEAD", None), ("GET", {"Range": "bytes=0-0"})):
            try:
                async with session.request(method, url, headers=headers) as response:
                    if response.status >= 400:
                        continue
                    name = _file_name(response)
                    is_html = "text/html" in response.headers.get("Content-Type", "")
                    return (safe_filename(name, "") or None), _total_size(response), is_html
            except UserError:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError, ValueError):
                continue
    return None, 0, False


async def download(job, url, path, label, limit=None):
    progress = Progress(job, label)
    try:
        async with _session(DOWNLOAD_TIMEOUT) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                total = response.content_length or 0
                if limit and total > limit:
                    raise UserError("size_limit")
                require_space(total)
                received = 0
                with open(path, "wb") as f:
                    async for chunk in response.content.iter_chunked(config.MB):
                        if job.cancelled:
                            raise Cancelled()
                        received += len(chunk)
                        if limit and received > limit:
                            raise UserError("size_limit")
                        f.write(chunk)
                        await progress.update(received, total)
    except aiohttp.ClientResponseError as e:
        raise UserError("error_generic", e=f"HTTP {e.status}")
    except asyncio.TimeoutError:
        raise UserError("error_generic", e="timeout")
    if os.path.getsize(path) == 0:
        raise UserError("empty_file")
    return path
