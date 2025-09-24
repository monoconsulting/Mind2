param(
  [string]$BaseUrl = 'http://localhost:8008'
)

$ErrorActionPreference = 'Stop'

function Get-EnvValue { param([string]$Path,[string]$Key) if (-not (Test-Path $Path)) { throw "Missing .env at $Path" } $line=(Select-String -Path $Path -Pattern "^$Key="|Select-Object -First 1).Line; if(-not $line){return $null}; return $line.Substring($line.IndexOf('=')+1) }

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot '.env'
$adminPassword = Get-EnvValue -Path $envPath -Key 'ADMIN_PASSWORD'
if (-not $adminPassword) { throw 'ADMIN_PASSWORD not found in .env' }

# Ensure inbox exists and add a demo file
$inbox = Join-Path $repoRoot 'inbox'
New-Item -ItemType Directory -Force -Path $inbox | Out-Null
$demoFile = Join-Path $inbox ('demo-' + [guid]::NewGuid().ToString() + '.txt')
Set-Content -Path $demoFile -Value 'demo e2e content' -Encoding UTF8

# Wait for API health
function Wait-ApiReady {
  param([string]$HealthUrl, [int]$TimeoutSec=120)
  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  while ((Get-Date) -lt $deadline) {
    try {
      $r = Invoke-WebRequest -UseBasicParsing -Uri $HealthUrl -TimeoutSec 5
      if ($r.StatusCode -eq 200) { return }
    } catch {}
    Start-Sleep -Seconds 2
  }
  throw "API not ready after ${TimeoutSec}s: $HealthUrl"
}

Wait-ApiReady -HealthUrl ("$BaseUrl/ai/api/health") -TimeoutSec 180

# Login
$body = @{ username='admin'; password=$adminPassword } | ConvertTo-Json
$login = Invoke-RestMethod -Uri ("$BaseUrl/ai/api/auth/login") -Method POST -Body $body -ContentType 'application/json'
$jwt = $login.access_token
$headers = @{ Authorization = "Bearer $jwt" }

# Trigger fetch (which auto-enqueues OCR)
$fetch = Invoke-RestMethod -Uri ("$BaseUrl/ai/api/ingest/fetch-ftp") -Method POST -Headers $headers -ContentType 'application/json'

# Optionally queue any remaining new files (noop if none)
$queue = Invoke-RestMethod -Uri ("$BaseUrl/ai/api/ingest/queue-new?limit=5") -Method POST -Headers $headers -ContentType 'application/json'

$out = [pscustomobject]@{ fetch = $fetch; queue = $queue }
$out | ConvertTo-Json -Depth 8