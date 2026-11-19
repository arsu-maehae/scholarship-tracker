from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from database import engine

app = FastAPI(title="Scholarship Tracker API", version="0.3.0")

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.get('/health/db')
def database_health():
    try:
        with engine.connect() as connection:
            name = connection.execute(text('SELECT current_database()')).scalar_one()
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail='Database connection unavailable') from None
    return {'status': 'ok', 'database': name}

from tracked import router as tracked_router
app.include_router(tracked_router)
