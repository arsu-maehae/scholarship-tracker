# Scholarship Discovery — complete continuation handoff

Prepared: 18 November 2026, Asia/Bangkok.

This handoff supersedes the early planning-only Scholarship_Tracker_Project_Handoff.md. The application now exists and is working. Older planning documents describe features that have not been implemented. Current repository files and fresh command output are authoritative if they differ from this snapshot.

## PostgreSQL CI milestone - 18 November 2026

GitHub Actions runs the offline importer tests, frontend build, and PostgreSQL 17 integration test on pushes and pull requests. The integration test requires an explicitly configured empty `scholarship_tracker_test` database; it does not delete tables or touch the local application database. It runs both Alembic migrations from scratch, checks preview and repeat imports, and checks search filters and hidden review states. Database host and port can be set with `POSTGRES_HOST` and `POSTGRES_PORT`; existing local defaults remain unchanged.

For a local run, start an isolated PostgreSQL 17 instance with a new empty database named `scholarship_tracker_test`, set `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST` and `POSTGRES_PORT` for that instance, then run from `backend`: `python -m unittest discover -s tests -p test_postgresql_integration.py -v`. Never point the test at the real catalogue. The integration suite and SQLite suite run in separate processes because the SQLite tests alter model types in memory.

The next product milestone is to establish a source-review workflow and add a small, officially verified batch of scholarships. No source facts or review dates were changed during the CI milestone. Check Git and GitHub for current merge and CI status.

## 1. Owner, objective and working style

Owner: Arsu Maehae, Computer Engineering student at King Mongkut's University of Technology North Bangkok. This is a practical full-stack/software-engineering portfolio project, personally motivated by researching postgraduate scholarships.

The user wants to select country, degree, programme/field, funding coverage and other filters, then find relevant scholarships internationally. Current scope is a curated database-backed discovery catalogue, not an exhaustive worldwide search service. Build a maintainable import/review pipeline before attempting broad automation.

Use English unless Thai is requested. Give clear steps and explain enough for the user to discuss implementation in an interview. The user is still learning Git, Docker and running multiple services. Prefer direct implementation in Codex instead of asking him to copy small code fragments repeatedly. He chose to defer the full README until later. Show development through real feature commits; do not manufacture historical commits.

## Milestone update ? 18 November 2026

On the local Windows checkout, the JSON importer milestone was verified against the healthy PostgreSQL database at Alembic head `de4ceda7784b`. The fresh preview showed exactly five key-only adoptions; applying it preserved IDs 1, 6, 7, 8 and 9. A subsequent preview showed five unchanged, and all five records remain published. All 17 offline importer tests and the frontend build passed. Direct API search-function checks against PostgreSQL covered combined filters, strict AI matches, and possible matches marked unverified.

The feature is committed on `feat/json-catalogue-import`; check `git status` and the remote for the current push state. The original snapshot below describes the state before this update. A fresh-database PostgreSQL migration/import test and CI remain useful next steps. No scholarship sources were rechecked during this milestone; the existing review dates were not changed.

## 2. Exact current stopping point

The user added nullable unique Scholarship.source_key and successfully applied the second migration:

```text
Running upgrade 0eff656828ea -> de4ceda7784b, add scholarship source key
de4ceda7784b (head)
```

He copied the JSON importer bundle into the local backend and ran:

```powershell
.\.venv\Scripts\python.exe import_catalogue_json.py data/scholarships.json --validate-only
.\.venv\Scripts\python.exe import_catalogue_json.py data/scholarships.json
```

Observed results, directly supplied by the user:

```text
VALID: 5 records. No database connection or changes.
ADOPT: erasmus-mundus:ediss:2027-2029
  source_key: null -> "erasmus-mundus:ediss:2027-2029"
ADOPT: chevening:thailand:2027-2028
  source_key: null -> "chevening:thailand:2027-2028"
ADOPT: fulbright:thai-graduate:overview
  source_key: null -> "fulbright:thai-graduate:overview"
ADOPT: thai-government:regional-pre-study:fy2570
  source_key: null -> "thai-government:regional-pre-study:fy2570"
ADOPT: erasmus-mundus:emai:funding-overview
  source_key: null -> "erasmus-mundus:emai:funding-overview"
PREVIEW ONLY; nothing saved: 0 insert, 5 adopt, 0 update, 0 unchanged
```

