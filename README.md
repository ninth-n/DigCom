# DigCom

Master's 1st year - Digital Communications

An IEEE 802.11a receiver on the ADALM-Pluto SDR, using GNU Radio. Project documentation is in the [Wiki](https://github.com/ninth-n/DigCom/wiki).

**Status: the receiver here is an interim choice, not a final decision.** We use `gr-ieee802-11` temporarily while we confirm with the lecturers whether a receiver will be provided or which one we should use. We will later decide whether to keep it permanently or replace it. Everything in this repository related to it may change or be removed.

## Contents

| Path | What it is |
| --- | --- |
| `Spectrum Analyzer.grc` | Spectrum analyzer flowgraph for the Pluto, built following the course tutorial |
| `wifi_rx_pluto.grc` | Interim Wi-Fi receiver for the Pluto, adapted from `examples/wifi_rx.grc` of `gr-ieee802-11` |
| `captures/wifi-rx-pluto-2026-11-03.pcapng` | Frames we captured with the interim receiver through Wireshark; see the Wiki |
| `deps/gr-ieee802-11` | Third-party 802.11 receiver blocks used by the interim receiver (submodule, not our work) |
| `deps/gr-foo` | Third-party helper blocks for the interim receiver, including the Wireshark connector (submodule, not our work) |

## Setup

Install the dependencies. On Debian 13:

```bash
sudo apt install gnuradio-dev cmake g++ git pkg-config pybind11-dev python3-pybind11 \
  liblog4cpp5-dev libspdlog-dev libfmt-dev libgmp-dev libmpfr-dev libboost-all-dev \
  libfftw3-dev libsndfile1-dev libvolk-dev libiio-dev libiio-utils libad9361-dev wireshark
```

Then clone and build:

```bash
git clone --recurse-submodules https://github.com/ninth-n/DigCom
cd DigCom
for m in deps/gr-foo deps/gr-ieee802-11; do
  cmake -S $m -B $m/build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build $m/build -j"$(nproc)" \
    && sudo cmake --install $m/build \
    && sudo ldconfig \
    || break
done
```

Tested with GNU Radio 3.10.12 on Debian 13. Open `wifi_rx_pluto.grc` in GNU Radio Companion with the Pluto connected. Decoded frames are printed to the console and saved to `/tmp/wifi.pcap`, which each run overwrites and which can be opened in Wireshark.

To watch frames in Wireshark in real time, replace the file with a named pipe and start Wireshark before the flowgraph (the flowgraph waits for it). Your user must be in the `wireshark` group:

```bash
rm -f /tmp/wifi.pcap && mkfifo /tmp/wifi.pcap
wireshark -k -i /tmp/wifi.pcap
```

The Pluto sustains about 6.5 Msps over USB, less than the 20 Msps Wi-Fi needs, so the console shows overflows (`O`) and some frames are lost.

## Credits and licence

The interim receiver is the work of Bastian Bloessl and contributors: [gr-ieee802-11](https://github.com/bastibl/gr-ieee802-11) and [gr-foo](https://github.com/bastibl/gr-foo), described in:

> B. Bloessl, M. Segata, C. Sommer and F. Dressler, "An IEEE 802.11a/g/p OFDM Receiver for GNU Radio", SRIF '13. https://doi.org/10.1145/2491246.2491248

Both are licensed under the GNU GPL v3 and are included here unmodified, as submodules with their own licence files. `wifi_rx_pluto.grc` is derived from `wifi_rx.grc` and is also licensed under the GPL v3 (`LICENSES/GPL-3.0.txt`). Changes made on 2026-11-03: replaced the USRP source with a PlutoSDR source, removed `lo_offset`, changed the sample rate, frequency and gain defaults, and enabled the Wireshark output with append mode turned off.

`wifi_rx_pluto.grc` was generated with AI assistance (Claude Code). See the Wiki for our AI usage declaration.
