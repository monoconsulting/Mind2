param(
  [string]$Url = 'http://localhost:8008/ai/api/health',
  [int]$TimeoutSec = 300
)

$ErrorActionPreference = 'SilentlyContinue'
$deadline = (Get-Date).AddSeconds($TimeoutSec)
while ((Get-Date) -lt $deadline) {
  try {
    $res = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
    if ($res.StatusCode -eq 200) {
      Write-Output "READY $($res.StatusCode)"
      exit 0
    }
  } catch {
    # ignore and retry
  }
  Start-Sleep -Seconds 3
}
Write-Error "API not ready after $TimeoutSec seconds: $Url"
exit 1
