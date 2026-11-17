#!/usr/bin/env python3
"""Headless gr-ieee802-11 receiver (same chain as wifi_rx_pluto.grc) for the weekly-guide experiments.

run() returns how many frames passed the checksum. Options change one thing at a time:
  cfo_hz       add a frequency offset to the recording (tests the offset correction)
  threshold    Sync Short threshold (default 0.56)
  window       autocorrelation window Nwin (default 48)
  sync_length  OFDM Sync Long search length (default 320)
  delay        delay on Sync Long's second input (default = sync_length, as in wifi_rx.grc)
  path         a recording, or any fc32 file (e.g. a synthetic one)
  eq_freq      carrier frequency told to the equalizer (default: the real one)
  tone_db      add a constant tone this many dB above the recording's background (at tone_hz)
"""
import math, os, sys, time
from gnuradio import analog, blocks, fft, gr
from gnuradio.fft import window as fft_window
import numpy as np
import pmt
import ieee802_11

RECORDINGS = {  # name -> (file, centre frequency in Hz)
    "ch36": ("Sample1_20MHz_Channel36.bin", 5180e6),
    "ch6": ("Sample2_20MHz_Channel6.bin", 2437e6),
    "ch100": ("Sample3_20MHz_Channel100.bin", 5500e6),
}
# The course recordings are too big for the repository: put them in recordings/ at the top of the
# repository (ignored by Git), or point CDIG_RECORDINGS at their folder.
REC_DIR = os.environ.get("CDIG_RECORDINGS",
                         os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "recordings"))
FS = 20e6


class array_source(gr.sync_block):
    """Plays a file (memory-mapped), then zeros forever, so the flowgraph doesn't stop at the end
    of the file before the last frames reach the counter (a plain file source ends the flowgraph
    at EOF and frames still in the message queue are lost)."""
    def __init__(self, path):
        gr.sync_block.__init__(self, name="array_source", in_sig=None, out_sig=[np.complex64])
        self.x = np.memmap(path, dtype=np.complex64, mode="r")
        self.pos = 0

    def work(self, input_items, output_items):
        out = output_items[0]
        n = max(0, min(len(out), len(self.x) - self.pos))
        out[:n] = self.x[self.pos:self.pos + n]
        out[n:] = 0
        self.pos += len(out)
        return len(out)


class counter(gr.basic_block):
    """Counts Decode MAC messages and keeps their metadata (never the frame bytes)."""
    def __init__(self):
        gr.basic_block.__init__(self, name="counter", in_sig=None, out_sig=None)
        self.meta = []
        self.message_port_register_in(pmt.intern("in"))
        self.set_msg_handler(pmt.intern("in"), self.handle)

    def handle(self, msg):
        self.meta.append(pmt.to_python(pmt.car(msg)))


def run(rec="ch100", path=None, freq=None, cfo_hz=0.0, threshold=0.56, window=48,
        sync_length=320, delay=None, eq_freq=None, tone_db=None, tone_hz=9e6, return_meta=False):
    if path is None:
        name, freq = RECORDINGS[rec]
        path = os.path.join(REC_DIR, name)
    delay = sync_length if delay is None else delay
    tb = gr.top_block()
    src = array_source(path)
    # rotator multiplies sample n by exp(j*2*pi*cfo/fs*n): a frequency shift of cfo_hz
    rot = blocks.rotator_cc(2 * math.pi * cfo_hz / FS)
    d16 = blocks.delay(gr.sizeof_gr_complex, 16)
    conj = blocks.conjugate_cc()
    mult = blocks.multiply_vcc(1)
    avg_c = blocks.moving_average_cc(window, 1, 4000, 1)
    mag = blocks.complex_to_mag(1)
    pwr = blocks.complex_to_mag_squared(1)
    avg_p = blocks.moving_average_ff(window + 16, 1, 4000, 1)
    div = blocks.divide_ff(1)
    short = ieee802_11.sync_short(threshold, 2, False, False)
    dlong = blocks.delay(gr.sizeof_gr_complex, delay)
    long_ = ieee802_11.sync_long(sync_length, False, False)
    s2v = blocks.stream_to_vector(gr.sizeof_gr_complex, 64)
    fft64 = fft.fft_vcc(64, True, fft_window.rectangular(64), True, 1)
    # eq_freq: carrier frequency given to the equalizer. It uses it only to turn the frequency offset
    # into a sampling-clock offset (epsilon = offset / carrier); a huge value switches that off.
    eq = ieee802_11.frame_equalizer(ieee802_11.Equalizer(0), eq_freq or freq, FS, False, False)
    dec = ieee802_11.decode_mac(False, False)
    cnt = counter()

    if tone_db is None:
        tb.connect(src, rot)
    else:
        # background power: median of |x|^2 over the first 2 M samples (mostly no frames)
        bg = float(np.median(np.abs(np.asarray(src.x[:2_000_000])) ** 2))
        tone = analog.sig_source_c(FS, analog.GR_COS_WAVE, tone_hz, math.sqrt(bg * 10 ** (tone_db / 10)))
        add = blocks.add_cc()
        tb.connect(src, (add, 0)); tb.connect(tone, (add, 1)); tb.connect(add, rot)
    tb.connect(rot, d16, conj)
    tb.connect(rot, (mult, 0)); tb.connect(conj, (mult, 1))
    tb.connect(mult, avg_c, mag, (div, 0))
    tb.connect(rot, pwr, avg_p, (div, 1))
    tb.connect(d16, (short, 0)); tb.connect(avg_c, (short, 1)); tb.connect(div, (short, 2))
    tb.connect(short, (long_, 0)); tb.connect(short, dlong, (long_, 1))
    tb.connect(long_, s2v, fft64, eq, dec)
    tb.msg_connect((dec, "out"), (cnt, "in"))

    tb.start()
    while src.pos < len(src.x) + 200000:  # the file, then 10 ms of zeros to flush the chain
        time.sleep(0.05)
    time.sleep(0.5)  # let the last messages reach the counter
    tb.stop(); tb.wait()
    return cnt.meta if return_meta else len(cnt.meta)


if __name__ == "__main__":
    # rx_chain.py <recording> [name=value ...], e.g. rx_chain.py ch100 sync_length=480
    kw = {k: float(v) if "." in v or "e" in v else int(v) for k, v in (a.split("=") for a in sys.argv[2:])}
    print(run(sys.argv[1] if len(sys.argv) > 1 else "ch100", **kw))
