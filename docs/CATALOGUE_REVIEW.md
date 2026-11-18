# Catalogue source review workflow

The catalogue is curated, not a complete list of awards. Research each record against the official awarding body, programme or university before publishing it. A source check is a dated snapshot, not a guarantee that a call is currently open or that an applicant is eligible.

1. Identify the award and its current cycle. Record a stable `source_key` for that opportunity or overview; do not reuse a key for a new cycle or change a key just to correct a title.
2. Read the official announcement and relevant eligibility, funding and application pages. Record the official URL and the actual date you checked it. Note any important limits and additional official sources in the description or funding notes. Never update `last_checked` without checking the source.
3. Record study destination rather than applicant nationality. Use the intake year only when verified; a fiscal year or deadline is not necessarily an intake. Record only supported field tags. Leave unknown dates, status, coverage and fields unknown rather than guessing. Explain important eligibility restrictions in `description`.
4. Start uncertain records as `draft` or `needs_review`. To publish, verify the identity, sources, key facts and uncertainties; the importer requires an official URL and review date, but that requirement alone does not verify the facts. Do not treat a programme overview as a confirmed open call or a personal eligibility decision.
5. Add reviewed records to a versioned JSON batch in `backend/data/`. If a new scheme is needed, add it to `backend/seed.py` and run the idempotent scheme seed. Validate with `python import_catalogue_json.py data/<batch>.json --validate-only`, then run without `--apply` to review the full database plan. Check every INSERT, ADOPT and UPDATE and resolve any unexpected changes before applying with `--apply`. Run preview again and expect unchanged records. The importer validates the whole batch and applies it transactionally.
6. Recheck sources when facts may have changed. Record a new review date only after the actual check. Archive outdated entries intentionally; deleting a record from a JSON file does not delete it from the database. Preserve historical cycles under their own keys.

## Batch reviewed 18 November 2026

- `mext:research-students:overview`: [Study in Japan - MEXT](https://www.studyinjapan.go.jp/en/planning/scholarships/mext-scholarships/). Graduate level, eligibility overview, routes, tuition, stipend and airfare checked; current cycle, specific fields and call remain unverified.
- `daad:stem-masters:2027-2028`: [DAAD STEM study scholarships](https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database?detail=57742130). Winter 2027/28 study, STEM disciplines, eligibility and benefits checked. DAAD requires a tuition-free programme and does not pay tuition; country-specific eligibility and current deadline require checking. Call status is unverified.
- `australian-rtp:research-degrees:overview`: [Australian Government Research Training Program](https://www.education.gov.au/research-block-grants/research-training-program). Research master's and doctoral routes, provider applications and variable benefits checked. Specific coverage, subject, intake and call depend on the provider and remain unverified.

These overview entries describe pathways, not guaranteed availability for every applicant. The earlier five entries retain their earlier review dates; they were not rechecked for this batch.
