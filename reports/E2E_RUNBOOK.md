# E2E_RUNBOOK (Dockerized)
Date: 2025-12-21

## Preconditions
- Docker stack running (`docker compose up -d --build`).
- API reachable at http://localhost:8008/ai/api.

## Known receipt files in repo (available today)
- `testfiles_for_import/pdf_test.pdf`
- `testfiles_for_import/swish_test.pdf`
- `testfiles_for_import/jpg_test.jpg`

**Gap:** Only 3 receipt files are available; the 13-file requirement cannot be satisfied without additional receipt artifacts.

## Upload + workflow dispatch (PowerShell)
```powershell
$base = "http://localhost:8008/ai/api"
$token = (Invoke-RestMethod -Method Post -Uri "$base/auth/login" -ContentType 'application/json' -Body (@{username='admin';password='adminadmin'} | ConvertTo-Json)).access_token
$headers = @{ Authorization = "Bearer $token"; 'X-User' = 'agent_upload' }

Invoke-RestMethod -Method Post -Uri "$base/ingest/upload" -Headers $headers -Form @{ files = Get-Item 'testfiles_for_import/pdf_test.pdf' }
Invoke-RestMethod -Method Post -Uri "$base/ingest/upload" -Headers $headers -Form @{ files = Get-Item 'testfiles_for_import/swish_test.pdf' }
Invoke-RestMethod -Method Post -Uri "$base/ingest/upload" -Headers $headers -Form @{ files = Get-Item 'testfiles_for_import/jpg_test.jpg' }
```

## Trigger AI steps explicitly (optional, if workflows stall)
```powershell
$payload = @{ file_ids = @('<FILE_ID_1>', '<FILE_ID_2>'); processing_steps = @('AI1','AI2','AI3','AI4') }
Invoke-RestMethod -Method Post -Uri "$base/ai/process/batch" -Headers $headers -Body ($payload | ConvertTo-Json) -ContentType 'application/json'
```

## Verification (DB)
Use the queries in `reports/DB_VALIDATION_QUERIES.md` to verify:
- workflow_runs + workflow_stage_runs status
- extracted fields used by AI4
- AI4 proposals + validation outcomes
