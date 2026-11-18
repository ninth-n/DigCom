"""Run the Pluto receiver's digital chain against recorded complex float32 I/Q."""

import argparse
import csv
from collections import Counter
from pathlib import Path

import ieee802_11 as wifi
import numpy as np
import pmt
from gnuradio import blocks, fft, gr
from gnuradio.fft import window


class Messages(gr.basic_block):
    def __init__(self, name, handler):
        super().__init__(name=name, in_sig=None, out_sig=None)
        port = pmt.intern("in")
        self.message_port_register_in(port)
        self.handler = handler
        self.set_msg_handler(port, self.receive)

    def receive(self, message):
        self.handler(message)


class Encodings(gr.sync_block):
    def __init__(self):
        super().__init__(name="Encoding tags", in_sig=[(np.uint8, 48)], out_sig=None)
        self.frames = []
        self.total = 0

    def work(self, inputs, outputs):
        count = len(inputs[0])
        for tag in self.get_tags_in_window(0, 0, count, pmt.intern("encoding")):
            self.frames.append((tag.offset, pmt.to_uint64(tag.value)))
        self.total += count
        return count


class Detections(gr.sync_block):
    def __init__(self):
        super().__init__(name="Short detections", in_sig=[np.complex64], out_sig=None)
        self.total = 0

    def work(self, inputs, outputs):
        count = len(inputs[0])
        self.total += len(self.get_tags_in_window(0, 0, count, pmt.intern("wifi_start")))
        return count


def run(recording, frequency, threshold):
    graph = gr.top_block()
    src = blocks.file_source(gr.sizeof_gr_complex, str(recording), False)
    delay = blocks.delay(gr.sizeof_gr_complex, 16)
    conjugate = blocks.conjugate_cc()
    multiply = blocks.multiply_cc()
    corr = blocks.moving_average_cc(48, 1, 4000)
    mag = blocks.complex_to_mag()
    power = blocks.complex_to_mag_squared()
    power_sum = blocks.moving_average_ff(64, 1, 4000)
    ratio = blocks.divide_ff()
    short = wifi.sync_short(threshold, 2, False, False)
    long = wifi.sync_long(320, False, False)
    align = blocks.delay(gr.sizeof_gr_complex, 320)
    vector = blocks.stream_to_vector(gr.sizeof_gr_complex, 64)
    transform = fft.fft_vcc(64, True, window.rectangular(64), True, 1)
    equalizer = wifi.frame_equalizer(wifi.Equalizer(0), frequency, 20e6, False, False)
    decoder = wifi.decode_mac(False, False)
    starts = Detections()
    encoding = Encodings()
    valid = Counter()
    symbols = []

    def count_frame(msg):
        key = pmt.dict_ref(pmt.car(msg), pmt.intern("encoding"), pmt.PMT_NIL)
        valid[pmt.to_uint64(key)] += 1

    mac = Messages("Valid frames", count_frame)
    constellation = Messages(
        "Constellation points", lambda msg: symbols.append(pmt.c32vector_elements(pmt.cdr(msg)))
    )
    graph.connect(src, delay, conjugate, (multiply, 1))
    graph.connect(src, (multiply, 0))
    graph.connect(multiply, corr, mag, (ratio, 0))
    graph.connect(src, power, power_sum, (ratio, 1))
    graph.connect(delay, (short, 0))
    graph.connect(corr, (short, 1))
    graph.connect(ratio, (short, 2))
    graph.connect(short, starts)
    graph.connect(short, (long, 0))
    graph.connect(short, align, (long, 1))
    graph.connect(long, vector, transform, equalizer, decoder)
    graph.connect(equalizer, encoding)
    graph.msg_connect(decoder, "out", mac, "in")
    graph.msg_connect(equalizer, "symbols", constellation, "in")
    graph.run()
    if encoding.total != len(symbols):
        raise RuntimeError(f"Symbol stream and message counts differ: {encoding.total} vs {len(symbols)}")
    points = np.asarray(symbols, dtype=np.complex64).reshape(-1, 48)
    groups = [points[start:end] for (start, mcs), end in zip(
        encoding.frames, [offset for offset, _ in encoding.frames[1:]] + [len(points)]
    ) if mcs in (0, 1)]
    bpsk = np.concatenate(groups).ravel() if groups else np.empty(0, np.complex64)
    # Decision-directed distance: useful for comparing clusters, not reference-symbol EVM.
    error = np.minimum(abs(bpsk - 1), abs(bpsk + 1))
    rms = float(np.sqrt(np.mean(error ** 2))) if len(error) else None
    median = float(np.median(error)) if len(error) else None
    return [threshold, starts.total, sum(valid.values()), valid[0], len(bpsk), rms, median], bpsk


