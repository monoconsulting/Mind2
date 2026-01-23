# PowerShell script to create audit-compliant codebase archive
# Structure: /code/, /dbbackup/, /dockerlogs/, /logs/, /manifest/

# Resolve repo root from script location (no hardcoded paths)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$sourceDir = $scriptDir
$timestamp = Get-Date -Format "yyyy-MM-dd"
$timestampForZip = Get-Date -Format "yyyy-MM-dd_HH-mm"

# Create backup folder
$codebaseBackupDir = "$sourceDir\.codebasebackup"
if (-not (Test-Path $codebaseBackupDir)) {
    New-Item -ItemType Directory -Path $codebaseBackupDir -Force | Out-Null
}

$zipFile = "$codebaseBackupDir\MIND_codebase_$timestampForZip.zip"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MIND Audit Snapshot Generator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Repo root: $sourceDir" -ForegroundColor Gray
Write-Host "Output: MIND_codebase_$timestampForZip.zip" -ForegroundColor Green
Write-Host ""

# Create temporary directory with proper structure
$tempDir = Join-Path $env:TEMP "codebase_audit_$([guid]::NewGuid().ToString())"
$codeDir = "$tempDir\code"
$dbBackupDir = "$tempDir\dbbackup"
$dockerLogsDir = "$tempDir\dockerlogs"
$logsDir = "$tempDir\logs"
$manifestDir = "$tempDir\manifest"

New-Item -ItemType Directory -Path $codeDir -Force | Out-Null
New-Item -ItemType Directory -Path $dbBackupDir -Force | Out-Null
New-Item -ItemType Directory -Path $dockerLogsDir -Force | Out-Null
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
New-Item -ItemType Directory -Path $manifestDir -Force | Out-Null

# ============================================
# SECTION 0: GIT EVIDENCE (DIRTY WORKTREE AUDIT)
# ============================================
Write-Host "[0/5] Git Evidence" -ForegroundColor Yellow
$repoGitStatus = Join-Path $sourceDir "logs\git_status_porcelain.txt"
$repoGitDiffStat = Join-Path $sourceDir "logs\git_diff_stat.txt"
$repoGitDiff = Join-Path $sourceDir "logs\git_diff.txt"
$repoGitDiffCached = Join-Path $sourceDir "logs\git_diff_cached.txt"
$repoGitFiles = @($repoGitStatus, $repoGitDiffStat, $repoGitDiff, $repoGitDiffCached)
$hasRepoGitEvidence = $true
foreach ($p in $repoGitFiles) {
    if (-not (Test-Path $p)) { $hasRepoGitEvidence = $false }
}

try {
    if ($hasRepoGitEvidence) {
        Copy-Item $repoGitStatus -Destination "$logsDir\git_status_porcelain.txt" -Force
        Copy-Item $repoGitDiffStat -Destination "$logsDir\git_diff_stat.txt" -Force
        Copy-Item $repoGitDiff -Destination "$logsDir\git_diff.txt" -Force
        Copy-Item $repoGitDiffCached -Destination "$logsDir\git_diff_cached.txt" -Force
        Write-Host "  Copied repo git evidence to logs/" -ForegroundColor Gray
    } else {
        Push-Location $sourceDir
        git status --porcelain=v1 | Out-File -FilePath "$logsDir\git_status_porcelain.txt" -Encoding UTF8
        git diff --stat | Out-File -FilePath "$logsDir\git_diff_stat.txt" -Encoding UTF8
        git diff | Out-File -FilePath "$logsDir\git_diff.txt" -Encoding UTF8
        git diff --cached | Out-File -FilePath "$logsDir\git_diff_cached.txt" -Encoding UTF8
        Pop-Location
        Write-Host "  Saved git evidence to logs/" -ForegroundColor Gray
    }
} catch {
    Write-Host "  WARNING: Failed to capture git evidence: $_" -ForegroundColor Yellow
}

# ============================================
# SECTION 1: DATABASE BACKUP
# ============================================
Write-Host "[1/5] Database Backup" -ForegroundColor Yellow

# Read DB config from .env (but NEVER include .env in ZIP)
$envFile = "$sourceDir\.env"
$dbName = ""
$dbUser = ""
$dbPass = ""

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^DB_NAME=(.+)$") { $dbName = $matches[1] }
        if ($_ -match "^DB_USER=(.+)$") { $dbUser = $matches[1] }
        if ($_ -match "^DB_PASS=(.+)$") { $dbPass = $matches[1] }
    }
}

