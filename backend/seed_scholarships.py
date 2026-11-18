from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import engine
from models import Scholarship, ScholarshipScheme


def main():
    with Session(engine) as session, session.begin():
        scheme = session.scalar(
            select(ScholarshipScheme).where(
                ScholarshipScheme.slug == "erasmus-mundus"
            )
        )

        if scheme is None:
            raise RuntimeError("Run seed.py first.")

        title = "EDISS - Erasmus Mundus scholarship"
        cycle = "2027-2029"

        existing = session.scalar(
            select(Scholarship).where(
                Scholarship.scheme_id == scheme.id,
                Scholarship.title == title,
                Scholarship.cycle == cycle,
            ).limit(1)
        )

        if existing is not None:
            print(f"Already exists: scholarship {existing.id}")
            return

        scholarship = Scholarship(
            scheme_id=scheme.id,
            title=title,
            cycle=cycle,
            intake_year=2027,
            description=(
                "Data science and machine learning integrated with "
                "software engineering. Consortium study locations "
                "depend on the selected mobility route."
            ),
            countries=["FI", "SE", "IT", "ES"],
            degree_levels=["master"],
            fields_of_study=[
                "ai",
                "data-science",
                "software-engineering",
            ],
            funding_category="full",
            funding_notes=(
                "Erasmus Mundus route: participation-cost waiver, "
                "insurance and EUR 1,400/month for up to 24 months. "
                "Competitive selection."
            ),
            call_status="unknown",
            review_state="published",
            official_url="https://www.master-ediss.eu/scholarship/",
            last_checked=date(2026, 11, 17),
        )

        session.add(scholarship)
        session.flush()
        print(f"Inserted scholarship: {scholarship.id}")


if __name__ == "__main__":
    main()