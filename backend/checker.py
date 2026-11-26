"""User-reviewed source requirements and conservative, non-decisional comparisons."""
import json
import re
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import engine
from models import StudentProfile, ReviewedRequirement, ExtractionAttempt
from tracked import router, get_item

KINDS=('nationality','prior_degree','field','target_intake','language_status')
Kind=Literal['nationality','prior_degree','field','target_intake','language_status']

class ProfileInput(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    nationality: str | None = Field(default=None,max_length=120)
    prior_degree: str | None = Field(default=None,max_length=120)
    field: str | None = Field(default=None,max_length=120)
    target_intake: str | None = Field(default=None,max_length=120)
    language_status: str | None = Field(default=None,max_length=120)

class RequirementInput(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    attempt_id: int
    excerpt: str = Field(min_length=1,max_length=400)
    kind: Kind
    expected: str = Field(min_length=1,max_length=120)

def compare(profile, requirements):
    results=[]
    for requirement in requirements:
        value=(getattr(profile,requirement.kind,None) or '').strip()
        expected=requirement.expected.strip()
        conflicts={r.expected.casefold() for r in requirements if r.kind==requirement.kind}
        if len(conflicts)>1:
            status,reason='verify','Source requirements differ; check whether they apply to the same applicant or intake.'
        elif not value:
            status,reason='verify','Your profile has no value for this requirement.'
        else:
            # Only a narrowly phrased positive requirement can be compared automatically.
            prefix={'nationality':'nationality','prior_degree':'prior degree','field':'field','target_intake':'target intake','language_status':'language test'}[requirement.kind]
            simple=re.fullmatch(rf'\s*(?:Required {prefix}:\s*|Applicants must have {prefix}\s+){re.escape(expected)}\s*\.?\s*',requirement.excerpt,re.I)
            if simple and value.casefold()==expected.casefold():
                status,reason='met','Your recorded answer matches this explicit requirement; confirm evidence with the provider.'
            elif simple and requirement.kind=='language_status' and value.casefold()=='not taken':
                status,reason='prepare','Your profile says the required language test has not been taken.'
            else:
                status,reason='verify',('Your profile mentions the same wording; check the full condition and supporting evidence.' if value.casefold()==expected.casefold() else 'Your profile differs; check the condition and alternatives on the source.')
        results.append({'id':requirement.id,'kind':requirement.kind,'expected':expected,'excerpt':requirement.excerpt,'source_url':requirement.source_url,'status':status,'reason':reason})
    return results

@router.get('/profile/current')
def read_profile():
    with Session(engine) as session:
        row=session.get(StudentProfile,1)
        return {key:getattr(row,key,None) for key in KINDS}

@router.put('/profile/current')
def save_profile(body: ProfileInput):
    with Session(engine) as session,session.begin():
        row=session.get(StudentProfile,1)
        if not row: row=StudentProfile(id=1);session.add(row)
        for key,value in body.model_dump().items(): setattr(row,key,value or None)
        session.flush()
        return {key:getattr(row,key) for key in KINDS}

@router.get('/{item_id}/requirements')
def requirements(item_id:int):
    with Session(engine) as session:
        get_item(session,item_id)
        rows=list(session.scalars(select(ReviewedRequirement).where(ReviewedRequirement.scholarship_id==item_id).order_by(ReviewedRequirement.id)))
        return compare(session.get(StudentProfile,1),rows)

@router.post('/{item_id}/requirements',status_code=201)
def add_requirement(item_id:int,body:RequirementInput):
    with Session(engine) as session,session.begin():
        get_item(session,item_id)
        attempt=session.get(ExtractionAttempt,body.attempt_id)
        if not attempt or attempt.scholarship_id!=item_id or not attempt.source_url or attempt.outcome!='found': raise HTTPException(422,'Choose a sourced extraction.')
        entries=json.loads(attempt.suggestions_json).get('eligibility',[])
        if not any(entry.get('excerpt')==body.excerpt for entry in entries): raise HTTPException(422,'Choose an extracted requirement excerpt.')
        if not body.expected.strip() or body.expected.casefold() not in body.excerpt.casefold(): raise HTTPException(422,'Use wording that appears in the excerpt.')
        row=ReviewedRequirement(scholarship_id=item_id,source_url=attempt.source_url,excerpt=body.excerpt,kind=body.kind,expected=body.expected)
        session.add(row);session.flush()
        return {'id':row.id}

@router.delete('/{item_id}/requirements/{requirement_id}')
def delete_requirement(item_id:int,requirement_id:int):
    with Session(engine) as session,session.begin():
        row=session.get(ReviewedRequirement,requirement_id)
        if not row or row.scholarship_id!=item_id: raise HTTPException(404,'Requirement not found')
        session.delete(row)
        return {'deleted':True}
