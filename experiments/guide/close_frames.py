#!/usr/bin/env python3
"""Weeks 2-3: two frames close together.

The article says a frame arriving shortly after another is missed (e.g. CTS after RTS). We take two
real 802.11a frames from the channel 100 recording, put frame 2 `gap` samples after the end of
frame 1 (background noise in between), and see which ones decode, for three Sync Long lengths
(the delay on Sync Long's second input always equals sync_length, as in wifi_rx.grc).

Frame 1: 14 bytes, 16-QAM 1/2, sent 14 us after an 802.11n frame in the recording.
Frame 2: 23 bytes, 16-QAM 1/2, followed in the recording by an 802.11n frame.
Usage: close_frames.py -> results/close_frames.csv
"""
import csv, os, tempfile
import numpy as np
from rx_chain import run, REC_DIR

X = np.memmap(os.path.join(REC_DIR, "Sample3_20MHz_Channel100.bin"), dtype=np.complex64, mode="r")
NOISE = np.asarray(X[18432683:18434683])  # 2000 samples of background just before frame 1's burst


def cut(search_from, search_to, noise_from):
    """The first burst of signal in [search_from, search_to) at least 300 samples long: where the
    power, averaged over 20 samples, is more than 10 dB above the background measured over the
    2000 samples from noise_from.
    Keeps 10 samples before and 30 after."""
    x = np.asarray(X[search_from:search_to])
    m = np.convolve(np.abs(x) ** 2, np.ones(20) / 20, "valid")
    on = np.concatenate([[0], (m > np.mean(np.abs(np.asarray(X[noise_from:noise_from + 2000])) ** 2) * 10).astype(int), [0]])
    starts, ends = np.flatnonzero(np.diff(on) == 1), np.flatnonzero(np.diff(on) == -1)
    start, end = next((s, e) for s, e in zip(starts, ends) if e - s >= 300)
    return x[max(start - 10, 0):end + 30]


def noise(n):
    return np.tile(NOISE, n // len(NOISE) + 1)[:n]


F1 = cut(18436600, 18438000, 18432683)  # the decodable frame at the end of the first burst
F2 = cut(18991400, 18992700, 18989000)  # the decodable frame at the start of the second burst
print(f"frame 1: {len(F1)} samples, frame 2: {len(F2)} samples")

rows = []
with tempfile.TemporaryDirectory() as d:
    f = os.path.join(d, "pair.bin")

    def decode(parts, sync_length=320):
        np.concatenate([noise(4000)] + parts + [noise(4000)]).astype(np.complex64).tofile(f)
        meta = run(path=f, freq=5500e6, sync_length=sync_length, return_meta=True)
        return [int(m["frame bytes"]) for m in meta]

    print("frame 1 alone:", decode([F1]), " frame 2 alone:", decode([F2]))
    for sync_length in (240, 320, 400):
        for gap in range(0, 481, 40):
            got = decode([F1, noise(gap), F2], sync_length)
            row = (sync_length, gap, gap / 20, 14 in got, 23 in got)
            rows.append(row); print(*row, flush=True)

os.makedirs("results", exist_ok=True)
with open("results/close_frames.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["sync_length", "gap_samples", "gap_us", "frame1_decoded", "frame2_decoded"])
    w.writerows(rows)
