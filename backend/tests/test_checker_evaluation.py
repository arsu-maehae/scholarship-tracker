"""Synthetic-profile evaluation against short excerpts checked 2026-11-26."""
import unittest
from types import SimpleNamespace
from checker import compare

EMMIR='https://www.emmir.org/requirements'
NL='https://www.studyinnl.org/finances/nl-scholarship'

class RealSourceEvaluation(unittest.TestCase):
    def test_reviewed_source_cases(self):
        # Each case records the synthetic fact, expected status, source evidence,
        # and action the explanation should direct the student to take.
        cases=[
            ('EMMIR degree match','prior_degree',"Bachelor's degree",'first degree',"The programme builds upon a first degree such as a Bachelor's degree (or an equivalent qualification) in a field related to migration studies: e.g. Social sciences, History, Cultural studies, Educational sciences, Law, Economics, Development Studies and Journalism.",EMMIR,'verify','check'),
            ('EMMIR degree missing','prior_degree',None,'first degree',"The programme builds upon a first degree such as a Bachelor's degree (or an equivalent qualification) in a field related to migration studies: e.g. Social sciences, History, Cultural studies, Educational sciences, Law, Economics, Development Studies and Journalism.",EMMIR,'verify','add'),
            ('EMMIR prior award','prior_degree','Masters','not eligible','Interested applicants who have already benefitted from an Erasmus Mundus Joint Master (EMJM) scholarship are not eligible to apply for an additional scholarship.',EMMIR,'verify','check'),
            ('NL non-EEA match','nationality','non-EEA','non-EEA','Your nationality is non-EEA.',NL,'verify','check'),
            ('NL non-EEA missing','nationality',None,'non-EEA','Your nationality is non-EEA.',NL,'verify','add'),
            ('NL institution requirements','field','Engineering','specific requirements','You meet the specific requirements of the institution of your choice.',NL,'verify','check'),
        ]
        for name,kind,value,expected,excerpt,source,status,action in cases:
            with self.subTest(case=name):
                row=SimpleNamespace(id=1,kind=kind,expected=expected,excerpt=excerpt,source_url=source)
                result=compare(SimpleNamespace(**{kind:value}),[row])[0]
                self.assertEqual(result['status'],status)
                self.assertIn(action,result['reason'].casefold())
                self.assertEqual(result['excerpt'],excerpt)
                self.assertEqual(result['source_url'],source)

    def test_conflicting_sources_require_manual_review(self):
        rows=[SimpleNamespace(id=i,kind='language_status',expected=value,excerpt='Required language test: '+value+'.',source_url=url) for i,value,url in [(1,'IELTS',EMMIR),(2,'TOEFL',NL)]]
        results=compare(SimpleNamespace(language_status='not taken'),rows)
        self.assertEqual([result['status'] for result in results],['verify','verify'])
        self.assertTrue(all('check' in result['reason'].casefold() for result in results))
