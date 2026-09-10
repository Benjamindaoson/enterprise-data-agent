# Production Runbook

## Local SQLite Demo

```powershell
.\scripts\run-local-sqlite.ps1 -Port 8087
```

## Verification

```powershell
.\scripts\verify.ps1 -BaseUrl http://127.0.0.1:8087
```

For authenticated mode:

```powershell
.\scripts\verify.ps1 -BaseUrl http://127.0.0.1:8087 -LoginCode $env:APP_LOGIN_CODE
```

## Docker Production Shape

```powershell
$env:APP_AUTH_SECRET="replace-with-long-random-secret"
docker compose -f docker-compose.prod.yml up --build
```

## Required Environment

- `APP_AUTH_SECRET`: required when `APP_AUTH_ENABLED=true`.
- `DB_URL`: SQLAlchemy URL. MySQL is the intended production database.
- `CORS_ORIGINS`: comma-separated browser origins.
- `RATE_LIMIT_PER_MINUTE`: per-token or per-IP in-process limit.
- `LLM_API_KEY`: optional. Without it the service returns deterministic Tool output.

## Known Scaling Boundary

The current rate limiter is process-local. Use Redis or an API gateway when running more than one API replica.

## Incident Checks

```powershell
Invoke-RestMethod http://127.0.0.1:8087/healthz
Invoke-RestMethod http://127.0.0.1:8087/readyz
Invoke-RestMethod http://127.0.0.1:8087/metrics
Get-Content -Tail 100 .\prod-local-8087.err.log
```

If `/healthz` is UP and `/readyz` is DOWN, the API process is alive but the database is unavailable.