$dbDumpSuccess = $false
$schemaDumpSuccess = $false

if ($dbName -and $dbUser -and $dbPass) {
    Write-Host "  Database: $dbName" -ForegroundColor Gray

    # Check if MySQL container is running
    $containerStatus = docker inspect -f '{{.State.Running}}' mind2-mysql-1 2>$null

    if ($containerStatus -eq "true") {
        $containerId = docker compose ps -q mysql 2>$null

        if ($containerId) {
            # Full dump
            Write-Host "  Creating full database dump..." -ForegroundColor Gray
            $containerDumpPath = "/tmp/mind_db_dump_temp.sql"
            docker compose exec -T mysql sh -c "mysqldump --default-character-set=utf8mb4 -u$dbUser -p$dbPass --single-transaction --routines --triggers --events --set-gtid-purged=OFF $dbName > $containerDumpPath" 2>&1 | Out-Null

            if ($LASTEXITCODE -eq 0) {
                docker cp "${containerId}:${containerDumpPath}" "$dbBackupDir\full_dump.sql" 2>&1 | Out-Null
                docker compose exec -T mysql sh -c "rm -f $containerDumpPath" 2>&1 | Out-Null

                if ((Test-Path "$dbBackupDir\full_dump.sql") -and ((Get-Item "$dbBackupDir\full_dump.sql").Length -gt 1000)) {
                    $dumpSize = (Get-Item "$dbBackupDir\full_dump.sql").Length / 1MB
                    Write-Host "  Full dump: $([math]::Round($dumpSize, 2)) MB" -ForegroundColor Green
                    $dbDumpSuccess = $true
                }
            }

            # Schema-only dump
            Write-Host "  Creating schema-only dump..." -ForegroundColor Gray
            $containerSchemaPath = "/tmp/mind_db_schema_temp.sql"
            docker compose exec -T mysql sh -c "mysqldump --default-character-set=utf8mb4 -u$dbUser -p$dbPass --no-data --single-transaction --routines --triggers --events --set-gtid-purged=OFF $dbName > $containerSchemaPath" 2>&1 | Out-Null

            if ($LASTEXITCODE -eq 0) {
                docker cp "${containerId}:${containerSchemaPath}" "$dbBackupDir\schema_only.sql" 2>&1 | Out-Null
                docker compose exec -T mysql sh -c "rm -f $containerSchemaPath" 2>&1 | Out-Null

                if ((Test-Path "$dbBackupDir\schema_only.sql") -and ((Get-Item "$dbBackupDir\schema_only.sql").Length -gt 100)) {
                    $schemaSize = (Get-Item "$dbBackupDir\schema_only.sql").Length / 1KB
                    Write-Host "  Schema dump: $([math]::Round($schemaSize, 2)) KB" -ForegroundColor Green
                    $schemaDumpSuccess = $true
                }
            }
        } else {
            Write-Host "  WARNING: Could not find MySQL container ID" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  WARNING: MySQL container not running" -ForegroundColor Yellow
    }
} else {
    Write-Host "  WARNING: Could not read DB config from .env" -ForegroundColor Yellow
}

if (-not $dbDumpSuccess) {
    "Database dump was not available.`nMySQL container may not be running." | Out-File -FilePath "$dbBackupDir\dump_not_available.txt" -Encoding UTF8
}

# ============================================
# SECTION 2: DOCKER LOGS VIA dockerlogs.bat
# ============================================
Write-Host ""
Write-Host "[2/5] Docker Logs Collection (via dockerlogs.bat)" -ForegroundColor Yellow

$dockerLogsSuccess = $false
$hasComposeLogsFile = $false
$hasComposePsFile = $false
$hasDockerInfoFile = $false
$hasCeleryWorkerLogs = $false
$celeryWorkerContainers = @()
$celeryStatusFromPs = "UNKNOWN"

# Check if dockerlogs.bat exists
$dockerlogsBat = Join-Path $sourceDir "dockerlogs.bat"
if (Test-Path $dockerlogsBat) {
    Write-Host "  Running dockerlogs.bat..." -ForegroundColor Gray

    # Run dockerlogs.bat from the repo root
    Push-Location $sourceDir
    try {
        & cmd.exe /c "dockerlogs.bat" 2>&1 | Out-Null
        Write-Host "  dockerlogs.bat completed" -ForegroundColor Gray
    } catch {
        Write-Host "  WARNING: dockerlogs.bat failed: $_" -ForegroundColor Yellow
    }
    Pop-Location

    # Copy files from .dockerlogs/ to our temp dockerlogs folder
    $dockerLogsSource = Join-Path $sourceDir ".dockerlogs"
    if (Test-Path $dockerLogsSource) {
        $logFiles = Get-ChildItem -Path $dockerLogsSource -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -ne ".zip" }

        foreach ($logFile in $logFiles) {
            Copy-Item $logFile.FullName -Destination $dockerLogsDir -Force
            Write-Host "  Copied: $($logFile.Name)" -ForegroundColor Gray

            # Track what we have
            if ($logFile.Name -eq "docker_compose_logs.txt") {
                $hasComposeLogsFile = $true
            }
            if ($logFile.Name -eq "docker_compose_ps.txt") {
                $hasComposePsFile = $true
            }
            if ($logFile.Name -eq "_docker_info.txt") {
                $hasDockerInfoFile = $true
            }
            if ($logFile.Name -like "*celery-worker*") {
                $hasCeleryWorkerLogs = $true
                $celeryWorkerContainers += $logFile.Name
            }
        }

        $copiedCount = ($logFiles | Measure-Object).Count
        if ($copiedCount -gt 0) {
            $dockerLogsSuccess = $true
            Write-Host "  Copied $copiedCount log file(s)" -ForegroundColor Green
        }
    } else {
        Write-Host "  WARNING: .dockerlogs/ directory not found after running dockerlogs.bat" -ForegroundColor Yellow
    }
} else {
    Write-Host "  WARNING: dockerlogs.bat not found at $dockerlogsBat" -ForegroundColor Yellow
    Write-Host "  Falling back to direct docker compose logs collection..." -ForegroundColor Gray
    try {
        $env:COMPOSE_PROFILES = "main"
        docker compose ps -a | Out-File -FilePath "$dockerLogsDir\docker_compose_ps.txt" -Encoding UTF8
        docker compose logs --no-color --tail 10000 | Out-File -FilePath "$dockerLogsDir\docker_compose_logs.txt" -Encoding UTF8
        docker info | Out-File -FilePath "$dockerLogsDir\_docker_info.txt" -Encoding UTF8
        $hasComposePsFile = $true
        $hasComposeLogsFile = $true
        $hasDockerInfoFile = $true
        $dockerLogsSuccess = $true
    } catch {
        Write-Host "  WARNING: direct docker log capture failed: $_" -ForegroundColor Yellow
    }
}

