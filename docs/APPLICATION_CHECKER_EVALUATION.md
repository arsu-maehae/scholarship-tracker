# Application Checker evaluation

Reviewed 26 November 2026 using synthetic profiles. Source wording is represented in the automated cases in `backend/tests/test_checker_evaluation.py`; the official links below provide the complete context. Actual results below are asserted by those tests, not eligibility decisions.

| Source requirement and synthetic profile | Expected | Actual | Next step in explanation? |
| --- | --- | --- | --- |
| [EMMIR first degree and related field](https://www.emmir.org/requirements): profile says bachelor's degree | verify | verify | Yes: check the complete condition and evidence. |
| Same EMMIR requirement: degree missing | verify | verify | Yes: add the profile fact and check the source. |
| [EMMIR prior Erasmus Mundus scholarship restriction](https://www.emmir.org/requirements): profile says master's degree, but has no prior-award fact | verify | verify | Yes: check the complete condition; a degree alone does not establish prior funding. |
| [NL Scholarship non-EEA nationality](https://www.studyinnl.org/finances/nl-scholarship): profile says non-EEA | verify | verify | Yes: check the complete condition. The checker does not determine EEA membership. |
| Same NL requirement: nationality missing | verify | verify | Yes: add the profile fact and check the source. |
| [NL institution-specific requirements](https://www.studyinnl.org/finances/nl-scholarship): profile says engineering | verify | verify | Yes: check the institution's complete requirements. |
| Conflicting IELTS and TOEFL requirements: profile says not taken | verify for both | verify for both | Yes: check whether the conditions apply to the same applicant or intake. This is a synthetic conflict, not a claim that these sources conflict. |
| Explicit synthetic IELTS requirement: profile names IELTS only | verify | verify | Yes: check score, test date and accepted alternatives. A test name is not proof of proficiency. |

Limitations: reviewed requirements must be manually mapped to a profile field and exact source wording. The narrow automatic matching rules do not interpret equivalents, exclusions, alternatives, age of qualifications, country groups, grades or score thresholds. Different values of the same profile field are treated as potentially conflicting even when they may be alternatives. Extraction can miss or truncate requirements. Review full official pages and consult the provider; no result is a final eligibility decision. The evaluation does not measure broad real-world accuracy or cover all requirements on either site.