This confirms JSON validation and the live PostgreSQL preview. Applying the adoption, rerunning the preview, running the 17 tests on his PC, and committing/pushing this feature have NOT been confirmed. Do not describe any of those as completed without fresh evidence.

The user now wants to transition from this ChatGPT conversation to Codex and work with GitHub. First finish this importer milestone; do not restart planning or rebuild the frontend.

## 3. Local environment and repository

| Item | Confirmed value |
| --- | --- |
| OS / terminal | Windows, VS Code, PowerShell |
| Project root | C:\Users\s6601\work\scholarship-tracker |
| Backend directory | root\backend |
| Python executable | backend\.venv\Scripts\python.exe |
| Frontend directory | root\frontend |
| GitHub repository | https://github.com/arsu-maehae/scholarship-tracker |
| origin configured by user | https://github.com/arsu-maehae/scholarship-tracker.git |
| Main branch | main |
| Intended current feature branch | feat/json-catalogue-import; actual checkout must be inspected |
| Frontend development URL | http://127.0.0.1:5173/ |
| Backend / Swagger | http://127.0.0.1:8000/ and /docs |
| PostgreSQL host port | 127.0.0.1:5433 |
| PostgreSQL container port | 5432 |
| Compose service | db |
| Observed container name | scholarship-tracker-db-1 |
| Database / role | scholarship_tracker / scholarship |

Versions observed earlier: Python 3.11.9, Node 20.19.5, npm 10.8.2, Git 2.51.0.windows.1, Docker 29.5.3, Compose v5.1.4, PostgreSQL image postgres:17. Frontend was created with create-vite 9.3.4, React/TypeScript template, ESLint selected. Actual installed versions should come from the current manifests/lockfiles, not assumptions about today's latest packages.

The user successfully pushed an initial commit to the public main branch. The screenshot showed short SHA a55168e and message feat: build scholarship discovery MVP. That is a historical observation, not a fresh remote inspection. No newer commit or upstream feature branch has been confirmed. Do not assume local importer/migration changes exist on origin yet.

The actual Windows checkout is separate from the ChatGPT preparation environment. Temporary Linux files used to prepare downloadable bundles are not the user's repository. A Codex cloud checkout will not automatically have his local .env, venv, database or uncommitted files. Prefer Codex in the existing VS Code folder for this transition.

## 4. Architecture and files

The browser uses relative /api requests to Vite. Vite proxies /api to FastAPI on port 8000. FastAPI uses SQLAlchemy/psycopg to reach the Docker PostgreSQL instance through host port 5433. No CORS change was needed for this development setup.

Expected structure (inspect current files):

```text
scholarship-tracker/
  AGENTS.md                         proposed durable guidance in this handoff bundle
  docs/CODEX_HANDOFF.md             this document
  .env                             local configuration; never print or commit
  .env.example                     placeholder configuration
  .gitignore
  compose.yaml
  README.md                        initially empty; full documentation deferred
  backend/
    .venv/
    requirements.txt
    database.py
    models.py
    main.py
    seed.py
    seed_scholarships.py
    import_catalogue.py            older fixed-snapshot importer
    import_catalogue_json.py       current reusable importer
    data/scholarships.json         five-record schema_version 1 catalogue
    tests/test_import_catalogue_json.py
    alembic.ini
    migrations/
      env.py
      README
      script.py.mako
      versions/
        0eff656828ea_create_scholarship_catalogue.py
        de4ceda7784b_add_scholarship_source_key.py
  frontend/
    package.json
    package-lock.json
    vite.config.ts
    src/
      main.tsx
      App.tsx
      App.css
      index.css
      countries.ts
      filters.css
```

