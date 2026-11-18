"""Integration checks against an explicitly configured, empty disposable PostgreSQL database.

Run separately from the SQLite unit suite. The test never drops or clears tables.
"""
import os
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

if os.environ.get("POSTGRES_DB") != "scholarship_tracker_test":
    raise RuntimeError("Set POSTGRES_DB=scholarship_tracker_test for a disposable test database")

from database import engine
from import_catalogue_json import load_catalogue, run_import, validate_document
from models import Scholarship, ScholarshipScheme
import main


class PostgreSQLIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if engine.dialect.name != "postgresql":
            raise RuntimeError("PostgreSQL is required")
        if inspect(engine).get_table_names():
            raise RuntimeError("Test database must be empty; no tables will be removed")
        command.upgrade(Config("alembic.ini"), "head")
        cls.records = load_catalogue(Path("data/scholarships.json"))
        with Session(engine) as session, session.begin():
            for slug in sorted({item["scheme_slug"] for item in cls.records}):
                session.add(ScholarshipScheme(name=slug, slug=slug))
        main.engine = engine

    def test_fresh_migrations_import_and_search(self):
        quiet = lambda _: None
        counts = run_import(engine, self.records, output=quiet)
        self.assertEqual(counts, {"INSERT": 5, "ADOPT": 0, "UPDATE": 0, "UNCHANGED": 0})
        with Session(engine) as session:
            self.assertEqual(session.scalars(select(Scholarship)).all(), [])
        self.assertEqual(run_import(engine, self.records, apply=True, output=quiet)["INSERT"], 5)
        self.assertEqual(run_import(engine, self.records, output=quiet)["UNCHANGED"], 5)
        with Session(engine) as session:
            before = [(row.id, row.source_key) for row in session.scalars(select(Scholarship).order_by(Scholarship.id))]
        self.assertEqual(run_import(engine, self.records, apply=True, output=quiet)["UNCHANGED"], 5)
        with Session(engine) as session:
            self.assertEqual([(row.id, row.source_key) for row in session.scalars(select(Scholarship).order_by(Scholarship.id))], before)

        drafts = validate_document({"schema_version": 1, "scholarships": [
            {"source_key": "test:" + state, "scheme_slug": "fulbright", "title": "Test " + state,
             "cycle": None, "review_state": state, "fields_of_study": ["ai"]}
            for state in ("draft", "needs_review", "archived")
        ]})
        run_import(engine, drafts, apply=True, output=quiet)
        defaults = dict(country=None, degree=None, field=None, include_unknown_fields=False,
                        funding=None, scheme=None, intake_year=None, limit=20, offset=0)
        def search(**kwargs):
            return main.search_scholarships(**(defaults | kwargs))
        self.assertEqual(search()["total"], 5)
        self.assertEqual(search(country="FI", degree="master", funding="full")["total"], 1)
        self.assertEqual(search(country="US", degree="master", funding="full")["total"], 0)
        self.assertEqual(search(field="ai")["total"], 2)
        possible = search(field="ai", include_unknown_fields=True)
        self.assertEqual(possible["total"], 5)
        self.assertEqual([item["field_match"] for item in possible["items"]],
                         ["exact", "exact", "unverified", "unverified", "unverified"])
        possible_gb = search(country="GB", degree="master", field="ai", include_unknown_fields=True)
        self.assertEqual(possible_gb["total"], 1)
        self.assertEqual(possible_gb["items"][0]["field_match"], "unverified")
        self.assertEqual(search(country="GB", degree="master", field="ai")["total"], 0)
        self.assertEqual(search(field="ai", limit=1, offset=1)["total"], 2)
        self.assertEqual(len(search(field="ai", limit=1, offset=1)["items"]), 1)

        reviewed = load_catalogue(Path("data/reviewed_2026-11-18.json"))
        with Session(engine) as session, session.begin():
            for slug in sorted({item["scheme_slug"] for item in reviewed}):
                session.add(ScholarshipScheme(name=slug, slug=slug))
        self.assertEqual(run_import(engine, reviewed, output=quiet)["INSERT"], 3)
        self.assertEqual(run_import(engine, reviewed, apply=True, output=quiet)["INSERT"], 3)
        self.assertEqual(run_import(engine, reviewed, output=quiet)["UNCHANGED"], 3)
        self.assertEqual(search()["total"], 8)
        japan = search(country="JP", degree="master")
        self.assertEqual(japan["total"], 1)
        self.assertIn("graduate", japan["items"][0]["description"].lower())
        self.assertEqual(search(country="DE", field="computer-science")["total"], 1)
        self.assertEqual(search(country="AU", funding="full")["total"], 0)

    @classmethod
    def tearDownClass(cls):
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
