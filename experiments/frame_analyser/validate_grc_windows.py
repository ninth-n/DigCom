"""Validate and execute the recording GRC with Qt running offscreen."""

import argparse
import csv
import importlib.util
import os
from pathlib import Path
import sys
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("recordings", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("XDG_CACHE_HOME", "C:/tmp/cdig-grc-cache")
sys.path.insert(0, str(root / "blocks"))

from PyQt5 import Qt
from gnuradio import gr
from gnuradio.grc.core.platform import Platform

platform = Platform(version=gr.version(), install_prefix=gr.prefix())
platform.build_library(platform.config.block_paths + [str(root / "blocks")])
flow = platform.make_flow_graph(str(root / "wifi_rx_recording.grc"))
flow.rewrite()
flow.validate()
if not flow.is_valid():
    raise RuntimeError(list(flow.iter_error_messages()))
generator = platform.Generator(flow, str(output))
generator.write()
spec = importlib.util.spec_from_file_location("recording_flow", generator.file_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
app = Qt.QApplication([])
results = []
for index, channel, expected in [(0, 36, 648), (1, 6, 172), (2, 100, 411)]:
    csv_path = output / f"ch{channel}.csv"
    graph = module.wifi_rx_recording(index, str(args.recordings.resolve()), str(csv_path))
    graph.start()
    started = time.monotonic()
    last_count = -1
    changed = started
    total = Path(graph.recording_file).stat().st_size // 8
    while True:
        app.processEvents()
        count = graph.frame_analyser_0.count
        if count != last_count:
            changed = time.monotonic()
            last_count = count
        if graph.recording_source.nitems_written(0) >= total and time.monotonic() - changed > 3:
            break
        if time.monotonic() - started > 120:
            raise TimeoutError(f"Channel {channel} did not finish within 120 seconds")
        time.sleep(0.02)
    graph.stop()
    graph.wait()
    if not graph.frame_analyser_0.log_file.closed:
        graph.frame_analyser_0.stop()
    with csv_path.open(newline="") as file:
        rows = list(csv.DictReader(file))
    count = graph.frame_analyser_0.count
    print(f"Channel {channel}: analyser={count}, CSV={len(rows)}, expected={expected}", flush=True)
    results.append([channel, expected, count, len(rows)])
    graph.close()
    if count != expected or len(rows) != expected:
        raise AssertionError(f"Channel {channel} count mismatch")
with (output / "validation.csv").open("w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["channel", "expected", "analyser", "csv_rows"])
    writer.writerows(results)