Backend dependencies previously specified: fastapi, uvicorn[standard], sqlalchemy>=2.0,<3.0, psycopg[binary]>=3.1,<4.0, python-dotenv, alembic. The reusable importer and its unittest suite require no new dependency beyond the backend environment.

database.py loads the project-root .env with python-dotenv and builds sqlalchemy.URL.create with POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB, postgresql+psycopg, host 127.0.0.1, port 5433. Engine uses pool_pre_ping and a five-second connection timeout. Read the loader code if needed; do not print the actual .env or connection URL/password.

compose.yaml provides db with health checks and a persistent postgres_data volume, publishing only 127.0.0.1:5433. Never delete that volume as a routine troubleshooting step.

## 5. Database schema and migrations

ScholarshipScheme / scholarship_schemes:

- id primary key; name String(150) unique; slug String(100) unique.

Scholarship / scholarships:

- id primary key; scheme_id indexed foreign key to scholarship_schemes.id, ondelete RESTRICT.
- source_key nullable String(200), unique. Added in the second migration.
- title String(250), cycle nullable String(100), intake_year nullable integer, description nullable Text.
- countries nullable PostgreSQL ARRAY(String(2)); degree_levels ARRAY(String(40)); fields_of_study ARRAY(String(100)).
- funding_category String(20): full, tuition_only, partial, unknown; default unknown.
- funding_notes nullable Text.
- call_status String(20): open, upcoming, closed, unknown; default unknown.
- review_state String(20): draft, needs_review, published, archived; default draft.
- official_url nullable Text; last_checked nullable Date; created_at timezone-aware DateTime, server default now.

The model has named check constraints for funding, call status and review state. Only published records are returned by public search.

Applied revisions: 0eff656828ea created the catalogue; de4ceda7784b added source_key. Alembic generated an unnamed uniqueness warning. The user fixed the migration to use uq_scholarships_source_key in both create_unique_constraint and drop_constraint, then successfully upgraded. The old warning comment in downgrade may still be present; the executable code was fixed. Do not regenerate or duplicate this applied migration.

## 6. API contract

main.py is currently version 0.2.0 following the filter update.

| Endpoint | Behavior |
| --- | --- |
| GET /health | {"status":"ok"} |
| GET /health/db | Queries current_database(); returns status and database; DB errors become 503 |
| GET /api/schemes | Array of id/name/slug, sorted by name |
| GET /api/filter-options | {"fields":[...]}, deduplicated lowercase tags from published records |
| GET /api/scholarships | Published catalogue, AND filters, counts, pagination, match metadata |

Scholarship search query parameters:

- country: two-letter code, normalized uppercase; uses ARRAY contains.
- degree: bachelor/master/phd/master_phd.
- field: nonblank trimmed lowercase tag, max 100 characters.
- include_unknown_fields: boolean, false by default for backward compatibility. With a field filter and true, include null or empty field lists as unverified possibilities. It does not broaden any other filter.
- funding: full/tuition_only/partial/unknown.
- scheme: slug, max 100 characters.
- intake_year: integer 1900–2200.
- limit: 1–100, default 20; offset >=0, default 0.

Response envelope: total, limit, offset, items. Items include id, title, scheme:{name,slug}, cycle, intake_year, countries, degree_levels, fields_of_study, field_match, funding_category, funding_notes, call_status, official_url, last_checked. There is no source_key field in the public serializer yet.

field_match is exact / unverified / not_filtered. Exact means the field tag was recorded, not personal eligibility. Unverified means null/empty field data, not proof the scholarship supports all subjects. When field-filtered, exact matches are ordered first with SQL CASE, then ID; otherwise order by ID. Counts use the same filtered statement before pagination.

There is no search text q, deadline filter, detail endpoint, authenticated write API or user-account system currently. Do not invent supported endpoints.

## 7. Frontend behavior and verified flows

App.tsx fetches schemes, field options and paginated results via /api. It has separate draft/applied filters; Find scholarships applies changes. Reset clears them. Fetch effects use AbortController to avoid stale responses. There are loading, failure/retry and no-match states. Official source links are limited to HTTP(S), opened with noopener/noreferrer. Funding/source notes expand inline.