# Verify critical files exist
if (-not $hasComposeLogsFile) {
    Write-Host "  WARNING: docker_compose_logs.txt not found" -ForegroundColor Yellow
    "docker_compose_logs.txt was not generated by dockerlogs.bat" | Out-File -FilePath "$dockerLogsDir\compose_logs_missing.txt" -Encoding UTF8
}
if (-not $hasComposePsFile) {
    Write-Host "  WARNING: docker_compose_ps.txt not found (CRITICAL for audit)" -ForegroundColor Yellow
    "docker_compose_ps.txt was not generated by dockerlogs.bat" | Out-File -FilePath "$dockerLogsDir\compose_ps_missing.txt" -Encoding UTF8
}
if (-not $hasDockerInfoFile) {
    Write-Host "  WARNING: _docker_info.txt not found" -ForegroundColor Yellow
}

# Check docker_compose_ps.txt for celery worker status (PRIMARY evidence source)
if ($hasComposePsFile) {
    $composePsPath = Join-Path $dockerLogsDir "docker_compose_ps.txt"
    $composePsContent = Get-Content $composePsPath -Raw -ErrorAction SilentlyContinue

    # Analyze celery worker status from compose ps output
    if ($composePsContent -match "celery-worker.*running" -or $composePsContent -match "celery-worker.*Up") {
        $celeryStatusFromPs = "RUNNING (shown in docker_compose_ps.txt)"
        $hasCeleryWorkerLogs = $true
        Write-Host "  Celery workers: RUNNING (from docker_compose_ps.txt)" -ForegroundColor Green
    } elseif ($composePsContent -match "celery-worker.*(exited|Exit|crashed|Exited)") {
        $celeryStatusFromPs = "EXITED/CRASHED (shown in docker_compose_ps.txt)"
        $hasCeleryWorkerLogs = $true
        Write-Host "  Celery workers: EXITED/CRASHED (from docker_compose_ps.txt)" -ForegroundColor Yellow
    } elseif ($composePsContent -match "celery-worker") {
        $celeryStatusFromPs = "PRESENT - status unclear (shown in docker_compose_ps.txt)"
        $hasCeleryWorkerLogs = $true
        Write-Host "  Celery workers: PRESENT (from docker_compose_ps.txt)" -ForegroundColor Yellow
    } else {
        $celeryStatusFromPs = "NOT PRESENT (service not defined or compose ps shows none)"
        Write-Host "  Celery workers: NOT PRESENT in docker_compose_ps.txt" -ForegroundColor Yellow
    }
} else {
    # Fallback to _docker_info.txt if docker_compose_ps.txt is missing
    if ($hasDockerInfoFile) {
        $dockerInfoPath = Join-Path $dockerLogsDir "_docker_info.txt"
        $dockerInfoContent = Get-Content $dockerInfoPath -Raw -ErrorAction SilentlyContinue
        if ($dockerInfoContent -match "celery-worker") {
            $hasCeleryWorkerLogs = $true
            $celeryStatusFromPs = "PRESENT (from _docker_info.txt, docker_compose_ps.txt missing)"
            Write-Host "  Celery workers found in _docker_info.txt (fallback)" -ForegroundColor Yellow
        } else {
            $celeryStatusFromPs = "UNKNOWN (docker_compose_ps.txt missing, no evidence in _docker_info.txt)"
            Write-Host "  WARNING: No celery workers found in _docker_info.txt" -ForegroundColor Yellow
        }
    } else {
        $celeryStatusFromPs = "UNKNOWN (no docker evidence files available)"
    }
}

