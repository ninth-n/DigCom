# Reproducing the early receiver experiments

These tools reconstruct the workflows described in [issue #1](https://github.com/ninth-n/DigCom/issues/1). The receiver scripts reuse the GNU Radio chain in `experiments/guide/rx_chain.py`. Use the same GNU Radio environment and out-of-tree modules as the receiver. On Windows, use the Radioconda environment. If GNU Radio cannot open its FFT cache due to a non-ASCII Windows profile path, set `XDG_CACHE_HOME` to an existing writable directory with an ASCII path.

## Offline results and Pluto model

From the repository root, replace `RECORDINGS` with the folder containing the three Moodle complex64 files:

```text
python experiments/reproduce/offline.py baseline RECORDINGS baseline.csv
python experiments/reproduce/offline.py sweep RECORDINGS sweep.csv
python experiments/reproduce/offline.py pluto RECORDINGS pluto.csv
```

Use `--channel ch36`, `ch6` or `ch100` to run one recording. The baseline CSV gives total CRC-valid frames and counts by encoding index. Indices 0, 2, 3 and 4 correspond to the four rates shown in the Wiki. The sweep changes the detection threshold or correlation window while keeping the other at its default. For constellation plots, see the [threshold experiment instructions](../README.md).

The Pluto model retains one buffer every `round(buffer * 20 / 6.5)` samples and concatenates the retained samples. It uses three equally spaced start offsets for each buffer size. Average the `percent` values by recording and buffer size to get the share of the full-recording count. The original offsets were not documented, so this is a reconstruction of the model and individual counts may differ. The model writes a temporary file containing about a third of one recording at a time.

## Generate the Pluto flowgraph

With PyYAML installed and the gr-ieee802-11 submodule checked out:

```text
python experiments/reproduce/generate_pluto.py deps/gr-ieee802-11/examples/wifi_rx.grc regenerated_wifi_rx_pluto.grc
```

The script swaps the USRP source for the ADALM-Pluto source, updates the project settings and enables the Wireshark output. Open the generated graph in GNU Radio Companion with the receiver dependencies installed. The filename must be new.

## Mask a capture

```text
python experiments/reproduce/mask_capture.py input.pcapng masked.pcapng
```

Keep raw captures outside Git. This script is specific to the receiver's single-interface, little-endian radiotap PCAPNG format. It replaces MAC addresses with per-file aliases, removes management bodies, clears payloads and rebuilds capture metadata while retaining packet timestamps and radio fields. It rejects unsupported packet layouts. Test on the published masked capture or synthetic inputs. Review any proposed public output before sharing, since timing and radio metadata remain visible.
