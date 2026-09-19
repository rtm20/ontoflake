param(
    [string]$Connection = 'hackathon',
    [string[]]$Steps = @('00', '01', 'put', '02', '03', '04', '05', '06', 'harness', 'app'),
    [switch]$Regenerate
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$snow = Join-Path $root '.venv\Scripts\snow.exe'
$py   = Join-Path $root '.venv\Scripts\python.exe'

function Invoke-Snow([string[]]$SnowArgs) {
    $out = & $snow @SnowArgs -c $Connection 2>&1 | Where-Object { $_ -notmatch 'encoding_diagnostics|warnings.warn' }
    $out | Out-String -Width 160 | Write-Host
    if ($LASTEXITCODE -ne 0) { throw "snow failed: $($SnowArgs -join ' ')" }
}

if ($Regenerate -or -not (Test-Path (Join-Path $root 'data\out\supplier.csv'))) {
    Write-Host "== generate synthetic data" -ForegroundColor Cyan
    & $py (Join-Path $root 'data\generate.py')
}

foreach ($step in $Steps) {
    if ($step -match '^\d+$') { $step = ([int]$step).ToString('00') }
    if ($step -eq 'put') {
        Write-Host "== PUT csv -> @ONTOFLAKE.RAW.LANDING" -ForegroundColor Cyan
        $dir = (Join-Path $root 'data\out') -replace '\\', '/'
        Invoke-Snow @('sql', '-q', "PUT 'file://$dir/*.csv' @ONTOFLAKE.RAW.LANDING AUTO_COMPRESS=TRUE OVERWRITE=TRUE")
        continue
    }
    if ($step -eq 'harness') {
        Write-Host "== persona consistency harness" -ForegroundColor Cyan
        $env:SNOWFLAKE_CONNECTION = $Connection
        & (Join-Path $root '.venv\Scripts\python.exe') (Join-Path $root 'harness\consistency_check.py')
        if ($LASTEXITCODE -ne 0) { throw "consistency harness failed" }
        continue
    }
    if ($step -eq 'app') {
        Write-Host "== deploy Streamlit app" -ForegroundColor Cyan
        Push-Location (Join-Path $root 'app')
        try { Invoke-Snow @('streamlit', 'deploy', '--replace', '--prune') } finally { Pop-Location }
        continue
    }
    $file = Get-ChildItem (Join-Path $root 'sql') -Filter "${step}_*.sql" | Select-Object -First 1
    if (-not $file) { Write-Host "== skip $step (no file)" -ForegroundColor DarkGray; continue }
    Write-Host "== $($file.Name)" -ForegroundColor Cyan
    if ($step -eq '06') {
        $pubFile = Join-Path $root 'config\keys\ontoflake_app_svc.pub'
        if (-not (Test-Path $pubFile)) { Write-Host "== skip 06 (no config/keys/ontoflake_app_svc.pub)" -ForegroundColor DarkGray; continue }
        Invoke-Snow @('sql', '-f', $file.FullName, '-D', "pub_key=$((Get-Content $pubFile -Raw).Trim())")
        continue
    }
    Invoke-Snow @('sql', '-f', $file.FullName)
}
Write-Host "== done" -ForegroundColor Green
