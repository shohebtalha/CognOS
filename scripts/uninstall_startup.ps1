$shortcutPath = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\CognOS.lnk"
if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath
    Write-Host "Removed CognOS startup shortcut."
} else {
    Write-Host "CognOS startup shortcut was not installed."
}
