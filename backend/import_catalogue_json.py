"""Validate, preview, or apply a JSON scholarship catalogue.

Preview is the default and never changes database rows. No scraping is performed.
"""
import argparse
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from sqlalchemy import inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models import Scholarship, ScholarshipScheme

FUNDING = {"full", "tuition_only", "partial", "unknown"}
CALL_STATUS = {"open", "upcoming", "closed", "unknown"}
REVIEW_STATES = {"draft", "needs_review", "published", "archived"}
DEGREES = {"bachelor", "master", "phd", "master_phd"}
KEY_PATTERN = re.compile(r"[a-z0-9][a-z0-9._:/-]{0,199}\Z")
TAG_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
# ISO 3166-1 assigned countries and territories; generated once, no runtime dependency.
COUNTRY_CODES = set("AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW".split())
REQUIRED = {"source_key", "scheme_slug", "title", "cycle"}
TEXT_LIMITS = {
    "source_key": 200, "scheme_slug": 100, "title": 250, "cycle": 100,
    "description": 20000, "funding_notes": 20000, "official_url": 2048,
}
ARRAY_FIELDS = {"countries", "degree_levels", "fields_of_study"}
ALLOWED = set(TEXT_LIMITS) | ARRAY_FIELDS | {
    "intake_year", "funding_category", "call_status", "review_state", "last_checked",
}
DEFAULTS = {
    "intake_year": None, "description": None, "countries": None,
    "degree_levels": None, "fields_of_study": None,
    "funding_category": "unknown", "funding_notes": None,
    "call_status": "unknown", "review_state": "draft",
    "official_url": None, "last_checked": None,
}


class CatalogueError(ValueError):
    """User-actionable validation or identity conflict."""


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CatalogueError(f"Duplicate JSON property: {key}")
        result[key] = value
    return result


def validate_document(document, today=None):
    """Validate the entire file before touching the database; return copied records."""
    today = today or date.today()
    if not isinstance(document, dict) or set(document) != {"schema_version", "scholarships"}:
        raise CatalogueError("Expected an object containing only schema_version and scholarships")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise CatalogueError("schema_version must be the integer 1")
    records = document["scholarships"]
    if not isinstance(records, list) or len(records) > 2000:
        raise CatalogueError("scholarships must be an array of at most 2000 records")
    clean, keys, identities = [], set(), set()
    for index, raw in enumerate(records, 1):
        prefix = f"Record {index}"
        def fail(message):
            raise CatalogueError(f"{prefix}: {message}")
        if not isinstance(raw, dict):
            fail("must be an object")
        if REQUIRED - raw.keys():
            fail("missing: " + ", ".join(sorted(REQUIRED - raw.keys())))
        if raw.keys() - ALLOWED:
            fail("unknown properties: " + ", ".join(sorted(raw.keys() - ALLOWED)))
        record = dict(raw)
        for field, limit in TEXT_LIMITS.items():
            if field not in record:
                continue
            value = record[field]
            if value is None and field not in {"source_key", "scheme_slug", "title"}:
                continue
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                fail(f"{field} must be nonblank text up to {limit} characters (or null when optional)")
            if value != value.strip():
                fail(f"{field} must not have leading/trailing whitespace")
        if not KEY_PATTERN.fullmatch(record["source_key"]):
            fail("source_key must use lowercase letters, digits or . _ : / -")
        if not TAG_PATTERN.fullmatch(record["scheme_slug"]):
            fail("scheme_slug must be a lowercase hyphenated slug")
        for field in ARRAY_FIELDS & record.keys():
            values = record[field]
            if values is None:
                continue
            if not isinstance(values, list) or len(values) > 249 or any(not isinstance(v, str) for v in values):
                fail(f"{field} must be a string array or null")
            if len(values) != len(set(values)):
                fail(f"{field} contains duplicate values")
            for value in values:
                if field == "countries" and value not in COUNTRY_CODES:
                    fail(f"unknown study country code: {value}")
                if field == "degree_levels" and value not in DEGREES:
                    fail(f"unknown degree: {value}")
                if field == "fields_of_study" and (len(value) > 100 or not TAG_PATTERN.fullmatch(value)):
                    fail("field tags must be lowercase hyphenated tags of up to 100 characters")
            record[field] = sorted(values)
        if "intake_year" in record and record["intake_year"] is not None:
            year = record["intake_year"]
            if type(year) is not int or not 1900 <= year <= 2200:
                fail("intake_year must be an integer between 1900 and 2200, or null")
        for field, allowed in [("funding_category", FUNDING), ("call_status", CALL_STATUS), ("review_state", REVIEW_STATES)]:
            if field in record and (not isinstance(record[field], str) or record[field] not in allowed):
                fail(f"invalid {field}; choose from {', '.join(sorted(allowed))}")
        if record.get("official_url") is not None:
            url = record["official_url"]
            try:
                parsed = urlsplit(url)
                valid = parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password and not any(c.isspace() for c in url)
                parsed.port  # Reject malformed port values too.
            except ValueError:
                valid = False
            if not valid:
                fail("official_url must be an absolute HTTPS URL without credentials")
        if record.get("last_checked") is not None:
            value = record["last_checked"]
            if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                fail("last_checked must be YYYY-MM-DD or null")
            try:
                checked = date.fromisoformat(value)
            except ValueError:
                fail("last_checked is not a valid date")
            if checked > today:
                fail("last_checked must not be in the future")
            record["last_checked"] = checked
        key = record["source_key"]
        identity = (record["scheme_slug"], record["title"], record["cycle"])
        if key in keys:
            fail(f"duplicate source_key: {key}")
        if identity in identities:
            fail("duplicate scheme/title/cycle identity")
        keys.add(key); identities.add(identity); clean.append(record)
    return clean


