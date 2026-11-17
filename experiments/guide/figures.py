#!/usr/bin/env python3
"""Week 1 (Figure 2 of the article, varying Nwin) and week 4 (Figure 3, the Sync Long matched filter),
on one real frame from the channel 100 recording (the 23-byte 16-QAM frame used in close_frames.py).
Computed in numpy exactly as the flowgraph does. Writes plots/fig2_nwin.png, plots/fig3_matched_filter.png
and prints the numbers quoted on the wiki.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from rx_chain import REC_DIR

X = np.memmap(os.path.join(REC_DIR, "Sample3_20MHz_Channel100.bin"), dtype=np.complex64, mode="r")
START = 18991601            # first sample of the frame's signal (found by power, see close_frames.py)
x = np.asarray(X[START - 200:START + 900])  # 200 samples of background, then the frame
L = np.array([0, 0, 0, 0, 0, 0, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1, 1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1,
              -1, 1, 1, 1, 1, 0, 1, -1, -1, 1, 1, -1, 1, -1, 1, -1, -1, -1, -1, -1, 1, 1, -1, -1, 1,
              -1, 1, -1, 1, 1, 1, 1, 0, 0, 0, 0, 0], complex)  # equalizer/base.cc, index 32 = DC
lt = np.fft.ifft(np.fft.ifftshift(L))     # the 64 time-domain samples of one long training symbol
mf = np.abs(np.correlate(x, lt, "valid"))  # sum_k x[n+k] conj(lt[k]), equation 6
# Align time so the first long symbol (after 160 short samples and a 32-sample guard) starts at 192.
first_peak = min(np.argsort(mf)[::-1][:2])
t = np.arange(len(x)) - (first_peak - 192)  # sample index relative to the frame start
print("frame start found", first_peak - 192 - 200, "samples after the power-based estimate")

INK, MUTED, GRID, SURFACE = "#1f1f1e", "#6b6a64", "#e4e3dd", "#fcfcfb"
BLUES = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]  # ordinal ramp: light = small Nwin
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "figure.facecolor": SURFACE,
                     "axes.facecolor": SURFACE, "axes.grid": True, "grid.color": GRID,
                     "axes.spines.top": False, "axes.spines.right": False})


def coefficient(x, nwin):
    """c[n] as in the flowgraph: |moving sum over Nwin of x[n] conj(x[n-16])| divided by the
    moving sum over Nwin+16 of |x[n]|^2 (both causal, ending at sample n)."""
    prod = np.zeros(len(x), complex)
    prod[16:] = x[16:] * np.conj(x[:-16])
    a = np.convolve(prod, np.ones(nwin))[:len(x)]
    p = np.convolve(np.abs(x) ** 2, np.ones(nwin + 16))[:len(x)]
    return np.abs(a) / p


# ---- Figure 2 with different Nwin ----
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.axhline(0.56, color=MUTED, lw=1, ls="--")
ax.text(880, 0.575, "threshold 0.56", color=MUTED, ha="right", va="bottom")
for nwin, col in zip((16, 32, 48, 96), BLUES):
    c = coefficient(x, nwin)
    lw = 2.4 if nwin == 48 else 1.6
    ax.plot(t, c, color=col, lw=lw, label=f"Nwin = {nwin}" + (" (default)" if nwin == 48 else ""))
    plateau = c[(t >= 100) & (t < 160)].mean()
    above = np.flatnonzero(c > 0.56)
    print(f"Nwin {nwin:3d}: plateau mean {plateau:.3f}, theory Nwin/(Nwin+16) = {nwin / (nwin + 16):.3f}, "
          f"first crossing of 0.56 at {t[above[0]] if len(above) else None}, "
          f"samples above 0.56 in the first 250: {int(np.sum(c[(t >= 0) & (t < 250)] > 0.56))}")
ax.axvspan(0, 160, color=GRID, alpha=0.5, lw=0)
ax.text(80, 1.02, "short training sequence (160 samples)", ha="center", color=MUTED, fontsize=9)
ax.set_xlim(-150, 900); ax.set_ylim(0, 1.08)
ax.set_xlabel("samples from the start of the frame (20 Msps: 20 samples = 1 µs)")
ax.set_ylabel("autocorrelation coefficient c[n]")
ax.legend(loc="upper right", frameon=False, bbox_to_anchor=(1, 0.92))
fig.tight_layout(); os.makedirs("plots", exist_ok=True); fig.savefig("plots/fig2_nwin.png", dpi=150)

# ---- Figure 3: matched filter with the long training symbol ----
tm = t[:len(mf)]
top = np.argsort(mf)[::-1][:3]
print("matched filter: top 3 peaks at", sorted(int(tm[i]) for i in top),
      "| peak / median outside peaks:", round(float(mf[top[0]] / np.median(mf)), 1))
n_p = max(int(tm[i]) for i in top[:2]) + 64
print("n_P = max(N_P) + 64 =", n_p, "(start of the signal field, incl. its cyclic prefix)")

fig, ax = plt.subplots(figsize=(8, 3.2))
ax.plot(tm, mf / mf.max(), color="#2a78d6", lw=1.6)
p1, p2 = sorted(top[:2])
ax.annotate(f"peak at {int(tm[p1])}", (tm[p1], mf[p1] / mf.max()), xytext=(-6, -2),
            textcoords="offset points", color=INK, fontsize=9, ha="right", va="top")
ax.annotate(f"peak at {int(tm[p2])}", (tm[p2], mf[p2] / mf.max()), xytext=(6, -2),
            textcoords="offset points", color=INK, fontsize=9, ha="left", va="top")
ax.axvline(n_p, color=MUTED, lw=1, ls="--")
ax.text(n_p + 6, 0.62, "n_P = last peak + 64\n(signal field starts)", color=MUTED, fontsize=9)
ax.axvspan(160, 320, color=GRID, alpha=0.5, lw=0)
ax.text(240, 1.04, "long training sequence (160 samples)", ha="center", color=MUTED, fontsize=9)
ax.set_xlim(-150, 600); ax.set_ylim(0, 1.1)
ax.set_xlabel("samples from the start of the frame")
ax.set_ylabel("matched filter output (normalised)")
fig.tight_layout(); fig.savefig("plots/fig3_matched_filter.png", dpi=150)
