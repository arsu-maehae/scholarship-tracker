"""Add a reviewed catalogue snapshot. Preview by default; use --apply to save.

Place beside database.py and models.py. No schema changes or new packages.
Research snapshot: 2026-11-17. This script does not scrape live websites.
"""
import argparse
from datetime import date
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from models import Scholarship, ScholarshipScheme

CHECKED = date(2026, 11, 17)
RECORDS = [
    {
        "scheme_slug": "chevening",
        "title": "Chevening Thailand Scholarship",
        "cycle": "2027-2028",
        "intake_year": 2027,
        "countries": ["GB"],
        "degree_levels": ["master"],
        "fields_of_study": None,
        "funding_category": "full",
        "call_status": "closed",
        "description": "For Thai applicants pursuing eligible one-year taught master's courses in the UK. This is a scheme-level opportunity, not a particular university course. Check the current eligibility and course rules.",
        "funding_notes": "Tuition and living support, approved travel, visa and specified allowances. Individual award terms apply. The Thailand page marks the 2027-2028 application round closed. Broad course coverage; field tags are not exhaustively indexed. Funding source: https://www.chevening.org/faqs/what-does-a-chevening-scholarship-cover/",
        "official_url": "https://www.chevening.org/scholarship/thailand/",
    },
    {
        "scheme_slug": "fulbright",
        "title": "Fulbright Thai Graduate Scholarship (TGS)",
        "cycle": "Programme overview - dated call unverified",
        "intake_year": None,
        "countries": ["US"],
        "degree_levels": ["master", "phd"],
        "fields_of_study": None,
        "funding_category": "partial",
        "call_status": "unknown",
        "description": "US graduate study for eligible Thai applicants, excluding clinical practice. Master's and PhD routes are separate. Check eligibility on the official page.",
        "funding_notes": "Usually partial support. Annual caps: USD 46,000 for master's or USD 40,000 for PhD, each for up to two years. Other benefits include flights, insurance and visa sponsorship. Uncovered costs may remain. Dated intake and opening are unverified; broad field coverage is not indexed.",
        "official_url": "https://www.fulbrightthai.org/tgs",
    },
    {
        "scheme_slug": "thai-government",
        "title": "OCSC regional government scholarship - pre-study appointment (overview)",
        "cycle": "FY2570",
        "intake_year": None,
        "countries": None,
        "degree_levels": ["master"],
        "fields_of_study": None,
        "funding_category": "unknown",
        "call_status": "open",
        "description": "Official FY2570 regional pre-study appointment call. Overview only: individual award codes specify destination, subject, agency and eligibility. Fiscal year is not necessarily the academic intake year. Do not treat Thailand as the study destination.",
        "funding_notes": "OVERVIEW ONLY: select an individual award code before assessing eligibility, destination, subject, funding and service obligations. These details have not been indexed. OCSC lists this master's call as open through 29 December 2026; closing time is not verified. Funding coverage remains unverified for a specific award. Destination and field filters will omit this overview.",
        "official_url": "https://www.ocsc.go.th/scholarships/degree-scholarships/",
    },
    {
        "scheme_slug": "erasmus-mundus",
        "title": "EMAI - Artificial Intelligence programme and funding overview",
        "cycle": "Programme overview - next award unverified",
        "intake_year": None,
        "countries": ["ES", "IT", "NL", "SI"],
        "degree_levels": ["master"],
        "fields_of_study": ["ai", "data-science", "robotics", "cybersecurity"],
        "funding_category": "unknown",
        "call_status": "unknown",
        "description": "Joint AI master's coordinated by UPF with Sapienza, Radboud and Ljubljana. Consortium destinations are listed; the actual study route depends on the programme. Funding for the next cohort must be verified.",
        "funding_notes": "The FAQ distinguishes Erasmus Mundus scholarships with living support from tuition fee waivers and refers to funding in the first four editions. This does not establish funding for a later intake. Homepage says applications are closed and the next round will open in November 2026, without an exact opening date. Next-cohort funding, intake and call status remain unverified. Sources: https://www.upf.edu/web/emai/faqs and https://www.upf.edu/web/emai/academic-information",
        "official_url": "https://www.upf.edu/web/emai",
    },
]


def validate_records():
    keys = set()
    for record in RECORDS:
        key = (record["scheme_slug"], record["title"], record["cycle"])
        if key in keys:
            raise ValueError(f"Duplicate import identity: {key}")
        keys.add(key)
        if record["funding_category"] not in {"full", "tuition_only", "partial", "unknown"}:
            raise ValueError("Invalid funding category")
        if record["call_status"] not in {"open", "upcoming", "closed", "unknown"}:
            raise ValueError("Invalid call status")
        if not record["official_url"].startswith("https://"):
            raise ValueError("Official HTTPS source required")
        for country in record["countries"] or []:
            if len(country) != 2 or not country.isascii() or not country.isupper():
                raise ValueError(f"Invalid country: {country}")


def import_records(engine, apply=False):
    """Insert only. Existing rows are never overwritten; all writes are atomic."""
    validate_records()
    inserted = skipped = 0
    with Session(engine) as session:
        with session.begin():
            # Serialize runs of this importer; the existing schema has no natural-key constraint.
            if engine.dialect.name == "postgresql":
                session.execute(text("SELECT pg_advisory_xact_lock(724139802)"))
            required = {record["scheme_slug"] for record in RECORDS}
            schemes = {row.slug: row for row in session.scalars(
                select(ScholarshipScheme).where(ScholarshipScheme.slug.in_(required))
            )}
            missing = required - schemes.keys()
            if missing:
                raise RuntimeError("Run seed.py first. Missing schemes: " + ", ".join(sorted(missing)))
            for record in RECORDS:
                data = dict(record)
                scheme_id = schemes[data.pop("scheme_slug")].id
                existing = session.scalars(select(Scholarship).where(
                    Scholarship.scheme_id == scheme_id,
                    Scholarship.title == data["title"],
                    Scholarship.cycle == data["cycle"],
                )).all()
                if len(existing) > 1:
                    raise RuntimeError("Existing duplicate identities require review: " + data["title"])
                if existing:
                    skipped += 1
                    print("SKIP existing: " + data["title"])
                    continue
                session.add(Scholarship(
                    scheme_id=scheme_id, review_state="published", last_checked=CHECKED, **data
                ))
                inserted += 1
                print(("INSERT: " if apply else "WOULD INSERT: ") + data["title"])
            session.flush()
            if not apply:
                # Roll back the preview, including flushed inserts.
                session.rollback()
    print(f"{'Saved' if apply else 'Preview only (nothing saved)'}: {inserted} new, {skipped} existing.")
    return inserted, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Save records; default is a rolled-back preview")
    args = parser.parse_args()
    from database import engine
    import_records(engine, apply=args.apply)


if __name__ == "__main__":
    main()
