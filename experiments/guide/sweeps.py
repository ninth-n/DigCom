#!/usr/bin/env python3
"""Weekly-guide sweeps on the recordings. Writes results/<name>.csv. Usage: sweeps.py cfo|synclen|delay"""
import csv, os, subprocess, sys
from rx_chain import run

OUT = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(OUT, exist_ok=True)


def sweep(name, header, rows):
    with open(os.path.join(OUT, name + ".csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(header)
        for row in rows:
            w.writerow(row); f.flush(); print(*row, flush=True)


what = sys.argv[1]
if what == "cfo":  # weeks 2-3: added frequency offset, in kHz
    offsets = sorted(set(range(-900, 901, 100)) | {-650, -550, 550, 650})
    sweep("cfo", ["recording", "added_khz", "frames"],
          ([rec, k, run(rec, cfo_hz=k * 1e3)] for rec in ("ch100", "ch6") for k in offsets))
elif what == "synclen":  # week 3: Sync Long search length, delay kept equal
    # Each run in its own process with a time limit: above ~417 Sync Long can deadlock the flowgraph.
    def run_limited(rec, n):
        try:
            r = subprocess.run([sys.executable, "rx_chain.py", rec, f"sync_length={n}"], timeout=90,
                               capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
            return r.stdout.split()[-1]
        except subprocess.TimeoutExpired:
            return "stalled"
    sweep("synclen", ["recording", "sync_length", "frames"],
          ([rec, n, run_limited(rec, n)] for rec in ("ch100", "ch6")
           for n in (128, 192, 224, 240, 256, 272, 288, 320, 400, 416, 432, 480, 640)))
elif what == "tone":  # week 2: a narrowband tone at +9 MHz, outside the 52 used subcarriers (+-8.3 MHz)
    sweep("tone", ["recording", "tone_db_over_background", "frames"],
          ([rec, db, run(rec, tone_db=db)] for rec in ("ch100", "ch6") for db in (None, 0, 10, 20, 30, 40)))
elif what == "delay":  # week 3: delayed input not equal to sync_length (320)
    sweep("delay", ["recording", "delay", "frames"],
          ([rec, d, run(rec, delay=d)] for rec in ("ch100", "ch6")
           for d in (300, 312, 316, 318, 319, 320, 321, 322, 324, 328, 340)))
elif what == "sco":  # week 3/5: same offsets with the equalizer's sampling-clock correction off
    sweep("sco", ["recording", "added_khz", "frames_normal", "frames_no_clock_correction", "long_frames_normal", "long_frames_no_clock_correction"],
          ([rec, k, len(a), len(b), sum(m["frame bytes"] > 500 for m in a), sum(m["frame bytes"] > 500 for m in b)]
           for rec in ("ch100", "ch6") for k in (-500, -300, 0, 300, 500)
           for a, b in [(run(rec, cfo_hz=k * 1e3, return_meta=True), run(rec, cfo_hz=k * 1e3, eq_freq=1e18, return_meta=True))]))
