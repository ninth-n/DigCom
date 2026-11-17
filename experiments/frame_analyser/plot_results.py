#!/usr/bin/env python3
"""Plots from Frame Analyser CSV logs. Usage: plot_results.py <results dir> <plots dir>"""
import csv, glob, os, re, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

res, out = sys.argv[1], sys.argv[2]
# Fixed categorical order (dataviz reference palette, light mode); marker shapes back up colour.
COLOR = {"BPSK 1/2": "#2a78d6", "QPSK 1/2": "#eb6834", "QPSK 3/4": "#1baf7a", "16-QAM 1/2": "#eda100"}
MARK = {"BPSK 1/2": "o", "QPSK 1/2": "s", "QPSK 3/4": "^", "16-QAM 1/2": "D"}
REC = [("Channel 36 (5180 MHz)", "rec_ch36.csv"), ("Channel 6 (2437 MHz)", "rec_ch6.csv"), ("Channel 100 (5500 MHz)", "rec_ch100.csv")]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 1,
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF,
                     "axes.facecolor": SURF, "legend.frameon": False})

def load(path):
    with open(path) as f:
        return list(csv.DictReader(f))

def save(fig, name):
    fig.tight_layout(); fig.savefig(os.path.join(out, name), dpi=150); plt.close(fig); print("wrote", name)

# 1. Recordings: SNR per encoding (median dot, 10-90% line).
fig, ax = plt.subplots(figsize=(8, 4))
encs = [e for e in COLOR if any(r["encoding"] == e for _, f in REC for r in load(os.path.join(res, f)))]
for i, (label, f) in enumerate(REC):
    rows = load(os.path.join(res, f))
    for j, e in enumerate(encs):
        s = np.array([float(r["snr_db"]) for r in rows if r["encoding"] == e])
        if len(s) < 5:
            continue
        x = i + (j - (len(encs) - 1) / 2) * 0.18
        ax.plot([x, x], np.percentile(s, [10, 90]), color=COLOR[e], lw=2, solid_capstyle="round")
        ax.plot(x, np.median(s), MARK[e], color=COLOR[e], ms=8, mec=SURF, mew=2,
                label=e if i == 0 or e == "QPSK 3/4" else None)
ax.set_xticks(range(len(REC)), [l for l, _ in REC]); ax.set_ylabel("SNR per frame (dB)")
ax.set_title("SNR by encoding in the course recordings (dot: median; line: 10th to 90th percentile)", fontsize=10, color=INK, loc="left")
h, l = ax.get_legend_handles_labels(); order = sorted(range(len(l)), key=lambda k: list(COLOR).index(l[k]))
ax.legend([h[k] for k in order], [l[k] for k in order], ncol=4, loc="upper right")
ax.text(0.0, -0.18, "Encodings with fewer than 5 frames in a recording are left out.", transform=ax.transAxes, fontsize=8, color=INK2)
save(fig, "recordings_snr_by_encoding.png")

# 2. Recordings: median channel magnitude per subcarrier.
fig, ax = plt.subplots(figsize=(8, 3.6))
sub = [k for k in range(-26, 27) if k != 0]  # 52 used subcarriers, DC excluded
for (label, f), c, m in zip(REC, ["#2a78d6", "#eb6834", "#1baf7a"], ["o", "s", "^"]):
    rows = load(os.path.join(res, f))
    h = np.array([[float(r[f"h{k}_db"]) for k in range(52)] for r in rows])
    med = np.median(h, axis=0); med -= med.max()
    ax.plot(sub, med, color=c, lw=2, marker=m, ms=4, markevery=6, label=label)
ax.set_xlabel("Subcarrier index"); ax.set_ylabel("Median |H| (dB, relative to peak)")
ax.set_title("Estimated channel response across subcarriers, course recordings", fontsize=10, color=INK, loc="left")
ax.legend(loc="lower center", ncol=3)
save(fig, "recordings_channel_response.png")

# 3. Live: frames and SNR against gain (two charts, one axis each).
live = {}
for p in glob.glob(os.path.join(res, "live_g*_r*.csv")):
    g, rep = map(int, re.findall(r"live_g(\d+)_r(\d+)", p)[0]); live[(g, rep)] = load(p)
if live:
    gains = sorted({g for g, _ in live})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.6))
    for rep, m in [(1, "o"), (2, "s")]:
        a1.plot([g for g in gains if (g, rep) in live], [len(live[(g, rep)]) for g in gains if (g, rep) in live],
                m, color="#2a78d6", ms=8, mec=SURF, mew=2, label=f"Run {rep}")
    a1.set_xlabel("RF gain (dB)"); a1.set_ylabel("Frames decoded in 15 s"); a1.set_title("Frames per run", fontsize=10, color=INK, loc="left"); a1.legend()
    for e in ["BPSK 1/2", "16-QAM 1/2"]:
        med = []
        for g in gains:
            s = [float(r["snr_db"]) for rep in (1, 2) for r in live.get((g, rep), []) if r["encoding"] == e]
            med.append(np.median(s) if len(s) >= 10 else np.nan)
        a2.plot(gains, med, "-" + MARK[e], color=COLOR[e], lw=2, ms=8, mec=SURF, mew=2, label=e)
    a2.set_xlabel("RF gain (dB)"); a2.set_ylabel("Median SNR per frame (dB)"); a2.set_title("SNR (both runs pooled)", fontsize=10, color=INK, loc="left"); a2.legend()
    fig.suptitle("Pluto on channel 100, 15 s per gain, two shuffled runs", fontsize=10, color=INK2, x=0.01, ha="left")
    save(fig, "live_gain_frames_and_snr.png")

# 4. Oscillator offset in ppm per recording (numbers, printed).
for label, f in REC:
    p = np.array([float(r["cfo_ppm"]) for r in load(os.path.join(res, f))])
    print(f"{label}: frequency offset median {np.median(p):.2f} ppm (10%: {np.percentile(p, 10):.2f}, 90%: {np.percentile(p, 90):.2f}), {len(p)} frames")
