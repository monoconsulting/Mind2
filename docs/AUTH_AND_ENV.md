# Auth and Environment Setup

This project uses Bearer JWT for API auth. For local/dev convenience, the API exposes a minimal login endpoint that issues tokens using a shared admin password.

## Endpoints (via Nginx)
- API base: http://localhost:8008/ai/api/
- Health (no auth): GET /ai/api/health
- Login (issues JWT): POST /ai/api/auth/login
- Protected test: GET /ai/api/admin/ping

## Required environment keys
Set these in `.env` at the repo root (Docker Compose picks them up):

- JWT_SECRET_KEY: Strong random secret used to sign JWTs (HS256). Preferred over `JWT_SECRET`.
- ADMIN_PASSWORD: Password accepted by `/auth/login` to mint a token.
- ALLOWED_ORIGINS: Comma-separated origins allowed by CORS (e.g., `http://localhost:5173,http://localhost:8008`).
- LOG_LEVEL: Logging verbosity (INFO, DEBUG, WARN, ERROR).
- DB_NAME, DB_USER, DB_PASS: Used by MySQL init and API DB connection.
- (Optional) REDIS_DB: Redis logical DB index (default 0).

Compose already wires internal host/ports for containers. Only set `DB_HOST/DB_PORT` and `REDIS_HOST/REDIS_PORT` if running the API outside Docker Compose.

## Generate a strong secret (Windows PowerShell)
```powershell
[Convert]::ToBase64String((New-Object byte[] 48 | %{ (New-Object System.Security.Cryptography.RNGCryptoServiceProvider).GetBytes($_); $_ }))
```
Paste the value into `JWT_SECRET_KEY`.

## Login from PowerShell
```powershell
# Request a token
$body = @{ username='admin'; password='<your ADMIN_PASSWORD>' } | ConvertTo-Json
$resp = Invoke-RestMethod -Uri 'http://localhost:8008/ai/api/auth/login' -Method POST -Body $body -ContentType 'application/json'
$JWT = $resp.access_token

# Call a protected route
Invoke-RestMethod -Uri 'http://localhost:8008/ai/api/admin/ping' -Headers @{ Authorization = "Bearer $JWT" }
```

- Success → 200 `{ "ok": true }`
- Bad creds → 401 `{ "error": "invalid_credentials" }`
- Login disabled (missing ADMIN_PASSWORD) → 503 `{ "error": "login_disabled" }`

## SPA/browser notes
Ensure your SPA origin is listed in `ALLOWED_ORIGINS` to receive CORS headers. Send the token in the `Authorization` header for each request.

## Production guidance
- Keep `JWT_SECRET_KEY` and `ADMIN_PASSWORD` out of code; inject via your orchestrator or a secrets manager.
- Consider migrating to an identity provider (OIDC) for real SSO. The current login is intended for dev/staging bootstrap.
