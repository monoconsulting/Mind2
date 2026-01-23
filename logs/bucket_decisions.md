# Dirty Worktree Handling Summary

## Worktree State
- Worktree was dirty at start of this cycle.

## Bucket A (Required for this task)
- backend/src/api/reconciliation_firstcard/__init__.py
- backend/src/api/app.py
- backend/src/services/tasks/celery_app.py
- create_codebase.ps1
- create_codebase.bat
- logs/git_status_porcelain.txt
- logs/git_diff_stat.txt
- logs/git_diff.txt
- logs/git_diff_cached.txt
- logs/pytest.txt
- logs/bucket_decisions.md

## Task Branch
- Branch: fix/celery-startup-and-manifest
- Commits:
  - 2db9613 fix: break celery import cycle and normalize audit inventory
  - b644e8c chore: include pytest and git evidence in audit zip
  - af58a50 chore: preserve repo git evidence in audit zip
  - 1e602b6 chore: capture docker logs without dockerlogs.bat
  - ba543da docs: update bucket decisions for audit

## Bucket B (Parallel/legitimate work moved to salvage branch)
- Branch: salvage/parallel-worktree-cleanup
- Commit: 9631108 (salvage: capture parallel worktree changes)
- Files captured:
  - TODO.md
  - backend/src/api/app.py
  - backend/src/api/ingest.py
  - backend/src/api/reconciliation_firstcard/routes/statements.py
  - backend/src/api/reconciliation_firstcard/routes/status.py
  - backend/src/api/reconciliation_firstcard/routes/upload.py
  - backend/src/api/reconciliation_firstcard/utils/db_helpers.py
  - backend/src/services/ocr.py
  - backend/src/services/tasks/creditcard_tasks.py
  - backend/src/services/tasks/invoice_tasks.py
  - backend/src/services/tasks/legacy.py
  - backend/src/services/tasks/ocr_tasks.py
  - backend/src/services/tasks/utils/invoice_utils.py
  - backend/src/services/tasks/workflow_tasks.py
  - backend/tests/integration/test_fc_resume_restart.py
  - backend/tests/unit/test_fc_workflow_coordinator.py
  - backend/src/scripts/fc_diagnostic.py
  - backend/src/tests/test_fc_restore.py
  - backend/tests/fixtures/fc_cards/FC_2504_page1_ocr_boxes_subset.json
  - backend/tests/integration/test_ocr_paddle.py
  - backend/tests/unit/test_wf3_ocr_gating.py
  - create_codebase.batOLD
  - create_codebase_archive_db.ps1
  - docker-compose.yml
  - dockerlogs.bat
  - docs/FIX_ERRORS_MCP_CODEX.md
  - docs/cgpt/CGPT_1.md
  - docs/cgpt/CGPT_2.md
  - docs/cgpt/CGPT_3.md
  - docs/cgpt/CGPT_4.md
  - docs/cgpt/CGPT_5.md
  - docs/cgpt/CGPT_6.md
  - main-system/app-frontend/src/ui/pages/Process.jsx
  - requirements.txt
  - scripts/collect_docker_logs.py
  - web/tests/manual-match.spec.ts
  - web/tests/verify-card-statements-list.spec.ts
  - web/tests/test_receipt_ocr_merge_regression.py

## Bucket C (Generated artifacts removed)
- Removed:
  - .dockerlogs/
  - test-files/
  - testfiles_for_import/FC_2504.pdf
  - web/test-reports/20260121-073807_fc_2504_tabular/
  - web/test-reports/20260121-180000_fc_2504_tabular_currency_fix/
  - web/test-reports/20260121_153803-manual-match-columns/
  - web/test-reports/20260121_163301-fc-currency/
  - web/test-reports/20260121_fc_2504_tabular_currency_fix_e2e/
- Rationale: generated artifacts; excluded by create_codebase.ps1 patterns (test-reports, .dockerlogs, testfiles_for_import, temp/test files).
