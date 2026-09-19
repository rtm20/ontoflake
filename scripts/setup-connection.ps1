$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$src  = Join-Path $root 'config\connections.toml'
$dstDir = Join-Path $env:USERPROFILE '.snowflake'
$dst  = Join-Path $dstDir 'connections.toml'
$cfg  = Join-Path $dstDir 'config.toml'
$snow = Join-Path $root '.venv\Scripts\snow.exe'

if ((Get-Content $src -Raw) -match 'PASTE_PASSWORD_HERE') { throw "Set password in $src first." }

New-Item -ItemType Directory -Force $dstDir | Out-Null
Copy-Item $src $dst -Force

# connections.toml takes precedence only if config.toml has no [connections.*]; strip any stale ones.
if (Test-Path $cfg) {
    $lines = Get-Content $cfg
    $out = @(); $skip = $false
    foreach ($l in $lines) {
        if ($l -match '^\[connections\.') { $skip = $true; continue }
        if ($l -match '^\[') { $skip = $false }
        if (-not $skip) { $out += $l }
    }
    Set-Content $cfg ($out -join "`n")
}

Write-Host "Wrote $dst"
& $snow connection test -c hackathon 2>&1 | Select-String -NotMatch 'encoding|warnings.warn'