def plot(output, thresholds, recording):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(thresholds), figsize=(3 * len(thresholds), 3.6),
                             squeeze=False, layout="constrained")
    rng = np.random.default_rng(0)
    for ax, threshold in zip(axes[0], thresholds):
        points = np.load(output / f"bpsk_{threshold:g}.npy")
        if len(points):
            sample = rng.choice(points, min(len(points), 12000), replace=False)
            ax.scatter(sample.real, sample.imag, s=2, alpha=0.16)
        else:
            ax.text(0, 0.5, "No BPSK symbols", ha="center")
        ax.scatter([-1, 1], [0, 0], color="red", marker="+")
        ax.set(xlim=(-2, 2), ylim=(-2, 2), aspect="equal", xlabel="I",
               title=f"Threshold {threshold:g}")
        ax.grid(alpha=0.2)
    axes[0, 0].set_ylabel("Q")
    fig.suptitle("Equalized BPSK · up to 12,000 points per setting · fixed axes")
    fig.savefig(output / "constellations.png", dpi=150)
    plt.close(fig)

    # Reconstruct the detector metric for a short excerpt without saving the I/Q.
    with recording.open("rb") as file:
        iq = np.fromfile(file, dtype="<c8", count=1_000_000).astype(np.complex128)
    if len(iq) < 64:
        return
    corr = np.convolve(iq[16:] * iq[:-16].conj(), np.ones(48), mode="valid")
    power = np.convolve(abs(iq) ** 2, np.ones(64), mode="valid")
    metric = np.divide(abs(corr), power, out=np.zeros_like(power), where=power > 0)
    edges = np.flatnonzero(np.diff(np.r_[False, metric > 0.56, False]))
    if len(edges):
        index = edges[2 * np.argmax(edges[1::2] - edges[::2])]
    else:
        index = int(np.argmax(metric))
    start, end = max(0, index - 160), min(len(metric), index + 320)
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    ax.plot((np.arange(start, end) - index) / 20, metric[start:end], label="Detection metric")
    for threshold in sorted(set(thresholds)):
        ax.axhline(threshold, linestyle="--", linewidth=0.8, label=f"{threshold:g}")
    ax.set(xlabel="Time relative to selected crossing or peak (µs)",
           ylabel="Normalized autocorrelation", title="Example from first 50 ms")
    ax.legend(ncol=3)
    fig.savefig(output / "autocorrelation.png", dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", type=Path)
    parser.add_argument("--frequency", type=float, required=True, help="centre frequency in Hz")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--thresholds", nargs="+", type=float, default=[0.56, 0.20, 0.40, 0.70, 0.80])
    parser.add_argument("--plot", action="store_true", help="render constellations with Matplotlib")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "summary.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["threshold", "short_tags", "valid_frames", "valid_6mbps_frames",
                         "bpsk_points", "bpsk_rms_distance", "bpsk_median_distance"])
        for threshold in args.thresholds:
            row, points = run(args.recording, args.frequency, threshold)
            writer.writerow(row)
            file.flush()
            np.save(args.output / f"bpsk_{threshold:g}.npy", points)
            print(row, flush=True)
    if args.plot:
        plot(args.output, args.thresholds, args.recording)


if __name__ == "__main__":
    main()
