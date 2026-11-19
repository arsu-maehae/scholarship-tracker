# Scholarship Tracker

A private, local workspace for scholarship links, deadlines and application tasks. Saving a link never fetches it. Optional extraction uses simple rules and source excerpts; it does not use AI, and you decide which suggestions to apply. Dates are not confirmed automatically.

## Requirements

Windows with Docker Desktop, Python 3.11, Node.js 20 or newer, npm and Git. The checked development setup uses PostgreSQL 17, React, Vite and FastAPI. Run commands from the restart worktree, not the old checkout.

## Start for the first time (PowerShell)

```powershell
cd C:\Users\s6601\work\scholarship-tracker-restart
docker compose up -d db --wait
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "from database import engine; from sqlalchemy import text; c=engine.connect(); n=c.scalar(text('select current_database()')); print(n); assert n=='scholarship_tracker_restart'; c.close()"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

In a second PowerShell terminal:

```powershell
cd C:\Users\s6601\work\scholarship-tracker-restart\frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. The backend is at http://127.0.0.1:8000. These defaults use a separate `scholarship-tracker-restart` Compose project and volume on localhost port 5434, with a local development database and development-only credentials. They do not use the original project's database on port 5433. To override local PostgreSQL settings, use environment variables `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, and `POSTGRES_PORT` consistently for Compose and the backend. Never commit real credentials or database backups.

If Docker Desktop is closed, start it and wait until it is running, then repeat `docker compose up -d db --wait`. Existing data remains in the restart project's Docker volume. Do not run `docker compose down -v` or delete volumes to troubleshoot.

## Using the tracker

Paste a public HTTP(S) information-page link and select **Save scholarship**. Use the detail screen to add facts, a confirmed deadline, status, notes and checklist items. The dashboard shows saved items and deadline states in the Asia/Bangkok calendar. Archive and restore items independently of status. A repeated normalized URL opens the existing item rather than creating a duplicate.

After saving, **Extract from page** is optional. The allowlist in `backend/official_page.py` currently contains `www.ox.ac.uk`, `www.studyinnl.org` and `www.studyinjapan.go.jp`. Only public HTML on these exact HTTPS hosts is fetched, without redirects or credentials; other pages, PDFs and failures can use pasted public text or manual entry. Suggestions quote short excerpts, may be incomplete, and do not change your confirmed fields until you apply and save them. If a later attempt fails, the last useful suggestions remain visible. The Oxford live smoke check was redirected and safely refused, so live provider extraction was not verified in this environment.

## Checks

```powershell
cd C:\Users\s6601\work\scholarship-tracker-restart\backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_import_catalogue_json.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_tracked.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_extraction.py -v
cd ..\frontend
npm run lint
npm run build
```

Database integration tests require a new, empty **disposable** PostgreSQL database named `scholarship_tracker_test` and matching `POSTGRES_*` environment variables; `test_postgresql_integration.py` refuses to clear an existing database and creates the schema only when it is empty. Run it first, then `test_tracked.py` and `test_extraction.py`. Never point these checks at your personal database.

## Backup and recovery

Keep backups outside Git. With the restart database running and its default user unchanged, create a custom-format backup inside the restart container and copy it to a private location:

```powershell
docker compose exec -T db pg_dump -U tracker_local -d scholarship_tracker_restart -Fc -f /tmp/tracker-backup.dump
docker compose cp db:/tmp/tracker-backup.dump "$env:USERPROFILE\Documents\scholarship-tracker-backup.dump"
```

To inspect or recover a backup without overwriting current records, create a **new** database in the same isolated server, copy the backup into the container, and restore into that new database. The commands below fail if the recovery database already exists; choose a new name instead of dropping anything:

```powershell
docker compose exec -T db createdb -U tracker_local scholarship_tracker_recovery
docker compose cp "$env:USERPROFILE\Documents\scholarship-tracker-backup.dump" db:/tmp/tracker-recovery.dump
docker compose exec -T db pg_restore -U tracker_local -d scholarship_tracker_recovery /tmp/tracker-recovery.dump
```

These commands do not replace the running database. Check the recovered data before deciding whether to use it; do not restore over existing personal data without a separate backup and an explicit decision.
