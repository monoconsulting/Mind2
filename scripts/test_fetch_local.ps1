param(
  [string]$BaseUrl = 'http://localhost:8008'
)

$ErrorActionPreference = 'Stop'

function Get-EnvValue {
  param(
    [string]$Path,
    [string]$Key
  )
  if (-not (Test-Path $Path)) { throw "Missing .env at $Path" }
  $line = (Select-String -Path $Path -Pattern "^$Key=" | Select-Object -First 1).Line
  if (-not $line) { return $null }
  return $line.Substring($line.IndexOf('=') + 1)
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot '.env'
$adminPassword = Get-EnvValue -Path $envPath -Key 'ADMIN_PASSWORD'
if (-not $adminPassword) { throw 'ADMIN_PASSWORD not found in .env' }

# Prepare local inbox with a demo file
$inbox = Join-Path $repoRoot 'inbox'
New-Item -ItemType Directory -Force -Path $inbox | Out-Null
$demoFile = Join-Path $inbox 'demo-receipt.txt'
Set-Content -Path $demoFile -Value 'demo receipt content' -Encoding UTF8

# Login to get JWT
$body = @{ username = 'admin'; password = $adminPassword } | ConvertTo-Json
$login = Invoke-RestMethod -Uri ("$BaseUrl/ai/api/auth/login") -Method POST -Body $body -ContentType 'application/json'
$jwt = $login.access_token

# Trigger fetch (local inbox mode works when FTP_HOST is not set)
$headers = @{ Authorization = "Bearer $jwt" }
$resp = Invoke-RestMethod -Uri ("$BaseUrl/ai/api/ingest/fetch-ftp") -Method POST -Headers $headers -ContentType 'application/json'
$resp | ConvertTo-Json -Depth 5