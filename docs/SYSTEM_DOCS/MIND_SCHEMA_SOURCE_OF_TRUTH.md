# Mind Schema Source of Truth

```
Version: 1.0
Date: 2025-11-26
```

## Canonical location

- **`database/migrations/` is the single authoritative source for database schema.**
- The migration runner resolves only this directory and enforces that every migration comes from here.
- Files under **`backend/migrations/` are deprecated** and retained solely for historical reference; they are not executed.

## File format & numbering

- Each migration must be a SQL file named `NNNN_description.sql`.
  - `NNNN` is a four‑digit, zero‑padded, monotonically increasing prefix.
  - Description uses lowercase words separated by underscores.
- Only `.sql` files are considered; other file types (README/SUMMARY/etc.) are ignored safely.
- Prefixes must be unique. Duplicate or malformed filenames fail validation before execution.

## Adding a new migration

1. Find the highest existing prefix in `database/migrations/` and choose the next number.
2. Create `NNNN_description.sql` with the schema change.
3. Keep SQL idempotent where practical (e.g., guard against existing objects).
4. Do **not** add migrations anywhere else; `backend/migrations/` must not receive new files.

## Deprecated backend migrations

- Legacy files in `backend/migrations/` are commented out with deprecation headers pointing to their canonical copies in `database/migrations/`.
- They remain only to preserve historical context; the migration runner will not read or execute them.

## Notes

- Non-SQL helper files in `database/migrations/` (e.g., READMEs) are ignored by the runner.
- The migration runner validates naming/uniqueness before applying migrations to prevent drift.
