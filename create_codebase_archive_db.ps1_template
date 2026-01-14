# PowerShell script to create codebase archive WITH DATABASE DUMP
$sourceDir = "E:\projects\Mind2"

# Get current date in YYYY-MM-DD format
$timestamp = Get-Date -Format "yyyy-MM-dd"
$timestampWithTime = Get-Date -Format "yyMMdd_HH-mm"

# Create backup folders if they don't exist
$codebaseBackupDir = "$sourceDir\.codebasebackup"
$dbBackupDir = "$sourceDir\.dbbackup"
if (-not (Test-Path $codebaseBackupDir)) {
    New-Item -ItemType Directory -Path $codebaseBackupDir -Force | Out-Null
}
if (-not (Test-Path $dbBackupDir)) {
    New-Item -ItemType Directory -Path $dbBackupDir -Force | Out-Null
}

$zipFile = "$codebaseBackupDir\codebase_$timestampWithTime.zip"
$dumpFile = "$dbBackupDir\mind_db_dump_$timestamp.sql"

Write-Host "Creating codebase archive WITH DATABASE: codebase_$timestampWithTime.zip" -ForegroundColor Green
Write-Host ""

# Read database configuration from .env file
Write-Host "Reading database configuration..." -ForegroundColor Yellow
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

if ($dbName -and $dbUser -and $dbPass) {
    Write-Host "Database: $dbName" -ForegroundColor Cyan
    Write-Host ""

    # Check if MySQL container is running
    $containerStatus = docker inspect -f '{{.State.Running}}' mind2-mysql-1 2>$null

    if ($containerStatus -ne "true") {
        Write-Host "ERROR: MySQL container (mind2-mysql-1) is not running!" -ForegroundColor Red
        Write-Host "Start Docker services first: mind_docker_compose_up.bat" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "ABORTED: Database dump is required for backup." -ForegroundColor Red
        exit 1
    } else {
        Write-Host "Creating MySQL dump..." -ForegroundColor Yellow

        # Create dump INSIDE the container to avoid PowerShell encoding issues (mojibake)
        # This preserves Swedish characters correctly
        $containerDumpPath = "/tmp/mind_db_dump_temp.sql"

        try {
            # Step 1: Create dump inside container
            $dumpResult = docker compose exec -T mysql sh -c "mysqldump --default-character-set=utf8mb4 -u$dbUser -p$dbPass --single-transaction --routines --triggers --events --set-gtid-purged=OFF $dbName > $containerDumpPath" 2>&1

            if ($LASTEXITCODE -ne 0) {
                Write-Host "ERROR: mysqldump failed inside container!" -ForegroundColor Red
                Write-Host "ABORTED: Database dump is required for backup." -ForegroundColor Red
                exit 1
            }

            # Step 2: Get container ID and copy file out
            $containerId = docker compose ps -q mysql
            if (-not $containerId) {
                Write-Host "ERROR: Could not find MySQL container ID!" -ForegroundColor Red
                Write-Host "ABORTED: Database dump is required for backup." -ForegroundColor Red
                exit 1
            }

            docker cp "${containerId}:${containerDumpPath}" $dumpFile 2>&1 | Out-Null

            if ($LASTEXITCODE -ne 0) {
                Write-Host "ERROR: Failed to copy dump from container!" -ForegroundColor Red
                Write-Host "ABORTED: Database dump is required for backup." -ForegroundColor Red
                exit 1
            }

            # Step 3: Clean up temp file in container
            docker compose exec -T mysql sh -c "rm -f $containerDumpPath" 2>&1 | Out-Null

            if ((Test-Path $dumpFile) -and ((Get-Item $dumpFile).Length -gt 1000)) {
                $dumpSize = (Get-Item $dumpFile).Length / 1MB
                Write-Host "Database dump created: $([math]::Round($dumpSize, 2)) MB" -ForegroundColor Green
            } else {
                Write-Host "ERROR: Database dump failed or is empty!" -ForegroundColor Red
                if (Test-Path $dumpFile) { Remove-Item $dumpFile -Force }
                Write-Host "ABORTED: Database dump is required for backup." -ForegroundColor Red
                exit 1
            }
        } catch {
            Write-Host "ERROR: Could not create database dump. Error: $_" -ForegroundColor Red
            if (Test-Path $dumpFile) { Remove-Item $dumpFile -Force }
            Write-Host "ABORTED: Database dump is required for backup." -ForegroundColor Red
            exit 1
        }
        Write-Host ""
    }
} else {
    Write-Host "ERROR: Could not read database configuration from .env file" -ForegroundColor Red
    Write-Host "ABORTED: Database dump is required for backup." -ForegroundColor Red
    exit 1
}

