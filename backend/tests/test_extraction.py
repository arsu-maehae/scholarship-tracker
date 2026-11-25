import os
import unittest
from uuid import uuid4
from email.message import Message
from unittest.mock import patch
from fastapi import HTTPException
from extraction import ExtractInput, extract, html_blocks, latest_extraction, suggest, text_blocks
from official_page import FetchError, fetch_official_html, official_pages_for, source_is_allowed_for_saved
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
        result=suggest(text_blocks('Deadline 12 January 2030 or 15 February'))
        self.assertIsNone(result['proposed_deadline'])
    def test_missing_and_unapproved_host(self):
        self.assertFalse(suggest(text_blocks('No details here'))['funding'])
        with self.assertRaises(FetchError): fetch_official_html('https://example.com/')
    def test_emmir_uses_only_verified_official_detail_pages(self):
        saved='https://www.emmir.org/'
        pages=official_pages_for(saved)
        self.assertEqual([page['url'] for page in pages],[
            'https://www.emmir.org/application-procedures',
            'https://www.emmir.org/requirements',
            'https://www.emmir.org/cost-and-funding',
        ])
        self.assertTrue(source_is_allowed_for_saved(saved,pages[0]['url']))
        self.assertFalse(source_is_allowed_for_saved(saved,'https://www.emmir.org/post/unverified'))
        self.assertFalse(source_is_allowed_for_saved(saved,'https://example.com/requirements'))
    def test_html_header_and_definition_list_keep_evidence(self):
        page = """<main>
          <header><h2>Application deadline: January 15, 2030</h2></header>
          <dl><dt>Scholarship value</dt><dd>EUR 1,400 per month.</dd></dl>
          <h3>Who can apply</h3><p>Open to graduates in engineering.</p>
          <h3>Required documents</h3><ul><li><p>Two signed reference letters.</p></li></ul>
        </main>"""
        result = suggest(html_blocks(page))
        self.assertEqual(result['proposed_deadline'], '2030-01-15')
        self.assertEqual(result['funding'][0]['excerpt'], 'EUR 1,400 per month.')
        self.assertEqual(result['eligibility'][0]['excerpt'], 'Open to graduates in engineering.')
        self.assertEqual(len(result['documents']), 1)
        self.assertEqual(result['documents'][0]['excerpt'], 'Two signed reference letters.')

    def test_emmir_style_pages_prioritise_verified_detail_sections(self):
        page = """<main>
          <h1>Costs &amp; Funding</h1><p>Home &gt; Applications &gt; Costs and Funding</p>
          <h2>Funding options</h2>
          <h3>Erasmus+ Scholarship Holders</h3>
          <p>Scholarship holders receive a monthly scholarship of 1400€ for 24 months, and health insurance and university fees are covered.</p>
          <h2>Required documentation for the online application</h2>
          <p>The applicant must upload the following documents.</p>
          <ul><li>Clear copy of a valid passport</li><li>CV</li><li>Statement of Purpose</li>
          <li>First university degree diploma and transcript</li><li>Documentation of language proficiency</li></ul>
          <h2>Application deadlines</h2>
          <p>20 December 2026 for scholarship applicants</p>
          <p>15 July 2027 for fee-paying applicants</p>
        </main>"""
        result = suggest(html_blocks(page))
        self.assertIn('1400€', result['funding'][0]['excerpt'])
        self.assertEqual([entry['excerpt'] for entry in result['documents']], [
            'Clear copy of a valid passport',
            'CV',
            'Statement of Purpose',
            'First university degree diploma and transcript',
            'Documentation of language proficiency',
        ])
        self.assertIsNone(result['proposed_deadline'])

    def test_pasted_headings_include_unlabelled_values(self):
        pasted = """Application deadline:

2030-01-15
Funding:
EUR 1,400 per month.
Supporting documents:
A degree certificate and two references.
"""
        result = suggest(text_blocks(pasted))
        self.assertEqual(result['proposed_deadline'], '2030-01-15')
        self.assertEqual(result['funding'][0]['excerpt'], 'EUR 1,400 per month.')
        self.assertEqual(result['documents'][0]['excerpt'], 'A degree certificate and two references.')

    def test_generic_scholarship_copy_is_not_funding_evidence(self):
        result = suggest(text_blocks('Explore our scholarships. This scholarship welcomes new students.'))
        self.assertEqual(result['funding'], [])

    def test_deadline_evidence_keeps_unconfirmed_dates_unresolved(self):
        for excerpt in (
            'Deadline expected to be 15 Jan 2030',
            'Deadline 15 Jan 2030 or 02/03/2030',
            'Deadline 29 Feb 2030',
        ):
            with self.subTest(excerpt=excerpt):
                self.assertIsNone(suggest(text_blocks(excerpt))['proposed_deadline'])
        result = suggest(text_blocks('Deadline: 15 Jan 2030'))
        self.assertEqual(result['proposed_deadline'], '2030-01-15')

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
    def test_emmir_detail_attempts_are_returned_by_official_source(self):
        item=tracked.save_link(tracked.SaveLink(source_url='https://www.emmir.org/'))
        pages={
            'https://www.emmir.org/application-procedures': '<main><h2>Application deadlines</h2><p>20 December 2026 for scholarship applicants</p><p>15 July 2027 for fee-paying applicants</p><h2>Required documentation</h2><p>CV</p></main>',
            'https://www.emmir.org/requirements': '<main><h2>Entry requirements</h2><p>Applicants must hold a relevant first degree.</p></main>',
            'https://www.emmir.org/cost-and-funding': '<main><h2>Funding options</h2><p>Scholarship holders receive a monthly scholarship of EUR 1,400.</p></main>',
        }
        with patch('extraction.fetch_official_html',side_effect=lambda url: pages[url]):
            for source_url in pages:
                self.assertEqual(extract(item['id'],ExtractInput(mode='page',source_url=source_url))['outcome'],'found')
        state=latest_extraction(item['id'])
        self.assertEqual([attempt['source_url'] for attempt in state['page_attempts']],list(pages))
        self.assertTrue(state['page_attempts'][0]['suggestions']['deadline'])
        self.assertTrue(state['page_attempts'][0]['suggestions']['documents'])
        self.assertEqual(state['page_attempts'][0]['suggestions']['funding'],[])
        self.assertTrue(state['page_attempts'][1]['suggestions']['eligibility'])
        self.assertEqual(state['page_attempts'][1]['suggestions']['deadline'],[])
        self.assertTrue(state['page_attempts'][2]['suggestions']['funding'])
        self.assertEqual(state['page_attempts'][2]['suggestions']['eligibility'],[])
        self.assertIsNone(tracked.read_item(item['id'])['deadline'])

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
