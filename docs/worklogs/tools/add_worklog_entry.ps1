<#
.SYNOPSIS
  Generate a rolling worklog entry block using Git and print to console.
.DESCRIPTION
  Produces a Markdown entry for the YY-MM-DD_Worklog.md (Rolling Log, newest-first).
  Saves a copy under .worklog_generated/YYYY-MM-DD_HHMM_entry.md and tries to copy to clipboard.
.PARAMETER Title
  Short title of the change.
.PARAMETER ChangeType
  One of: feat, fix, chore, docs, perf, refactor, test, ops.
.PARAMETER Scope
  Component/module scope, e.g. transcripts/parser.
.PARAMETER Tickets
  Optional ticket IDs or PR links, comma-separated.
.PARAMETER UseLastCommit
  If set, collect changed files from the last commit instead of working tree.
.EXAMPLE
  .\tools\add_worklog_entry.ps1 -Title 'Fix transcript parser guard' -ChangeType fix -Scope 'transcripts/parser' -Tickets 'ABC-123' -UseLastCommit
#>
param(
  [Parameter(Mandatory=$true)][string]$Title,
  [Parameter(Mandatory=$true)][ValidateSet('feat','fix','chore','docs','perf','refactor','test','ops')][string]$ChangeType,
  [Parameter(Mandatory=$true)][string]$Scope,
  [string]$Tickets = "",
  [switch]$UseLastCommit
)

function Exec([string]$cmd) {
  try {
    $out = (Invoke-Expression $cmd) 2>$null
    return $out
  } catch {
    return $null
  }
}

$now = Get-Date
$hhmm = $now.ToString('HH:mm')
$datestamp = $now.ToString('yyyy-MM-dd_HHmm')

$branch = Exec 'git rev-parse --abbrev-ref HEAD'
if (-not $branch) { $branch = '<branch-not-found>' }

$commit = Exec 'git rev-parse --short HEAD'
if (-not $commit) { $commit = '<commit-not-found>' }

if ($UseLastCommit) {
  $files = Exec 'git diff --name-only HEAD~1..HEAD'
} else {
  $files = Exec 'git diff --name-only'
  if (-not $files -or $files.Count -eq 0) {
    $files = Exec 'git diff --name-only HEAD~1..HEAD'
  }
}
if (-not $files) { $files = @() }

# Detect docs updates
$docsUpdated = @()
foreach ($f in $files) {
  if ($f -match '^(docs/|documentation/|doc/|README\.md$)') {
    $docsUpdated += $f
  }
}

# Build comma lists
$filesListShort = ($files -join ', ')
if (-not $filesListShort) { $filesListShort = '<none>' }

$docsList = ($docsUpdated | ForEach-Object { "  - `{$_}` — <what changed>" }) -join "`n"
if (-not $docsList) { $docsList = '  - N/A' }

# Entry body
$entry = @"
#### [$hhmm] $Title
- **Change type:** $ChangeType
- **Scope (component/module):** `$Scope`
- **Tickets/PRs:** $Tickets
- **Branch:** `$branch`
- **Commit(s):** `$commit`
- **Environment:** <runtime/container/profile if relevant>
- **Commands run:**
  ```bash
  <command one>
  <command two>
  ```
- **Result summary:** <1–3 lines outcome>
- **Files changed (exact):**
  - <fill with paths/line ranges/symbols>
- **Unified diff (minimal, per file or consolidated):**
  ```diff
  <paste minimal unified diffs here>
  ```
- **Tests executed:** <pytest/playwright commands + brief pass/fail>
- **Performance note (if any):** <metric before → after>
- **System documentation updated:**
$docsList
- **Artifacts:** <screenshots/logs/report paths>
- **Next action:** <what to do next>
"@

# Index row
$indexRow = "| $hhmm | $Title | $ChangeType | `"$Scope`" | $Tickets | `$commit` | $filesListShort |"

# Output
"--- INDEX ROW ---"
$indexRow
"`n--- ENTRY BLOCK ---"
$entry

# Save generated copy
$outfile = ".worklog_generated/$datestamp`_entry.md"
$dir = Split-Path $outfile -Parent
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
$indexRow + "`n`n" + $entry | Out-File -FilePath $outfile -Encoding UTF8
Write-Host "`nSaved: $outfile"

# Try to copy to clipboard (Windows / PowerShell Core)
try {
  $combined = $indexRow + "`n`n" + $entry
  if (Get-Command Set-Clipboard -ErrorAction SilentlyContinue) {
    $combined | Set-Clipboard
    Write-Host "Copied to clipboard via Set-Clipboard."
  } elseif (Get-Command clip.exe -ErrorAction SilentlyContinue) {
    $combined | clip.exe
    Write-Host "Copied to clipboard via clip.exe."
  }
} catch { }