Country selector: 249 ISO country/territory codes in countries.ts, English names via Intl.DisplayNames, alphabetically sorted. Listing a country does not imply catalogue coverage. Field selector loads indexed tags and shows friendly labels. Include possible matches with unrecorded fields is checked by default but disabled while no field is selected; select a field to enable it. Changing it still requires Find scholarships. This disabled state confused the user earlier; explain it plainly if asked.

Scheme labels are prominent. EDISS is shown as a programme under Erasmus Mundus; do not relabel the entire scheme as EDISS. The user specifically requested this distinction.

User screenshots confirmed: unfiltered five results after catalogue expansion; FI gives EDISS; US initially zero before adding Fulbright; FI + master's + full gives one; same with tuition-only gives zero. After the filter update, AI with possible matches unchecked returned two entries (EDISS/EMAI) with recorded-field messages. The user reported seeing five after the earlier instruction, but a subsequent screenshot showed Any field; do not treat that screenshot alone as proof of the AI-inclusive case. Recheck combinations locally if changing filtering.

Expected current fixtures if the five records are unchanged:

| Filters | Result |
| --- | --- |
| Reset | 5 |
| FI + master + full | EDISS only |
| GB + master + full | Chevening only |
| US + master + partial | Fulbright only |
| US + master + full | 0 |
| field=ai, strict default | EDISS and EMAI |
| field=ai, include_unknown_fields=true | EDISS and EMAI first; Chevening/Fulbright/OCSC unverified |
| GB + master + ai, possible enabled | Chevening, unverified field |
| Same, strict only | 0 |

These are fixture expectations, not comprehensive scholarship availability or eligibility conclusions.

## 8. Current catalogue and research limits

There are four schemes and five published entries. The JSON carries the earlier research snapshot dated 17 November 2026; building the importer on 18 November did not reverify scholarship facts. Verify time-sensitive facts from official sources before updating them.

| Stable source_key | Entry and stored meaning |
| --- | --- |
| erasmus-mundus:ediss:2027-2029 | EDISS; cycle 2027–2029, intake 2027, destinations FI/SE/IT/ES, master, ai/data-science/software-engineering, full funding, call unknown |
| chevening:thailand:2027-2028 | UK master's, intake 2027, full funding, closed status in the snapshot, fields unrecorded |
| fulbright:thai-graduate:overview | US master's or PhD, partial support, intake/call unknown, fields unrecorded |
| thai-government:regional-pre-study:fy2570 | OCSC regional pre-study appointment master's overview, fiscal FY2570, destination/field/intake/funding unknown, open in the snapshot |
| erasmus-mundus:emai:funding-overview | EMAI programme/funding overview, ES/IT/NL/SI, master, ai/data-science/robotics/cybersecurity, next intake/funding/call unknown |

Official source URLs stored or used earlier:

- EDISS: https://www.master-ediss.eu/scholarship/
- Chevening: https://www.chevening.org/scholarship/thailand/ and https://www.chevening.org/faqs/what-does-a-chevening-scholarship-cover/
- Fulbright: https://www.fulbrightthai.org/tgs
- OCSC: https://www.ocsc.go.th/scholarships/degree-scholarships/ and https://scholar.ocsc.go.th/
- EMAI: https://www.upf.edu/web/emai, /faqs, /academic-information and /about-this-master.

Important decisions: Fulbright TGS was marked partial because its official FAQ says support is usually partial; do not assume Fulbright means all costs funded. OCSC fiscal year is not an intake year; specific award codes determine destinations, subjects, coverage and obligations. It is an overview, not an individual award. EMAI's older FAQ referred to funding in the first four editions, so later intake funding was deliberately left unknown. EDISS was retained from the earlier seed and not rechecked during importer development.

## 9. JSON importer behavior