def load_catalogue(path):
    path = Path(path)
    if path.stat().st_size > 5 * 1024 * 1024:
        raise CatalogueError("Catalogue exceeds the 5 MiB input limit")
    try:
        # utf-8-sig accepts files saved with a UTF-8 BOM on Windows.
        document = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=no_duplicate_keys)
    except (json.JSONDecodeError, UnicodeError, RecursionError) as error:
        raise CatalogueError(f"Invalid UTF-8 JSON: {error}") from None
    return validate_document(document)


def equivalent(field, old, new):
    # Array ordering has no meaning for these filters; avoid spurious updates.
    if field in ARRAY_FIELDS and old is not None and new is not None:
        return sorted(old) == sorted(new)
    return old == new


@dataclass
class Change:
    action: str
    key: str
    row: object
    values: dict
    changed: dict


def make_plan(session, records):
    schemes = {s.slug: s for s in session.scalars(select(ScholarshipScheme))}
    missing = {r["scheme_slug"] for r in records} - schemes.keys()
    if missing:
        raise CatalogueError("Unknown schemes: " + ", ".join(sorted(missing)) + ". Add the schemes first; existing schemes can be seeded with seed.py.")
    plan, targeted_ids = [], set()
    for record in records:
        key = record["source_key"]
        scheme_id = schemes[record["scheme_slug"]].id
        row = session.scalar(select(Scholarship).where(Scholarship.source_key == key))
        candidates = session.scalars(select(Scholarship).where(
            Scholarship.scheme_id == scheme_id,
            Scholarship.title == record["title"],
            Scholarship.cycle == record["cycle"],
        )).all()
        if row is not None and row.scheme_id != scheme_id:
            raise CatalogueError(f"{key}: cannot move an existing key to another scheme")
        if row is not None:
            if any(candidate.id != row.id for candidate in candidates):
                raise CatalogueError(f"{key}: requested identity conflicts with another database record")
        elif len(candidates) > 1:
            raise CatalogueError(f"{key}: multiple legacy matches; resolve duplicates first")
        elif candidates:
            row = candidates[0]
            if row.source_key is not None:
                raise CatalogueError(f"{key}: identity already belongs to {row.source_key}; keep the existing stable key")
        if row is not None:
            if row.id in targeted_ids:
                raise CatalogueError(f"{key}: two input records target the same database row")
            targeted_ids.add(row.id)
        supplied = {k: v for k, v in record.items() if k != "scheme_slug"}
        if (row is not None and row.last_checked is not None
                and supplied.get("last_checked") is not None
                and supplied["last_checked"] < row.last_checked):
            raise CatalogueError(f"{key}: incoming last_checked is older than the database; review the source instead of overwriting newer research")
        if row is None:
            values = {**DEFAULTS, **supplied, "scheme_id": scheme_id}
        else:
            # Omitted values preserve existing fields; explicit null clears a nullable field.
            values = dict(supplied)
        effective_review = values.get("review_state", row.review_state if row is not None else "draft")
        url = values.get("official_url", row.official_url if row is not None else None)
        checked = values.get("last_checked", row.last_checked if row is not None else None)
        if effective_review == "published" and (not url or not checked):
            raise CatalogueError(f"{key}: publishing requires official_url and last_checked; use draft or needs_review until checked")
        if row is None:
            changes = {name: (None, value) for name, value in values.items()}
            action = "INSERT"
        else:
            changes = {name: (getattr(row, name), value) for name, value in values.items()
                       if not equivalent(name, getattr(row, name), value)}
            action = "ADOPT" if row.source_key is None else "UPDATE" if changes else "UNCHANGED"
        plan.append(Change(action, key, row, values, changes))
    return plan


