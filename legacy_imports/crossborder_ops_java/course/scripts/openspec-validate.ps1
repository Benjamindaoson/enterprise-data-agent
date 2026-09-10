$ErrorActionPreference = "Stop"

$openspec = Join-Path $env:APPDATA "npm\openspec.cmd"
if (-not (Test-Path $openspec)) {
    throw "OpenSpec CLI not found at $openspec. Install @fission-ai/openspec first."
}

& $openspec validate build-crossborder-ops-agent --strict
