# Scholarship Discovery — development guidance

Read docs/CODEX_HANDOFF.md before your first change. Read the actual repository and git status too: the handoff is a dated snapshot, not a replacement for current files. If this repository already has AGENTS.md instructions, merge relevant guidance rather than overwriting them.

## Product

Build a useful scholarship discovery application for Arsu Maehae. The current product searches a curated PostgreSQL catalogue by study destination, degree, field, funding, scheme and intake. It does not discover every scholarship worldwide. Preserve truthful uncertainty and official source links.

## Stack and local commands

- React + TypeScript + Vite frontend; FastAPI + SQLAlchemy + psycopg backend; PostgreSQL 17 via Docker Compose; Alembic migrations.
- Windows project: C:\Users\s6601\work\scholarship-tracker. The active Codex checkout may differ; detect it.
- Database from project root: `docker compose up -d db --wait`.
- Backend from backend: `.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000`.
- Frontend from frontend: `npm run dev`; build check: `npm run build`.
- Import tests from backend: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_import_catalogue_json.py -v`.
- Use the environment's equivalent Python path on Linux/cloud. Do not assume the Windows venv transfers.

## Implementation and data rules

- Continue the working app; do not scaffold it again or replace the stack.
- Preserve unrelated local changes. Inspect diffs before editing or staging.
- Never print .env contents, expose credentials, or commit virtual environments, node_modules or build output. Use .env.example placeholders for setup guidance.
- Use Alembic for schema changes. Never reset the real database or delete its Docker volume to solve a migration problem. Preserve applied migrations.
- source_key is a stable opportunity/call identifier. Correcting titles does not change it; new cycles receive new keys. Preserve IDs during adoption.
- Default importer behavior is preview; --apply writes. Validate the entire batch and apply atomically. Draft/needs_review/archived entries stay out of public search.
- Unrecorded fields are not confirmed broad eligibility. Possible matches must stay visibly unverified; all other selected filters remain AND conditions.
- Country means study destination, not applicant nationality. Fiscal year is not necessarily intake year. Separate full funding, tuition-only, partial and unknown.
- Unknown dates, coverage or call status remain unknown. Never advance last_checked without checking the actual official source.
- Use primary official sources when adding or revising scholarship facts; record the review date. Do not publish fictional examples as real awards.

## Checks and GitHub

- Run relevant checks for a change. For importer work, run offline tests and a live PostgreSQL preview; for frontend changes, run the build and relevant interaction checks. Report what actually ran and any unavailable checks.
- Use feature branches and focused, meaningful commits. Preserve history; do not force-push or recreate old development activity.
- Commit/push when the user authorizes that milestone. Never silently merge into main, publish or deploy.
- Check git status, branch, remote and diff before committing. Stage task-specific files rather than all local files blindly.
- Keep docs/CODEX_HANDOFF.md current when a milestone finishes. The user chose to defer the full README until later; do not make that the next task.
- Explain completed behavior and validation in plain English so Arsu can discuss his project in an interview. Continue routine authorized work without repeated permission questions.
