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

try {
  $repoRoot = Split-Path -Parent $PSScriptRoot
  $envPath = Join-Path $repoRoot '.env'
  $adminPassword = Get-EnvValue -Path $envPath -Key 'ADMIN_PASSWORD'
  if (-not $adminPassword) { throw 'ADMIN_PASSWORD not found in .env' }

  # Ping
  $pingOk = $false; $pingResp = $null; $pingErr = $null
  try {
    $pingResp = Invoke-RestMethod -Uri ("$BaseUrl/ai/api/admin/ping") -TimeoutSec 5
    $pingOk = $true
  } catch {
    $pingErr = $_.Exception.Message
  }

  # Login
  $loginOk = $false; $jwt = $null; $loginResp = $null; $loginErr = $null
  try {
    $body = @{ username = 'admin'; password = $adminPassword } | ConvertTo-Json
    $loginResp = Invoke-RestMethod -Uri ("$BaseUrl/ai/api/auth/login") -Method POST -Body $body -ContentType 'application/json' -TimeoutSec 10
    if ($loginResp.access_token) { $jwt = $loginResp.access_token; $loginOk = $true }
  } catch {
    $loginErr = $_.Exception.Message
  }

  # Receipts
  $receipts = $null; $itemsCount = $null; $meta = $null; $receiptsErr = $null
  if ($loginOk -and $jwt) {
    try {
      $headers = @{ Authorization = "Bearer $jwt" }
      $receipts = Invoke-RestMethod -Uri ("$BaseUrl/ai/api/receipts?page=1&page_size=10") -Headers $headers -TimeoutSec 15
      if ($receipts.items) {
        $itemsCount = $receipts.items.Count
      } elseif ($receipts -is [System.Array]) {
        $itemsCount = $receipts.Count
      } else {
        $itemsCount = 0
      }
      if ($receipts.meta) { $meta = $receipts.meta }
    } catch {
      $receiptsErr = $_.Exception.Message
    }
  }

  # Admin ping (unauthenticated should be 401, authenticated should be 200)
  $admin401 = $null; $admin200 = $null
  try {
    $null = Invoke-WebRequest -UseBasicParsing -Uri ("$BaseUrl/ai/api/admin/ping") -Method GET -TimeoutSec 5
    $admin401 = $true
  } catch {
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode.value__ -eq 401) { $admin401 = $false } else { $admin401 = $true }
  }
  try {
    if ($jwt) {
      $authHeaders = @{ Authorization = "Bearer $jwt" }
      $resp = Invoke-WebRequest -UseBasicParsing -Uri ("$BaseUrl/ai/api/admin/ping") -Headers $authHeaders -Method GET -TimeoutSec 5
      $admin200 = ($resp.StatusCode -eq 200)
    }
  } catch {
    $admin200 = $false
  }

  $result = [pscustomobject]@{
    base_url = $BaseUrl
    ping_ok = $pingOk
    ping = $pingResp
    login_ok = $loginOk
    token_len = if ($jwt) { $jwt.Length } else { 0 }
    receipts_items = $itemsCount
    meta = $meta
    admin_ping_unauthenticated_is_401 = (-not $admin401)
    admin_ping_authenticated_ok = $admin200
    errors = [pscustomobject]@{
      ping = $pingErr
      login = $loginErr
      receipts = $receiptsErr
    }
  }
  $result | ConvertTo-Json -Depth 6
} catch {
  Write-Error $_.Exception.Message
  exit 1
}