File shape: an object with exactly schema_version:1 and scholarships:[...]. Required per record: source_key, scheme_slug, title, cycle; cycle may be null. Other properties are optional. New records default draft with unknown funding/call and nullable metadata. Existing rows preserve omitted properties; explicit null clears nullable values. Removing an entry from JSON does not delete it; use archived to hide intentionally.

Accepted record properties: source_key, scheme_slug, title, cycle, description, funding_notes, official_url, countries, degree_levels, fields_of_study, intake_year, funding_category, call_status, review_state, last_checked. Unknown properties, duplicate JSON properties, duplicate source keys and duplicate scheme/title/cycle identities are rejected.

Validation includes field lengths, lowercase stable-key/tag patterns, assigned uppercase ISO country codes, enum values, actual ISO dates, nonfuture last_checked, absolute HTTPS URLs without credentials, UTF-8/BOM support, maximum 5 MiB file and 2000 records. Scheme slugs must already exist. Publication requires official_url and last_checked after merging with existing data. That is a mechanical gate, not source verification. Drafts remain hidden.

Identity algorithm: find source_key first. If absent, look for exact scheme ID + title + cycle. A unique unkeyed row is adopted, preserving ID. Multiple legacy matches, a different key already owning that natural identity, scheme reassignment, or two inputs targeting one row abort. A stable-key title correction updates the same row if it creates no identity conflict. New cycles should receive new keys; do not reuse a key to overwrite historical rounds.

Plan actions: INSERT, ADOPT, UPDATE, UNCHANGED. Array order is ignored for comparisons. Incoming older last_checked dates cannot overwrite newer database research. Preview prints changes without mutating or flushing rows; --validate-only avoids the database entirely. Apply validates/plans the full batch and writes in one transaction. PostgreSQL apply takes advisory transaction lock 724139802 (shared with the old importer) plus a SHARE ROW EXCLUSIVE table lock on scholarships for adoption consistency. It preserves existing IDs/created_at and does not delete records.

Older seed.py creates schemes idempotently. seed_scholarships.py adds EDISS if its original identity is absent. import_catalogue.py is the previous four-entry fixed-snapshot importer (insert/skip only). Prefer import_catalogue_json.py going forward and avoid running older seed/import scripts after renaming identities; their title-based logic could reintroduce legacy duplicates.

## 10. Commands that work

Run Docker from root:

```powershell
cd C:\Users\s6601\work\scholarship-tracker
docker desktop start
docker info --format '{{.ServerVersion}}'
docker compose up -d db --wait
docker compose ps
docker compose exec -T db psql -P pager=off -U scholarship -d scholarship_tracker -c "SELECT current_database();"
```

Run backend in its own terminal:

