"""Local AI endpoint tests; all provider work is mocked."""
import os
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from starlette.requests import Request
import main
from gemini_client import AIError


def request(origin='http://127.0.0.1:5173', host='127.0.0.1:8000', client='127.0.0.1', header='ScholarshipDiscovery'):
    scope = {'type': 'http', 'method': 'POST', 'path': '/api/catalogue-preferences',
             'client': (client, 1234), 'server': ('127.0.0.1', 8000),
             'headers': [(b'origin', origin.encode()), (b'host', host.encode()), (b'x-requested-with', header.encode())]}
    return Request(scope)


class LocalEndpointTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'GEMINI_TEST_MODE':'true'}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_local_request_returns_validated_preferences(self):
        expected = {'filters': {'country': 'FI'}, 'unsupported': []}
        with patch('main.filter_options', return_value={'fields':['ai']}), patch('main.list_schemes', return_value=[]), patch('main.parse_preferences', return_value=expected) as parser:
            result = main.catalogue_preferences(main.NaturalSearchRequest(text='Finland'), request())
        self.assertEqual(result, expected)
        parser.assert_called_once_with('Finland', fields={'ai'}, schemes=set())

    def test_rejects_untrusted_clients_and_origins_before_provider(self):
        for r in (request(origin='https://untrusted.example'), request(client='192.168.1.2'), request(host='untrusted.example'), request(header='')):
            with self.subTest(r=r), patch('main.parse_preferences') as parser, self.assertRaises(HTTPException) as error:
                main.catalogue_preferences(main.NaturalSearchRequest(text='Finland'), r)
            self.assertEqual(error.exception.status_code, 403)
            parser.assert_not_called()

    def test_disabled_or_quota_error_returns_clear_failure(self):
        with patch('main.filter_options', return_value={'fields':[]}), patch('main.list_schemes', return_value=[]), patch('main.parse_preferences', side_effect=AIError('Gemini quota exhausted')):
            with self.assertRaises(HTTPException) as error:
                main.catalogue_preferences(main.NaturalSearchRequest(text='Finland'), request())
            self.assertEqual(error.exception.status_code, 503)
            self.assertIn('quota', error.exception.detail)


if __name__ == '__main__': unittest.main()
