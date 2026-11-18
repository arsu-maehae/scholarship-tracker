# Gemini local tools - zero-spending setup

The local website has a Search with Gemini button and the backend also provides a CLI. They interpret a request as validated filters and search the local catalogue; they do not discover scholarships on the web. The website AI endpoint is restricted to the local development app and is not an authenticated production endpoint. The page extractor fetches one explicitly supplied official HTML page from a narrow allowlist and produces an unpublished importer candidate plus verbatim supporting excerpts. A reviewer must inspect both; quotation presence does not prove the interpretation. The tool never writes catalogue records or marks facts as human-reviewed.

## Required before any live use

1. In Google AI Studio, inspect the dedicated project's usage tier and confirm it is **Free**. In Google Cloud Billing, verify that the same project has **no linked billing account**. Do not link one or start a trial. An API key alone does not establish either condition. Verify that the selected model is available on the project's Free tier. If any of these cannot be confirmed, keep Gemini disabled and do not make live calls.
2. Google lists `gemini-3.5-flash-lite` standard input/output as free on the Free tier in its [pricing documentation](https://ai.google.dev/gemini-api/docs/pricing), checked 18 November 2026. Google lists structured-output support and no announced shutdown date for this model. The prior `gemini-3.7-flash` endpoint now routes to a different model; this integration uses the explicit model ID instead. Model availability and terms may change. The code permits only this checked model; update the code and review the current official pricing before changing it. Grounding and external tools are not enabled.
3. If and only if those checks succeed, put `GEMINI_API_KEY`, `GEMINI_ENABLED=true`, `GEMINI_FREE_TIER_CONFIRMED=true` and `GEMINI_MODEL=gemini-3.5-flash-lite` in the ignored project-root `.env`. The confirmation setting is your assertion, not an automated billing verification. Do not share the key in chat or commit it. Set `GEMINI_ENABLED=false` to disable use.
4. Google says Free-tier inputs and outputs may be used to improve its products. Do not send private or sensitive information. Read the current [pricing and data-use details](https://ai.google.dev/gemini-api/docs/pricing) before enabling it.

No billing, credits or paid trial was created during development. Live calls are permitted only after the owner verifies the Free-tier project and absence of a linked billing account; check the current project status before every test. Local limits (two attempted requests per minute, twenty per rolling day, one-hour response cache, bounded inputs/outputs, 15-second network timeout and no retry) reduce use but do not guarantee zero billing. Google quotas and model availability can differ. A quota response stops the request and leaves catalogue search available. The usage/cache file `backend/.gemini-usage.sqlite3` is ignored by Git; it contains cached model output and timestamps. Limits are local to this checkout and do not constrain other devices, processes using different cache paths, or other API clients.

## Website usage

Enter a request in Keywords and click **Search with Gemini**. The app displays the interpreted filters and searches the catalogue. Existing selected filters are preserved; conflicting or unsupported preferences stop the search for clarification. Ordinary Find scholarships remains available. Gemini is contacted only when the button is pressed, not in the background. The owner has enabled the local setting for this feature after reporting that the project has no billing account; defaults in `.env.example` remain off. Check project billing status and model terms before future use. Requests can use quota and send the text to Google.

## Usage after setup

Run from `backend`:

```powershell
.\.venv\Scripts\python.exe gemini_tool.py search "AI master's scholarships in Finland with full funding"
.\.venv\Scripts\python.exe gemini_tool.py extract "https://www.ox.ac.uk/admissions/graduate/fees-and-funding/funding/clarendon/applicants" --source-key "clarendon:review-example" --scheme "clarendon"
```

The search prints interpreted filters and actual published catalogue results. If the model reports unsupported or ambiguous conditions (such as nationality or deadlines), it stops rather than silently dropping them. Interpretations can still be wrong: inspect the filters. Ordinary app filtering works independently of Gemini.

Extraction currently supports only exact hosts `www.ox.ac.uk`, `www.studyinnl.org` and `www.studyinjapan.go.jp`, HTTPS port 443, HTML responses and no redirects. Resolved addresses must all be public and the connection is pinned to a checked address. Pages may be unavailable, too large or incompatible. The output includes a `catalogue` object that can be saved as JSON and an associated `provenance` object to retain for review. The source key and scheme are assigned by the human reviewer; preserve existing identities and inspect importer preview before any apply. An existing key could target an existing row if imported, so never apply an unexpected update. Extracted entries are always `needs_review`, not published, and have no `last_checked` review date.

Tests use fake credentials and mocked responses; CI prohibits live Gemini calls. The separate Brave integration is disabled unless `BRAVE_SEARCH_ENABLED=true`; do not enable it under a zero-spending requirement. Fully free live worldwide discovery is not established by this milestone.
