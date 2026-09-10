param(
    [int]$Port = 8087
)

$ErrorActionPreference = "Stop"
$env:DB_URL = "sqlite:///./local-demo.db"
$env:APP_AUTH_ENABLED = "false"
$env:RATE_LIMIT_PER_MINUTE = "0"

.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port $Port
