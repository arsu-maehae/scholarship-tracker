"""Offline tests. Uses disposable SQLite databases with ARRAY mapped to JSON.

Run from backend: python -m unittest discover -s tests -p test_import_catalogue_json.py -v
No connection to database.py or your PostgreSQL database is made.
"""
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from sqlalchemy import JSON, create_engine, event, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from models import Base, Scholarship, ScholarshipScheme
from import_catalogue_json import CatalogueError, load_catalogue, run_import, validate_document


def document(*records):
    return {"schema_version": 1, "scholarships": list(records)}


def record(**changes):
    return {
        "source_key": "erasmus-mundus:example:2027",
        "scheme_slug": "erasmus-mundus", "title": "Example test award",
        "cycle": "2027", "countries": ["FI"], "degree_levels": ["master"],
        "fields_of_study": ["ai"], **changes,
    }


class ValidationTests(unittest.TestCase):
    def test_unknown_property_and_invalid_values(self):
        invalid = [dict(unexpected=True), dict(countries=["ZZ"]), dict(countries=["fi"]),
                   dict(degree_levels=["masters"]), dict(funding_category="free"),
                   dict(intake_year=True), dict(fields_of_study=["AI"]),
                   dict(last_checked="9999-12-31"), dict(last_checked="2026-02-30"),
                   dict(official_url="https://name:password@example.org/"),
                   dict(source_key="Capitalized"), dict(title=" "), dict(review_state="approved")]
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(CatalogueError):
                validate_document(document(record(**changes)))

    def test_duplicate_keys_and_natural_identity(self):
        with self.assertRaises(CatalogueError):
            validate_document(document(record(), record(title="Other")))
        with self.assertRaises(CatalogueError):
            validate_document(document(record(), record(source_key="other:key")))

    def test_format_and_missing_required_fields(self):
        for value in [[], {}, {"schema_version": True, "scholarships": []},
                      document({"title": "Incomplete"})]:
            with self.subTest(value=value), self.assertRaises(CatalogueError):
                validate_document(value)

    def test_json_bom_and_duplicate_property(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalogue.json"
            path.write_text(json.dumps(document(record())), encoding="utf-8-sig")
            self.assertEqual(len(load_catalogue(path)), 1)
            path.write_text('{"schema_version":1,"schema_version":1,"scholarships":[]}', encoding="utf-8")
            with self.assertRaises(CatalogueError): load_catalogue(path)
            path.write_text('{broken', encoding="utf-8")
            with self.assertRaises(CatalogueError): load_catalogue(path)

    def test_example_catalogue_is_valid(self):
        path = Path(__file__).resolve().parents[1] / "data" / "scholarships.json"
        self.assertEqual(len(load_catalogue(path)), 5)


class ImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not hasattr(Scholarship, "source_key"):
            raise RuntimeError("Add Scholarship.source_key to models.py before running tests")
        # Confirm the actual model compiles for PostgreSQL before test-only type variants.
        ddl = str(CreateTable(Scholarship.__table__).compile(dialect=postgresql.dialect()))
        assert "source_key" in ddl and "UNIQUE (source_key)" in ddl
        for name in ["countries", "degree_levels", "fields_of_study"]:
            column = Scholarship.__table__.c[name]
            column.type = column.type.with_variant(JSON(none_as_null=True), "sqlite")

    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session, session.begin():
            session.add(ScholarshipScheme(name="Erasmus Mundus", slug="erasmus-mundus"))
        self.output = []

    def tearDown(self):
        self.engine.dispose()

    def run_records(self, *raw, apply=False):
        return run_import(self.engine, validate_document(document(*raw)), apply=apply, output=self.output.append)

    def rows(self):
        with Session(self.engine) as session:
            return session.scalars(select(Scholarship).order_by(Scholarship.id)).all()

    def test_preview_is_read_only_and_apply_is_idempotent(self):
        self.assertEqual(self.run_records(record())["INSERT"], 1)
        self.assertEqual(self.rows(), [])
        self.run_records(record(), apply=True)
        self.assertEqual(self.run_records(record(), apply=True)["UNCHANGED"], 1)
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0].review_state, "draft")

    def test_update_same_key_renames_same_row_and_preserves_omitted_fields(self):
        self.run_records(record(funding_category="partial"), apply=True)
        before = self.rows()[0]
        renamed = {"source_key": before.source_key, "scheme_slug": "erasmus-mundus",
                   "title": "Renamed", "cycle": "2027"}
        self.assertEqual(self.run_records(renamed)["UPDATE"], 1)
        self.assertEqual(self.rows()[0].title, before.title)
        self.run_records(renamed, apply=True)
        after = self.rows()[0]
        self.assertEqual(after.id, before.id)
        self.assertEqual(after.title, "Renamed")
        self.assertEqual(after.funding_category, "partial")
        self.assertEqual(after.countries, ["FI"])

    def test_legacy_adoption_preserves_database_id(self):
        self.run_records(record(), apply=True)
        before = self.rows()[0]
        with Session(self.engine) as session, session.begin():
            session.get(Scholarship, before.id).source_key = None
        self.assertEqual(self.run_records(record())["ADOPT"], 1)
        self.assertIsNone(self.rows()[0].source_key)
        self.run_records(record(), apply=True)
        self.assertEqual(self.rows()[0].id, before.id)
        self.assertEqual(self.rows()[0].source_key, record()["source_key"])
        self.assertEqual(len(self.rows()), 1)

    def test_ambiguous_legacy_matches_are_rejected(self):
        with Session(self.engine) as session, session.begin():
            scheme_id = session.scalar(select(ScholarshipScheme.id))
            session.add_all([Scholarship(scheme_id=scheme_id, title=record()["title"], cycle="2027") for _ in range(2)])
        with self.assertRaises(CatalogueError): self.run_records(record(), apply=True)
        self.assertTrue(all(row.source_key is None for row in self.rows()))

    def test_changed_key_cannot_duplicate_same_identity(self):
        self.run_records(record(), apply=True)
        with self.assertRaises(CatalogueError):
            self.run_records(record(source_key="different:key"), apply=True)
        self.assertEqual(len(self.rows()), 1)

    def test_missing_scheme_leaves_all_records_unchanged(self):
        with self.assertRaises(CatalogueError):
            self.run_records(record(), record(source_key="missing:key", title="Other", scheme_slug="missing"), apply=True)
        self.assertEqual(self.rows(), [])

    def test_publication_requires_source_and_checked_date(self):
        with self.assertRaises(CatalogueError): self.run_records(record(review_state="published"), apply=True)
        self.run_records(record(review_state="published", official_url="https://example.org/award", last_checked="2026-01-01"), apply=True)
        self.assertEqual(self.rows()[0].review_state, "published")
        self.run_records(record(review_state="needs_review"), apply=True)
        self.assertEqual(self.rows()[0].review_state, "needs_review")

    def test_stale_research_is_rejected(self):
        self.run_records(record(last_checked="2026-01-02"), apply=True)
        with self.assertRaises(CatalogueError):
            self.run_records(record(last_checked="2026-01-01", funding_category="partial"), apply=True)
        self.assertEqual(self.rows()[0].last_checked, date(2026, 1, 2))

    def test_explicit_null_clears_optional_field(self):
        self.run_records(record(description="Old note"), apply=True)
        self.run_records(record(description=None), apply=True)
        self.assertIsNone(self.rows()[0].description)

    def test_array_reordering_is_not_a_change(self):
        self.run_records(record(countries=["FI", "SE"]), apply=True)
        self.assertEqual(self.run_records(record(countries=["SE", "FI"]))["UNCHANGED"], 1)

    def test_database_error_rolls_back_entire_batch(self):
        calls = [0]
        def fail_second_insert(connection, cursor, statement, parameters, context, many):
            if statement.startswith("INSERT INTO scholarships"):
                calls[0] += 1
                if calls[0] == 2:
                    raise IntegrityError(statement, parameters, Exception("injected failure"))
        event.listen(self.engine, "before_cursor_execute", fail_second_insert)
        try:
            with self.assertRaises(IntegrityError):
                self.run_records(record(), record(source_key="example:second", title="Second"), apply=True)
        finally:
            event.remove(self.engine, "before_cursor_execute", fail_second_insert)
        self.assertEqual(self.rows(), [])

    def test_five_existing_records_are_adopted_without_duplication(self):
        path = Path(__file__).resolve().parents[1] / "data" / "scholarships.json"
        records = load_catalogue(path)
        with Session(self.engine) as session, session.begin():
            for slug in {r["scheme_slug"] for r in records} - {"erasmus-mundus"}:
                session.add(ScholarshipScheme(name=slug, slug=slug))
        run_import(self.engine, records, apply=True, output=lambda _: None)
        before_ids = [r.id for r in self.rows()]
        with Session(self.engine) as session, session.begin():
            for row in session.scalars(select(Scholarship)):
                row.source_key = None
        counts = run_import(self.engine, records, apply=True, output=lambda _: None)
        self.assertEqual(counts["ADOPT"], 5)
        self.assertEqual([r.id for r in self.rows()], before_ids)
        self.assertEqual(run_import(self.engine, records, apply=True, output=lambda _: None)["UNCHANGED"], 5)


if __name__ == "__main__":
    unittest.main()