# ============================================
# SECTION 3: PYTEST EVIDENCE
# ============================================
Write-Host ""
Write-Host "[3/5] Test Evidence (pytest)" -ForegroundColor Yellow

$pytestSuccess = $false
$pytestOutput = ""

# Try to run pytest in the backend container
Write-Host "  Running pytest -q in backend container..." -ForegroundColor Gray
try {
    $pytestResult = docker compose exec -T ai-api pytest -q --tb=short 2>&1
    $pytestOutput = $pytestResult -join "`n"

    if ($LASTEXITCODE -eq 0) {
        $pytestSuccess = $true
        Write-Host "  pytest completed successfully" -ForegroundColor Green
    } else {
        Write-Host "  pytest completed with failures (exit code: $LASTEXITCODE)" -ForegroundColor Yellow
    }
} catch {
    $pytestOutput = "pytest execution failed: $_"
    Write-Host "  WARNING: pytest execution failed: $_" -ForegroundColor Yellow
}

# Save pytest output (container execution)
if ($pytestOutput) {
    $pytestOutput | Out-File -FilePath "$logsDir\pytest_container.txt" -Encoding UTF8
    Write-Host "  Saved container pytest output to logs/pytest_container.txt" -ForegroundColor Gray
} else {
    "pytest was not executed or produced no output" | Out-File -FilePath "$logsDir\pytest_not_run.txt" -Encoding UTF8
}

# Prefer repo-run pytest output if present (per audit rules)
$repoPytest = Join-Path $sourceDir "logs\pytest.txt"
if (Test-Path $repoPytest) {
    Copy-Item $repoPytest -Destination "$logsDir\pytest.txt" -Force
    Write-Host "  Copied repo pytest output to logs/pytest.txt" -ForegroundColor Gray
}

# ============================================
# SECTION 4: CODE FILES
# ============================================
Write-Host ""
Write-Host "[4/5] Code Files" -ForegroundColor Yellow

# Patterns to exclude
$excludePatterns = @(
    "node_modules", "__pycache__", ".pytest_cache", ".venv", "venv", "env",
    "dist", "build", ".git", ".vscode", ".idea", "videos", "test-artifacts",
    "_dbdumps", "storage", "temp", "old", "design_screenshots", "design_comparison",
    "inbox", "testfiles_for_import", "ui-design", "nul", "test-results",
    "playwright-report", ".codebasebackup", ".dbbackup", ".dockerlogs", "test-reports"
)

