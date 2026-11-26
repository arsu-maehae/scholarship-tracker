"""Deterministic, evidence-only extraction. Never modifies confirmed fields."""
from datetime import datetime
import json
import re
from urllib.parse import urldefrag
from bs4 import BeautifulSoup
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from models import ExtractionAttempt
from database import engine
from official_page import FetchError, fetch_official_html, official_pages_for, source_is_allowed_for_saved
from tracked import router, get_item, get_source_pages

class ExtractInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    mode: str = Field(pattern='^(page|text)$')
    text: str | None = Field(default=None,max_length=20000)
    source_url: str | None = Field(default=None,max_length=2048)
    @model_validator(mode='after')
    def valid_text(self):
        if self.mode=='text' and (not self.text or not self.text.strip()): raise ValueError('Paste public page text')
        if self.mode=='text' and self.source_url is not None: raise ValueError('Pasted text cannot specify a source URL')
        return self

CATEGORY_PATTERNS = {
    'deadline': re.compile(
        r'\b(?:deadlines?|closing date|applications? close[sd]?|'
        r'apply by|submit by|due by|no later than)\b', re.I
    ),
    'funding': re.compile(
        r'\b(?:funding|tuition|stipends?|allowances?|participation costs?|'
        r'monthly scholarship|scholarship holders?|financial support|'
        r'(?:health insurance|registration|student service) fees?|'
        r'scholarship (?:amount|value|covers|coverage|benefits))\b', re.I
    ),
    'eligibility': re.compile(
        r'\b(?:eligib\w*|qualifications?|nationality|citizens?|'
        r'applicants? must|who can apply|entry requirements)\b', re.I
    ),
    'documents': re.compile(
        r'\b(?:documents?|transcripts?|degree diplomas?|reference letters?|'
        r'letters? of (?:reference|recommendation)|passport|'
        r'curriculum vitae|CV|personal statement|statement of purpose|'
        r'(?:proof|documentation) of (?:english|language)|language proficiency)\b', re.I
    ),
}

TEXT_HEADINGS = re.compile(
    r'(?:(?:application |scholarship )?deadlines?|closing date|'
    r'(?:scholarship )?(?:funding|value|amount|benefits)|what it covers|'
    r'eligibility(?: criteria| requirements)?|who can apply|'
    r'(?:required |supporting |application )?documents|what you need to submit)', re.I
)
MONTHS = (
    r'Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
    r'Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?'
)
NAMED_DATE = re.compile(
    rf'\b(?:\d{{1,2}}\s+(?:{MONTHS})\.?\s+\d{{4}}|'
    rf'(?:{MONTHS})\.?\s+\d{{1,2}},?\s+\d{{4}})\b', re.I
)
ISO_DATE = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')
MONTH_NAME = re.compile(rf'\b(?:{MONTHS})\b', re.I)
AMBIGUOUS_DATE = re.compile(
    r'\b(?:or|between|depending|alternatively|extensions?|opens?|opening|'
    r'closed|extended|estimated|tentative|expected|previous|last year|'
    r'to be (?:announced|confirmed))\b|\b\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}\b', re.I
)
EXTRA_FUNDING_HEADINGS = {'benefits', 'value', 'amount'}
HEADING_TAGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'dt'}
PRIORITY_HEADINGS = {
    'deadline': re.compile(r'\b(?:application deadlines?|application timeline)\b', re.I),
    'funding': re.compile(r'\b(?:funding options?|erasmus\+? scholarship holders?|participation costs?)\b', re.I),
    'eligibility': re.compile(r'\b(?:entry requirements?|language requirements?|selection criteria)\b', re.I),
    'documents': re.compile(r'\brequired documentation\b', re.I),
}


