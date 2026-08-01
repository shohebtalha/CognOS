$ErrorActionPreference = "SilentlyContinue"

$cognosDir = Join-Path $HOME ".cognos\terminal"
$transcript = Join-Path $cognosDir "transcript.log"
New-Item -ItemType Directory -Force $cognosDir | Out-Null

if (-not $global:CognOSTranscriptStarted) {
    Start-Transcript -Path $transcript -Append | Out-Null
    $global:CognOSTranscriptStarted = $true
}

function global:prompt {
    $exitCode = if ($global:LASTEXITCODE -ne $null) { $global:LASTEXITCODE } else { 0 }
    if ($exitCode -ne 0) {
        "[CognOS command failed: exit_code=$exitCode]" | Out-Host
    }
    "PS $($executionContext.SessionState.Path.CurrentLocation)> "
}
