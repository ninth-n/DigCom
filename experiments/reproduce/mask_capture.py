"""Mask single-interface little-endian radiotap PCAPNG captures from this receiver."""
import argparse
from pathlib import Path
import struct


def block(kind, body):
    body += bytes(-len(body) % 4)
    size = len(body) + 12
    return struct.pack("<II", kind, size) + body + struct.pack("<I", size)


def mask_packet(packet, aliases):
    # The receiver emits a 17-byte legacy radiotap header. Reject extra fields,
    # which could hold vendor data or change the frame layout.
    if len(packet) < 19 or struct.unpack_from("<BBHI", packet) != (0, 0, 17, 0x86E):
        raise ValueError("Unsupported radiotap header")
    radio, frame = bytearray(packet[:17]), bytearray(packet[17:])
    if radio[8] & 0x20:
        raise ValueError("Unsupported radiotap data padding")
    if radio[8] & 0x10:
        del frame[-4:]
    radio[8] &= ~0x50  # Output has neither an FCS nor a bad-FCS indication.
    if len(frame) < 2:
        raise ValueError("Truncated frame")
    control = int.from_bytes(frame[:2], "little")
    kind, subtype = (control >> 2) & 3, (control >> 4) & 15
    if control & 3:
        raise ValueError("Unsupported 802.11 version")
    if kind in (0, 2):
        addresses = [4, 10, 16]
        end = 24
        if kind == 2 and control & 0x300 == 0x300:
            addresses.append(24)
            end += 6
        if kind == 2 and subtype & 8:
            end += 2
            if control & 0x8000:
                end += 4
        if kind == 0:
            frame = frame[:end]
    elif kind == 1 and subtype in (5, 8, 9, 10, 11, 12, 13, 14, 15):
        addresses = [4] if subtype in (12, 13) else [4, 10]
        end = 10 if len(addresses) == 1 else 16
    else:
        raise ValueError("Unsupported 802.11 frame type")
    if len(frame) < end:
        raise ValueError("Truncated 802.11 header")
    for offset in addresses:
        address = bytes(frame[offset:offset + 6])
        if address not in aliases:
            aliases[address] = b"\x02" + (len(aliases) + 1).to_bytes(5, "big")
        frame[offset:offset + 6] = aliases[address]
    # Keep only defined header fields, zeroing optional data/control fields as well.
    fixed = max(addresses) + 6
    if kind in (0, 2):
        frame[22:24] = bytes(2)  # Remove sequence numbers that could link captures.
        if fixed < 24:
            fixed = 24
    frame[fixed:] = bytes(len(frame) - fixed)
    return radio + frame


def mask(data):
    output = bytearray(block(0x0A0D0D0A, struct.pack("<IHHq", 0x1A2B3C4D, 1, 0, -1)))
    aliases = {}
    pos = 0
    interfaces = sections = packets = 0
    while pos < len(data):
        if len(data) - pos < 12:
            raise ValueError("Truncated block")
        kind, size = struct.unpack_from("<II", data, pos)
        if size < 12 or size % 4 or pos + size > len(data):
            raise ValueError("Invalid block length")
        body = data[pos + 8:pos + size - 4]
        if struct.unpack_from("<I", data, pos + size - 4)[0] != size:
            raise ValueError("Mismatched block length")
        pos += size
        if kind == 0x0A0D0D0A:
            sections += 1
            if sections != 1 or body[:4] != b"\x4d\x3c\x2b\x1a":
                raise ValueError("Expected one little-endian section")
        elif kind == 1:
            interfaces += 1
            if sections != 1 or interfaces != 1 or len(body) < 8 or body[:2] != b"\x7f\x00":
                raise ValueError("Expected one radiotap interface")
            resolution = b"\x06"
            offset = 8
            while offset + 4 <= len(body):
                code, length = struct.unpack_from("<HH", body, offset)
                offset += 4
                if offset + length > len(body):
                    raise ValueError("Truncated interface option")
                if code == 0:
                    break
                if code == 9 and length == 1:
                    resolution = body[offset:offset + 1]
                offset += (length + 3) & ~3
            output += block(1, struct.pack("<HHIHH", 127, 0, 65535, 9, 1) + resolution + bytes(7))
        elif kind == 6:
            if interfaces != 1 or len(body) < 20:
                raise ValueError("Missing interface or truncated packet block")
            interface, high, low, captured, original = struct.unpack_from("<IIIII", body)
            if interface or captured != original or captured > len(body) - 20:
                raise ValueError("Unsupported interface or truncated packet")
            packet = mask_packet(body[20:20 + captured], aliases)
            output += block(6, struct.pack("<IIIII", 0, high, low, len(packet), len(packet)) + packet)
            packets += 1
        elif kind in (2, 3):
            raise ValueError("Unsupported packet block")
    if not packets:
        raise ValueError("No packets found")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        masked = mask(args.capture.read_bytes())
        with args.output.open("xb") as output:
            output.write(masked)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
