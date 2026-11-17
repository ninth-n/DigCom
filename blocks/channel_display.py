"""Repeat the latest channel PDU as vectors for a continuously updating Qt sink."""

import threading

import numpy as np
import pmt
from gnuradio import gr


class channel_display(gr.sync_block):
    def __init__(self):
        super().__init__(name="Channel display source", in_sig=None,
                         out_sig=[(np.float32, 52)])
        self.latest = np.zeros(52, dtype=np.float32)
        self.lock = threading.Lock()
        self.message_port_register_in(pmt.intern("channel"))
        self.set_msg_handler(pmt.intern("channel"), self.receive)

    def receive(self, message):
        values = np.asarray(pmt.f32vector_elements(pmt.cdr(message)), dtype=np.float32)
        if values.shape == (52,) and np.all(np.isfinite(values)):
            with self.lock:
                self.latest = values

    def work(self, inputs, outputs):
        with self.lock:
            outputs[0][:] = self.latest
        return len(outputs[0])
