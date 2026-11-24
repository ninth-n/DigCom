# Live Frame Analyser check on Windows

Connect the ADALM-Pluto by USB. From PowerShell in the repository run:

```powershell
./open_pluto_analyser.ps1
```

The launcher creates a private local folder under `live-runs/` and prints its
path. The graph uses `ip:pluto.local` as in the original Pluto receiver.
If it cannot connect, check the USB connection and the Pluto's IIO URI.

1. Open the flowgraph with the launcher above and press F6 in GNU Radio Companion.
2. Select a channel with traffic and a fixed gain. Leave the sample rate at
   20 MS/s. For a timed comparison, select the settings, close the run and
   use a new launcher session with those settings set before pressing F6.
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
