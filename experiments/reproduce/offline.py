"""Reproduce the offline counts, parameter sweeps and Pluto throughput model."""
import argparse
from collections import Counter
import csv
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "guide"))
from rx_chain import FS, RECORDINGS, run

THRESHOLDS = (0.2, 0.3, 0.4, 0.5, 0.56, 0.6, 0.7, 0.8, 0.9, 0.95)
WINDOWS = (8, 16, 24, 32, 48, 64, 96, 128, 192)
BUFFERS = (32768, 131072, 524288, 2097152)


def model(path, freq, baseline, scratch):
    samples = np.memmap(path, mode="r", dtype=np.complex64)
    try:
        for size in BUFFERS:
            period = round(size * FS / 6.5e6)
            for start in (0, period // 3, 2 * period // 3):
                with scratch.open("wb") as output:
                    for offset in range(start, len(samples), period):
                        samples[offset:offset + size].tofile(output)
                count = run(path=str(scratch), freq=freq)
                yield dict(buffer=size, start=start, frames=count,
                           reference_frames=baseline,
                           percent=100 * count / baseline if baseline else "")
    finally:
        del samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("baseline", "sweep", "pluto"))
    parser.add_argument("recordings", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--channel", choices=RECORDINGS)
    args = parser.parse_args()
    selected = (args.channel,) if args.channel else tuple(RECORDINGS)
    paths = {key: (args.recordings / RECORDINGS[key][0]).resolve() for key in selected}
    for path in paths.values():
        if not path.is_file():
            parser.error(f"Missing recording: {path}")
    encoding_names = [f"encoding_{i}" for i in range(8)] + ["unknown_encoding"]
    fields = {
        "baseline": ["frames", *encoding_names],
        "sweep": ["threshold", "window", "frames"],
        "pluto": ["buffer", "start", "frames", "reference_frames", "percent"],
    }
    with args.output.open("x", newline="", encoding="utf-8") as output, TemporaryDirectory() as tmp:
        writer = csv.DictWriter(output, ["recording", *fields[args.mode]])
        writer.writeheader()
        for key, path in paths.items():
            freq = RECORDINGS[key][1]
            if args.mode == "baseline":
                frames = run(path=str(path), freq=freq, return_meta=True)
                encodings = Counter(int(meta.get("encoding", -1)) for meta in frames)
                row = {f"encoding_{i}": encodings[i] for i in range(8)}
                row["unknown_encoding"] = len(frames) - sum(row.values())
                writer.writerow(dict(recording=key, frames=len(frames), **row))
            elif args.mode == "sweep":
                settings = dict.fromkeys([(t, 48) for t in THRESHOLDS] + [(0.56, w) for w in WINDOWS])
                for threshold, window in settings:
                    count = run(path=str(path), freq=freq, threshold=threshold, window=window)
                    writer.writerow(dict(recording=key, threshold=threshold, window=window, frames=count))
            else:
                baseline = run(path=str(path), freq=freq)
                for row in model(path, freq, baseline, Path(tmp) / "buffered.fc32"):
                    writer.writerow(dict(recording=key, **row))


if __name__ == "__main__":
    main()
