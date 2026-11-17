#!/usr/bin/env python3
"""Frame Analyser extension 4: channel impulse response against the 0.8 us cyclic prefix.

For every decoded frame in the three recordings, take the receiver's channel estimate (52 complex
values, one per used subcarrier), put it back on the 64 FFT bins (DC and the 11 guard bins stay 0),
and inverse-FFT it: that is the channel's impulse response, sampled every 50 ns (20 Msps).
Then measure how much of its energy arrives later than 16 samples (0.8 us, the cyclic prefix)
after the strongest tap. Energy beyond the cyclic prefix causes interference between symbols.
Usage: impulse_response.py -> prints a table; plots/impulse_response.png
"""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "guide"))
from rx_chain import run

# csi order (lib/equalizer/base.cc get_csi): FFT bins 6..58 without 32, i.e. subcarriers -26..-1, 1..26
BINS = np.array([k for k in range(6, 59) if k != 32])


def impulse_response(csi):
    H = np.zeros(64, complex)
    H[BINS] = csi
    h = np.fft.ifft(np.fft.ifftshift(H))  # bin 32 is DC (fft_vcc shift=True), so undo the shift
    p = np.abs(h) ** 2
    return np.roll(p, -np.argmax(p)) / p.sum()  # strongest tap first, total energy 1


rows, profiles = [], {}
for rec in ("ch36", "ch6", "ch100"):
    P = np.array([impulse_response(np.asarray(m["csi"])) for m in run(rec, return_meta=True)])
    profiles[rec] = np.median(P, axis=0)
    # taps 0..15 after the peak are inside the cyclic prefix; taps 48..63 are *before* the peak
    # (circular), which is where timing error and the window's leakage land.
    late = P[:, 16:48].sum(axis=1)
    tau = np.arange(64); tau[tau >= 48] -= 64  # tap delay in samples relative to the peak
    rms = np.sqrt((P * tau ** 2).sum(1) - (P * tau).sum(1) ** 2) * 50  # ns
    rows.append((rec, len(P), np.median(late) * 100, np.percentile(late, 90) * 100, np.median(rms)))

print("recording  frames  energy later than 0.8us: median   90th pct   RMS delay spread (median)")
for rec, n, med, p90, rms in rows:
    print(f"{rec:9s}  {n:6d}  {med:30.2f}%  {p90:8.2f}%   {rms:6.0f} ns")

# Baselines, measured the same way: the 12 zeroed bins (DC, guards) leak energy into every tap,
# so even a perfect channel doesn't read 0%. A second path beyond the cyclic prefix reads ~20%.
k = np.r_[-26:0, 1:27]
tau = np.arange(64); tau[tau >= 48] -= 64
for label, H in (("flat channel (ideal)", np.ones(52)),
                 ("2 paths, 2nd 0.5 us later, -6 dB", 1 + 0.5 * np.exp(-2j * np.pi * k * 0.5e-6 * 312.5e3)),
                 ("2 paths, 2nd 1.0 us later, -6 dB", 1 + 0.5 * np.exp(-2j * np.pi * k * 1.0e-6 * 312.5e3))):
    P = impulse_response(H)
    rms = np.sqrt((P * tau ** 2).sum() - (P * tau).sum() ** 2) * 50
    print(f"baseline: {label:34s} late {P[16:48].sum() * 100:5.2f}%   RMS {rms:4.0f} ns")

os.makedirs(os.path.join(os.path.dirname(__file__), "plots"), exist_ok=True)
fig, ax = plt.subplots(figsize=(8, 3.4), facecolor="#fcfcfb")
ax.set_facecolor("#fcfcfb")
tau_us = (np.arange(-8, 40)) * 0.05
for (rec, col) in zip(("ch36", "ch6", "ch100"), ("#2a78d6", "#eb6834", "#1baf7a")):
    prof = np.roll(profiles[rec], 8)[:48]
    ax.plot(tau_us, 10 * np.log10(prof), color=col, lw=1.8, label=rec.replace("ch", "channel "))
ax.axvspan(0, 0.8, color="#e4e3dd", alpha=0.6, lw=0)
ax.text(0.4, 1.5, "cyclic prefix (0.8 µs)", ha="center", color="#6b6a64", fontsize=9)
ax.set_ylim(-40, 4)
ax.set_xlabel("delay after the strongest path (µs)")
ax.set_ylabel("median power (dB of total)")
ax.grid(color="#e4e3dd"); ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, loc="upper right")
fig.tight_layout()
fig.savefig(os.path.join(os.path.dirname(__file__), "plots", "impulse_response.png"), dpi=150)