def run_import(engine, records, apply=False, output=print):
    if not hasattr(Scholarship, "source_key"):
        raise CatalogueError("models.py needs the Scholarship.source_key column")
    columns = {column["name"] for column in inspect(engine).get_columns("scholarships")}
    if "source_key" not in columns:
        raise CatalogueError("Database is missing source_key. Run: python -m alembic upgrade head")
    counts = {action: 0 for action in ("INSERT", "ADOPT", "UPDATE", "UNCHANGED")}
    with Session(engine) as session, session.begin():
        if apply and engine.dialect.name == "postgresql":
            # Keep the old importer and this importer serialized during transition.
            session.execute(text("SELECT pg_advisory_xact_lock(724139802)"))
            # Protect adoption/identity checks from concurrent legacy inserts or edits.
            session.execute(text("LOCK TABLE scholarships IN SHARE ROW EXCLUSIVE MODE"))
        plan = make_plan(session, records)
        for item in plan:
            counts[item.action] += 1
            output(f"{item.action}: {item.key}")
            for name, (old, new) in item.changed.items():
                output(f"  {name}: {json.dumps(old, ensure_ascii=True, default=str)} -> {json.dumps(new, ensure_ascii=True, default=str)}")
        if apply:
            for item in plan:
                if item.action == "INSERT":
                    session.add(Scholarship(**item.values))
                elif item.action != "UNCHANGED":
                    for name in item.changed:
                        setattr(item.row, name, item.values[name])
            session.flush()
    output(("SAVED" if apply else "PREVIEW ONLY; nothing saved") + ": " + ", ".join(f"{n} {a.lower()}" for a, n in counts.items()))
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Path to the catalogue JSON file")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Save all planned changes atomically")
    mode.add_argument("--validate-only", action="store_true", help="Validate JSON without connecting to PostgreSQL")
    args = parser.parse_args(argv)
    try:
        records = load_catalogue(args.path)
        if args.validate_only:
            print(f"VALID: {len(records)} records. No database connection or changes.")
            return 0
        from database import engine
        run_import(engine, records, apply=args.apply)
    except (CatalogueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print("ERROR: Database operation failed. Check Docker/PostgreSQL, your migration and database configuration; preview again before retrying.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
