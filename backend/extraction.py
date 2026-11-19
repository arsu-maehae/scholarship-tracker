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
from official_page import FetchError, fetch_official_html
from tracked import router, get_item

class ExtractInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    mode: str = Field(pattern='^(page|text)$')
    text: str | None = Field(default=None,max_length=20000)
    @model_validator(mode='after')
    def valid_text(self):
        if self.mode=='text' and (not self.text or not self.text.strip()): raise ValueError('Paste public page text')
        return self

def html_blocks(html):
    soup=BeautifulSoup(html,'html.parser')
    for element in soup(['script','style','nav','header','footer','noscript','form','svg']): element.decompose()
    root=soup.find('main') or soup.find('article') or soup.body or soup
    blocks=[]; heading=''
    for element in root.find_all(['h1','h2','h3','h4','p','li','tr']):
        content=' '.join(element.stripped_strings)
        if not content: continue
        if element.name.startswith('h'): heading=content[:150]; continue
        if len(content)<=2000: blocks.append((heading,content))
        if len(blocks)>=300: break
    return blocks

def text_blocks(value):
    return [('', ' '.join(line.split())) for line in value.splitlines() if line.strip()][:300]

def suggest(blocks):
    categories={'deadline':r'\b(deadline|closing date|closes|apply by|applications close)\b',
                'funding':r'\b(scholarship|tuition|stipend|funding|grant|allowance)\b',
                'eligibility':r'\b(eligib|qualif|nationality|applicants? must|requirements?)',
                'documents':r'\b(documents?|transcripts?|reference letters?|recommendation|passport|curriculum vitae)\b'}
    suggestions={key:[] for key in categories}
    for heading,body in blocks:
        for key,pattern in categories.items():
            if re.search(pattern,heading+' '+body,re.I) and len(suggestions[key])<5:
                suggestions[key].append({'heading':heading[:150],'excerpt':body[:400]})
    dates=set()
    for entry in suggestions['deadline']:
        for match in re.finditer(r'\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b',entry['excerpt'],re.I):
            try: dates.add(datetime.strptime(match.group(1),'%d %B %Y').date().isoformat())
            except ValueError: pass
    suggestions['proposed_deadline']=next(iter(dates)) if len(dates)==1 and len(suggestions['deadline'])==1 else None
    return suggestions

def attempt_dict(row):
    return {'id':row.id,'input_kind':row.input_kind,'source_url':row.source_url,'outcome':row.outcome,'attempted_at':row.attempted_at,'suggestions':json.loads(row.suggestions_json)}

@router.post('/{item_id}/extract')
def extract(item_id: int, body: ExtractInput):
    with Session(engine) as session, session.begin():
        item=get_item(session,item_id)
        if not session.scalar(text('select pg_try_advisory_xact_lock(:namespace, :item)'),{'namespace':123912,'item':item_id}):
            raise HTTPException(429,'An extraction is already running for this scholarship.')
        source=urldefrag(item.source_url)[0] if body.mode=='page' else None
        try:
            blocks=html_blocks(fetch_official_html(source)) if body.mode=='page' else text_blocks(body.text or '')
            data=suggest(blocks)
            outcome='found' if any(data[k] for k in ('deadline','funding','eligibility','documents')) else 'no_details'
        except FetchError as error:
            outcome='unsupported' if 'supported HTTPS host list' in str(error) else 'failed'
            data={'message':str(error)}
        row=ExtractionAttempt(scholarship_id=item_id,input_kind=body.mode,source_url=source,outcome=outcome,suggestions_json=json.dumps(data))
        session.add(row); session.flush(); return attempt_dict(row)

@router.get('/{item_id}/extraction')
def latest_extraction(item_id: int):
    with Session(engine) as session:
        get_item(session,item_id)
        rows=session.scalars(select(ExtractionAttempt).where(ExtractionAttempt.scholarship_id==item_id).order_by(ExtractionAttempt.id.desc())).all()
        latest=attempt_dict(rows[0]) if rows else None
        previous=next((attempt_dict(row) for row in rows[1:] if row.outcome=='found'),None)
        return {'latest':latest,'previous_found':previous if latest and latest['outcome']!='found' else None}
