# Restart handoff

The owner authorized `docs/SCHOLARSHIP_TRACKER_RESTART_PLAN.md`; the earlier build plan remains paused. Work in the `restart/scholarship-tracker` worktree, preserve the original checkout, database, source keys and migration history, and never enable paid services or AI.

URL-first tracking is implemented; deterministic source suggestions are a later step on an isolated Compose database `scholarship_tracker_restart` (localhost port 5434). Do not use the original database for smoke tests. Preserve all migrations including 2a0b2c3d4e5f. Unit, disposable PostgreSQL, frontend build/lint and synthetic HTTP/restart checks passed. A browser walkthrough remains pending: the browser-access host was unavailable. Optional page extraction has not yet been implemented in this commit. Do not mark the browser or remote extraction checks complete without evidence.
