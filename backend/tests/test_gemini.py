"""Mock-only tests: no key from the environment can reach a live API."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from gemini_client import AIError, generate, _request, MODEL
from gemini_extract import extract_candidate
from gemini_preferences import parse_preferences
from official_page import fetch_official_html

ENV = {'GEMINI_ENABLED':'true', 'GEMINI_FREE_TIER_CONFIRMED':'true',
       'GEMINI_API_KEY':'fake-test-key', 'GEMINI_TEST_MODE':'true'}


class GeminiTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, ENV, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_disabled_and_ci_cannot_call_network(self):
        with patch.dict(os.environ, {'GEMINI_ENABLED':'false'}), patch('gemini_client.urlopen') as network:
            with self.assertRaises(AIError): generate('hello', {})
            with self.assertRaises(AIError): extract_candidate('https://www.ox.ac.uk/', 'test:key', 'x')
            network.assert_not_called()
        with patch('gemini_client.urlopen') as network:
            with self.assertRaises(AIError): _request('x', {}, 'fake', MODEL)
            network.assert_not_called()

    def test_cached_and_rate_limited(self):
        calls = []
        def fake(*args): calls.append(1); return {'ok': True}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.sqlite'
            self.assertEqual(generate('first', {}, path=path, transport=fake), {'ok': True})
            self.assertEqual(generate('first', {}, path=path, transport=fake), {'ok': True})
            generate('second', {}, path=path, transport=fake)
            with self.assertRaises(AIError): generate('third', {}, path=path, transport=fake)
            self.assertEqual(len(calls), 2)

    def test_failure_counts_and_quota_error(self):
        def failed(*args): raise AIError('quota exhausted')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.sqlite'
            for query in ('first', 'second'):
                with self.assertRaisesRegex(AIError, 'quota'): generate(query, {}, path=path, transport=failed)
            with self.assertRaisesRegex(AIError, 'limit'): generate('third', {}, path=path, transport=failed)

    def test_provider_quota_and_invalid_json_are_reported(self):
        with patch.dict(os.environ, {'GEMINI_TEST_MODE':'false'}), patch('gemini_client.urlopen', side_effect=HTTPError('https://example.invalid', 429, 'quota', None, None)):
            with self.assertRaisesRegex(AIError, 'quota'): _request('x', {}, 'fake', MODEL)
        for status, message in ((400, 'HTTP 400'), (402, 'billing'), (403, 'access'), (404, 'model'), (500, 'HTTP 500')):
            with self.subTest(status=status), patch.dict(os.environ, {'GEMINI_TEST_MODE':'false'}), patch('gemini_client.urlopen', side_effect=HTTPError('https://example.invalid', status, 'failure', None, None)):
                with self.assertRaisesRegex(AIError, message): _request('x', {}, 'fake', MODEL)
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return b'not-json'
        with patch.dict(os.environ, {'GEMINI_TEST_MODE':'false'}), patch('gemini_client.urlopen', return_value=Response()):
            with self.assertRaisesRegex(AIError, 'invalid output'): _request('x', {}, 'fake', MODEL)

    def test_preferences_validation_and_unsupported(self):
        data = dict(q=None, country='FI', degree='master', field='ai', funding='full', scheme=None, intake_year=None, unsupported=['nationality is not indexed'])
        result = parse_preferences('AI masters Finland', fields={'ai'}, schemes=set(), generator=lambda *_: data)
        self.assertEqual(result['filters']['country'], 'FI')
        self.assertTrue(result['unsupported'])
        with self.assertRaises(AIError): parse_preferences('x', fields={'ai'}, schemes=set(), generator=lambda *_: {**data, 'country':'ZZ'})
        with self.assertRaises(AIError): parse_preferences('x', fields={'ai'}, schemes=set(), generator=lambda *_: 'not json')

    def test_extract_requires_verbatim_evidence_and_stays_unpublished(self):
        text = 'Scholarship title Alpha Award. This award supports graduate study in Finland.'
        result = {'title':'Alpha Award', 'title_evidence':'Scholarship title Alpha Award',
                  'description':'Supports graduate study.', 'description_evidence':'supports graduate study in Finland'}
        fake = lambda *_: result
        output = extract_candidate('https://www.ox.ac.uk/test', 'test:alpha', 'test', fetcher=lambda _: text, generator=fake)
        candidate = output['catalogue']['scholarships'][0]
        self.assertEqual(candidate['review_state'], 'needs_review')
        self.assertNotIn('last_checked', candidate)
        self.assertIn('title', output['provenance']['evidence'])
        with self.assertRaises(AIError):
            extract_candidate('https://www.ox.ac.uk/test', 'test:alpha', 'test', fetcher=lambda _: text,
                              generator=lambda *_: {**result, 'description_evidence':'made up source text'})
        empty = extract_candidate('https://www.ox.ac.uk/test', 'test:alpha', 'test', fetcher=lambda _: text,
                                  generator=lambda *_: {**result, 'description':None, 'description_evidence':None})
        self.assertNotIn('description', empty['catalogue']['scholarships'][0])

    def test_url_guard_blocks_private_and_redirects(self):
        for url in ('http://www.ox.ac.uk/', 'https://127.0.0.1/', 'https://www.ox.ac.uk@127.0.0.1/', 'https://www.ox.ac.uk:444/', 'https://169.254.169.254/'):
            with self.subTest(url=url), self.assertRaises(AIError): fetch_official_html(url)
        with patch('official_page.socket.getaddrinfo', return_value=[(0,0,0,'',('127.0.0.1',443))]):
            with self.assertRaises(AIError): fetch_official_html('https://www.ox.ac.uk/')
        with patch('official_page.socket.getaddrinfo', return_value=[(0,0,0,'',('8.8.8.8',443))]), patch('official_page.PinnedHTTPS') as conn:
            conn.return_value.getresponse.return_value.status = 302
            with self.assertRaisesRegex(AIError, 'redirected'): fetch_official_html('https://www.ox.ac.uk/')
            conn.return_value.getresponse.return_value.status = 200
            conn.return_value.getresponse.return_value.headers.get_content_type.return_value = 'application/pdf'
            with self.assertRaisesRegex(AIError, 'HTML'): fetch_official_html('https://www.ox.ac.uk/file.pdf')


if __name__ == '__main__': unittest.main()
