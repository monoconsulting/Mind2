# Archived migrations

- `0007_add_ai_llm_tables.sql` – superseded by `0041_add_ai_llm_tables.sql`. Kept here for historical reference only.
- `0031_create_workflow_tracking.sql` – superseded by `0042_create_workflow_tracking.sql` during workflow schema redesign.
- `0039_add_workflow_tracking_tables.sql` – earlier workflow tracking proposal that added duplicate tables and optional mirrored columns on `unified_files`. Consolidated into `0042_create_workflow_tracking.sql` to keep a single source of truth for workflow tracking.

These files are not part of the active migration chain. Migration runners should execute only the `.sql` files in `database/migrations/` (excluding this `archive/` folder).
