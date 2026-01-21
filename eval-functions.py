#!/usr/bin/env python3
"""
Evaluate SHA-256 circuit from input.txt, constants.txt, and functions.txt.

Processes files line-by-line, storing values in a hash map as they're computed.
Outputs the resulting hash (from OUTPUT-W0 through OUTPUT-W7) as a hex string.

Usage:
    python eval-functions.py
    python eval-functions.py -d ./circuit_dir
"""

import argparse
import sys
import os


def rotr(x, n):
    """Right rotate 32-bit value by n bits."""
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF


def evaluate(func, values):
    """Evaluate a function with given input values."""
    if func == "XOR":
        return values[0] ^ values[1]
    elif func == "AND":
        return values[0] & values[1]
    elif func == "OR":
        return values[0] | values[1]
    elif func == "NOT":
        return (~values[0]) & 0xFFFFFFFF
    elif func == "ADD":
        return (values[0] + values[1]) & 0xFFFFFFFF
    elif func == "COPY":
        return values[0]
    elif func.startswith("ROTR"):
        return rotr(values[0], int(func[4:]))
    elif func.startswith("SHR"):
        return values[0] >> int(func[3:])
    else:
        raise ValueError(f"Unknown function: {func}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate SHA-256 circuit and output hash")
    parser.add_argument("--dir", "-d", default=".", help="Directory containing circuit files")
    args = parser.parse_args()

    nodes = {}

    # Process input.txt
    with open(os.path.join(args.dir, "input.txt"), 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                label, value = line.split(',')
                nodes[label] = int(value, 16)

    # Process constants.txt
    with open(os.path.join(args.dir, "constants.txt"), 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                label, value = line.split(',')
                nodes[label] = int(value, 16)

    # Process functions.txt line by line
    with open(os.path.join(args.dir, "functions.txt"), 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split(',')
                label, func = parts[0], parts[1]
                inputs = [nodes[inp] for inp in parts[2:]]
                nodes[label] = evaluate(func, inputs)

    # Output hash
    print(''.join(f'{nodes[f"OUTPUT-W{i}"]:08x}' for i in range(8)))


if __name__ == "__main__":
    main()
