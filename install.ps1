# Link this repo's VSCodium config into place (Windows).
# Symlinks need Developer Mode enabled or an elevated shell; otherwise files are copied.
# Existing files are moved aside to <name>.bak.<timestamp>, never deleted.
$ErrorActionPreference = 'Stop'

$repo    = $PSScriptRoot
$userDir = Join-Path $env:APPDATA 'VSCodium\User'
$stamp   = Get-Date -Format 'yyyyMMdd-HHmmss'
New-Item -ItemType Directory -Force -Path $userDir | Out-Null

foreach ($name in 'settings.json', 'keybindings.json') {
    $src = Join-Path $repo "User\$name"
    $dst = Join-Path $userDir $name

    $item = Get-Item $dst -ErrorAction SilentlyContinue
    if ($item -and $item.LinkType -eq 'SymbolicLink' -and $item.Target -eq $src) {
        Write-Host "ok      $dst"; continue
    }
    if ($item) {
        Move-Item $dst "$dst.bak.$stamp"
        Write-Host "backup  $dst -> $dst.bak.$stamp"
    }
    try {
        New-Item -ItemType SymbolicLink -Path $dst -Target $src | Out-Null
        Write-Host "linked  $dst"
    } catch {
        Copy-Item $src $dst
        Write-Host "copied  $dst  (no symlink permission; re-run after edits, or enable Developer Mode)"
    }
}
# Greenpuccin theme, as a local extension. A directory junction needs no special permission.
# VSCodium only loads folders listed in extensions.json once that file exists, so register it there too.
$extDir = if ($env:VSCODIUM_EXTENSIONS_DIR) { $env:VSCODIUM_EXTENSIONS_DIR } else { Join-Path $env:USERPROFILE '.vscode-oss\extensions' }
$themeSrc = Join-Path $repo 'theme\greenpuccin'
$themeDst = Join-Path $extDir 'local.greenpuccin'
New-Item -ItemType Directory -Force -Path $extDir | Out-Null
$item = Get-Item $themeDst -ErrorAction SilentlyContinue
if ($item -and $item.LinkType -eq 'Junction' -and $item.Target -eq $themeSrc) {
    Write-Host "ok      $themeDst"
} else {
    if ($item) {
        Move-Item $themeDst "$themeDst.bak.$stamp"
        Write-Host "backup  $themeDst -> $themeDst.bak.$stamp"
    }
    New-Item -ItemType Junction -Path $themeDst -Target $themeSrc | Out-Null
    Write-Host "linked  $themeDst"
}
$registry = Join-Path $extDir 'extensions.json'
if (Test-Path $registry) {
    $version = (Get-Content (Join-Path $themeSrc 'package.json') -Raw | ConvertFrom-Json).version
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

Write-Host "`nDone. Restart VSCodium."
