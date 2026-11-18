# Scholarship Discovery - project status

Updated: 18 November 2026 (Asia/Bangkok). This is a snapshot; check the current files and `git status` for later changes.

## Goal

Help people find scholarships internationally, using a reviewed catalogue and separate web-search suggestions. The app cannot guarantee that it finds every scholarship. Search results do not establish a person's eligibility.

## Milestones

| Milestone | Status | What it means |
| --- | --- | --- |
| 1. Working discovery app | Complete | React, FastAPI and PostgreSQL app with structured filters and official source links. |
| 2. JSON catalogue importer | Complete and merged | Validates and previews changes; applies a batch atomically using stable source keys. |
| 3. Automated PostgreSQL checks | Complete and merged | GitHub Actions runs importer tests, a fresh PostgreSQL integration test and frontend build. |
| 4. Review and merge importer | Complete | Pull request #1 was merged into `main`. |
| 5. Catalogue review workflow | Implemented; pushed, not merged | Official-source review process is documented in `docs/CATALOGUE_REVIEW.md`. |
| 6. Grow the catalogue | Ongoing | Twelve published entries exist in the local database. This is a small curated catalogue, not worldwide coverage. The latest four-record batch is uncommitted. |
| 7. Scholarship details | Implemented; pushed, not merged | Cards show eligibility notes, coverage, date uncertainty and source checks. The owner reported the first three new cards and links worked in the browser. |
| 8. Worldwide search and discovery | In progress | Catalogue keyword search and an in-app web-results section are implemented locally. Real web search requires a provider key and has not been verified end to end. |
| 9. Saved opportunities and application planning | Planned | Decide the appropriate first version before implementation. |
| 10. Source maintenance | Planned | Add a way to find stale entries and check sources regularly. |
| 11. Deployment | Planned | Prepare and verify production hosting when authorized. |
| 12. Full README and portfolio handoff | Planned | Full README remains deferred by the owner. |

## Gemini milestone - local preparation

Gemini is disabled by default in example configuration; it has been enabled in the ignored local `.env` for the website at the owner?s request after the owner reported a Free-tier project with no linked billing. The website has a Search with Gemini button, and local CLI commands have been prepared for natural-language catalogue filtering and evidence-linked extraction from a limited set of official HTML pages. Extraction produces only an unpublished `needs_review` candidate; it does not write to the database. The owner reports the project shows Free tier and has no linked billing account; this has not been independently verified. One authorized live CLI catalogue search succeeded using `gemini-3.5-flash-lite`; browser integration remains outstanding; this CLI does not implement free live worldwide discovery. See `docs/GEMINI.md` for the required checks and limitations. The existing Brave provider is disabled by default under the zero-spending direction.

## Current application

- The local database contains 12 published entries. The latest batch added Global Korea, NL Scholarship, NUS Research Scholarship and Oxford Clarendon. The three earlier additions were MEXT, DAAD STEM and the Australian Research Training Program.
- The catalogue supports destination, degree, field, funding, scheme, intake and keyword search. Its filters are combined; unrecorded fields are only included as visibly unverified possible field matches when requested.
- Submitting a search also requests web suggestions displayed inside the app. They are separate, unverified results: search terms do not guarantee that every filter matches. They are not automatically added to the catalogue.
- Live web suggestions are disabled by default, and no `BRAVE_SEARCH_API_KEY` is configured in this checkout. Setup and cost/privacy notes are in `docs/WEB_SEARCH.md`. Never put the key in Git or share it in chat.

## Evidence and remaining checks

- The latest four-record import was previewed as four inserts and applied. A repeat preview reported four unchanged; the two earlier batches reported three and five unchanged.
- Seventeen offline importer tests, provider unit tests, the frontend build and a fresh PostgreSQL migration/import/search integration test passed locally. Live API checks confirmed 12 catalogue entries and the new country filters.
- The owner confirmed browser checks for the earlier eight-entry catalogue and three initial new cards. The new worldwide search UI has been served locally, but its browser interaction and a real provider response have not been verified.
- Set up the chosen search provider, restart the backend, and check that a real query shows results in the app. Verify loading, no results, errors, new searches and filter wording. Review current provider pricing and quota first.

## Git state at this snapshot

- Current branch: `feat/global-catalogue-batch`, based on `feat/catalogue-review-details`.
- `feat/catalogue-review-details` was committed and pushed at `1470c37`; it has not been merged into `main`.
- The later four-record catalogue batch, worldwide-search implementation and related tests/docs are local uncommitted changes. Preserve them; do not reset the working tree.
- Commit and push only when authorized. Do not merge or deploy without the owner's authorization. Git does not include the contents of the local PostgreSQL database.

## Useful files

- `docs/CODEX_HANDOFF.md` - detailed technical handoff and history.
- `docs/CATALOGUE_REVIEW.md` - official-source review workflow and batch notes.
- `docs/WEB_SEARCH.md` - provider setup and search limitations.
- `backend/data/` - versioned catalogue batches.
