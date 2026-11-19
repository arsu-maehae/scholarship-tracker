# Scholarship Tracker — Codex build plan

## Start here

**Paste a scholarship link → save it → optionally extract key details → track the application.**

Build a personal tracker for scholarships the user finds on university, government, or scholarship-provider sites. The finished first release runs on the user's computer without paid services, accounts, or API keys. Its core workflow is saving a URL, organizing the application, and seeing upcoming deadlines. Reading supported pages is an assistive feature. The user can save the link and leave immediately, then review a suggestion later if it matters to their application.

This plan supersedes the earlier catalogue, worldwide discovery, JSON importer, Gemini, and Brave Search plans. Read it fully, inspect the actual checkout, and implement the milestones in order. Continue through verification and GitHub pushes within the authorized scope. Use the milestone checklist to resume after a session ends. This document defines the project. The app's README should explain how to run and use the finished app.

## 0. Restart safely

- The expected checkout is `C:\Users\s6601\work\scholarship-tracker` and the expected remote is `arsu-maehae/scholarship-tracker`. Verify the repository, current branch, status (including untracked paths), remotes, history, and upstream. If a restart branch has already been prepared, inspect it and continue from it. Otherwise use a separate worktree on a dedicated branch such as `restart/scholarship-tracker`, from a verified usable commit. Record its starting SHA. If nothing from the old feature set is usable, implement a minimal tracker in that isolated branch while preserving existing Git history.
- Preserve the original checkout and its uncommitted work. Keep old branches, the original database, and Docker volumes intact. Never reset or clean the user's tree, rewrite history, force-push, or delete persistent data for this restart.
- Reuse functioning React/TypeScript/Vite scaffolding, FastAPI setup, and SQLAlchemy/Alembic/PostgreSQL infrastructure when practical. Give the tracker its own local database or isolated Compose project and volume. Verify the connection's database before migrations. Test against a disposable database. Do not use the old catalogue database for smoke tests.
- Remove obsolete screens, routes, scripts, dependencies, feature flags, CI jobs, and setup instructions from the active tracker branch as appropriate. Audit references before deleting files. Keep any Alembic revisions needed by the retained migration chain. The new schema can coexist with historical tables without exposing them in the app. Do not port previous catalogue records into the personal tracker by default.
- Treat the GitHub repo as public. Stage only intended code, migrations, docs, configuration examples, and synthetic fixtures. Exclude secrets, real applications, database files/dumps, raw fetched HTML, and local logs. If GitHub authentication or network access is unavailable, save tested commits locally and report the exact push command and blocker.

## 1. Make the tracker usable without page extraction

### User flow

1. Open the dashboard and paste a scholarship URL. Click **Save scholarship**. Only the URL is required. The backend saves it to the database with status **Saved** and returns the new item. The form does not fetch the page.
2. Open the saved item. Fill in or edit its title, provider, intake, deadline, funding, eligibility, and notes as needed. Add checklist items such as “Request recommendation” and mark them complete individually.
3. Move the application through **Saved → Preparing → Submitted → Accepted / Rejected**. Let the user correct an incorrect status directly. Let them archive an item separately from its application status and restore it later.
4. Use the dashboard to find a saved item by title/provider, filter by status, and see the next deadlines. The application detail always links to the source.

### Data and behavior

| Model | Minimum fields and rules |
| --- | --- |
| Tracked scholarship | ID, original source URL, normalized URL key, optional title/provider/intake, optional deadline date, optional funding and eligibility text, optional notes, status, archive timestamp, created/updated timestamps |
| Checklist item | ID, scholarship ID, task label, completion value |
| Extraction attempt | Added in milestone 2. Scholarship ID, input kind, source URL when fetched, attempt timestamp, outcome, and bounded structured suggestions with evidence |

- Use typed schemas, bounded text fields, UTC timestamps, and database constraints for stable invariants. Use a calendar date for the user's confirmed deadline. Show explicit source time and timezone in the evidence if provided. Compare date-only deadlines to the user's local calendar date, defaulting to `Asia/Bangkok` for this project. Mark dates strictly before today as past due and today's date as due today.
- Normalize URLs conservatively for duplicate detection. Lowercase scheme and hostname, remove the fragment and default port, and preserve distinctions in paths and query strings. Enforce uniqueness at the database level so a retry or concurrent save cannot create duplicates. On a duplicate, return the existing item's ID, including archived items. For this version one URL represents one tracker item. A user can edit the intake if the provider reuses a URL.
- Make the dashboard list active items by default, with a separate archived view. Show upcoming deadlines for Saved/Preparing items and provide visible overdue and unknown-date states. Confirmed dates alone drive the dashboard. Persist status, checklist, and notes independently of extraction attempts. Display dates and labels without relying solely on color.
- Treat page text and user notes as plain text. Use safe link handling for public HTTP(S) URLs. Reject malformed URLs and embedded credentials. Tell users to paste a public information page instead of a private application portal link.

