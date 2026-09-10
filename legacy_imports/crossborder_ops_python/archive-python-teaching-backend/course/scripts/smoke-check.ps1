param(
    [string]$BaseUrl = "http://127.0.0.1:8090"
)

$ErrorActionPreference = "Stop"

function Assert-True($condition, $message) {
    if (-not $condition) {
        throw $message
    }
}

Write-Host "Checking backend health..."
$health = Invoke-RestMethod -Uri "$BaseUrl/actuator/health" -Method Get
Assert-True ($health.status -eq "UP") "Backend health is not UP"

Write-Host "Checking classroom login..."
$loginBody = @{ operatorId = 3 } | ConvertTo-Json
$login = Invoke-RestMethod -Uri "$BaseUrl/auth/login" -Method Post -ContentType "application/json" -Body $loginBody
Assert-True ($login.operatorId -eq 3) "Login response did not return operator 3"

Write-Host "Checking business summary tool..."
$summary = Invoke-RestMethod -Uri "$BaseUrl/test/tool/business-summary" -Method Post -ContentType "application/json" -Body "{}"
Assert-True ($summary -match "2,849.94") "Business summary did not include the expected average order profit"

Write-Host "Checking visual payload tool..."
$chart = Invoke-RestMethod -Uri "$BaseUrl/test/tool/business-trend-chart" -Method Post -ContentType "application/json" -Body "{}"
Assert-True ($chart -match "VISUAL_PAYLOAD:") "Chart response did not include VISUAL_PAYLOAD"

Write-Host "Smoke check passed."
