# Restart handoff

The owner paused the previous build plan and will define a new scope. Do not resume the previous milestones. Preserve the existing catalogue, personal records, source links, and Alembic migration history. Do not reset the local database or remove Docker volumes.

This restart branch starts from commit f134de0, whose manual tracker foundation passed GitHub Actions. The already-applied 2a0b2c3d4e5f migration is retained for compatibility with the existing local database; it does not activate source intake. The prior work is preserved in local branch backup/scholarship-tracker-pre-restart. No live AI calls or paid services should be enabled during baseline preparation.