### API contract

Use existing conventions if the repo already has a suitable structure. Preserve these operations and keep React and FastAPI contracts aligned.

| Operation | Route |
| --- | --- |
| List/search/filter | `GET /api/tracked-scholarships` |
| Save a link | `POST /api/tracked-scholarships` |
| Read or edit a saved item, including archive/restore | `GET / PATCH /api/tracked-scholarships/{id}` |
| Create a checklist task | `POST /api/tracked-scholarships/{id}/checklist` |
| Edit, check off, or remove a task | `PATCH / DELETE /api/tracked-scholarships/{id}/checklist/{task_id}` |
| Extract suggestions from the saved page or pasted text | `POST /api/tracked-scholarships/{id}/extract` |
| Read the latest extraction attempt | `GET /api/tracked-scholarships/{id}/extraction` |

Use predictable errors for invalid input and missing items. Scope each checklist operation to the given scholarship. Accept only allowed fields on edits so extraction inputs cannot overwrite tracker state. Use the Vite development proxy for `/api`. Bind the app and database to localhost for local use.

**Exit check:** Save a link without fetching it, reopen it after restarting the app, update its status and a checklist task, see the confirmed deadline on the dashboard, and archive and restore it. Commit and push this working milestone.

## 2. Read a URL and show useful suggestions

### How the URL becomes text

1. On a saved detail page, the user clicks **Extract from page**. React posts to the item's extraction endpoint with a page input mode. The backend looks up the stored URL. The initial save never waits on this operation.
2. The backend checks whether the URL is eligible for automatic reading. Its HTTP fetcher makes a bounded HTTPS GET to the approved scholarship host and receives HTML. Use the existing hardened fetcher if it passes the checks below. `httpx` is an option when the transport can enforce those checks.
3. Parse the HTML with Beautiful Soup. Remove scripts, styles, and obvious layout elements. Prefer the main article and retain headings, paragraphs, list items, and useful table rows. Keep heading context so a scholarship deadline can be distinguished from a general admissions deadline. Render the output as plain text.
4. Run small, deterministic rules over those blocks. Group useful excerpts under **Deadline**, **Funding**, **Eligibility**, and **Required documents**. Propose a date only when the wording and full date are clear. Show competing dates with their heading/intake context. Add text-backed title or provider suggestions when straightforward.
5. Show suggestions next to current values. The user can apply an individual suggestion, edit it, or ignore it. Use the normal save action to update tracker fields. A re-extraction can update suggestions and its timestamp. Confirmed fields, checklist items, and status change only through explicit edits.

### Source support and fallbacks

| Input or outcome | App behavior |
| --- | --- |
| Public HTML on an approved host | Download and extract short, categorized excerpts with the source URL and time of extraction |
| Multiple intakes, partial dates, relative dates, or conflicting statements | Show the excerpts and leave the confirmed deadline empty or preserve its current value |
| Login, blocked page, heavy JavaScript, PDF, unsupported host, or timeout | Keep the saved item and offer **Paste page text** or manual editing |
| User pastes page text | Run the same rules without a network request and label evidence **Pasted text** |
| No meaningful detail found | Explain that no supported details were found and keep the editor available |

- Return short plain-text evidence for each suggestion, optionally including the heading and date candidates. Preserve the source wording without inventing amounts, funding coverage, eligibility, or a closing date. Keep “not found” distinct from “the provider says it is unavailable.” Add a manual checklist task from a suggested requirement only after the user chooses to do so.
- Use an explicit attempt status such as `found`, `no_details`, `unsupported`, or `failed`. Keep input size and result size bounded. Never store full page HTML or the entire pasted input. A failed retry must preserve the user's fields and previously usable suggestions. Label old suggestions and their timestamps if a later attempt fails. Disable duplicate extraction clicks while pending and enforce a backend per-item limit so concurrent requests cannot pile up.
- Start with a small configurable list of exact official hostnames. Verify any example host during development before including it in the documented supported list. Full coverage across websites, PDF parsing, authenticated browsing, recurring monitoring, outbound alerts, cloud deployment, and third-party AI are outside this release. Use the manual app path for every link you can save safely.

### Fetching safeguards

