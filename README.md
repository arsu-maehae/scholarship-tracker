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

After saving, use **Extract all source pages** or select an individual official page. Public HTTPS HTML pages are fetched with destination and redirect checks; PDFs, blocked or JavaScript-only pages can use pasted public text or manual entry. Suggestions quote short excerpts, may be incomplete, and do not change confirmed fields until you apply and save them. If a later attempt fails, the last useful suggestions remain visible.

## Short demo: EMMIR to a checklist

1. Save `https://www.emmir.org/`, open the record, and choose **Extract all source pages**. Review the official links and excerpts.
2. Under **Proposed checklist tasks**, edit a document task and choose **Accept task**. It is saved to the checklist; repeat extraction without creating another copy of the same sourced proposal.
3. In **Application checker**, enter and save your profile facts. Choose an eligibility excerpt, select the relevant profile fact, and enter exact wording from the excerpt to add it for review. Read its status, explanation and official source. Replace any synthetic test profile values with your own.
4. If you choose an applicant-specific deadline, click **Save changes** to confirm it. Return to the dashboard to see the saved deadline and checklist progress; optionally set a task due date.

The checker assists review, not an eligibility decision. Missing, conflicting and complex conditions generally show **verify**. It does not interpret equivalence, exceptions, score thresholds, EEA membership or institution-specific rules; the narrow **met** and **prepare** rules cover only certain explicit sentence forms. Extraction can miss details, and the official source may have changed. Check full requirements with the provider. See [the synthetic-profile evaluation](docs/APPLICATION_CHECKER_EVALUATION.md) for cases and gaps. No AI or paid API is used.

## Checks

```powershell
cd C:\Users\s6601\work\scholarship-tracker-restart\backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_import_catalogue_json.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_tracked.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_extraction.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_checker*.py -v
cd ..\frontend
npm test -- --run
npm run lint
npm run build
```

Database integration tests require a new, empty **disposable** PostgreSQL database named `scholarship_tracker_test` and matching `POSTGRES_*` environment variables; `test_postgresql_integration.py` refuses to clear an existing database and creates the schema only when it is empty. Run it first, then `test_tracked.py` and `test_extraction.py`. Never point these checks at your personal database.

## Backup and recovery

Backups contain your private scholarship records, notes and profile. Keep them in a private location outside Git and retain more than one copy. These commands use the isolated `scholarship-tracker-restart` Compose project and the default database user `tracker_local`; they do not connect to the original project's database. If you changed the database user, adapt the scripts only after checking your configuration. Start Docker Desktop and the restart database first:

```powershell
cd C:\Users\s6601\work\scholarship-tracker-restart
docker compose --project-name scholarship-tracker-restart --file compose.yaml up -d db --wait
.\scripts\Backup-Tracker.ps1
```

The script prints a unique `.dump` file in `Documents\ScholarshipTrackerBackups`; it never intentionally replaces an existing file. You can choose another existing or new private directory with `-BackupDirectory "C:\path\to\private\backups"`. The dump is a consistent snapshot of the restart database at export time. Record its path for recovery.

To restore, choose a **new** name beginning `scholarship_tracker_restore_`, followed by lowercase letters, digits or underscores. The script refuses an existing database and the live database name; a failed restore leaves the newly created database in place for inspection, without overwriting anything:

```powershell
.\scripts\Restore-Tracker.ps1 -BackupFile "C:\path\to\your\backup.dump" -RecoveryDatabase scholarship_tracker_restore_check1
```

Check the recovered schema version and record counts. Replace `scholarship_tracker_restore_check1` with your chosen name in both commands. Compare with the source only if it has not changed since the backup; otherwise differences may be expected.

```powershell
docker compose --project-name scholarship-tracker-restart --file compose.yaml exec -T db psql -U tracker_local -d scholarship_tracker_restore_check1 -c "select version_num from alembic_version; select (select count(*) from tracked_scholarships) as scholarships, (select count(*) from tracked_checklist) as tasks, (select count(*) from student_profile) as profiles, (select count(*) from reviewed_requirements) as reviewed_requirements;"
docker compose --project-name scholarship-tracker-restart --file compose.yaml exec -T db psql -U tracker_local -d scholarship_tracker_restart -c "select version_num from alembic_version; select (select count(*) from tracked_scholarships) as scholarships, (select count(*) from tracked_checklist) as tasks, (select count(*) from student_profile) as profiles, (select count(*) from reviewed_requirements) as reviewed_requirements;"
```

Counts alone cannot prove that the contents are correct. To inspect the restored records in the app, stop the existing backend, then in a **separate PowerShell window** run the following with your recovery name. Check `http://127.0.0.1:8000/health/db` reports that name before opening the frontend at `http://127.0.0.1:5173`. Inspect scholarship links, notes, funding, checklist and profile. Changes made while connected here affect the recovery database, not the original restart database.

```powershell
cd C:\Users\s6601\work\scholarship-tracker-restart\backend
$env:POSTGRES_DB = 'scholarship_tracker_restore_check1'
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

When finished, stop that backend and close its PowerShell window. Start the normal backend in a fresh window with no `POSTGRES_DB` override, and check `/health/db` reports `scholarship_tracker_restart`. The restore does not replace the live database. Do not reset, delete, or restore over either existing database or Docker volume to recover data; keep the backup and verified recovery database until you decide on a separate recovery plan.
