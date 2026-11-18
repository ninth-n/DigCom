param(
    [string]$RecordingsDir = (Join-Path $PSScriptRoot 'recordings'),
    [string]$CsvPath = (Join-Path $PSScriptRoot 'frame-analyser.csv'),
    [string]$RadiocondaRoot = 'C:/Radioconda'
)

# Configure this launch using local paths supplied by the caller.
$env:PATH = "$RadiocondaRoot;$RadiocondaRoot/Library/bin;$RadiocondaRoot/Scripts;" + $env:PATH
$env:CDIG_RECORDINGS = (Resolve-Path -LiteralPath $RecordingsDir -ErrorAction Stop).Path
$env:CDIG_CSV = [IO.Path]::GetFullPath($CsvPath)
if (-not (Test-Path -LiteralPath (Split-Path $env:CDIG_CSV -Parent))) {
    throw 'The CSV output directory must already exist.'
}
$env:GRC_BLOCKS_PATH = Join-Path $PSScriptRoot 'blocks'
$env:PYTHONPATH = (Join-Path $PSScriptRoot 'blocks') + [IO.Path]::PathSeparator + $env:PYTHONPATH
$env:XDG_CACHE_HOME = Join-Path $env:TEMP 'cdig-grc-cache'
Push-Location $PSScriptRoot
try {
    & (Join-Path $RadiocondaRoot 'python.exe') -B (Join-Path $RadiocondaRoot 'Scripts/gnuradio-companion-script.py') (Join-Path $PSScriptRoot 'wifi_rx_recording.grc')
} finally {
    Pop-Location
}
