#!/usr/bin/env python3
"""
Expand word-level values to bit-level representation.

Converts each 32-bit word to 32 individual bit nodes.
Optionally adds CONST-0 and CONST-1 as special constant bits.

Usage:
    python expand-words.py -i constants.txt -o constants-bits.txt --add-constants
    python expand-words.py -i input.txt -o input-bits.txt
"""

import argparse


def expand_word_to_bits(label, value):
    """Expand a 32-bit value to 32 bit lines."""
    lines = []
    for bit in range(32):
        bit_value = (value >> bit) & 1
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
                value = int(hex_value, 16)
                lines.extend(expand_word_to_bits(label, value))

    # Write output
    with open(args.output, 'w') as f:
        f.write('\n'.join(lines))

    print(f"Generated {args.output} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
