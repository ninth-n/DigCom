param([string]$RadiocondaRoot = 'C:/Radioconda')

$python = Join-Path $RadiocondaRoot 'python.exe'
$companion = Join-Path $RadiocondaRoot 'Scripts/gnuradio-companion-script.py'
if (!(Test-Path -LiteralPath $python) -or !(Test-Path -LiteralPath $companion)) {
    throw 'Radioconda or GNU Radio Companion was not found.'
}
$run = 'live-runs/' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$env:PATH = "$RadiocondaRoot;$RadiocondaRoot/Library/bin;$RadiocondaRoot/Scripts;" + $env:PATH
$env:GRC_BLOCKS_PATH = Join-Path $PSScriptRoot 'blocks'
$env:PYTHONPATH = $env:GRC_BLOCKS_PATH + [IO.Path]::PathSeparator + $env:PYTHONPATH
$env:XDG_CACHE_HOME = Join-Path $env:TEMP 'cdig-grc-cache'
$env:CDIG_LIVE_RUN = $run

Push-Location $PSScriptRoot
try {
    New-Item -ItemType Directory -Path $run -ErrorAction Stop | Out-Null
    Write-Host "Results: $PSScriptRoot/$run"
    Write-Host 'Use F6 to start. Close the receiver window to finish the capture.'
    & $python -B $companion (Join-Path $PSScriptRoot 'wifi_rx_pluto_analyser.grc')
} finally {
    Pop-Location
}
