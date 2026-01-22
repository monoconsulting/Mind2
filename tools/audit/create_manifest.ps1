param(
  [Parameter(Mandatory=$true)][string]$RepoRoot,
  [Parameter(Mandatory=$true)][string]$StagingDir,
  [Parameter(Mandatory=$true)][string]$ZipName
)

$ErrorActionPreference = "Stop"

$manifestDir = Join-Path $StagingDir "manifest"
if (!(Test-Path $manifestDir)) { New-Item -ItemType Directory -Path $manifestDir | Out-Null }

$now = Get-Date
$manifestPath = Join-Path $manifestDir "manifest.md"
$changeSummaryPath = Join-Path $manifestDir "change_summary.md"

@"
# Audit Manifest

- ZipName: $ZipName
- CreatedAt: $($now.ToString("yyyy-MM-dd HH:mm:ss"))
- RepoRoot: $RepoRoot

## Commands used to create this ZIP
- create_codebase.bat (repo root)
- docker compose ps -> /dockerlogs/docker_compose_ps.txt
- docker compose logs --no-color -> /dockerlogs/docker_compose_logs.txt

## Tests executed (evidence must exist under /code/web/test-reports/<timestamp>_audit_snapshot_build/)
- python -m pytest -q backend/tests --collect-only
- python -m pytest -v backend/tests/unit/test_fc_cards_tabular.py
- python -m pytest -v backend/tests/integration/test_fc_full_workflow.py
- python -m pytest -v backend/tests/integration/test_queue_resume.py (must be clean OR cleanly skipped with exit code 0)

## Exclusions
- .git/, node_modules/, venv/, .venv/, __pycache__/, caches, build outputs
- .env and .env.* and other secret patterns

"@ | Set-Content -Encoding UTF8 $manifestPath

@"
# Change Summary

Describe what changed since the previous audit snapshot.
MUST include:
- Files modified/added/removed (paths)
- Why each change was necessary
- Confirmation no unrelated changes were introduced

"@ | Set-Content -Encoding UTF8 $changeSummaryPath