$excludeExtensions = @(
    "*.pyc", "*.pyo", "*.pyd", "*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp",
    "*.ico", "*.svg", "*.mp4", "*.avi", "*.mov", "*.wmv", "*.zip", "*.rar",
    "*.7z", "*.tar", "*.gz", "*.iso", "*.har", "*.log", "*.sqlite", "*.db",
    "Untitled-*", "*.pem", "*.key", "id_rsa*"
)

$excludeSpecificFiles = @(
    ".env", ".env.local", ".env.production", ".env.*",
    "mono_se_db*.sql", "pip-log.txt", "credentials.json", "*.credentials"
)

function Should-Exclude {
    param($relativePath, $fileName)

    # Always exclude .env files
    if ($fileName -like ".env*") { return $true }

    foreach ($pattern in $excludePatterns) {
        if ($relativePath -match "\\$pattern\\|^$pattern\\|\\$pattern$|^$pattern$") {
            return $true
        }
    }
    foreach ($ext in $excludeExtensions) {
        if ($fileName -like $ext) { return $true }
    }
    foreach ($file in $excludeSpecificFiles) {
        if ($fileName -like $file) { return $true }
    }
    return $false
}

function Normalize-InventoryPath {
    param($pathValue)
    $normalized = $pathValue -replace "\\", "/"
    return $normalized.TrimStart("/")
}

$fileCount = 0
$fileInventory = @()

Get-ChildItem -Path $sourceDir -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $relativePath = $_.FullName.Substring($sourceDir.Length + 1)
    $normalizedPath = Normalize-InventoryPath $relativePath

    if (-not (Should-Exclude $relativePath $_.Name)) {
        $destPath = Join-Path $codeDir $relativePath

        if ($_.PSIsContainer) {
            if (-not (Test-Path $destPath)) {
                New-Item -ItemType Directory -Path $destPath -Force -ErrorAction SilentlyContinue | Out-Null
            }
        } else {
            $destDir = Split-Path $destPath -Parent
            if (-not (Test-Path $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force -ErrorAction SilentlyContinue | Out-Null
            }
            try {
                Copy-Item $_.FullName -Destination $destPath -Force -ErrorAction SilentlyContinue
                $fileCount++
                $fileInventory += "code/$normalizedPath`t$($_.Length)"
                if ($fileCount % 200 -eq 0) {
                    Write-Host "  Copied $fileCount files..." -ForegroundColor Gray
                }
            } catch { }
        }
    }
}

Write-Host "  Total code files: $fileCount" -ForegroundColor Green

# ============================================
# SECTION 5: MANIFEST FILES (TRUTHFUL)
# ============================================
Write-Host ""
Write-Host "[5/5] Generating Manifest (Evidence-Based)" -ForegroundColor Yellow

# Determine actual evidence available
$dockerLogsFiles = Get-ChildItem -Path $dockerLogsDir -File -ErrorAction SilentlyContinue
$dockerLogsFileNames = ($dockerLogsFiles | ForEach-Object { $_.Name }) -join ", "
$celeryLogsInZip = $dockerLogsFiles | Where-Object { $_.Name -like "*celery*" }
$hasCeleryEvidence = ($celeryLogsInZip.Count -gt 0) -or $hasCeleryWorkerLogs

$bucketSummaryPath = Join-Path $sourceDir "logs\bucket_decisions.md"
$bucketSummaryContent = ""
if (Test-Path $bucketSummaryPath) {
    $bucketSummaryContent = Get-Content $bucketSummaryPath -Raw -ErrorAction SilentlyContinue
    try {
        Copy-Item $bucketSummaryPath -Destination "$logsDir\bucket_decisions.md" -Force
    } catch { }
}

# manifest.md
$manifestContent = @"
# MIND Audit Snapshot Manifest

## System Information
- **System Prefix**: MIND
- **Generated**: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
- **Generator**: create_codebase.bat -> create_codebase.ps1 -> dockerlogs.bat

## Generation Command
``````
create_codebase.bat
``````

