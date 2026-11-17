#!/usr/bin/env python3
"""Run the receiver chain with the Frame Analyser, headless, from a recording or the Pluto.
Usage: run_chain.py file <recording fc32> <freq Hz> <csv>
       run_chain.py pluto <seconds> <freq Hz> <gain dB> <csv>
"""
import os, sys, time
from gnuradio import blocks, fft, gr
from gnuradio.fft import window
import ieee802_11
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "blocks"))
from frame_analyser import frame_analyser  # blocks/frame_analyser.py

mode = sys.argv[1]
tb = gr.top_block()
if mode == "file":
    path, freq, csv_path = sys.argv[2], float(sys.argv[3]), sys.argv[4]
    src = blocks.file_source(gr.sizeof_gr_complex, path, False)
else:
    from gnuradio import iio
    seconds, freq, gain, csv_path = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
    src = iio.fmcomms2_source_fc32("ip:pluto.local", [True, True], 524288)
    src.set_len_tag_key("packet_len"); src.set_frequency(int(freq)); src.set_samplerate(int(20e6))
    src.set_gain_mode(0, "manual"); src.set_gain(0, gain); src.set_quadrature(True)
    src.set_rfdc(True); src.set_bbdc(True); src.set_filter_params("Auto", "", 0, 0)

# Same chain as wifi_rx_pluto.grc: threshold 0.56, window 48, LS equalizer.
d16 = blocks.delay(gr.sizeof_gr_complex, 16); conj = blocks.conjugate_cc(); mult = blocks.multiply_vcc(1)
avg_c = blocks.moving_average_cc(48, 1, 4000, 1); mag = blocks.complex_to_mag(1)
pwr = blocks.complex_to_mag_squared(1); avg_p = blocks.moving_average_ff(64, 1, 4000, 1); div = blocks.divide_ff(1)
short = ieee802_11.sync_short(0.56, 2, False, False); dlong = blocks.delay(gr.sizeof_gr_complex, 320)
long_ = ieee802_11.sync_long(320, False, False); s2v = blocks.stream_to_vector(gr.sizeof_gr_complex, 64)
fft64 = fft.fft_vcc(64, True, window.rectangular(64), True, 1)
eq = ieee802_11.frame_equalizer(ieee802_11.Equalizer(0), freq, 20e6, False, False)
dec = ieee802_11.decode_mac(False, False)
fa = frame_analyser(csv_path, 0)
tb.connect(src, d16, conj); tb.connect(src, (mult, 0)); tb.connect(conj, (mult, 1)); tb.connect(mult, avg_c, mag, (div, 0))
tb.connect(src, pwr, avg_p, (div, 1)); tb.connect(d16, (short, 0)); tb.connect(avg_c, (short, 1)); tb.connect(div, (short, 2))
tb.connect(short, (long_, 0)); tb.connect(short, dlong, (long_, 1)); tb.connect(long_, s2v, fft64, eq, dec)
tb.msg_connect((dec, "out"), (fa, "frames"))
tb.start()
if mode == "file":
    total = os.path.getsize(path) // gr.sizeof_gr_complex
    while src.nitems_written(0) < total:
        time.sleep(0.5)
    time.sleep(3)
else:
    time.sleep(seconds)
tb.stop(); tb.wait()
