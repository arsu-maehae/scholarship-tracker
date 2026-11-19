"""Restrict the single-user API to the local development app."""
from fastapi import HTTPException, Request

def local_only(request: Request):
    if (request.client is None or request.client.host not in ('127.0.0.1','::1')
        or request.headers.get('host') not in ('127.0.0.1:8000','localhost:8000','[::1]:8000')):
        raise HTTPException(403, 'Local access only')
    if request.method not in ('GET','HEAD') and (request.headers.get('origin') not in ('http://127.0.0.1:5173','http://localhost:5173') or request.headers.get('x-requested-with') != 'ScholarshipTracker'):
        raise HTTPException(403, 'Changes must come from the local tracker')
