"""Retrieve unverified web suggestions without exposing provider credentials."""
import json
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


class WebSearchError(Exception):
    pass


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value, limit):
    if not isinstance(value, str):
        return ""
    parser = TextOnly()
    parser.feed(value[:10000])
    return " ".join(" ".join(parser.parts).split())[:limit]


def search_web(query, key):
    params = urlencode({"q": query, "country": "ALL", "count": 10, "result_filter": "web", "text_decorations": "false"})
    request = Request("https://api.search.brave.com/res/v1/web/search?" + params,
                      headers={"Accept": "application/json", "X-Subscription-Token": key})
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read(1_000_001))
        raw = payload.get("web", {}).get("results", [])
        if not isinstance(raw, list):
            raise ValueError("Invalid response")
        items = []
        seen = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            if not isinstance(url, str) or len(url) > 2048:
                continue
            try:
                parsed = urlsplit(url)
                if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                    continue
                parsed.port
            except ValueError:
                continue
            title = plain_text(item.get("title"), 300)
            if not title or url in seen:
                continue
            seen.add(url)
            items.append({"title": title, "url": url, "source": parsed.hostname,
                          "snippet": plain_text(item.get("description"), 500)})
        return items
    except (URLError, TimeoutError, OSError, ValueError, TypeError, AttributeError):
        raise WebSearchError("Search provider unavailable") from None
