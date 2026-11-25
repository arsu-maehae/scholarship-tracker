"""Fetch a small allowlist of official HTML pages with DNS pinning and no redirects."""
import http.client
import ipaddress
import socket
import ssl
import time
import queue
import threading
from urllib.parse import urlsplit

class FetchError(Exception):
    pass

ALLOWED_HOSTS = {'www.studyinnl.org', 'www.ox.ac.uk', 'www.studyinjapan.go.jp', 'www.emmir.org'}
DEFAULT_MAX_BYTES = 262_144
HOST_MAX_BYTES = {'www.emmir.org': 1_048_576}
OFFICIAL_PAGE_GROUPS = {
    'www.emmir.org': (
        {'label': 'Application deadlines and required documents', 'url': 'https://www.emmir.org/application-procedures', 'categories': ('deadline', 'documents')},
        {'label': 'Entry and language requirements', 'url': 'https://www.emmir.org/requirements', 'categories': ('eligibility',)},
        {'label': 'Costs and funding', 'url': 'https://www.emmir.org/cost-and-funding', 'categories': ('funding',)},
    ),
}
RESTRICTED_PATHS = {
    'www.emmir.org': frozenset({'/', '/application-procedures', '/requirements', '/cost-and-funding'}),
}


def official_pages_for(saved_url):
    try:
        host = urlsplit(saved_url).hostname
    except (TypeError, ValueError):
        return []
    return [{**page, 'categories': list(page['categories'])} for page in OFFICIAL_PAGE_GROUPS.get(host, ())]


def source_is_allowed_for_saved(saved_url, source_url):
    try:
        saved = urlsplit(saved_url)
        source = urlsplit(source_url)
    except (TypeError, ValueError):
        return False
    if saved.hostname in OFFICIAL_PAGE_GROUPS:
        configured = {page['url'] for page in OFFICIAL_PAGE_GROUPS[saved.hostname]}
        configured.add(f'https://{saved.hostname}/')
        return source_url in configured
    return source_url == saved_url

def resolve_public(host):
    result=queue.Queue(maxsize=1)
    def resolve():
        try: result.put(socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM))
        except OSError: result.put(None)
    threading.Thread(target=resolve,daemon=True).start()
    try: entries=result.get(timeout=4)
    except queue.Empty: raise FetchError('DNS lookup timed out.') from None
    if not entries: raise FetchError('Could not resolve the official host.')
    addresses={entry[4][0] for entry in entries}
    if any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise FetchError('The official host resolved to a non-public address.')
    return sorted(addresses)


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, hostname, address):
        super().__init__(hostname, 443, timeout=8, context=ssl.create_default_context())
        self.address = address
    def connect(self):
        raw = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def fetch_official_html(url):
    if not isinstance(url, str) or len(url) > 2048 or any(c.isspace() for c in url):
        raise FetchError('Invalid official URL.')
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        if parsed.scheme != 'https' or host not in ALLOWED_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.fragment:
            raise FetchError('This page is not on the supported HTTPS host list. Paste the public page text instead.')
        if host in RESTRICTED_PATHS and (parsed.path or '/') not in RESTRICTED_PATHS[host]:
            raise FetchError('This official host is supported only for its verified scholarship information pages.')
        addresses = resolve_public(host)
        deadline = time.monotonic() + 12
        max_bytes = HOST_MAX_BYTES.get(host, DEFAULT_MAX_BYTES)
        connection = PinnedHTTPS(host, addresses[0])
        try:
            path = (parsed.path or '/') + (('?' + parsed.query) if parsed.query else '')
            connection.request('GET', path, headers={'Accept': 'text/html', 'Accept-Encoding': 'identity', 'User-Agent': 'ScholarshipDiscovery/1.0'})
            response = connection.getresponse()
            if response.status != 200:
                raise FetchError(f'Official page returned HTTP {response.status}; redirects are not followed.')
            if response.headers.get_content_type() != 'text/html':
                raise FetchError('Only HTML pages are supported; paste text from PDF or other formats.')
            if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
                raise FetchError('Compressed responses are not supported.')
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > max_bytes:
                raise FetchError('Official page exceeds the size limit.')
            chunks, size = [], 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0: raise FetchError('Official page fetch timed out.')
                if connection.sock is not None:
                    connection.sock.settimeout(min(8, remaining))
                chunk = response.read1(min(8192, max_bytes + 1 - size))
                if not chunk: break
                chunks.append(chunk)
                size += len(chunk)
                if size > max_bytes: raise FetchError('Official page exceeds the size limit.')
            body = b''.join(chunks)
            charset = response.headers.get_content_charset() or 'utf-8'
            text = body.decode(charset, errors='replace')
        finally:
            connection.close()
    except FetchError:
        raise
    except (OSError, ValueError, LookupError, http.client.HTTPException):
        raise FetchError('Could not safely retrieve the official page.') from None
    return text
