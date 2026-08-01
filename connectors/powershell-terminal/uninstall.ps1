$markerStart = "# >>> CognOS terminal connector >>>"
$markerEnd = "# <<< CognOS terminal connector <<<"

if (-not (Test-Path $PROFILE.CurrentUserAllHosts)) {
    Write-Host "No PowerShell profile found."
    exit 0
}

$content = Get-Content -Raw $PROFILE.CurrentUserAllHosts
$pattern = [regex]::Escape($markerStart) + "(.|\n|\r)*?" + [regex]::Escape($markerEnd)
$updated = [regex]::Replace($content, $pattern, "").Trim()
Set-Content -Path $PROFILE.CurrentUserAllHosts -Value $updated

Write-Host "CognOS PowerShell terminal connector removed."
