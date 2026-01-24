#!/usr/bin/env python3
"""
Expand word-level values to bit-level representation.

Converts each 32-bit word to 32 individual bit nodes.
Supports unknown bytes marked as 'XX' in hex, which become 'X' bits.
Optionally adds CONST-0 and CONST-1 as special constant bits.

Usage:
    python expand-words.py -i constants.txt -o constants-bits.txt --add-constants
    python expand-words.py -i input.txt -o input-bits.txt
"""

import argparse


def parse_hex_with_unknowns(hex_str):
    """Parse hex string that may contain XX for unknown bytes.

    Returns list of 4 values, each is either an int (0-255) or None (unknown).
    """
    hex_str = hex_str.upper()
    bytes_list = []
    for i in range(0, 8, 2):  # 4 bytes = 8 hex chars
        pair = hex_str[i:i+2]
        if pair == "XX":
            bytes_list.append(None)
        else:
            bytes_list.append(int(pair, 16))
    return bytes_list


def expand_word_to_bits(label, hex_value):
    """Expand a 32-bit hex value to 32 bit lines.

    Handles XX for unknown bytes, outputting X for those bits.
    """
    bytes_list = parse_hex_with_unknowns(hex_value)

    lines = []
    for bit in range(32):
        byte_idx = 3 - (bit // 8)  # Big-endian: bit 0-7 in last byte, bit 24-31 in first byte
        bit_in_byte = bit % 8

        if bytes_list[byte_idx] is None:
            # Unknown byte -> unknown bit
            lines.append(f"{label}-B{bit},X")
        else:
            bit_value = (bytes_list[byte_idx] >> bit_in_byte) & 1
            lines.append(f"{label}-B{bit},{bit_value}")

    return lines


def main():
    parser = argparse.ArgumentParser(description="Expand word-level values to bits")
    parser.add_argument("--input", "-i", required=True, help="Input file (word-level)")
    parser.add_argument("--output", "-o", required=True, help="Output file (bit-level)")
    parser.add_argument("--add-constants", "-c", action="store_true",
                        help="Add CONST-0 and CONST-1 to output")
    args = parser.parse_args()

    lines = []
    unknown_bits = 0

    # Add special constant bits if requested
    if args.add_constants:
        lines.append("CONST-0,0")
        lines.append("CONST-1,1")

    # Process input file
    with open(args.input, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                label, hex_value = line.split(',')
                expanded = expand_word_to_bits(label, hex_value)
                lines.extend(expanded)
                unknown_bits += sum(1 for l in expanded if l.endswith(',X'))

    # Write output
    with open(args.output, 'w') as f:
        f.write('\n'.join(lines))

    if unknown_bits > 0:
        print(f"Generated {args.output} ({len(lines)} lines, {unknown_bits} unknown bits)")
    else:
        print(f"Generated {args.output} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
