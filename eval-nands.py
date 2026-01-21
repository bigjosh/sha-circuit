#!/usr/bin/env python3
"""
Evaluate NAND circuit and output SHA-256 hash.

Usage:
    python eval-nands.py
    python eval-nands.py -d /path/to/circuit
"""

import argparse
import os


def main():
    parser = argparse.ArgumentParser(description="Evaluate NAND circuit")
    parser.add_argument("--dir", "-d", default=".", help="Directory containing circuit files")
    args = parser.parse_args()

    nodes = {}  # label -> bool

    # Load constants-bits.txt
    with open(os.path.join(args.dir, "constants-bits.txt"), 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                label, value = line.split(',')
                nodes[label] = value == '1'

    # Load input-bits.txt
    with open(os.path.join(args.dir, "input-bits.txt"), 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                label, value = line.split(',')
                nodes[label] = value == '1'

    # Process nands.txt
    with open(os.path.join(args.dir, "nands.txt"), 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                label, a, b = line.split(',')
                nodes[label] = not (nodes[a] and nodes[b])

    # Extract output bits and assemble hash
    result = []
    for word in range(8):
        value = 0
        for bit in range(32):
            if nodes[f"OUTPUT-W{word}-B{bit}"]:
                value |= (1 << bit)
        result.append(f"{value:08x}")

    print(''.join(result))


if __name__ == "__main__":
    main()
