#!/usr/bin/env python3
"""
Expand input.txt to bit-level representation.

Converts each 32-bit input word to 32 individual bit nodes.

Usage:
    python expand-input.py
    python expand-input.py -o input-bits.txt
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
    parser = argparse.ArgumentParser(description="Expand input.txt to bit-level")
    parser.add_argument("--input", "-i", default="input.txt", help="Input file")
    parser.add_argument("--output", "-o", default="input-bits.txt", help="Output file")
    args = parser.parse_args()

    lines = []

    # Process input.txt
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