Saving a URL and allowing the server to fetch it are separate operations. Apply the following before connecting to a user-supplied destination.

- Require HTTPS on port 443 and an exact server-configured allowlist match. Reject credentials, IP literals, and malformed hosts. Disable redirects and environment proxies. Keep TLS certificate and hostname verification on. Fetch one page with no cookies or credentials. Do not fetch scripts, images, embedded resources, or discovered links.
- Use a tested transport or egress policy that prevents connections to private, loopback, link-local, reserved, or otherwise nonpublic destinations (IPv4 and IPv6). Where the application owns the check, validate resolved addresses and ensure the connection uses an approved address while still validating TLS for the original hostname. Avoid a configuration that checks DNS once and then lets the client independently resolve the host before connecting. If safe fetching cannot be enforced in the runtime, keep live fetching disabled and finish the pasted-text workflow while reporting that limitation.
- Set a short total time budget and bounded connect/read timeouts. Stream the response with a decoded byte cap, require a successful HTML response, and return plain, actionable errors. Avoid logging URLs with sensitive query strings or raw HTML. Tests use mocks or fixtures and never depend on a provider's live page. See [OWASP's guidance for server-side URL fetching](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).

**Exit check:** Through the UI, save a link, extract from a controlled HTML fixture through the mocked fetch boundary, read the evidence, apply one suggestion, and confirm the dashboard updates. Verify a failed attempt keeps the saved record and that pasted text works. With access to a supported official site and the safeguards enabled, smoke-test a single public link and record which site and fields worked. If live access is unavailable, report remote behavior as unverified. Commit and push the milestone.

## 3. Verify and hand over

- Run backend tests for saving and duplicates, validation, edits, checklist scoping, archiving, and deadline semantics. Cover a clear deadline, competing intakes, missing fields, different HTML layouts, and the paste fallback. Verify fetch policy blocks unapproved destinations and redirects, refuses nonpublic resolution, and handles unexpected content, oversized responses, and timeouts. Use synthetic data and mock transport/resolver boundaries.
- Run migrations from an empty disposable database and verify the app can restart against it with saved items intact. Run the frontend lint and production build. Check the browser flow on desktop and narrow widths, including loading, errors, empty states, and keyboard access. Verify that page-fetch failure never blocks the manual tracker.
- Write a README for someone cloning the repo. Include Windows PowerShell setup from the repo root, prerequisites and tested versions, exact database and migration commands, backend and frontend commands, local addresses, the test commands, safe backup/restore instructions, and how to recover if Docker Desktop is closed. Document the allowlist, paste fallback, and local-only model. Verify the README commands against the actual branch and current configuration. Keep the README example keys and application data synthetic.
- Preserve the zero-spending requirement. The tracker runs locally using open-source libraries and the existing local setup. Use GitHub for code history. Do not enable paid CI runners, start trials, require payment details, or create cloud resources. If an existing workflow runs on push, inspect it before publishing the branch. Prefer local checks if CI cost is unclear.

## GitHub progress and stopping point

1. Confirm the remote and current restart branch before every push. Review the staged file list and diff for changes outside the milestone, secrets, and personal data.
2. Push each tested milestone to the same restart branch. Use meaningful commits such as `feat: add persistent scholarship application tracker`, `feat: extract scholarship details with source evidence`, and `docs: document and verify local tracker setup`.
3. First push with `git push -u origin <actual-restart-branch>`, then use `git push` after verifying the upstream. If the remote branch has unexpected changes, inspect them and reconcile only when safe. Leave merging into `main` to the user.
4. Finish with the branch link, commit SHAs, passing check results, the exact local startup commands, and any unverified behavior or blocker. If one integration is blocked, finish independent work first and report the remaining action clearly.

## Release checklist

- [ ] Original work and data preserved. Restart branch and isolated database verified.
- [ ] A link saves even if the source is unreachable. Saved data survives a restart.
- [ ] Status, notes, checklist, archive/restore, and deadline views work.
- [ ] Supported page extraction produces suggestions with evidence. Pasted text and manual entry work when fetching is unavailable.
- [ ] An ambiguous date stays unconfirmed. Fetch failures and retries preserve user edits.
- [ ] Fresh database migrations, backend tests, frontend build/lint, and browser smoke checks completed or reported with concrete blockers.
- [ ] README startup steps verified. Tested commits on the GitHub restart branch or local SHAs and push blocker reported.

## Current progress (2026-11-19)

- URL-first tracking is implemented and passed disposable PostgreSQL and synthetic HTTP persistence checks; browser walkthrough pending.
- Deterministic extraction and delivery remain in progress.
