# Detection threshold: offline results

The three course recordings were replayed at 20 MS/s with window 48,
minimum plateau setting 2 and LS equalization on GNU Radio 3.10.12
(Windows/Radioconda). At 0.56 the CRC-valid counts were 648, 172 and
411 for channels 36, 6 and 100 respectively. All 15 CRC-valid counts
matched the published Wiki sweep.

| Threshold | Channel 36 | Channel 6 | Channel 100 |
| ---: | ---: | ---: | ---: |
| 0.20 | 60 | 21 | 29 |
| 0.40 | 638 | 166 | 411 |
| 0.56 | 648 | 172 | 411 |
| 0.70 | 642 | 132 | 405 |
| 0.80 | 0 | 0 | 0 |

## Channel 36

| Threshold | Sync Short tags | CRC-valid frames | Median BPSK distance to ±1 |
| ---: | ---: | ---: | ---: |
| 0.20 | 262,168 | 60 | 1.052 |
| 0.40 | 5,722 | 638 | 0.519 |
| 0.56 | 4,361 | 648 | 0.238 |
| 0.70 | 3,418 | 642 | 0.207 |
| 0.80 | 0 | 0 | — |

At 0.20 there are many more candidate starts, but far fewer valid frames.
This does not identify which synchronization or decoding step failed.
At 0.70 the BPSK output is closer to the ideal points by the median
distance, but six fewer frames pass CRC than at 0.56. The point sets
can come from different frames and include candidates with an invalid
MAC CRC, so this is a comparison of output populations, not a paired
measurement of improvements on individual frames.

At 0.80 Sync Short emitted no start tags on any of the three recordings.
On channel 100 the illustrated autocorrelation excerpt plateaus near 0.75
but briefly exceeds it, so 48/64 is a useful approximation for a steady
periodic preamble, not a strict ceiling. The plotted excerpt does not
establish the maximum over the entire recording.

For a demonstration, use the channel 36 recording and show the
constellation and valid-frame count at 0.56. Switch to 0.80 to show the
detector stop emitting tags, then to 0.20 to show why more candidate
detections do not translate into more valid frames.