def html_blocks(html):
    soup = BeautifulSoup(html, 'html.parser')
    for element in soup(['script', 'style', 'nav', 'footer', 'noscript', 'form', 'svg']):
        element.decompose()
    root = soup.find('main') or soup.find('article') or soup.body or soup
    blocks = []
    heading = ''
    for element in root.find_all([*HEADING_TAGS, 'p', 'li', 'tr', 'dd']):
        if element.name == 'p' and element.find_parent(['li', 'tr', 'dd']):
            continue
        content = ' '.join(element.stripped_strings)
        if not content:
            continue
        if element.name in HEADING_TAGS:
            heading = content[:150]
            if any(pattern.search(content) for pattern in CATEGORY_PATTERNS.values()):
                # Some pages put the value directly in a heading.
                blocks.append(('', content))
        elif len(content) <= 2000:
            blocks.append((heading, content))
        if len(blocks) >= 300:
            break
    return blocks


def text_blocks(value):
    blocks = []
    heading = ''
    for line in value.splitlines():
        body = ' '.join(line.split())
        if not body:
            continue
        label = body.rstrip(':').strip()
        if TEXT_HEADINGS.fullmatch(label):
            heading = label
        elif body.endswith(':') and len(body) <= 100:
            heading = ''
        else:
            blocks.append((heading, body))
            if len(blocks) >= 300:
                break
    return blocks


def deadline_candidate(entries):
    dates = set()
    for entry in entries:
        excerpt = entry['excerpt']
        matches = [*NAMED_DATE.finditer(excerpt), *ISO_DATE.finditer(excerpt)]
        residual = excerpt
        for match in reversed(sorted(matches, key=lambda match: match.start())):
            raw = match.group().replace('.', '').replace(',', '')
            if raw[0].isalpha() or ' ' in raw:
                raw = MONTH_NAME.sub(lambda month: month.group()[:3], raw)
            for date_format in ('%d %b %Y', '%b %d %Y', '%Y-%m-%d'):
                try:
                    dates.add(datetime.strptime(raw, date_format).date().isoformat())
                    break
                except ValueError:
                    continue
            else:
                return None
            residual = residual[:match.start()] + ' ' + residual[match.end():]
        if (
            MONTH_NAME.search(residual)
            or AMBIGUOUS_DATE.search(residual)
            or not matches
        ):
            return None
    return next(iter(dates)) if len(dates) == 1 else None


def deadline_value(excerpt):
    """Return one exact date for an explicitly selected excerpt, never for the whole page."""
    matches = [*NAMED_DATE.finditer(excerpt), *ISO_DATE.finditer(excerpt)]
    values = set()
    for match in matches:
        raw = match.group().replace('.', '').replace(',', '')
        if raw[0].isalpha() or ' ' in raw:
            raw = MONTH_NAME.sub(lambda month: month.group()[:3], raw)
        for date_format in ('%d %b %Y', '%b %d %Y', '%Y-%m-%d'):
            try:
                values.add(datetime.strptime(raw, date_format).date().isoformat())
                break
            except ValueError:
                continue
        else:
            return None
    return next(iter(values)) if len(values) == 1 else None


def suggest(blocks):
    suggestions = {key: [] for key in CATEGORY_PATTERNS}
    candidates = {key: [] for key in CATEGORY_PATTERNS}
    deadline_evidence = []
    for position, (heading, body) in enumerate(blocks):
        if (not re.search(r'[\w\d]', body, re.UNICODE)
                or body.lower().startswith('home >')
                or body.casefold() == heading.casefold()):
            continue
        for category, pattern in CATEGORY_PATTERNS.items():
            special_heading = category == 'funding' and heading.lower() in EXTRA_FUNDING_HEADINGS
            if not (special_heading or pattern.search(heading + ' ' + body)):
                continue
            if TEXT_HEADINGS.fullmatch(body.rstrip(':')):
                continue
            if category == 'documents' and re.search(r'\bfollowing documents\b', body, re.I):
                continue
            evidence = {'heading': heading[:150], 'excerpt': body[:400]}
            if category == 'deadline':
                evidence['date'] = deadline_value(body)
                # Check all matched blocks before suggesting a date, even beyond the display cap.
                deadline_evidence.append({'excerpt': body})
            if evidence not in (candidate[2] for candidate in candidates[category]):
                score = (4 if PRIORITY_HEADINGS[category].search(heading) else 0)
                score += 2 if pattern.search(body) else 0
                score += 1 if pattern.search(heading) or special_heading else 0
                if category == 'deadline' and (NAMED_DATE.search(body) or ISO_DATE.search(body)):
                    score += 2
                candidates[category].append((-score, position, evidence))
    for category in CATEGORY_PATTERNS:
        suggestions[category] = [entry for _, _, entry in sorted(candidates[category])[:5]]
    proposed = deadline_candidate(deadline_evidence)
    suggestions['proposed_deadline'] = (
        proposed if proposed and deadline_candidate(suggestions['deadline']) == proposed else None
    )
    return suggestions


