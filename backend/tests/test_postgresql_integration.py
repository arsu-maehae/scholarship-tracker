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
import tracker


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

    def test_fresh_migrations_and_import(self):
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

        for filename, expected in [("data/reviewed_2026-11-18.json", 3), ("data/reviewed_global_2026-11-18.json", 4)]:
            batch = load_catalogue(Path(filename))
            with Session(engine) as session, session.begin():
                for slug in sorted({item["scheme_slug"] for item in batch}):
                    session.add(ScholarshipScheme(name=slug, slug=slug))
            self.assertEqual(run_import(engine, batch, apply=True, output=quiet)["INSERT"], expected)
            self.assertEqual(run_import(engine, batch, output=quiet)["UNCHANGED"], expected)

        body = tracker.ApplicationInput(title='Test application', source_url='https://example.org/award', cycle='2030', notes='Private test note', next_action='Prepare documents')
        app = tracker.create_application(body)
        task = tracker.create_task(app['id'], tracker.TaskInput(title='Request transcript'))
        tracker.create_deadline(app['id'], tracker.DeadlineInput(label='Submit', kind='official', due_date='2030-01-10'))
        tracker.update_task(app['id'], task['id'], tracker.TaskInput(title='Request transcript', completed=True))
        rows = tracker.list_applications()
        self.assertEqual(rows[0]['notes'], 'Private test note')
        self.assertTrue(rows[0]['tasks'][0]['completed'])
        self.assertEqual(str(rows[0]['deadlines'][0]['due_date']), '2030-01-10')
        with self.assertRaises(tracker.HTTPException) as duplicate:
            tracker.create_application(body)
        self.assertEqual(duplicate.exception.status_code, 409)
        tracker.update_application(app['id'], body.model_copy(update={'archived': True, 'status':'submitted'}))
        self.assertEqual(tracker.list_applications(), [])
        self.assertEqual(len(tracker.list_applications(archived=True)), 1)
        tracker.update_application(app['id'], body.model_copy(update={'archived': False}))
        self.assertEqual(len(tracker.list_applications()), 1)

    @classmethod
    def tearDownClass(cls):
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
