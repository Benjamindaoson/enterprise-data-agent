param(
    [string]$BaseUrl = "http://127.0.0.1:8087",
    [string]$LoginCode = ""
)

$ErrorActionPreference = "Stop"

.\.venv\Scripts\python.exe -m pytest
powershell -NoProfile -ExecutionPolicy Bypass -File course\scripts\smoke-check.ps1 -BaseUrl $BaseUrl -LoginCode $LoginCode
