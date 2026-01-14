<#
.SYNOPSIS
Deletes all files named exactly "nul" in the current directory and all subdirectories.

.DESCRIPTION
"nul" is a reserved device name in Windows (like CON, PRN, AUX, COM1, LPT1).
Standard PowerShell/Windows APIs cannot see or delete these files.

This script uses:
1. Git to find files named "nul" (git bypasses Windows name restrictions)
2. The \\?\ path prefix to delete them (bypasses Windows device name parsing)

.NOTES
Run in the folder you want to clean. Requires git to be installed.
#>

$rootPath = (Get-Location).Path

Write-Host "Searching for 'nul' files using git (bypasses Windows reserved name restrictions)..."

# Use git ls-files to find untracked files named "nul"
$gitOutput = git ls-files --others --exclude-standard 2>$null | Where-Object { $_ -match '(^|/)nul$' }

# Also check for tracked files named "nul"
$gitTracked = git ls-files 2>$null | Where-Object { $_ -match '(^|/)nul$' }

$allNulFiles = @()
if ($gitOutput) { $allNulFiles += $gitOutput }
if ($gitTracked) { $allNulFiles += $gitTracked }

if ($allNulFiles.Count -eq 0) {
    Write-Host "No files named 'nul' found."
    exit 0
}

Write-Host "Found $($allNulFiles.Count) file(s) named 'nul':"

foreach ($relativePath in $allNulFiles) {
    $fullPath = Join-Path $rootPath $relativePath
    # Convert to \\?\ path to bypass Windows device name parsing
    $literalPath = "\\?\$fullPath"

    Write-Host "  - $relativePath"

    try {
        # Use cmd.exe del with \\?\ prefix - this works for reserved names
        $result = cmd /c "del `"$literalPath`"" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    Deleted successfully!" -ForegroundColor Green
        } else {
            Write-Warning "    cmd del failed, trying .NET method..."
            # Fallback: try .NET File.Delete with literal path
            [System.IO.File]::Delete($literalPath)
            Write-Host "    Deleted via .NET!" -ForegroundColor Green
        }
    }
    catch {
        Write-Warning "    Failed to delete: $($_.Exception.Message)"
    }
}

Write-Host ""
Write-Host "Done. Run 'git status' to verify."
