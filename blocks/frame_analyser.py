"""Frame Analyser: per-frame statistics for the gr-ieee802-11 receiver.

Connect Decode MAC's "out" message port to this block's "frames" input.
For every decoded frame it reads the metadata the receiver attaches
(encoding, length, SNR, frequency offset, channel response). It never
reads the frame bytes, so no addresses or payloads are logged.
"""
import csv
import time

import numpy as np
import pmt
from gnuradio import gr

# Encoding numbers used by gr-ieee802-11 (include/ieee802_11/mapper.h).
ENCODINGS = {
    0: ("BPSK 1/2", 6), 1: ("BPSK 3/4", 9), 2: ("QPSK 1/2", 12), 3: ("QPSK 3/4", 18),
    4: ("16-QAM 1/2", 24), 5: ("16-QAM 3/4", 36), 6: ("64-QAM 2/3", 48), 7: ("64-QAM 3/4", 54),
}


class frame_analyser(gr.basic_block):
    def __init__(self, log_path="", report_every=100):
        gr.basic_block.__init__(self, name="Frame Analyser", in_sig=None, out_sig=None)
        self.report_every = int(report_every)
        self.snr_by_encoding = {}  # encoding number -> list of SNRs (dB)
        self.count = 0
        self.start_time = time.time()
        self.log = None
        if log_path:
            self.log_file = open(log_path, "w", newline="")
            self.log = csv.writer(self.log_file)
            self.log.writerow(["time_s", "frame", "encoding", "rate_mbps", "bytes", "snr_db",
                               "cfo_hz", "cfo_ppm"] + [f"h{k}_db" for k in range(52)])
        self.message_port_register_in(pmt.intern("frames"))
        self.set_msg_handler(pmt.intern("frames"), self.handle_frame)
        self.message_port_register_out(pmt.intern("channel"))

    def handle_frame(self, msg):
        meta = pmt.to_python(pmt.car(msg))  # metadata only; pmt.cdr(msg) holds the frame bytes
        enc = int(meta.get("encoding", -1))
        snr = float(meta.get("snr", np.nan))
        cfo = float(meta.get("frequency offset", np.nan))
        carrier = float(meta.get("nominal frequency", np.nan))
        csi = np.asarray(meta.get("csi", np.zeros(52)), dtype=np.complex64)
        h_db = 20 * np.log10(np.abs(csi) + 1e-12)  # channel magnitude per subcarrier, dB

        self.count += 1
        self.snr_by_encoding.setdefault(enc, []).append(snr)
        if self.log:
            name, rate = ENCODINGS.get(enc, ("unknown", 0))
            self.log.writerow([f"{time.time() - self.start_time:.3f}", self.count, name, rate,
                               int(meta.get("frame bytes", 0)), f"{snr:.2f}", f"{cfo:.0f}",
                               f"{cfo / carrier * 1e6:.2f}"] + [f"{v:.2f}" for v in h_db])

        # Send the channel response out so a vector sink can plot it live.
        self.message_port_pub(pmt.intern("channel"),
                              pmt.cons(pmt.PMT_NIL, pmt.init_f32vector(len(h_db), h_db.tolist())))
        if self.report_every and self.count % self.report_every == 0:
            print(self.summary(), flush=True)

    def summary(self):
        lines = [f"Frame Analyser: {self.count} frames in {time.time() - self.start_time:.0f} s"]
        for enc in sorted(self.snr_by_encoding):
            s = np.array(self.snr_by_encoding[enc])
            name = ENCODINGS.get(enc, ("unknown", 0))[0]
            lines.append(f"  {name:10s} {len(s):5d} frames  SNR median {np.nanmedian(s):5.1f} dB"
                         f"  (10% {np.nanpercentile(s, 10):5.1f}, 90% {np.nanpercentile(s, 90):5.1f})")
        return "\n".join(lines)

    def stop(self):
        print(self.summary(), flush=True)
        if self.log:
            self.log_file.close()
        return True
