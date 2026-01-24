#!/usr/bin/env python3
"""
Evaluate NAND circuit and output SHA-256 hash.

Usage:
    python eval-nands.py
    python eval-nands.py -i input-bits.txt -i constants-bits.txt
    python eval-nands.py -i input-bits.txt -i constants-bits.txt -n nands-optimized.txt
    python eval-nands.py -d /path/to/circuit
"""

import argparse
import os


def load_inputs(filepaths):
    """Load input values from one or more input files.

    Each file should have lines in the format: label,value
    where value is 0 or 1.
    """
    nodes = {}
    for filepath in filepaths:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    label, value = line.split(',')
                    nodes[label] = value == '1'
    return nodes


def main():
    parser = argparse.ArgumentParser(description="Evaluate NAND circuit")
    parser.add_argument("--inputs", "-i", action="append", default=None,
                        help="Input file(s) containing bit values (can be specified multiple times)")
    parser.add_argument("--dir", "-d", default=".", help="Directory containing circuit files (used if -i not specified)")
    parser.add_argument("--nands", "-n", default=None, help="Path to NAND file (default: nands.txt in dir)")
    args = parser.parse_args()

    # Determine input files
    if args.inputs:
        input_files = args.inputs
    else:
        # Default: load both constants-bits.txt and input-bits.txt from dir
        input_files = [
            os.path.join(args.dir, "constants-bits.txt"),
            os.path.join(args.dir, "input-bits.txt")
        ]

    # Load all input values
    nodes = load_inputs(input_files)

    # Process nands file
    nands_path = args.nands if args.nands else os.path.join(args.dir, "nands.txt")
    with open(nands_path, 'r') as f:
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