Write-Host "Collecting relevant code files..." -ForegroundColor Yellow
Write-Host "Excluding: node_modules, cache files, images, videos, temp files, etc." -ForegroundColor Yellow
Write-Host ""

# Patterns to exclude
$excludePatterns = @(
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".git",
    ".vscode",
    ".idea",
    "videos",
    "test-artifacts",
    "_dbdumps",
    "storage",
    "temp",
    "old",
    "design_screenshots",
    "design_comparison",
    "inbox",
    "testfiles_for_import",
    "ui-design",
    "nul",
    "test-results",
    "playwright-report",
    ".codebasebackup",
    ".dbbackup"
)

$excludeExtensions = @(
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.jpg",
    "*.jpeg",
    "*.png",
    "*.gif",
    "*.bmp",
    "*.ico",
    "*.svg",
    "*.mp4",
    "*.avi",
    "*.mov",
    "*.wmv",
    "*.zip",
    "*.rar",
    "*.7z",
    "*.tar",
    "*.gz",
    "*.iso",
    "*.har",
    "*.log",
    "*.sqlite",
    "*.db",
    "Untitled-*"
)

$excludeSpecificFiles = @(
    "mono_se_db*.sql",
    "pip-log.txt",
    "pip-delete-this-directory.txt"
)

# Create temporary directory for filtered files
$tempDir = Join-Path $env:TEMP "codebase_temp_$([guid]::NewGuid().ToString())"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

Write-Host "Copying files to temporary directory..." -ForegroundColor Cyan

# Function to check if path should be excluded
function Should-Exclude {
    param($relativePath, $fileName)

    # Check directory patterns
    foreach ($pattern in $excludePatterns) {
        if ($relativePath -match "\\$pattern\\|^$pattern\\|\\$pattern$") {
            return $true
        }
    }

    # Check file extensions
    foreach ($ext in $excludeExtensions) {
        if ($fileName -like $ext) {
            return $true
        }
    }

    # Check specific file patterns
    foreach ($file in $excludeSpecificFiles) {
        if ($fileName -like $file) {
            return $true
        }
    }

    return $false
}

# Copy files recursively, excluding patterns
$fileCount = 0
Get-ChildItem -Path $sourceDir -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $relativePath = $_.FullName.Substring($sourceDir.Length + 1)

    if (-not (Should-Exclude $relativePath $_.Name)) {
        $destPath = Join-Path $tempDir $relativePath

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
                if ($fileCount % 100 -eq 0) {
                    Write-Host "  Copied $fileCount files..." -ForegroundColor Gray
                }
            } catch {
                # Silently skip files that can't be copied
            }
        }
    }
}

Write-Host "Total files copied: $fileCount" -ForegroundColor Green
Write-Host ""

# Copy database dump to temp directory (required)
Write-Host "Adding database dump to archive..." -ForegroundColor Cyan
Copy-Item $dumpFile -Destination "$tempDir\mind_db_dump.sql" -Force

Write-Host "Creating zip archive..." -ForegroundColor Cyan

# Remove existing zip if it exists
if (Test-Path $zipFile) {
    Remove-Item $zipFile -Force
}

# Create zip archive
Compress-Archive -Path "$tempDir\*" -DestinationPath $zipFile -Force

Write-Host "Cleaning up temporary files..." -ForegroundColor Cyan
Remove-Item -Path $tempDir -Recurse -Force

# Verify that database dump is included in the zip
Write-Host "Verifying archive contents..." -ForegroundColor Cyan
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($zipFile)
$dumpInZip = $zip.Entries | Where-Object { $_.FullName -eq "mind_db_dump.sql" }
$zip.Dispose()

if (-not $dumpInZip) {
    Write-Host ""
    Write-Host "ERROR: Database dump (mind_db_dump.sql) is NOT in the zip file!" -ForegroundColor Red
    Write-Host "ABORTED: Backup verification failed." -ForegroundColor Red
    Remove-Item $zipFile -Force
    exit 1
}

Write-Host ""
Write-Host "Archive created and verified successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Locations:" -ForegroundColor Yellow
Write-Host "  Codebase: $zipFile" -ForegroundColor White
$fileSize = (Get-Item $zipFile).Length / 1MB
Write-Host ("  Size: {0:N2} MB" -f $fileSize) -ForegroundColor Gray
Write-Host "  Database: $dumpFile" -ForegroundColor White
$dumpSize = (Get-Item $dumpFile).Length / 1MB
Write-Host ("  Size: {0:N2} MB" -f $dumpSize) -ForegroundColor Gray
Write-Host ""
Write-Host "Contents of zip:" -ForegroundColor Yellow
Write-Host "  - Complete codebase (excluding node_modules, cache, media files)" -ForegroundColor White
Write-Host "  - Full MySQL database dump (mind_db_dump.sql)" -ForegroundColor White
Write-Host ""
