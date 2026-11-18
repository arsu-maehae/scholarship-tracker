"""Local personal application tracker API."""
from datetime import date
from typing import Literal
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from database import engine
from models import Application, ApplicationDeadline, ApplicationTask

router = APIRouter(prefix='/api/applications')
Status = Literal['researching','preparing','submitted','result_received','withdrawn']


def local_only(request: Request):
    if (request.client is None or request.client.host not in ('127.0.0.1','::1')
        or request.headers.get('host') not in ('127.0.0.1:8000','localhost:8000','[::1]:8000')):
        raise HTTPException(403, 'Local access only')
    if request.method not in ('GET','HEAD') and (request.headers.get('origin') not in ('http://127.0.0.1:5173','http://localhost:5173') or request.headers.get('x-requested-with') != 'ScholarshipTracker'):
        raise HTTPException(403, 'Changes must come from the local tracker')


class ApplicationInput(BaseModel):
    title: str = Field(min_length=1, max_length=250)
    provider: str | None = Field(default=None,max_length=250)
    source_url: str | None = Field(default=None,max_length=2048)
    cycle: str | None = Field(default=None,max_length=100)
    status: Status = 'researching'
    notes: str | None = Field(default=None,max_length=20000)
    next_action: str | None = Field(default=None,max_length=2000)
    archived: bool = False
    submission_date: date | None = None
    interview_date: date | None = None
    outcome: str | None = Field(default=None,max_length=100)

    @field_validator('title')
    @classmethod
    def valid_title(cls, v):
        if not v.strip(): raise ValueError('Title is required')
        return v.strip()

    @field_validator('source_url')
    @classmethod
    def valid_url(cls, v):
        if not v: return None
        try:
            parsed=urlsplit(v)
            if parsed.scheme not in ('https','http') or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in v): raise ValueError()
            parsed.port
        except ValueError: raise ValueError('Enter an absolute HTTP or HTTPS URL') from None
        return v


class TaskInput(BaseModel):
    title: str = Field(min_length=1,max_length=250)
    due_date: date | None = None
    completed: bool = False
    @field_validator('title')
    @classmethod
    def valid_title(cls, v):
        if not v.strip(): raise ValueError('Task title is required')
        return v.strip()


class DeadlineInput(BaseModel):
    label: str = Field(min_length=1,max_length=250)
    kind: Literal['official','personal']
    due_date: date | None = None
    due_time: str | None = Field(default=None,max_length=20)
    timezone: str | None = Field(default=None,max_length=100)
    @field_validator('label')
    @classmethod
    def valid_label(cls,v):
        if not v.strip(): raise ValueError('Deadline label is required')
        return v.strip()


def as_dict(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def get_application(session, app_id):
    app = session.get(Application, app_id)
    if not app: raise HTTPException(404, 'Application not found')
    return app


def duplicate(session, body, exclude=None):
    if not body.source_url or not body.cycle: return
    statement=select(Application).where(Application.source_url == body.source_url, Application.cycle == body.cycle)
    if exclude is not None: statement=statement.where(Application.id != exclude)
    existing=session.scalar(statement)
    if existing: raise HTTPException(409, {'message':'An application for this source and cycle already exists.', 'existing_id':existing.id})


@router.get('', dependencies=[Depends(local_only)])
def list_applications(q: str = '', status: str = '', archived: bool = False):
    if len(q)>100: raise HTTPException(422, 'Search too long')
    if status and status not in ('researching','preparing','submitted','result_received','withdrawn'): raise HTTPException(422, 'Invalid status')
    with Session(engine) as session:
        stmt=select(Application).where(Application.archived == archived)
        if q.strip():
            term=q.strip().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            stmt=stmt.where(or_(Application.title.ilike(f'%{term}%',escape='\\'),Application.provider.ilike(f'%{term}%',escape='\\')))
        if status: stmt=stmt.where(Application.status == status)
        items=[]
        for app in session.scalars(stmt.order_by(Application.id.desc())):
            item=as_dict(app)
            deadlines=session.scalars(select(ApplicationDeadline).where(ApplicationDeadline.application_id==app.id).order_by(ApplicationDeadline.due_date.asc().nullslast())).all()
            item['deadlines']=[as_dict(x) for x in deadlines]
            item['tasks']=[as_dict(x) for x in session.scalars(select(ApplicationTask).where(ApplicationTask.application_id==app.id).order_by(ApplicationTask.id))]
            items.append(item)
        return items


@router.post('', dependencies=[Depends(local_only)], status_code=201)
def create_application(body: ApplicationInput):
    with Session(engine) as session, session.begin():
        duplicate(session,body)
        app=Application(**body.model_dump())
        session.add(app); session.flush()
        return as_dict(app)


@router.put('/{app_id}', dependencies=[Depends(local_only)])
def update_application(app_id: int, body: ApplicationInput):
    with Session(engine) as session, session.begin():
        app=get_application(session,app_id); duplicate(session,body,app_id)
        for key,value in body.model_dump().items(): setattr(app,key,value)
        session.flush(); return as_dict(app)


@router.post('/{app_id}/tasks', dependencies=[Depends(local_only)], status_code=201)
def create_task(app_id: int, body: TaskInput):
    with Session(engine) as session, session.begin():
        get_application(session,app_id); row=ApplicationTask(application_id=app_id,**body.model_dump()); session.add(row); session.flush(); return as_dict(row)


@router.put('/{app_id}/tasks/{task_id}', dependencies=[Depends(local_only)])
def update_task(app_id: int, task_id: int, body: TaskInput):
    with Session(engine) as session, session.begin():
        row=session.get(ApplicationTask,task_id)
        if not row or row.application_id != app_id: raise HTTPException(404,'Task not found')
        for key,value in body.model_dump().items(): setattr(row,key,value)
        session.flush(); return as_dict(row)


@router.delete('/{app_id}/tasks/{task_id}', dependencies=[Depends(local_only)])
def delete_task(app_id: int, task_id: int):
    with Session(engine) as session, session.begin():
        row=session.get(ApplicationTask,task_id)
        if not row or row.application_id != app_id: raise HTTPException(404,'Task not found')
        session.delete(row); return {'deleted':True}


@router.post('/{app_id}/deadlines', dependencies=[Depends(local_only)], status_code=201)
def create_deadline(app_id: int, body: DeadlineInput):
    with Session(engine) as session, session.begin():
        get_application(session,app_id); row=ApplicationDeadline(application_id=app_id,**body.model_dump()); session.add(row); session.flush(); return as_dict(row)


@router.put('/{app_id}/deadlines/{deadline_id}', dependencies=[Depends(local_only)])
def update_deadline(app_id: int, deadline_id: int, body: DeadlineInput):
    with Session(engine) as session, session.begin():
        row=session.get(ApplicationDeadline,deadline_id)
        if not row or row.application_id != app_id: raise HTTPException(404,'Deadline not found')
        for key,value in body.model_dump().items(): setattr(row,key,value)
        session.flush(); return as_dict(row)


@router.delete('/{app_id}/deadlines/{deadline_id}', dependencies=[Depends(local_only)])
def delete_deadline(app_id: int, deadline_id: int):
    with Session(engine) as session, session.begin():
        row=session.get(ApplicationDeadline,deadline_id)
        if not row or row.application_id != app_id: raise HTTPException(404,'Deadline not found')
        session.delete(row); return {'deleted':True}
