$ErrorActionPreference = "Stop"

$baseUrl = "http://127.0.0.1:8087"

function Assert-True($condition, $message) {
    if (-not $condition) {
        throw $message
    }
}

Write-Host "Checking backend health..."
$health = Invoke-RestMethod -Uri "$baseUrl/actuator/health" -Method Get
Assert-True ($health.status -eq "UP") "Backend health is not UP"

Write-Host "Checking classroom login..."
$loginBody = @{ operatorId = 3 } | ConvertTo-Json
$login = Invoke-RestMethod -Uri "$baseUrl/auth/login" -Method Post -ContentType "application/json" -Body $loginBody
Assert-True ($login.operatorId -eq 3) "Login response did not return operator 3"

Write-Host "Checking business summary tool..."
$summary = Invoke-RestMethod -Uri "$baseUrl/test/tool/business-summary" -Method Post -ContentType "application/json" -Body "{}"
Assert-True ($summary.Length -gt 20) "Business summary response is too short"

Write-Host "Checking visual payload tool..."
$chart = Invoke-RestMethod -Uri "$baseUrl/test/tool/business-trend-chart" -Method Post -ContentType "application/json" -Body "{}"
Assert-True ($chart -match "VISUAL_PAYLOAD:") "Chart response did not include VISUAL_PAYLOAD"

Write-Host "Smoke check passed."