## Scripts Invoked
- **DB Backup**: mysqldump via docker compose exec (full + schema-only)
- **Docker Logs**: dockerlogs.bat -> scripts/collect_docker_logs.py
- **Tests**: pytest -q (local -> logs/pytest.txt); pytest -q via docker compose exec ai-api (logs/pytest_container.txt)
- **Git Evidence**: git status/diff outputs saved to logs/

## Declared Exclusions
- ``.env`` and all environment files (security)
- ``node_modules/``, ``__pycache__/``, ``.venv/`` (dependencies)
- ``.git/`` (version control)
- ``*.zip``, ``*.log``, media files (binary/generated)
- ``storage/``, ``test-results/`` (runtime data)
- Private keys and credentials (``*.pem``, ``*.key``, ``credentials.json``)

## ZIP Structure
- ``/code/`` - Repository source code
- ``/dbbackup/`` - Database dumps (full + schema-only)
- ``/dockerlogs/`` - Container logs and status (via dockerlogs.bat)
- ``/logs/`` - Test output + git evidence
- ``/manifest/`` - This manifest and inventory
"@
$manifestContent | Out-File -FilePath "$manifestDir\manifest.md" -Encoding UTF8
Write-Host "  Created manifest.md" -ForegroundColor Gray

# file_inventory.txt
$inventoryContent = @()
$inventoryContent += "# File Inventory for MIND_codebase_$timestampForZip.zip"
$inventoryContent += "# Format: path<TAB>size_bytes"
$inventoryContent += ""

# Add dbbackup files
Get-ChildItem -Path $dbBackupDir -File -ErrorAction SilentlyContinue | ForEach-Object {
    $inventoryContent += "$(Normalize-InventoryPath "dbbackup/$($_.Name)")`t$($_.Length)"
}

# Add dockerlogs files
Get-ChildItem -Path $dockerLogsDir -File -ErrorAction SilentlyContinue | ForEach-Object {
    $inventoryContent += "$(Normalize-InventoryPath "dockerlogs/$($_.Name)")`t$($_.Length)"
}

# Add logs files
Get-ChildItem -Path $logsDir -File -ErrorAction SilentlyContinue | ForEach-Object {
    $inventoryContent += "$(Normalize-InventoryPath "logs/$($_.Name)")`t$($_.Length)"
}

# Add code files (from earlier collection)
$inventoryContent += $fileInventory

# Add manifest files (will be added after creation)
$inventoryContent += "manifest/manifest.md`t$((Get-Item "$manifestDir\manifest.md").Length)"

$inventoryContent -join "`n" | Out-File -FilePath "$manifestDir\file_inventory.txt" -Encoding UTF8
Write-Host "  Created file_inventory.txt" -ForegroundColor Gray

# change_summary.md
$changeSummary = @"
# Change Summary

## Git Status at Snapshot Time
``````
"@

try {
    Push-Location $sourceDir
    $gitStatus = git status --porcelain 2>&1
    $gitLog = git log --oneline -10 2>&1
    Pop-Location
    $changeSummary += $gitStatus
    $changeSummary += @"
``````

## Recent Commits (last 10)
``````
$gitLog
``````
"@
} catch {
    $changeSummary += "Git not available`n``````"
}

if ($bucketSummaryContent) {
    $changeSummary += "`n`n## Dirty Worktree Handling`n"
    $changeSummary += $bucketSummaryContent
}

$changeSummary | Out-File -FilePath "$manifestDir\change_summary.md" -Encoding UTF8
Write-Host "  Created change_summary.md" -ForegroundColor Gray

# agent_final_message.md - TRUTHFUL AND EVIDENCE-BASED
# Celery status is ONLY derived from docker_compose_ps.txt (primary evidence)
$composeLogsStatus = if ($hasComposeLogsFile) { "PRESENT - docker_compose_logs.txt exists" } else { "MISSING - docker_compose_logs.txt not generated" }
$composePsStatus = if ($hasComposePsFile) { "PRESENT - docker_compose_ps.txt exists" } else { "MISSING - docker_compose_ps.txt not generated" }
$dockerInfoStatus = if ($hasDockerInfoFile) { "PRESENT - _docker_info.txt exists" } else { "MISSING - _docker_info.txt not generated" }
$pytestStatus = if ($pytestSuccess) { "PASSED - see logs/pytest.txt" } elseif (Test-Path "$logsDir\pytest.txt") { "EXECUTED WITH FAILURES - see logs/pytest.txt" } else { "NOT EXECUTED - pytest could not run" }