```powershell
cd C:\Users\s6601\work\scholarship-tracker\backend
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend in another terminal:

```powershell
cd C:\Users\s6601\work\scholarship-tracker\frontend
npm run build
npm run dev
```

Do not start a second Vite instance if 5173 is already occupied by this app. Reload the browser after file changes. Stop a foreground server using Ctrl+C only when restarting that service.

Importer/migrations/tests from backend:

```powershell
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe import_catalogue_json.py data/scholarships.json --validate-only
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_import_catalogue_json.py -v
.\.venv\Scripts\python.exe import_catalogue_json.py data/scholarships.json
# Next write, after confirming the key-only adoption plan:
.\.venv\Scripts\python.exe import_catalogue_json.py data/scholarships.json --apply
# Must then show five unchanged:
.\.venv\Scripts\python.exe import_catalogue_json.py data/scholarships.json
```

## 11. Troubleshooting history

- empty compose file: the initial compose.yaml was empty; populated later. It is now working. Do not overwrite it merely because an old log mentions this.
- Docker API pipe missing: error included npipe:////./pipe/dockerDesktopLinuxEngine and The system cannot find the file specified. Docker Desktop's Linux engine was stopped. Starting Docker Desktop, waiting for Engine running and rerunning compose solved it. This recurred after restarting the PC.
- Vite ECONNREFUSED 127.0.0.1:8000: FastAPI was not running. Start it in a separate terminal; old proxy messages are not new failures.
- API 500 after FastAPI started: PostgreSQL was unavailable while Docker was stopped. Check /health/db after starting db, rather than changing frontend code.
- Terminal showed (END): psql pager. Use -P pager=off and exec -T for scripted checks.
- src refspec HEAD does not match any: no first Git commit existed. Commit staged source before pushing.
- nothing to commit / Everything up-to-date: no saved file changes; git commands do not write a README. The user then chose to defer the README.
- Unnamed constraint warning from Alembic: fixed by naming both create and drop as uq_scholarships_source_key before applying; current head is confirmed.
- Checkbox could not be unchecked: disabled while Any field was selected. Choosing AI enabled it and the user successfully got the two strict matches.

## 12. Validation evidence and outstanding checks

Confirmed on the user's PC through command output/screenshots: Docker db healthy; /health and /health/db; migrations at head; four schemes; five-entry catalogue; multiple country/degree/funding filter checks; friendly filter update; strict AI results; JSON validation and five-adoption live preview.

Performed in the separate preparation environment: strict TS compilation and frontend bundling; DOM interaction checks with a mock API for country/field labels, queries, reset, exact/possible notices and error retry; API checks with SQLite emulation for PostgreSQL arrays and PostgreSQL SQL compilation; 17 importer unittests using disposable SQLite with JSON substitutions for ARRAY columns. Local importer tests cover validation, draft defaults, preservation/null clearing, stable-key rename, legacy adoption, ambiguous/conflicting identities, stale dates, no-op repeats and transaction rollback on an injected failure. These tests are shipped in backend/tests/test_import_catalogue_json.py.

Preparation environment had no live PostgreSQL service and a visual Chromium launch was blocked. Do not claim its SQLite tests validated PostgreSQL locking or visual layout. The user has now validated the read-only PostgreSQL preview; apply/locking and a complete fresh-database migration/import path still need live verification.

## 13. GitHub workflow and handoff continuity

Inspect first from root:

```powershell
git status --short --branch
git branch --show-current
git remote -v
git log -5 --oneline
git diff --stat
```

The intended branch feat/json-catalogue-import was instructed but branch creation was not shown. If currently on main, create the feature branch while preserving current work. If it exists, inspect before switching; do not discard changes or reset branches. Existing origin is already configured: do not add it again.

When checks pass, stage only related model/migration/importer/data/tests plus the new handoff files. Exclude .env, backend/.venv, __pycache__, frontend/node_modules, frontend/dist and temporary output. Review git diff --cached and git status; never blindly stage all unrelated user changes.

Suggested feature commit: feat: import scholarship catalogue from JSON. Push the feature branch, e.g. git push -u origin feat/json-catalogue-import, then review it through a GitHub pull request into main. Do not merge automatically. A push records code/files, not the user's PostgreSQL data or running environment. CI checks have not been added yet. No PR is confirmed to exist.

Keep AGENTS.md for durable conventions and this document for dated state. Before ending a milestone, update completed/pending status and the next step. In a new Codex session, start by reading both. This prevents dependence on the original ChatGPT conversation.

## 14. Scope not implemented; next milestones

Not implemented: worldwide crawling, scheduled ingestion, programme-title text search, source parsing adapters, admin review UI, authentication, personal saved lists in the real backend, application tracking, document uploads, eligibility scoring, deadline/reminder system, CI or real application deployment. A separate static prototype existed earlier; it is not the working React/FastAPI/PostgreSQL deployment and should not be mistaken for current production infrastructure.

The importer adoption and verification described above are complete. Check Git status and remote state before deciding the next task.

After that, choose one manageable milestone: add PostgreSQL-backed CI tests/fresh-database migration verification, or prepare a small set of newly verified records through the draft/review workflow. Source-specific automated imports come after that foundation. Do not add a large set of unsourced or fictional awards to inflate coverage.

The long-term product remains scholarship discovery useful to Arsu, with honest source provenance and uncertainty, and portfolio-quality engineering he can explain.
