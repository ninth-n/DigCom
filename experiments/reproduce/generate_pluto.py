"""Generate the project Pluto flowgraph from the pinned upstream Wi-Fi receiver."""
import argparse
from pathlib import Path

import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    graph = yaml.safe_load(args.upstream.read_text(encoding="utf-8"))
    config = yaml.safe_load(Path(__file__).with_name("pluto_settings.yml").read_text(encoding="utf-8"))
    blocks = {block["name"]: block for block in graph["blocks"]}
    source = config["source"]
    old = "uhd_usrp_source_0"
    if blocks[old]["id"] != "uhd_usrp_source" or source["name"] in blocks:
        parser.error("Expected the pinned upstream USRP receiver")
    graph["options"]["parameters"].update(config["options"])
    for name, values in config["parameters"].items():
        blocks[name]["parameters"].update(values)
    for name in ("blocks_file_sink_0", "foo_wireshark_connector_0"):
        blocks[name]["states"]["state"] = "enabled"
    graph["blocks"] = [
        block for name, block in blocks.items() if name not in {old, "lo_offset"}
    ] + [source]
    for connection in graph["connections"]:
        if connection[0] == old:
            connection[0] = source["name"]
    with args.output.open("x", encoding="utf-8") as output:
        yaml.safe_dump(graph, output, sort_keys=False)


if __name__ == "__main__":
    main()
