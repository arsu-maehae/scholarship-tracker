from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from database import engine
from models import ScholarshipScheme

SCHEMES = [
    {"name": "Erasmus Mundus", "slug": "erasmus-mundus"},
    {"name": "Thai government (ก.พ.)", "slug": "thai-government"},
    {"name": "Chevening", "slug": "chevening"},
    {"name": "Fulbright", "slug": "fulbright"},
    {"name": "Japanese Government (MEXT)", "slug": "mext"},
    {"name": "DAAD", "slug": "daad"},
    {"name": "Australian Government Research Training Program", "slug": "australian-rtp"},
]


def main():
    statement = (
        insert(ScholarshipScheme)
        .values(SCHEMES)
        .on_conflict_do_nothing(index_elements=["slug"])
    )

    with engine.begin() as connection:
        connection.execute(statement)
        count = connection.execute(
            select(func.count()).select_from(ScholarshipScheme)
        ).scalar_one()

    print(f"Seed complete. Total schemes: {count}")


if __name__ == "__main__":
    main()