def attempt_dict(row):
    return {'id':row.id,'input_kind':row.input_kind,'source_url':row.source_url,'outcome':row.outcome,'attempted_at':row.attempted_at,'suggestions':json.loads(row.suggestions_json)}

@router.post('/{item_id}/extract')
def extract(item_id: int, body: ExtractInput):
    with Session(engine) as session, session.begin():
        item=get_item(session,item_id)
        additional_pages=get_source_pages(session,item_id)
        if not session.scalar(text('select pg_try_advisory_xact_lock(:namespace, :item)'),{'namespace':123912,'item':item_id}):
            raise HTTPException(429,'An extraction is already running for this scholarship.')
        saved_source=urldefrag(item.source_url)[0]
        source=urldefrag(body.source_url or saved_source)[0] if body.mode=='page' else None
        if source and not source_is_allowed_for_saved(saved_source, source, additional_pages):
            raise HTTPException(422, 'Choose the saved page or one of its added official source pages.')
        try:
            blocks=html_blocks(fetch_official_html(source)) if body.mode=='page' else text_blocks(body.text or '')
            data=suggest(blocks)
            outcome='found' if any(data[k] for k in ('deadline','funding','eligibility','documents')) else 'no_details'
            if outcome=='no_details':
                data['message']='The page was fetched, but no supported details were found. Paste visible public text if the page requires JavaScript.'
        except FetchError as error:
            outcome='unsupported' if 'Only HTML pages' in str(error) else 'failed'
            data={'message':str(error)}
        row=ExtractionAttempt(scholarship_id=item_id,input_kind=body.mode,source_url=source,outcome=outcome,suggestions_json=json.dumps(data))
        session.add(row); session.flush(); return attempt_dict(row)

@router.get('/{item_id}/extraction')
def latest_extraction(item_id: int):
    with Session(engine) as session:
        item=get_item(session,item_id)
        additional_pages=get_source_pages(session,item_id)
        rows=session.scalars(select(ExtractionAttempt).where(ExtractionAttempt.scholarship_id==item_id).order_by(ExtractionAttempt.id.desc())).all()
        latest=attempt_dict(rows[0]) if rows else None
        previous=next((attempt_dict(row) for row in rows[1:] if row.outcome=='found'),None)
        official_pages=official_pages_for(item.source_url,additional_pages)
        latest_found_by_source={}
        for row in rows:
            if row.outcome=='found' and row.source_url and row.source_url not in latest_found_by_source:
                latest_found_by_source[row.source_url]=attempt_dict(row)
        page_attempts=[]
        for page in official_pages:
            if page['url'] not in latest_found_by_source:
                continue
            attempt=latest_found_by_source[page['url']]
            if page['categories'] is not None:
                allowed=set(page['categories'])
                attempt['suggestions']={**attempt['suggestions'],
                                        **{category:[] for category in CATEGORY_PATTERNS if category not in allowed}}
                if 'deadline' not in allowed:
                    attempt['suggestions']['proposed_deadline']=None
            page_attempts.append(attempt)
        return {'latest':latest,'previous_found':previous if latest and latest['outcome']!='found' else None,
                'official_pages':official_pages,'page_attempts':page_attempts}
