import os
import unittest
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch
import checker
import tracked
from extraction import ExtractInput, extract

def requirement(kind,expected,excerpt):
    return SimpleNamespace(id=1,kind=kind,expected=expected,excerpt=excerpt,source_url='https://example.org/requirements')

class ComparisonTests(unittest.TestCase):
    def test_explicit_match_and_missing_or_qualified_text(self):
        rule=requirement('nationality','Thai','Required nationality: Thai.')
        self.assertEqual(checker.compare(SimpleNamespace(nationality='Thai'),[rule])[0]['status'],'met')
        self.assertEqual(checker.compare(SimpleNamespace(nationality=None),[rule])[0]['status'],'verify')
        rule.excerpt='Thai applicants may apply unless other conditions apply.'
        self.assertEqual(checker.compare(SimpleNamespace(nationality='Thai'),[rule])[0]['status'],'verify')
    def test_language_preparation_and_conflict(self):
        rule=requirement('language_status','IELTS','Required language test: IELTS.')
        self.assertEqual(checker.compare(SimpleNamespace(language_status='not taken'),[rule])[0]['status'],'prepare')
        result=checker.compare(SimpleNamespace(language_status='IELTS'),[rule])[0]
        self.assertEqual(result['status'],'verify')
        self.assertIn('score',result['reason'])
        other=requirement('language_status','TOEFL','Required language test: TOEFL.')
        self.assertEqual([r['status'] for r in checker.compare(SimpleNamespace(language_status='IELTS'),[rule,other])],['verify','verify'])

@unittest.skipUnless(os.environ.get('POSTGRES_DB')=='scholarship_tracker_test','requires disposable database')
class CheckerDatabaseTests(unittest.TestCase):
    def test_profile_and_sourced_requirement_persist(self):
        item=tracked.save_link(tracked.SaveLink(source_url='https://example.org/'+uuid4().hex))
        with patch('extraction.fetch_official_html',return_value='<main><h2>Eligibility</h2><p>Applicants must have nationality Thai.</p></main>'):
            attempt=extract(item['id'],ExtractInput(mode='page'))
        excerpt=attempt['suggestions']['eligibility'][0]['excerpt']
        checker.save_profile(checker.ProfileInput(nationality='Thai'))
        checker.add_requirement(item['id'],checker.RequirementInput(attempt_id=attempt['id'],excerpt=excerpt,kind='nationality',expected='Thai'))
        self.assertEqual(checker.read_profile()['nationality'],'Thai')
        result=checker.requirements(item['id'])[0]
        self.assertEqual(result['status'],'met')
        self.assertEqual(result['source_url'],item['source_url'])
        self.assertIsNone(tracked.read_item(item['id'])['deadline'])
