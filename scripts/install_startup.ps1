$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$desktop = Join-Path $repo "desktop"
$shortcutPath = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\CognOS.lnk"
$target = "cmd.exe"
$args = "/c cd /d `"$desktop`" && npm run start"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.Arguments = $args
$shortcut.WorkingDirectory = $desktop
$shortcut.WindowStyle = 7
$shortcut.Description = "Start CognOS desktop assistant"
$shortcut.Save()

Write-Host "CognOS startup shortcut installed:"
Write-Host $shortcutPath
