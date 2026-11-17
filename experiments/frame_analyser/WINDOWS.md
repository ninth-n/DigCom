# GNU Radio Companion recording integration on Windows

Open `wifi_rx_recording.grc` using `open_recording_receiver.ps1` from a
PowerShell session with Radioconda installed at `C:/Radioconda`.
The launcher sets the block, Python and library paths for that process.

The recording flowgraph uses the receiver's digital chain at 20 MS/s,
threshold 0.56, correlation window 48, Sync Long length 320 and LS
equalization. Decode MAC's `out` message port feeds Frame Analyser's
`frames` port. Its `channel` output feeds Channel Display Source, which
holds the latest finite 52-value response and repeats it through a
Throttle into the QT GUI Vector Sink. Continuous vectors let the display
refresh even after a short recording has finished producing frame PDUs.

Before running, set the three Parameter blocks at the top of the graph.
`recordings_dir` is the directory containing the three Moodle .bin files.
`csv_path` must name a file in an existing directory. Each run overwrites
that file, so use a different name for each recording.
`recording` selects 0 for channel 36, 1 for channel 6 or 2 for channel 100.
The defaults point to the local CDIG folder on the development PC.

Generate with F5 and execute with F6. The file plays once at processing
speed. The constellation and channel response update during playback.
After the input finishes, press Stop if the message-to-stream display
keeps the graph running. The CSV is closed and the final summary printed
when the graph stops. A flow-control warning is expected because the
finite recording runs as fast as the PC can process it.

The recording path is converted to a relative path before opening it,
avoiding the non-ASCII Windows profile path issue seen with File Source.
An ASCII cache path avoids the FFT cache issue.

## Validation

The GRC core validated and generated the flowgraph on GNU Radio 3.10.12
in Radioconda. The generated Qt flowgraph was run with the offscreen Qt
backend on all three recordings. Each CSV was reopened and its row count
checked against Frame Analyser and the known receiver baseline.

| Channel | Expected | Frame Analyser | CSV data rows |
| --- | ---: | ---: | ---: |
| 36 | 648 | 648 | 648 |
| 6 | 172 | 172 | 172 |
| 100 | 411 | 411 | 411 |

To repeat from the repository directory, use Radioconda Python to run
`experiments/frame_analyser/validate_grc_windows.py RECORDINGS OUTPUT`.
The utility generates Python into OUTPUT, processes Qt events, waits for
the input and a three-second quiet period, stops the graph, then checks
the CSV files. It has a 120-second timeout per recording. OUTPUT also
receives `validation.csv`. Keep the output and recordings outside Git.

The generated receiver was also run with a visible Qt window. The
constellation and channel-response curve were observed on channel 36.
The initial GRC run option was corrected so Execute starts processing.
Live Pluto/Wireshark comparison remains a follow-up check.
