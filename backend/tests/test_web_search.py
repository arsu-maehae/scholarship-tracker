import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from web_search import WebSearchError, search_web


class Response:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, limit):
        return json.dumps({"web": {"results": [
            {"title": "<b>Scholarship</b> &amp; study", "url": "https://example.edu/award", "description": "<b>Check</b> terms"},
            {"title": "Unsafe", "url": "javascript:alert(1)"},
            {"title": "Duplicate", "url": "https://example.edu/award"},
            {"title": "Credentials", "url": "https://user:pass@example.edu/"}
        ]}}).encode()


class WebSearchTests(unittest.TestCase):
    @patch("web_search.urlopen", return_value=Response())
    def test_sanitizes_and_limits_results(self, request):
        results = search_web("scholarship Japan", "test-key")
        self.assertEqual(results, [{"title": "Scholarship & study", "url": "https://example.edu/award", "source": "example.edu", "snippet": "Check terms"}])
        self.assertEqual(request.call_args.kwargs["timeout"], 8)
        self.assertEqual(request.call_args.args[0].get_header("X-subscription-token"), "test-key")
        self.assertIn("country=ALL", request.call_args.args[0].full_url)

    @patch("web_search.urlopen", side_effect=URLError("provider failure"))
    def test_provider_error_does_not_leak_details(self, _):
        with self.assertRaises(WebSearchError) as error:
            search_web("scholarship", "test-key")
        self.assertNotIn("test-key", str(error.exception))


if __name__ == "__main__": unittest.main()