$agentMessage = @"
# Agent Final Message

## Snapshot Summary
- **Archive**: MIND_codebase_$timestampForZip.zip
- **Generated**: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
- **Code Files**: $fileCount
- **DB Full Dump**: $(if ($dbDumpSuccess) { "YES - dbbackup/full_dump.sql" } else { "NO" })
- **DB Schema Dump**: $(if ($schemaDumpSuccess) { "YES - dbbackup/schema_only.sql" } else { "NO" })
- **Docker Logs**: $(if ($dockerLogsSuccess) { "COLLECTED via dockerlogs.bat" } else { "NOT COLLECTED" })

## Evidence Verification (TRUTHFUL - Evidence-Backed Claims Only)

### Docker Logs Evidence (Required Files)
| File | Status | Purpose |
|------|--------|---------|
| docker_compose_ps.txt | $composePsStatus | PRIMARY: Compose-scoped container status (running/exited) |
| docker_compose_logs.txt | $composeLogsStatus | All service logs including startup/crash info |
| _docker_info.txt | $dockerInfoStatus | Docker versions + global/project container status |

- **Files in /dockerlogs/**: $dockerLogsFileNames

### Celery Worker Evidence (Derived from docker_compose_ps.txt)
- **Status**: $celeryStatusFromPs
$(if ($celeryWorkerContainers.Count -gt 0) { "- **Individual log files**: $($celeryWorkerContainers -join ', ')" })
- **Evidence source**: dockerlogs/docker_compose_ps.txt
- **Verification**: Open docker_compose_ps.txt and search for "celery-worker" to verify this claim

### Test Evidence
- **pytest execution**: $pytestStatus
$(if (Test-Path "$logsDir\pytest.txt") { "- **Output file**: logs/pytest.txt" } else { "- **Output file**: NOT PRESENT" })

### Dirty Worktree Handling
$(if ($bucketSummaryContent) { $bucketSummaryContent } else { "No bucket summary provided." })

## Verification Steps for Auditor
1. Extract ZIP and verify /code/, /dbbackup/, /dockerlogs/, /logs/, /manifest/ exist
2. Verify no .env file exists anywhere in the archive
3. **Check /dockerlogs/docker_compose_ps.txt** - PRIMARY evidence for container status
4. Check /dockerlogs/docker_compose_logs.txt for ALL service logs (includes ai-api/mysql/redis/nginx)
5. Check /dockerlogs/_docker_info.txt for docker versions and GLOBAL vs PROJECT container views
6. Review /logs/pytest.txt for test execution evidence
7. Verify /manifest/manifest.md contains generation details

## What Was NOT Done (if applicable)
$(if (-not $hasComposePsFile) { "- docker_compose_ps.txt was not generated - celery status cannot be verified" })
$(if (-not $hasCeleryWorkerLogs) { "- Celery workers were not found in docker_compose_ps.txt - check docker_compose_logs.txt for reasons" })
$(if (-not $pytestSuccess) { "- pytest did not pass all tests - see logs/pytest.txt for details" })
$(if (-not $dbDumpSuccess) { "- Database dump failed - MySQL container may not have been running" })
"@

$agentMessage | Out-File -FilePath "$manifestDir\agent_final_message.md" -Encoding UTF8
Write-Host "  Created agent_final_message.md (truthful)" -ForegroundColor Gray

# Update file_inventory with manifest files
$inventoryUpdate = Get-Content "$manifestDir\file_inventory.txt"
$inventoryUpdate += "manifest/file_inventory.txt`t$((Get-Item "$manifestDir\file_inventory.txt").Length)"
$inventoryUpdate += "manifest/change_summary.md`t$((Get-Item "$manifestDir\change_summary.md").Length)"
$inventoryUpdate += "manifest/agent_final_message.md`t$((Get-Item "$manifestDir\agent_final_message.md").Length)"
$inventoryUpdate -join "`n" | Out-File -FilePath "$manifestDir\file_inventory.txt" -Encoding UTF8

# ============================================
# CREATE ZIP ARCHIVE
# ============================================
Write-Host ""
Write-Host "Creating ZIP archive..." -ForegroundColor Cyan

if (Test-Path $zipFile) {
    Remove-Item $zipFile -Force
}

Compress-Archive -Path "$tempDir\*" -DestinationPath $zipFile -Force

Write-Host "Cleaning up..." -ForegroundColor Gray
Remove-Item -Path $tempDir -Recurse -Force

# ============================================
# VERIFICATION
# ============================================
Write-Host ""
Write-Host "Verifying archive..." -ForegroundColor Cyan

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($zipFile)

$hasCode = $zip.Entries | Where-Object { $_.FullName -like "code*" }
$hasDbBackup = $zip.Entries | Where-Object { $_.FullName -like "dbbackup*" }
$hasDockerLogs = $zip.Entries | Where-Object { $_.FullName -like "dockerlogs*" }
$hasLogs = $zip.Entries | Where-Object { $_.FullName -like "logs*" }
$hasManifest = $zip.Entries | Where-Object { $_.FullName -like "manifest*" }
$hasEnv = $zip.Entries | Where-Object { $_.FullName -like "*.env*" -or $_.Name -eq ".env" }
$hasComposeLogs = $zip.Entries | Where-Object { $_.FullName -like "*docker_compose_logs.txt*" }
$hasComposePs = $zip.Entries | Where-Object { $_.FullName -like "*docker_compose_ps.txt*" }
$hasCeleryLogs = $zip.Entries | Where-Object { $_.FullName -like "*celery*" }
$hasPytestOutput = $zip.Entries | Where-Object { $_.FullName -like "*pytest*" }
$hasGitEvidence = $zip.Entries | Where-Object { $_.FullName -like "logs/git_*" }

$zip.Dispose()

Write-Host "  /code/: $(if ($hasCode) { 'OK' } else { 'MISSING' })" -ForegroundColor $(if ($hasCode) { 'Green' } else { 'Red' })
Write-Host "  /dbbackup/: $(if ($hasDbBackup) { 'OK' } else { 'MISSING' })" -ForegroundColor $(if ($hasDbBackup) { 'Green' } else { 'Red' })
Write-Host "  /dockerlogs/: $(if ($hasDockerLogs) { 'OK' } else { 'MISSING' })" -ForegroundColor $(if ($hasDockerLogs) { 'Green' } else { 'Red' })
Write-Host "  /logs/: $(if ($hasLogs) { 'OK' } else { 'MISSING' })" -ForegroundColor $(if ($hasLogs) { 'Green' } else { 'Red' })
Write-Host "  /manifest/: $(if ($hasManifest) { 'OK' } else { 'MISSING' })" -ForegroundColor $(if ($hasManifest) { 'Green' } else { 'Red' })
Write-Host "  .env excluded: $(if (-not $hasEnv) { 'OK' } else { 'FAIL - .env FOUND!' })" -ForegroundColor $(if (-not $hasEnv) { 'Green' } else { 'Red' })
Write-Host "  docker_compose_ps.txt: $(if ($hasComposePs) { 'OK' } else { 'MISSING (CRITICAL)' })" -ForegroundColor $(if ($hasComposePs) { 'Green' } else { 'Red' })
Write-Host "  docker_compose_logs.txt: $(if ($hasComposeLogs) { 'OK' } else { 'MISSING' })" -ForegroundColor $(if ($hasComposeLogs) { 'Green' } else { 'Yellow' })
Write-Host "  Celery evidence: $(if ($hasCeleryLogs) { 'OK' } else { 'WARNING - not found' })" -ForegroundColor $(if ($hasCeleryLogs) { 'Green' } else { 'Yellow' })
Write-Host "  pytest output: $(if ($hasPytestOutput) { 'OK' } else { 'WARNING - not found' })" -ForegroundColor $(if ($hasPytestOutput) { 'Green' } else { 'Yellow' })
Write-Host "  git evidence: $(if ($hasGitEvidence) { 'OK' } else { 'WARNING - not found' })" -ForegroundColor $(if ($hasGitEvidence) { 'Green' } else { 'Yellow' })

# Final summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AUDIT SNAPSHOT COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Archive: $zipFile" -ForegroundColor White
$fileSize = (Get-Item $zipFile).Length / 1MB
Write-Host ("Size: {0:N2} MB" -f $fileSize) -ForegroundColor Gray
Write-Host ""
