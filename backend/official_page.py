"""Safely fetch user-selected public HTTPS scholarship pages."""
import http.client
import ipaddress
import queue
import socket
import ssl
import threading
import time
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit


class FetchError(Exception):
    pass


MAX_BYTES = 1_048_576
MAX_REDIRECTS = 3
PRESET_PAGE_GROUPS = {
    'www.emmir.org': (
        {'label': 'Application deadlines and required documents', 'url': 'https://www.emmir.org/application-procedures', 'categories': ('deadline', 'documents')},
        {'label': 'Entry and language requirements', 'url': 'https://www.emmir.org/requirements', 'categories': ('eligibility',)},
        {'label': 'Costs and funding', 'url': 'https://www.emmir.org/cost-and-funding', 'categories': ('funding',)},
    ),
}


def normalize_public_https_url(value):
    if not isinstance(value, str) or not value or len(value) > 2048 or any(c.isspace() or ord(c) < 32 for c in value):
        raise FetchError('Enter a valid public HTTPS URL.')
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        if parsed.scheme.lower() != 'https' or not host or parsed.username is not None or parsed.password is not None or parsed.port not in (None, 443):
            raise ValueError()
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            host = host.encode('idna').decode('ascii').lower().rstrip('.')
            if len(host) > 253 or '.' not in host or host.endswith(('.local', '.localhost', '.internal')):
                raise ValueError()
        else:
            if not address.is_global:
                raise ValueError()
            host = address.compressed
            if address.version == 6:
                host = '[' + host + ']'
        return urlunsplit(('https', host, parsed.path or '/', parsed.query, ''))
    except (ValueError, UnicodeError):
        raise FetchError('Enter a public HTTPS URL without credentials or a custom port.') from None


def _page_label(url):
    parsed = urlsplit(url)
    path = parsed.path.rstrip('/')
    return (parsed.hostname or 'Official source') + (path if path else '')


def official_pages_for(saved_url, additional_pages=()):
    try:
        saved = normalize_public_https_url(urldefrag(saved_url)[0])
        host = urlsplit(saved).hostname
    except FetchError:
        return []
    presets = PRESET_PAGE_GROUPS.get(host, ())
    pages = [
        {**page, 'categories': list(page['categories']), 'removable': False, 'id': None}
        for page in presets
    ] if presets else [{
        'id': None,
        'label': 'Saved scholarship page',
        'url': saved,
        'categories': None,
        'removable': False,
    }]
    seen = {page['url'] for page in pages}
    for row in additional_pages:
        source_url = row.source_url if hasattr(row, 'source_url') else row['source_url']
        try:
            source_url = normalize_public_https_url(source_url)
        except FetchError:
            continue
        if source_url in seen:
            continue
        row_id = row.id if hasattr(row, 'id') else row.get('id')
        pages.append({
            'id': row_id,
            'label': _page_label(source_url),
            'url': source_url,
            'categories': None,
            'removable': True,
        })
        seen.add(source_url)
    return pages


def source_is_allowed_for_saved(saved_url, source_url, additional_pages=()):
    try:
        source = normalize_public_https_url(urldefrag(source_url)[0])
        saved = normalize_public_https_url(urldefrag(saved_url)[0])
    except FetchError:
        return False
    allowed = {saved, *(page['url'] for page in official_pages_for(saved, additional_pages))}
    return source in allowed


def resolve_public(host):
    result = queue.Queue(maxsize=1)

    def resolve():
        try:
            result.put(socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM))
        except OSError:
            result.put(None)

    threading.Thread(target=resolve, daemon=True).start()
    try:
        entries = result.get(timeout=4)
    except queue.Empty:
        raise FetchError('DNS lookup timed out.') from None
    if not entries:
        raise FetchError('Could not resolve the official host.')
    addresses = {entry[4][0] for entry in entries}
    if any(not ipaddress.ip_address(address).is_global for address in addresses):
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


def _read_html(response, connection, deadline):
    if response.headers.get_content_type() != 'text/html':
        raise FetchError('Only HTML pages are supported; paste text from PDF or other formats.')
    if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
        raise FetchError('Compressed responses are not supported.')
    content_length = response.headers.get('Content-Length')
    try:
        if content_length and int(content_length) > MAX_BYTES:
            raise FetchError('Official page exceeds the 1 MB size limit.')
    except ValueError:
        raise FetchError('Official page returned an invalid content length.') from None
    chunks, size = [], 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FetchError('Official page fetch timed out.')
        if connection.sock is not None:
            connection.sock.settimeout(min(8, remaining))
        chunk = response.read1(min(8192, MAX_BYTES + 1 - size))
        if not chunk:
            break
        chunks.append(chunk)
        size += len(chunk)
        if size > MAX_BYTES:
            raise FetchError('Official page exceeds the 1 MB size limit.')
    charset = response.headers.get_content_charset() or 'utf-8'
    return b''.join(chunks).decode(charset, errors='replace')


def fetch_official_html(url):
    deadline = time.monotonic() + 15
    current = normalize_public_https_url(url)
    visited = set()
    for redirect_count in range(MAX_REDIRECTS + 1):
        if current in visited:
            raise FetchError('Official page redirect loop detected.')
        visited.add(current)
        parsed = urlsplit(current)
        host = parsed.hostname
        addresses = resolve_public(host)
        connection = PinnedHTTPS(host, addresses[0])
        try:
            path = parsed.path + (('?' + parsed.query) if parsed.query else '')
            connection.request('GET', path, headers={
                'Accept': 'text/html',
                'Accept-Encoding': 'identity',
                'User-Agent': 'ScholarshipTracker/1.0',
            })
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                if redirect_count == MAX_REDIRECTS:
                    raise FetchError('Official page redirected too many times.')
                location = response.headers.get('Location')
                if not location:
                    raise FetchError('Official page returned a redirect without a destination.')
                current = normalize_public_https_url(urljoin(current, location))
                continue
            if response.status != 200:
                raise FetchError(f'Official page returned HTTP {response.status}. Paste its public text if access requires a login or browser.')
            return _read_html(response, connection, deadline)
        except FetchError:
            raise
        except (OSError, ValueError, LookupError, http.client.HTTPException):
            raise FetchError('Could not safely retrieve the official page. Paste the public page text instead.') from None
        finally:
            connection.close()
    raise FetchError('Official page redirected too many times.')
