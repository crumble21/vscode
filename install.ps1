# Link this repo's config into VSCodium and/or VS Code (Windows).
#
#   .\install.ps1                  every editor that's installed (codium, code)
#   .\install.ps1 codium           just VSCodium
#   .\install.ps1 code             just VS Code
#
# Symlinks need Developer Mode enabled or an elevated shell; otherwise settings files are copied.
# Existing files are moved aside to <name>.bak.<timestamp>, never deleted. Safe to re-run.
param([ValidateSet('codium', 'code')][string[]]$Editor)
$ErrorActionPreference = 'Stop'

$repo  = $PSScriptRoot
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

if (-not $Editor) {
    $Editor = @('codium', 'code') | Where-Object { Get-Command $_ -ErrorAction SilentlyContinue }
    if (-not $Editor) { throw "Neither codium nor code is on PATH; name one: .\install.ps1 codium|code" }
}

function Backup($dst) {
    Move-Item $dst "$dst.bak.$stamp"
    Write-Host "backup  $dst -> $dst.bak.$stamp"
}

function Link-File($src, $dst) {
    $item = Get-Item $dst -ErrorAction SilentlyContinue
    if ($item -and $item.LinkType -eq 'SymbolicLink' -and $item.Target -eq $src) { Write-Host "ok      $dst"; return }
    if ($item) { Backup $dst }
    try {
        New-Item -ItemType SymbolicLink -Path $dst -Target $src | Out-Null
        Write-Host "linked  $dst"
    } catch {
        Copy-Item $src $dst
        Write-Host "copied  $dst  (no symlink permission; re-run after edits, or enable Developer Mode)"
    }
}

function Link-Dir($src, $dst) {  # a directory junction needs no special permission
    $item = Get-Item $dst -ErrorAction SilentlyContinue
    if ($item -and $item.LinkType -eq 'Junction' -and $item.Target -eq $src) { Write-Host "ok      $dst"; return }
    if ($item) { Backup $dst }
    New-Item -ItemType Junction -Path $dst -Target $src | Out-Null
    Write-Host "linked  $dst"
}

function Register-Theme($extDir, $themeDst) {
    # The editor only loads folders listed in extensions.json once that file exists.
    $registry = Join-Path $extDir 'extensions.json'
    if (-not (Test-Path $registry)) { return }
    $version = (Get-Content (Join-Path $repo 'theme\greenpuccin\package.json') -Raw | ConvertFrom-Json).version
    $entries = @(Get-Content $registry -Raw | ConvertFrom-Json | Where-Object { $_.identifier.id -ne 'local.greenpuccin' })
    $uriPath = $themeDst -replace '\\', '/'                # file URI path: C:\x -> /c:/x
    if ($uriPath -match '^([A-Za-z]):') { $uriPath = $Matches[1].ToLower() + $uriPath.Substring(1) }
    $uriPath = '/' + $uriPath
    $entries += [pscustomobject]@{
        identifier       = @{ id = 'local.greenpuccin' }
        version          = $version
        location         = [ordered]@{ '$mid' = 1; path = $uriPath; scheme = 'file' }
        relativeLocation = 'local.greenpuccin'
    }
    # WriteAllText: UTF-8 without a BOM (Set-Content -Encoding UTF8 adds one on PowerShell 5.1)
    [IO.File]::WriteAllText($registry, (ConvertTo-Json -InputObject $entries -Depth 10 -Compress))
    Write-Host "registered local.greenpuccin $version in $registry"
}

foreach ($e in $Editor) {
    if ($e -eq 'codium') {
        $name = 'VSCodium'; $userDir = Join-Path $env:APPDATA 'VSCodium\User'
        $extDir = if ($env:VSCODIUM_EXTENSIONS_DIR) { $env:VSCODIUM_EXTENSIONS_DIR } else { Join-Path $env:USERPROFILE '.vscode-oss\extensions' }
    } else {
        $name = 'VS Code'; $userDir = Join-Path $env:APPDATA 'Code\User'
        $extDir = if ($env:VSCODE_EXTENSIONS_DIR) { $env:VSCODE_EXTENSIONS_DIR } else { Join-Path $env:USERPROFILE '.vscode\extensions' }
    }
    Write-Host "== $name"
    New-Item -ItemType Directory -Force -Path $userDir, $extDir | Out-Null
    foreach ($file in 'settings.json', 'keybindings.json') {
        Link-File (Join-Path $repo "User\$file") (Join-Path $userDir $file)
    }
    $themeDst = Join-Path $extDir 'local.greenpuccin'
    Link-Dir (Join-Path $repo 'theme\greenpuccin') $themeDst
    Register-Theme $extDir $themeDst
    Write-Host ''
}

Write-Host "Done. Restart the editor."
