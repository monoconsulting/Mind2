# PowerShell script to create codebase archive WITH DATABASE DUMP
$sourceDir = "E:\projects\Mind2"

# Get current date and time in YYMMDD_HH-MM format
$timestamp = Get-Date -Format "yyMMdd_HH-mm"
$zipFile = "$sourceDir\codebase_$timestamp.zip"
$dumpFile = "$sourceDir\database_dump_$timestamp.sql"

Write-Host "Creating codebase archive WITH DATABASE: codebase_$timestamp.zip" -ForegroundColor Green
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
    Write-Host "Creating MySQL dump..." -ForegroundColor Yellow

    # Create MySQL dump using docker exec
    $dumpCommand = "docker exec mind2-mysql-1 mysqldump -u$dbUser -p$dbPass $dbName"

    try {
        Invoke-Expression "$dumpCommand > `"$dumpFile`" 2>&1"

        if (Test-Path $dumpFile) {
            $dumpSize = (Get-Item $dumpFile).Length / 1MB
            Write-Host "Database dump created: $([math]::Round($dumpSize, 2)) MB" -ForegroundColor Green
        } else {
            Write-Host "Warning: Database dump failed. Continuing without dump..." -ForegroundColor Red
        }
    } catch {
        Write-Host "Warning: Could not create database dump. Error: $_" -ForegroundColor Red
        Write-Host "Continuing without dump..." -ForegroundColor Yellow
    }
    Write-Host ""
} else {
    Write-Host "Warning: Could not read database configuration from .env file" -ForegroundColor Red
    Write-Host "Continuing without database dump..." -ForegroundColor Yellow
    Write-Host ""
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
    "playwright-report"
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

# Copy database dump to temp directory if it exists
$hasDump = $false
if (Test-Path $dumpFile) {
    Write-Host "Adding database dump to archive..." -ForegroundColor Cyan
    Copy-Item $dumpFile -Destination "$tempDir\database_dump.sql" -Force
    $hasDump = $true
}

Write-Host "Creating zip archive..." -ForegroundColor Cyan

# Remove existing zip if it exists
if (Test-Path $zipFile) {
    Remove-Item $zipFile -Force
}

# Create zip archive
Compress-Archive -Path "$tempDir\*" -DestinationPath $zipFile -Force

Write-Host "Cleaning up temporary files..." -ForegroundColor Cyan
Remove-Item -Path $tempDir -Recurse -Force

# Remove temporary database dump
if (Test-Path $dumpFile) {
    Remove-Item $dumpFile -Force
}

Write-Host ""
Write-Host "Archive created successfully!" -ForegroundColor Green
Write-Host "Location: $zipFile" -ForegroundColor White
$fileSize = (Get-Item $zipFile).Length / 1MB
Write-Host ("Size: {0:N2} MB" -f $fileSize) -ForegroundColor White
Write-Host ""
Write-Host "Contents:" -ForegroundColor Yellow
Write-Host "  - Complete codebase (excluding node_modules, cache, media files)" -ForegroundColor White
if ($hasDump) {
    Write-Host "  - Full MySQL database dump (database_dump.sql)" -ForegroundColor White
}
Write-Host ""
