# PowerShell script to create codebase archive (CODE ONLY - NO DATABASE)
$sourceDir = "E:\projects\Mind2"

# Get current date and time in YYMMDD_HH-MM format
$timestamp = Get-Date -Format "yyMMdd_HH-mm"
$zipFile = "$sourceDir\codebase_$timestamp.zip"

Write-Host "Creating codebase archive (code only): codebase_$timestamp.zip" -ForegroundColor Green
Write-Host ""
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

Write-Host "Creating zip archive..." -ForegroundColor Cyan

# Remove existing zip if it exists
if (Test-Path $zipFile) {
    Remove-Item $zipFile -Force
}

# Create zip archive
Compress-Archive -Path "$tempDir\*" -DestinationPath $zipFile -Force

Write-Host "Cleaning up temporary files..." -ForegroundColor Cyan
Remove-Item -Path $tempDir -Recurse -Force

Write-Host ""
Write-Host "Archive created successfully!" -ForegroundColor Green
Write-Host "Location: $zipFile" -ForegroundColor White
$fileSize = (Get-Item $zipFile).Length / 1MB
Write-Host ("Size: {0:N2} MB" -f $fileSize) -ForegroundColor White
Write-Host ""
Write-Host "Contents:" -ForegroundColor Yellow
Write-Host "  - Complete codebase (excluding node_modules, cache, media files)" -ForegroundColor White
Write-Host "  - NO database dump included (use create_codebase_archive_db.bat for DB)" -ForegroundColor Yellow
Write-Host ""
