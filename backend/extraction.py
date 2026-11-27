"""Deterministic, evidence-only extraction. Never modifies confirmed fields."""
from datetime import datetime
import hashlib
import json
import re
from urllib.parse import urldefrag
from bs4 import BeautifulSoup
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from models import ExtractionAttempt, ChecklistItem
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
    'application_steps': re.compile(r'\b(?:apply online|online application|submit (?:your |the )?application|application portal|upload (?:your |the )?documents|applicants? (?:register|complete|submit))\b', re.I),
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
    'application_steps': re.compile(r'\b(?:application procedure|how to apply)\b', re.I),
}

def financial_kind(heading, body):
    benefit = bool(re.search(r'\b(?:monthly scholarship|scholarship (?:value|amount|benefits|holders? (?:receive|are selected))|scholarship holders? receive|scholarship amounts? to)\b', body, re.I))
    cost = bool(re.search(r'\b(?:participation costs?|tuition|living (?:costs?|expenses)|pay(?:ing|ment)?|travel costs?|fees?)\b', body, re.I))
    if benefit and cost: return 'mixed'
    if benefit: return 'benefit'
    if cost: return 'cost'
    return 'unclear'

def actionable_requirement(category, heading, body):
    if category == 'documents':
        return bool(re.search(r'\b(?:passport|\bcv\b|curriculum vitae|transcripts?|diploma|certificate|statement of purpose|personal statement|reference letters?|letters? of (?:reference|recommendation)|documentation of language|language proficiency|proof of (?:english|language))\b', body, re.I)) and not bool(re.search(r'\b(?:will be (?:compiled|answered)|unable to reply|documents (?:might|may) need|following documents)\b', body, re.I))
    if category == 'application_steps':
        return bool(re.search(r'\b(?:applicants? (?:register|complete|submit)|submit (?:your |the )?application|upload (?:your |the )?documents|apply online)\b', body, re.I)) and not bool(re.search(r'\b(?:receive a confirmation|will be (?:evaluated|notified)|unable to reply)\b', body, re.I))
    return False


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
            if not (special_heading or pattern.search(body if category == 'application_steps' else heading + ' ' + body)):
                continue
            if TEXT_HEADINGS.fullmatch(body.rstrip(':')):
                continue
            if category == 'documents' and re.search(r'\bfollowing documents\b', body, re.I):
                continue
            if category in ('documents','application_steps') and not actionable_requirement(category, heading, body):
                continue
            evidence = {'heading': heading[:150], 'excerpt': body}
            if category == 'funding':
                evidence['financial_kind'] = financial_kind(heading, body)
                if re.search(r'\b(?:following participation costs|three funding options)\b',body,re.I):
                    continue
            if category == 'deadline':
                evidence['date'] = deadline_value(body)
                # Check all matched blocks before suggesting a date, even beyond the display cap.
                deadline_evidence.append({'excerpt': body})
            if evidence not in (candidate[2] for candidate in candidates[category]):
                score = (4 if PRIORITY_HEADINGS[category].search(heading) else 0)
                if category == 'funding' and evidence['financial_kind'] in ('benefit','mixed'):
                    score += 5
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
    data=json.loads(row.suggestions_json)
    if 'funding' in data:
        for entry in data['funding']:
            entry['financial_kind']=financial_kind(entry.get('heading',''),entry.get('excerpt',''))
        data['funding']=[entry for entry in data['funding'] if not re.search(r'\b(?:following participation costs|three funding options)\b',entry.get('excerpt',''),re.I)]
    for category in ('documents','application_steps'):
        if category in data:
            data[category]=[entry for entry in data[category] if actionable_requirement(category,entry.get('heading',''),entry.get('excerpt',''))]
    return {'id':row.id,'input_kind':row.input_kind,'source_url':row.source_url,'outcome':row.outcome,'attempted_at':row.attempted_at,'suggestions':data}

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
            outcome='found' if any(data[k] for k in CATEGORY_PATTERNS) else 'no_details'
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
                if 'documents' in allowed: allowed.add('application_steps')
                attempt['suggestions']={**attempt['suggestions'],
                                        **{category:[] for category in CATEGORY_PATTERNS if category not in allowed}}
                if 'deadline' not in allowed:
                    attempt['suggestions']['proposed_deadline']=None
            page_attempts.append(attempt)
        return {'latest':latest,'previous_found':previous if latest and latest['outcome']!='found' else None,
                'official_pages':official_pages,'page_attempts':page_attempts}

def proposal_key(source, excerpt):
    return hashlib.sha256((source+'\n'+' '.join(excerpt.split()).casefold()).encode('utf-8')).hexdigest()

class AcceptProposal(BaseModel):
    model_config=ConfigDict(extra='forbid')
    attempt_id: int
    category: str = Field(pattern='^(documents|application_steps)$')
    excerpt: str = Field(min_length=1,max_length=2000)
    label: str = Field(min_length=1,max_length=250)

@router.post('/{item_id}/accept-proposal')
def accept_proposal(item_id: int, body: AcceptProposal):
    with Session(engine) as session, session.begin():
        get_item(session,item_id)
        attempt=session.get(ExtractionAttempt,body.attempt_id)
        if not attempt or attempt.scholarship_id!=item_id or attempt.outcome!='found' or not attempt.source_url:
            raise HTTPException(422,'Choose a sourced extraction proposal.')
        entries=json.loads(attempt.suggestions_json).get(body.category,[])
        if not any(entry.get('excerpt')==body.excerpt for entry in entries):
            raise HTTPException(422,'The supporting excerpt was not found.')
        entry=next(entry for entry in entries if entry.get('excerpt')==body.excerpt)
        if not actionable_requirement(body.category,entry.get('heading',''),body.excerpt):
            raise HTTPException(422,'This excerpt is not an actionable applicant task or document.')
        label=body.label.strip()
        if not label: raise HTTPException(422,'Task wording is required.')
        key=proposal_key(attempt.source_url,body.excerpt)
        session.execute(text('select pg_advisory_xact_lock(:namespace, :item)'),{'namespace':123913,'item':item_id})
        existing=session.scalar(select(ChecklistItem).where(ChecklistItem.scholarship_id==item_id,ChecklistItem.proposal_key==key))
        if existing: return {'id':existing.id,'already_accepted':True}
        task=ChecklistItem(scholarship_id=item_id,label=label,proposal_key=key)
        session.add(task); session.flush()
        return {'id':task.id,'already_accepted':False}
