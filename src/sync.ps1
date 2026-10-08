# Denní synchronizace vinné karty: export z ERP -> output/wines.json -> GitHub -> Vercel.
#
# Spouští naplánovaná úloha Windows "EnotekaVinotrh-Sync" (denně 4:00, viz CLAUDE.md).
# Commituje a pushuje do main jen tehdy, když se změnila data webu -- Vercel pak
# nasadí sám. Při chybě exportu nebo transformace se nic necommituje a web zůstane
# beze změny. Průběh se zapisuje do logs/sync.log.

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
# UNC cesta místo Y:\ -- namapovaný disk nemusí v naplánované úloze existovat
$Source = '\\ZNOJMO\LahoferFTP\enoteka\Enoteka_pozice.xlsx'
$Target = Join-Path $Root 'data\Enoteka_pozice.xlsx'
$LogDir = Join-Path $Root 'logs'
$Log = Join-Path $LogDir 'sync.log'
$DataPaths = @('output/wines.json', 'output/k_doplneni.json', 'data/Enoteka_pozice.xlsx')

New-Item -ItemType Directory -Force $LogDir | Out-Null
function Write-Log($msg) {
    $line = '{0:yyyy-MM-dd HH:mm:ss}  {1}' -f (Get-Date), $msg
    Add-Content -Path $Log -Value $line -Encoding utf8
    Write-Output $line
}

# git/py píšou do stderr i běžné zprávy -- vyhodnocuje se jen exit code
function Invoke-Native([string]$exe, [string[]]$arguments) {
    $ErrorActionPreference = 'Continue'
    $out = & $exe @arguments 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) {
        throw "$exe $($arguments -join ' ') selhalo (exit $LASTEXITCODE): $($out -join ' | ')"
    }
    return $out
}

Set-Location $Root
try {
    Write-Log 'Start synchronizace'
    if (-not (Test-Path $Source)) { throw "Export nenalezen: $Source" }
    $sourceItem = Get-Item $Source
    Write-Log ("Export z ERP: {0:yyyy-MM-dd HH:mm}" -f $sourceItem.LastWriteTime)

    Invoke-Native git @('pull', '--ff-only', '--quiet') | Out-Null
    Copy-Item $Source $Target -Force

    $env:PYTHONIOENCODING = 'utf-8'
    [Console]::OutputEncoding = [Text.Encoding]::UTF8
    $transform = Invoke-Native py @('-3', '-W', 'ignore', 'src/transform.py')
    $transform | Where-Object { $_ -notmatch 'URL na vinotrh\.cz \(\d+/' -and $_.Trim() } | ForEach-Object { Write-Log "  $_" }

    $changed = Invoke-Native git (@('status', '--porcelain', '--') + $DataPaths[0..1])
    if (-not $changed) {
        # xlsx se při každém exportu binárně liší, i když data stejná -- nevracet do gitu zbytečně
        Invoke-Native git @('checkout', '--', 'data/Enoteka_pozice.xlsx') | Out-Null
        Write-Log 'Data beze změny, nic se nenasazuje'
        exit 0
    }

    Invoke-Native git (@('add', '--') + $DataPaths) | Out-Null
    $msg = 'Aktualizovat data vinné karty z ERP ({0:yyyy-MM-dd})' -f (Get-Date)
    Invoke-Native git @('commit', '--quiet', '-m', $msg, '--', $DataPaths[0], $DataPaths[1], $DataPaths[2]) | Out-Null
    Invoke-Native git @('push', '--quiet', 'origin', 'main') | Out-Null
    Write-Log "Nasazeno: $msg"
}
catch {
    # rozpracovanou kopii exportu vrátit, ať příští běh začíná z čistého stavu
    & git checkout -- data/Enoteka_pozice.xlsx 2>$null
    Write-Log "CHYBA: $($_.Exception.Message)"
    exit 1
}
