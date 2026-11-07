# Offline Wi-Fi detection threshold experiment

Run the digital chain of `wifi_rx_pluto.grc` on the Moodle baseband recordings.
The same input is replayed for each threshold, so no Pluto or USB capture is
needed. The inputs are raw interleaved float32 I/Q at 20 MS/s. Keep the course
recordings and the generated output outside the repository.

From PowerShell, with Radioconda and the `ieee802_11` module available:

```powershell
Set-Location 'C:/path/to/CDIG'
$env:XDG_CACHE_HOME = 'threshold-results'
$env:MPLCONFIGDIR = 'threshold-results/mpl'
& C:/Radioconda/python.exe -B 'C:/path/to/DigCom/experiments/threshold_sweep.py' `
  'Wifi_Project_Baseband_recordings/Sample1_20MHz_Channel36.bin' `
  --frequency 5180e6 --output threshold-results/run-ch36 --plot
```

Use a relative recording path and ASCII cache path to avoid GNU Radio file
and FFT cache errors with non-ASCII Windows profile paths. `--plot` needs
Matplotlib. For Sample 2 use 2437 MHz and for Sample 3 use 5500 MHz. Use a
different output directory for each recording. The default sweep is 0.56,
0.20, 0.40, 0.70 and 0.80; override it with `--thresholds` if needed.
The optional autocorrelation plot reconstructs the metric over the first
50 ms and zooms into one example. It is an illustration, not a log of
every threshold crossing.

Fixed settings: 48 samples for the correlation sum, 64 for the power sum,
lag 16, minimum plateau setting 2, long sync length 320 and LS equalization.
Receiver gain is already baked into each recording.

- `short_tags`: start tags emitted by Sync Short, including candidates that
  later fail synchronization, header decoding or CRC.
- `valid_frames`: frames emitted by Decode MAC after its CRC check. Without
  a known number of transmissions this is a count, not a delivery ratio.
- BPSK symbols are selected using the decoded PHY encoding tag, before the MAC
  CRC check. A candidate with an incorrectly decoded header can still
  contribute points. The plots use the same axes; points outside the displayed
  range still count in the reported RMS and median distance to the nearest
  BPSK point (+1 or −1). These are decision-directed distances, not EVM against
  known transmitted symbols. The frames selected by different thresholds may
  differ, so the metrics describe the observed output populations.

For the demo, compare 0.56 with 0.80 on the same input, then show 0.20 to
illustrate why accepting more candidates can yield fewer valid frames.
