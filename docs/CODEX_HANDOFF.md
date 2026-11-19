# Restart handoff

The owner authorized `docs/SCHOLARSHIP_TRACKER_RESTART_PLAN.md`; the earlier build plan remains paused. Work in the `restart/scholarship-tracker` worktree, preserve the original checkout, database, source keys and migration history, and never enable paid services or AI.

URL-first tracking and deterministic source suggestions are implemented on an isolated Compose database `scholarship_tracker_restart` (localhost port 5434). Do not use the original database for smoke tests. Preserve all migrations including 2a0b2c3d4e5f. Unit, disposable PostgreSQL, frontend build/lint and synthetic HTTP/restart checks passed. A browser walkthrough remains pending: the browser-access host was unavailable. The single live Oxford check redirected and was rejected; live supported-page extraction is not verified. Do not mark the browser or remote extraction checks complete without evidence.

The README provides local setup and recovery guidance. A custom-format backup and restore into a new recovery database was exercised with synthetic data in a disposable PostgreSQL container. Commits a39c54c and f735f31 passed GitHub Actions; the later hostname/date hardening is in 07ff7e7. No user application data, credentials, paid services or live AI calls were used for testing.
