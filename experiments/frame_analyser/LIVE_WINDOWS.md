# Live Frame Analyser check on Windows

Connect the ADALM-Pluto by USB. From PowerShell in the repository run:

```powershell
./open_pluto_analyser.ps1
```

The launcher creates a private local folder under `live-runs/` and prints its
path. The graph uses `ip:pluto.local` as in the original Pluto receiver.
If it cannot connect, check the USB connection and the Pluto's IIO URI.

1. Open the flowgraph with the launcher above. The default settings are
   channel 100 (5500 MHz), gain 50 dB and 20 MS/s. To use another channel or
   gain for a timed run, set its default in GRC before pressing F6.
2. Press F6 and keep those settings fixed during the measurement.
3. Run for about 30 seconds and close the receiver's Qt window normally.
4. Open `frames.pcap` from the printed folder in Wireshark. Clear the display
   filter and read the total **Packets** count.
5. Count data rows in `frames.csv` (replace the example with the printed path):

   ```powershell
   @(Import-Csv -LiteralPath '.\live-runs\YOUR-RUN\frames.csv').Count
   ```

Record channel, centre frequency, gain, duration, both counts and any
overflow messages. Decode MAC delivers the same decoded frames to both
branches. Two zero counts do not validate the setup. If counts differ,
repeat on an active channel and check whether frames were still queued when
you stopped. These counts describe the receiver output, not all frames
transmitted over the air.

Run the launcher again for each retained measurement. Pressing F6 again in
the same Companion session can overwrite that session's files. Keep the
raw PCAP local because it can contain nearby devices' addresses.

If `ip:pluto.local` does not resolve, change **Pluto IIO URI** in GRC to
`ip:192.168.2.1` if the Pluto uses its default USB IP address.

## Running without the PowerShell launcher

From the repository root, create a fresh output directory and set
`CDIG_LIVE_RUN` before opening GRC or running the generated Python. For
example, on Linux with the receiver dependencies installed:

```sh
export CDIG_LIVE_RUN="$(mktemp -d "$PWD/live-runs/run-XXXXXXXX")"
```

Create the parent `live-runs/` first. GRC needs `blocks/` in
`GRC_BLOCKS_PATH`, and the generated Python needs it in `PYTHONPATH`.
If you already generated the Python, you can start it with
`python3 wifi_rx_pluto_analyser.py --pluto-uri ip:192.168.2.1`.
