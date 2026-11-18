# Scholarship Tracker — Codex build plan

**Owner instruction to Codex.** Implement this plan in my existing scholarship-tracker repository. This file supersedes the old discovery, worldwide search, and AI search roadmaps. Work through all milestones in order. Test, commit, and push each completed milestone to GitHub. Update the progress table as you go. Continue independent work when something is blocked, and use this same file to resume in a new session.

## 1. What we are building

Build my personal scholarship application workspace. I paste a scholarship announcement link, get a summary with evidence from the source, correct and save it, and track the application through deadlines, preparation, submission, interviews, and the result.

~~~mermaid
flowchart TD
    A["Paste a scholarship link"] --> B["Extract facts and evidence"]
    B --> C["Review and save"]
    C --> D["Track deadlines and tasks"]
    D --> E["Record the submission and result"]
~~~

**My Applications** is the home page. **Add from link** is its main action. Offer **Paste announcement text** and **Add manually** so I can continue when a page or AI provider is unavailable. The official provider handles submissions. This app links to the provider and tracks my work. Build a single-user app that runs locally.

## 2. Start from the existing project

- GitHub repository is [arsu-maehae/scholarship-tracker](https://github.com/arsu-maehae/scholarship-tracker). The Windows checkout has been at **C:\Users\s6601\work\scholarship-tracker**, using VS Code and PowerShell. Detect the actual checkout.
- Reuse React, TypeScript, Vite, FastAPI, SQLAlchemy, PostgreSQL in Docker Compose, Alembic, and GitHub Actions. Check dependency files and existing test commands.
- The 18 November 2026 snapshot reported a merged JSON catalogue importer and PostgreSQL CI, plus 12 published records in the owner's local database. Later work included keyword search, web suggestions, and a Gemini CLI prototype. Treat this as historical context. Inspect current files, Git, and test results to establish what exists now.
- Read repository instructions. Check the branch, remote, history, tracked and untracked changes, DB migration state, and baseline test/build results. Use a disposable DB for experiments and fresh installation tests.
- This task authorizes the in-scope implementation, cleanup, tests, additive development migrations, commits, and feature-branch pushes below. Keep going without asking at every milestone. Surface concrete blockers such as unavailable credentials, an inaccessible checkout, or a destructive action that would require the owner's decision. Merging into the default branch and deploying require separate authorization.
- The owner wants the actual repository developed. A detached scratch copy or mock demo alone is insufficient. If the local Windows folder is unavailable, work against the accessible repository branch and accurately distinguish its database from the owner's local database.

## 3. Retire the unrelated work

| Earlier feature | What to do on the active feature branch |
| --- | --- |
| Worldwide discovery, external web results, and Brave search | Remove the active interface, provider wiring, routes, and obsolete settings, docs, tests, and dependencies. Verify no Brave or other external search calls remain in the tracker. |
| Natural-language catalogue search | Retire the feature. Reuse the Gemini client, structured output validation, and fetch restrictions only where they serve link intake. |
| Catalogue-first home page and public discovery filters | Replace the product entry point with My Applications. Retain shared components or a simple way to save an existing opportunity only if useful to tracking. Search and status filters for personal applications remain in scope. |
| Existing scholarship data, source keys, JSON importer, and Alembic history | Preserve rows, stable keys, and applied migrations. Retain the importer and its checks where used to maintain or bootstrap existing data. Keep personal records separate. |
| Prior docs and Git history | Update obsolete active docs so old goals or provider setup no longer direct development. Keep recoverability in Git. This plan is the only product roadmap. |

Inspect dependencies and callers before removing code. Preserve unrelated work and locally checkpoint relevant uncommitted code before removing it if needed. Verify staged files before committing any checkpoint. Keep secrets, data dumps, private records, and ignored files outside commits. Avoid resets that discard work, deleting historical branches, rewriting history, dropping old tables, or deleting Docker volumes. Add personal tracker tables with Alembic. Existing data does not need to become personal applications automatically.

## 4. What to extract from a source

When a supported page is available, return an editable draft for one scholarship and intake. If the source contains different awards, cycles, or conflicting dates, let me choose or correct the relevant facts. Keep the scholarship scheme and study programme distinct.

| Section | Facts to capture when stated |
| --- | --- |
| Opportunity | Award name, programme, provider, destination, degree, intake, original announcement, and official application URL |
| Funding | Tuition, stipend, travel, caps, duration, and costs the applicant still pays |
| Eligibility | Nationality, degree, GPA, experience, and other conditions |
| English | Accepted tests, minimum scores, exemptions, and when to submit results |
| Deadlines | Application and document deadlines, precision, relevant cycle, stated time and timezone |
| Documents and process | Checklist candidates, references, essays, application portal and steps |
| Obligations | Service, residency, or return requirements |

Show a supporting excerpt and its source URL or pasted-text reference for material extracted facts. Check excerpts against the actual input text. Show evidence as plain text and give me the source link. Review confirms whether each excerpt actually supports the fact. Mark missing or ambiguous details clearly. Keep dates as stated, including date-only values and unknown timezones. Never guess an unstated year, timezone, eligibility condition, or funding term. Record retrieval time separately from human review time.

### Retrieval and review

- Start with selected official public HTML pages. Inspect and reuse the existing narrow allowlist and fetcher if suitable. Verify a supported-source fixture end to end. Provide an actionable error for unsupported or unreadable sources.
- Restrict the server fetcher to known official HTTPS hosts. Validate network destinations, keep the connection on validated public addresses, reject unsafe redirects, and bound response size, extraction size, and elapsed time. Restrict the feature to this local tracker. Treat page text as untrusted data and process it without obeying embedded instructions. Validate generated fields before showing them. Render source and model output safely.
- For blocked pages, login walls, script-heavy sites, or PDF announcements, preserve the URL and let me paste public announcement text or fill in a draft manually. A text-based PDF path may be reused if already available and testable locally. Pasted text is the fallback for other PDFs. OCR and universal website support are outside this release.
- Keep fetched and interpreted facts in a draft until I explicitly save. Caching or repeating extraction must not create a personal application. Give me a chance to edit the draft first. Never submit anything to the provider on my behalf.
- Offer a manual **Refresh source** action. Show proposed differences and evidence before accepting updates. Preserve personal notes, progress, preparation deadlines, and completed tasks.

### Zero-spending requirement

- Treat the budget as **zero**. No paid services, billing activation, payment method, credits, trial, paid hosting, or paid fallback. Keep Google Search grounding, Brave, and other search providers out of the flow.
- Gemini is optional, disabled by default, and used for structured extraction of public source text only. Keep its credential server-side in the ignored root .env. Use placeholders in .env.example. Keep personal notes, applications, documents, and credentials out of model prompts, logs, committed fixtures, and CI.
- Before a live test, verify the current model in official Google model, pricing, and billing docs and in the dedicated project's Free tier. Confirm the project still has no linked billing account. Verify the configured model and its actual routing. The earlier prototype named gemini-3.7-flash, which was reported to route to a successor. An API key or confirmation flag alone does not verify billing status. Honor the owner's existing authorization only within its verified scope.
- Use a supported free model only. Limit requests, input, output, and time. Cache repeated extraction if useful. Stop on quota, billing, or model-access errors and keep manual entry available. Never upgrade or substitute a paid tool.
- Run all automated checks with fixtures or mocked responses, including CI. If a no-cost live path cannot be verified, finish the rest of the product, demonstrate the mocked flow, and report the live provider check as pending. Keep the app usable with AI disabled.

## 5. Persistent tracker

Implement application records, source snapshots or evidence, deadlines, and checklist tasks with migrations that work on a clean and previously populated database. Use internal IDs. Treat source URL and cycle together as a duplicate signal because a provider can reuse the same URL next year. Offer to open an existing record instead of silently overwriting it. Keep separate cycles possible.

- **My Applications** shows saved opportunities, statuses, the next deadline, and the next action. Provide text search, status filtering, an empty state, and a way to revisit archived entries.
- **Application detail** supports editing reviewed facts, personal notes, deadlines, and tasks. Let me accept, edit, or skip checklist items suggested from required documents. Tasks can be added, edited, completed, and removed. Permit status and date corrections without losing submission or outcome details.
- **Deadlines** distinguish official dates from personal preparation dates. Show unknown dates separately and keep date-only precision. Show the source timezone for timed official deadlines when known.
- **Progress** starts at Researching and supports Preparing, Submitted, Result received, and Withdrawn. Record submission date, interview date if applicable, and outcome such as accepted, waitlisted, or rejected. Provide archive and restore.
- **Dashboard** surfaces upcoming and overdue deadlines and tasks, plus next actions. Entries without recorded deadlines remain visible. Check persistence across a reload and service restart.
- Bind to localhost by default. Account systems, public deployment, automated submissions, alerts, reminders, and worldwide discovery are outside this release.

## 6. Build, verify, commit, and push

Complete these milestones in order. Verify behavior through the real browser, API, and database as applicable. Run the existing checks too. Add focused tests for new behavior existing checks would miss. Use fixtures and disposable data for smoke tests.

| Milestone | Work and acceptance criteria | Suggested commit |
| --- | --- | --- |
| 1. Pivot and cleanup | Preserve needed work. Retire discovery and provider paths that have no tracker role. Establish My Applications as the entry point. Align active docs and CI. Verify startup and build, and preserve existing rows and migration history. | feat: refocus app on scholarship tracking |
| 2. Manual tracker | Save, edit, and archive applications with notes, progress, deadlines, next action, and task CRUD. Verify without an AI key, including persistence and both fresh and upgrade migrations. | feat: add persistent scholarship application tracker |
| 3. Link intake | Deliver source fetching, structured extraction, evidence review, ambiguity handling, fallback, and explicit save in the browser. Test a controlled official-link fixture, unreadable source, missing facts, wrong evidence, and quota or disabled AI. | feat: review scholarship facts from a source link |
| 4. Planning | Add dashboard, checklist suggestions, date precision, outcomes, and manual refresh with a diff. Verify duplicate handling and retention of personal data after refresh. | feat: add application planning and source refresh |
| 5. Delivery | Run final backend checks, frontend lint/build, migrations, CI, and browser walkthrough. Write a polished README with local setup, optional no-cost extraction setup, and known limits. Complete this progress table and push the final branch. | docs: document and verify scholarship tracker |

### GitHub workflow

1. Verify the existing origin and use a feature branch such as **feat/personal-scholarship-tracker**. Choose the base after checking which branches hold needed work. Preserve unrelated local edits and existing commits.
2. For each verified milestone, review the diff and stage only scoped changes. Ensure private files and incidental build output stay ignored. Commit the milestone with its progress entry and push to the feature branch. The owner authorizes ongoing milestone pushes without another confirmation.
3. Verify the pushed remote commit. Check available GitHub Actions results and fix relevant failures with new commits. Keep verified commits locally and continue independent work if authentication or access blocks a push. Report the exact blocker. Do not force-push or auto-merge.
4. At completion, provide the branch, commit IDs, tests and browser results, and a GitHub comparison or PR link if available. Keep the owner’s application data local.

### Final browser walkthrough

- With AI disabled and an empty test database, manually add an application and its deadline, next action, and one task. Confirm persistence after reload and service restart.
- Import a supported link with known example facts. Review the funding and deadline excerpts, correct a fact, and save one record. Use a controlled mocked response if live free AI is unavailable and disclose that. If a live free test is available and authorized, verify one provider response separately.
- Attempt an unsupported link. Paste announcement text or enter it manually and confirm the original URL is retained. Verify the same recovery behavior for quota exhaustion.
- Complete a task, submit the application in the tracker, and record an interview or outcome. Verify the dashboard updates. Check that duplicate handling and source refresh preserve personal data.
- Verify clean setup from the README, database migration on existing and new data, and no retired-provider requests or credential requirements for ordinary startup and tests.

## 7. Completion and progress

Complete when a supported scholarship link reaches an editable evidence review, the reviewed draft saves to My Applications, and tasks, deadlines, status, and outcomes persist across restarts. The text and manual fallback must work. Existing data and migration history must be recoverable, unrelated discovery pathways must be retired, and verified commits must be pushed. Report any live extraction verification blocked by the zero-spending requirement separately from verified fixture behavior.

Update the table in this file as work advances. For each stage record the actual checks, result, and any remaining blocker. Record pushed commit links in the next milestone or final report. On resumption reconcile the table against the actual checkout and remote before continuing.

| Milestone | Status at handoff | Evidence |
| --- | --- | --- |
| 1. Pivot and cleanup | Complete locally | Discovery paths retired; tracker home established. Build, lint, 17 importer tests, fresh PostgreSQL migrations/import and local startup checks passed; existing 12 published rows retained. |
| 2. Manual tracker | In progress; browser walkthrough pending | Additive migration, tracker API and manual UI implemented. Fresh and upgrade PostgreSQL checks, service-restart persistence, importer tests, frontend build/lint and mocked UI passed; local database migrated with 12 catalogue entries preserved. Browser automation unavailable. |
| 3. Link intake | Pending | Reuse Gemini CLI components if present |
| 4. Planning | Pending | |
| 5. Delivery | Pending | |

**Start now.** Inspect the repository, preserve existing work, and implement Milestone 1. Continue through the remaining milestones under this plan. When I say “continue the build plan,” resume from the first unfinished milestone.
