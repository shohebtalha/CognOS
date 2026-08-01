$ErrorActionPreference = "Stop"

$source = Join-Path $PSScriptRoot "CognOS.Profile.ps1"
$profileDir = Split-Path -Parent $PROFILE.CurrentUserAllHosts
New-Item -ItemType Directory -Force $profileDir | Out-Null

$markerStart = "# >>> CognOS terminal connector >>>"
$markerEnd = "# <<< CognOS terminal connector <<<"
$block = @"
$markerStart
. "$source"
$markerEnd
"@

if (Test-Path $PROFILE.CurrentUserAllHosts) {
    $content = Get-Content -Raw $PROFILE.CurrentUserAllHosts
    if ($content -notlike "*$markerStart*") {
        Add-Content -Path $PROFILE.CurrentUserAllHosts -Value "`n$block"
    }
} else {
    Set-Content -Path $PROFILE.CurrentUserAllHosts -Value $block
}

Write-Host "CognOS PowerShell terminal connector installed."
Write-Host "Transcript path: $HOME\.cognos\terminal\transcript.log"
