# Open the offline receiver with the project's Frame Analyser available.
$env:PATH = 'C:/Radioconda;C:/Radioconda/Library/bin;C:/Radioconda/Scripts;' + $env:PATH
$env:GRC_BLOCKS_PATH = Join-Path $PSScriptRoot 'blocks'
$env:PYTHONPATH = (Join-Path $PSScriptRoot 'blocks') + [IO.Path]::PathSeparator + $env:PYTHONPATH
$env:XDG_CACHE_HOME = Join-Path $env:TEMP 'cdig-grc-cache'
& C:/Radioconda/python.exe -B C:/Radioconda/Scripts/gnuradio-companion-script.py (Join-Path $PSScriptRoot 'wifi_rx_recording.grc')
