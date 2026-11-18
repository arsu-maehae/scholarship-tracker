from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import text, select, func, or_, case
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import engine
from models import ScholarshipScheme, Scholarship

app = FastAPI(
    title="Scholarship Discovery API",
    version="0.2.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def database_health() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            database_name = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable",
        ) from None

    return {
        "status": "ok",
        "database": database_name,
    }

@app.get("/api/schemes")
def list_schemes() -> list[dict[str, int | str]]:
    statement = select(ScholarshipScheme).order_by(
        ScholarshipScheme.name
    )

    with Session(engine) as session:
        schemes = session.scalars(statement).all()

        return [
            {
                "id": scheme.id,
                "name": scheme.name,
                "slug": scheme.slug,
            }
            for scheme in schemes
        ]

@app.get("/api/filter-options")
def filter_options() -> dict:
    """Indexed fields only, deduplicated across published catalogue records."""
    statement = select(Scholarship.fields_of_study).where(
        Scholarship.review_state == "published"
    )
    with Session(engine) as session:
        fields = sorted({
            value.strip().lower()
            for values in session.scalars(statement)
            for value in (values or [])
            if value and value.strip()
        })
    return {"fields": fields}


@app.get("/api/scholarships")
def search_scholarships(
    country: str | None = Query(
        default=None, pattern=r"^[A-Za-z]{2}$"
    ),
    degree: Literal[
        "bachelor", "master", "phd", "master_phd"
    ] | None = None,
    field: str | None = Query(
        default=None, min_length=1, max_length=100
    ),
    include_unknown_fields: bool = Query(
        default=False,
        description="With a field filter, also return unrecorded fields as unverified possibilities, not confirmed matches.",
    ),
    funding: Literal[
        "full", "tuition_only", "partial", "unknown"
    ] | None = None,
    scheme: str | None = Query(default=None, max_length=100),
    intake_year: int | None = Query(
        default=None, ge=1900, le=2200
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    statement = (
        select(
            Scholarship,
            ScholarshipScheme.name,
            ScholarshipScheme.slug,
        )
        .join(
            ScholarshipScheme,
            Scholarship.scheme_id == ScholarshipScheme.id,
        )
        .where(Scholarship.review_state == "published")
    )

    if country:
        statement = statement.where(
            Scholarship.countries.contains([country.upper()])
        )

    if degree:
        statement = statement.where(
            Scholarship.degree_levels.contains([degree])
        )

    normalized_field = field.strip().lower() if field is not None else None
    if normalized_field == "":
        raise HTTPException(status_code=422, detail="Field must not be blank")

    ordering = [Scholarship.id]
    if normalized_field:
        exact_field = Scholarship.fields_of_study.contains([normalized_field])
        missing_fields = or_(
            Scholarship.fields_of_study.is_(None),
            func.cardinality(Scholarship.fields_of_study) == 0,
        )
        statement = statement.where(
            or_(exact_field, missing_fields) if include_unknown_fields else exact_field
        )
        # Exact recorded matches first; unknowns remain visibly unverified.
        ordering = [case((exact_field, 0), else_=1), Scholarship.id]

    if funding:
        statement = statement.where(
            Scholarship.funding_category == funding
        )

    if scheme:
        statement = statement.where(
            ScholarshipScheme.slug == scheme
        )

    if intake_year is not None:
        statement = statement.where(
            Scholarship.intake_year == intake_year
        )

    with Session(engine) as session:
        total = session.scalar(
            select(func.count()).select_from(statement.subquery())
        )

        rows = session.execute(
            statement
            .order_by(*ordering)
            .offset(offset)
            .limit(limit)
        ).all()

        items = [
            {
                "id": scholarship.id,
                "title": scholarship.title,
                "scheme": {
                    "name": scheme_name,
                    "slug": scheme_slug,
                },
                "cycle": scholarship.cycle,
                "description": scholarship.description,
                "intake_year": scholarship.intake_year,
                "countries": scholarship.countries,
                "degree_levels": scholarship.degree_levels,
                "fields_of_study": scholarship.fields_of_study,
                "field_match": (
                    "not_filtered" if normalized_field is None
                    else "exact" if normalized_field in (scholarship.fields_of_study or [])
                    else "unverified"
                ),
                "funding_category": scholarship.funding_category,
                "funding_notes": scholarship.funding_notes,
                "call_status": scholarship.call_status,
                "official_url": scholarship.official_url,
                "last_checked": scholarship.last_checked,
            }
            for scholarship, scheme_name, scheme_slug in rows
        ]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }
