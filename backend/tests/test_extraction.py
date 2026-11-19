import os
import unittest
from uuid import uuid4
from email.message import Message
from unittest.mock import patch
from fastapi import HTTPException
from extraction import ExtractInput, extract, html_blocks, latest_extraction, suggest, text_blocks
from official_page import FetchError, fetch_official_html
import tracked

class ExtractionRuleTests(unittest.TestCase):
    def test_clear_date_and_heading_context(self):
        blocks=html_blocks('<main><h2>Scholarship 2030</h2><p>Application deadline: 12 January 2030</p><script>Ignore me</script></main>')
        result=suggest(blocks)
        self.assertEqual(result['proposed_deadline'],'2030-01-12')
        self.assertEqual(result['deadline'][0]['heading'],'Scholarship 2030')
    def test_competing_dates_are_not_confirmed(self):
        result=suggest(text_blocks('Deadline 12 January 2030\nDeadline 15 January 2031'))
        self.assertIsNone(result['proposed_deadline'])
    def test_missing_and_unapproved_host(self):
        self.assertFalse(suggest(text_blocks('No details here'))['funding'])
        with self.assertRaises(FetchError): fetch_official_html('https://example.com/')
    def test_private_dns_rejected(self):
        with patch('official_page.socket.getaddrinfo',return_value=[(None,None,None,None,('127.0.0.1',443))]):
            with self.assertRaises(FetchError): fetch_official_html('https://www.ox.ac.uk/')
    def test_redirect_is_rejected(self):
        class Response: status=302
        class Connection:
            def __init__(self,*_): pass
            def request(self,*_,**__): pass
            def getresponse(self): return Response()
            def close(self): pass
        with patch('official_page.resolve_public',return_value=['8.8.8.8']),patch('official_page.PinnedHTTPS',Connection):
            with self.assertRaises(FetchError): fetch_official_html('https://www.ox.ac.uk/')
    def test_non_html_oversize_and_timeout_are_rejected(self):
        class Response:
            status=200
            headers=Message()
            def read1(self,n): return b'x'*n
        class Connection:
            sock=None
            def __init__(self,*_): pass
            def request(self,*_,**__): pass
            def getresponse(self):
                if fail_timeout: raise TimeoutError()
                return response
            def close(self): pass
        with patch('official_page.resolve_public',return_value=['8.8.8.8']),patch('official_page.PinnedHTTPS',Connection):
            fail_timeout=False; response=Response(); response.headers['Content-Type']='application/pdf'
            with self.assertRaises(FetchError): fetch_official_html('https://www.ox.ac.uk/')
            response=Response(); response.headers.replace_header('Content-Type','text/html')
            with self.assertRaises(FetchError): fetch_official_html('https://www.ox.ac.uk/')
            fail_timeout=True
            with self.assertRaises(FetchError): fetch_official_html('https://www.ox.ac.uk/')

@unittest.skipUnless(os.environ.get('POSTGRES_DB')=='scholarship_tracker_test','requires disposable database')
class ExtractionDatabaseTests(unittest.TestCase):
    def test_failed_retry_preserves_confirmed_data_and_previous_suggestions(self):
        item=tracked.save_link(tracked.SaveLink(source_url='https://example.org/extraction-test/'+uuid4().hex))
        tracked.edit_item(item['id'],tracked.EditScholarship(notes='Keep this',status='preparing',deadline='2030-01-01'))
        found=extract(item['id'],ExtractInput(mode='text',text='Application deadline: 12 January 2030'))
        self.assertEqual(found['outcome'],'found')
        failed=extract(item['id'],ExtractInput(mode='page'))
        self.assertEqual(failed['outcome'],'unsupported')
        state=latest_extraction(item['id'])
        self.assertEqual(state['previous_found']['id'],found['id'])
        record=tracked.read_item(item['id'])
        self.assertEqual(record['notes'],'Keep this')
        self.assertEqual(record['status'],'preparing')
        self.assertEqual(str(record['deadline']),'2030-01-01')
    def test_missing_item(self):
        with self.assertRaises(HTTPException): latest_extraction(999999)

if __name__=='__main__': unittest.main()
