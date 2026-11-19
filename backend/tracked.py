"""URL-first local scholarship tracker; saving never fetches a page."""
from datetime import date, datetime, timezone
import ipaddress
import re
from typing import Literal
from urllib.parse import urlsplit, urlunsplit
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from database import engine
from models import TrackedScholarship, ChecklistItem
from local_guard import local_only

router = APIRouter(prefix='/api/tracked-scholarships', dependencies=[Depends(local_only)])
Status = Literal['saved','preparing','submitted','accepted','rejected']

def normalize_url(value: str) -> str:
    if not value or len(value)>2048 or any(c.isspace() or ord(c)<32 for c in value):
        raise ValueError('Enter a valid public HTTP or HTTPS URL')
    try:
        u=urlsplit(value)
        host=u.hostname
        if u.scheme.lower() not in ('http','https') or not host or u.username is not None or u.password is not None:
            raise ValueError()
        port=u.port
        try:
            address=ipaddress.ip_address(host)
        except ValueError:
            ascii_host=host.encode('idna').decode('ascii').lower().rstrip('.')
            if len(ascii_host)>253 or '.' not in ascii_host or ascii_host.endswith(('.local','.localhost','.internal')) or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', part) for part in ascii_host.split('.')):
                raise ValueError()
            host=ascii_host
        else:
            if not address.is_global: raise ValueError()
            host=address.compressed
            if address.version==6: host='['+host+']'
        host=host.lower()
        if port and port != (443 if u.scheme.lower()=='https' else 80): host += ':'+str(port)
        return urlunsplit((u.scheme.lower(),host,u.path,u.query,''))
    except (ValueError, UnicodeError):
        raise ValueError('Enter a valid public HTTP or HTTPS URL without credentials') from None

class SaveLink(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_url: str = Field(min_length=1,max_length=2048)
    @field_validator('source_url')
    @classmethod
    def valid_url(cls, v): normalize_url(v); return v

class EditScholarship(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str | None = Field(default=None,max_length=250)
    provider: str | None = Field(default=None,max_length=250)
    intake: str | None = Field(default=None,max_length=250)
    deadline: date | None = None
    funding: str | None = Field(default=None,max_length=10000)
    eligibility: str | None = Field(default=None,max_length=10000)
    notes: str | None = Field(default=None,max_length=20000)
    status: Status | None = None
    archived: bool | None = None

class ChecklistInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    label: str = Field(min_length=1,max_length=250)
    completed: bool = False
    @field_validator('label')
    @classmethod
    def valid_label(cls,v):
        if not v.strip(): raise ValueError('Task label is required')
        return v.strip()

class ChecklistEdit(BaseModel):
    model_config = ConfigDict(extra='forbid')
    label: str | None = Field(default=None,min_length=1,max_length=250)
    completed: bool | None = None
    @field_validator('label')
    @classmethod
    def valid_label(cls,v):
        if v is not None and not v.strip(): raise ValueError('Task label is required')
        return v.strip() if v else v

def get_item(session, item_id):
    row=session.get(TrackedScholarship,item_id)
    if not row: raise HTTPException(404,'Scholarship not found')
    return row

def serialize(session,row):
    result={c.name:getattr(row,c.name) for c in row.__table__.columns}
    result['checklist']=[{c.name:getattr(task,c.name) for c in task.__table__.columns} for task in session.scalars(select(ChecklistItem).where(ChecklistItem.scholarship_id==row.id).order_by(ChecklistItem.id))]
    return result

@router.get('')
def list_items(q: str='', status: str='', archived: bool=False):
    if len(q)>100: raise HTTPException(422,'Search too long')
    if status and status not in ('saved','preparing','submitted','accepted','rejected'): raise HTTPException(422,'Invalid status')
    with Session(engine) as session:
        query=select(TrackedScholarship).where(TrackedScholarship.archived_at.is_not(None) if archived else TrackedScholarship.archived_at.is_(None))
        if q.strip():
            term=q.strip().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            query=query.where(or_(TrackedScholarship.title.ilike('%'+term+'%',escape='\\'),TrackedScholarship.provider.ilike('%'+term+'%',escape='\\')))
        if status: query=query.where(TrackedScholarship.status==status)
        return [serialize(session,row) for row in session.scalars(query.order_by(TrackedScholarship.id.desc()))]

@router.post('',status_code=201)
def save_link(body: SaveLink):
    key=normalize_url(body.source_url)
    with Session(engine) as session:
        try:
            row=TrackedScholarship(source_url=body.source_url,url_key=key)
            session.add(row); session.flush(); result=serialize(session,row); session.commit(); return result
        except IntegrityError:
            session.rollback()
            existing=session.scalar(select(TrackedScholarship).where(TrackedScholarship.url_key==key))
            if existing: raise HTTPException(409,{'message':'This link is already saved.','existing_id':existing.id,'archived':existing.archived_at is not None}) from None
            raise

@router.get('/{item_id}')
def read_item(item_id: int):
    with Session(engine) as session: return serialize(session,get_item(session,item_id))

@router.patch('/{item_id}')
def edit_item(item_id: int, body: EditScholarship):
    changes=body.model_dump(exclude_unset=True)
    if 'status' in changes and changes['status'] is None: raise HTTPException(422,'Status is required')
    with Session(engine) as session, session.begin():
        row=get_item(session,item_id)
        for key,value in changes.items():
            if key=='archived':
                if value is not None: row.archived_at=datetime.now(timezone.utc) if value else None
            else: setattr(row,key,value)
        row.updated_at=datetime.now(timezone.utc); session.flush(); return serialize(session,row)

@router.post('/{item_id}/checklist',status_code=201)
def add_checklist(item_id: int, body: ChecklistInput):
    with Session(engine) as session, session.begin():
        get_item(session,item_id); task=ChecklistItem(scholarship_id=item_id,**body.model_dump()); session.add(task); session.flush()
        return {c.name:getattr(task,c.name) for c in task.__table__.columns}

@router.patch('/{item_id}/checklist/{task_id}')
def edit_checklist(item_id: int, task_id: int, body: ChecklistEdit):
    with Session(engine) as session, session.begin():
        task=session.get(ChecklistItem,task_id)
        if not task or task.scholarship_id!=item_id: raise HTTPException(404,'Task not found')
        for key,value in body.model_dump(exclude_unset=True).items():
            if value is None: raise HTTPException(422,'Task fields cannot be null')
            setattr(task,key,value)
        session.flush(); return {c.name:getattr(task,c.name) for c in task.__table__.columns}

@router.delete('/{item_id}/checklist/{task_id}')
def delete_checklist(item_id: int, task_id: int):
    with Session(engine) as session, session.begin():
        task=session.get(ChecklistItem,task_id)
        if not task or task.scholarship_id!=item_id: raise HTTPException(404,'Task not found')
        session.delete(task); return {'deleted':True}
