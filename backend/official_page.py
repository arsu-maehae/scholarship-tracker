"""Fetch a small allowlist of official HTML pages with DNS pinning and no redirects."""
from html.parser import HTMLParser
import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import urlsplit

from gemini_client import AIError

ALLOWED_HOSTS = {'www.studyinnl.org', 'www.ox.ac.uk', 'www.studyinjapan.go.jp'}


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'template'): self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'template') and self.hidden: self.hidden -= 1
    def handle_data(self, text):
        if not self.hidden: self.parts.append(text)


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
        raise AIError('Invalid official URL.')
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        if parsed.scheme != 'https' or host not in ALLOWED_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.fragment:
            raise AIError('Only supported HTTPS official hosts on port 443 are allowed.')
        addresses = {entry[4][0] for entry in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
            raise AIError('The official host resolved to a non-public address.')
        deadline = time.monotonic() + 12
        connection = PinnedHTTPS(host, sorted(addresses)[0])
        try:
            path = (parsed.path or '/') + (('?' + parsed.query) if parsed.query else '')
            connection.request('GET', path, headers={'Accept': 'text/html', 'Accept-Encoding': 'identity', 'User-Agent': 'ScholarshipDiscovery/1.0'})
            response = connection.getresponse()
            if response.status != 200:
                raise AIError('Official page was unavailable or redirected; redirects are not followed.')
            if response.headers.get_content_type() != 'text/html':
                raise AIError('Only HTML pages are supported; PDF and other formats are not supported.')
            if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
                raise AIError('Compressed responses are not supported.')
            chunks, size = [], 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0: raise AIError('Official page fetch timed out.')
                if connection.sock is not None:
                    connection.sock.settimeout(min(8, remaining))
                chunk = response.read1(min(8192, 262145 - size))
                if not chunk: break
                chunks.append(chunk)
                size += len(chunk)
                if size > 262144: raise AIError('Official page exceeds the size limit.')
            body = b''.join(chunks)
            charset = response.headers.get_content_charset() or 'utf-8'
            text = body.decode(charset, errors='replace')
        finally:
            connection.close()
    except AIError:
        raise
    except (OSError, ValueError, LookupError, http.client.HTTPException):
        raise AIError('Could not safely retrieve the official page.') from None
    parser = VisibleText()
    parser.feed(text)
    visible = ' '.join(' '.join(parser.parts).split())[:12000]
    if not visible: raise AIError('No readable page text was found.')
    return visible
