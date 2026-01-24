#!/usr/bin/env python3
"""
Evaluate NAND circuit and output SHA-256 hash.

Supports three-valued logic: 0, 1, and X (unbound/unknown).
X values propagate through the circuit according to NAND semantics:
- If either input is 0, output is 1 (regardless of X)
- If one input is 1 and other is X, output is X
- If both inputs are X, output is X

Usage:
    python eval-nands.py
    python eval-nands.py -i input-bits.txt -i constants-bits.txt
    python eval-nands.py -i input-bits.txt -i constants-bits.txt -n nands-optimized.txt
    python eval-nands.py -d /path/to/circuit
"""

import argparse
import os

# Constants for three-valued logic
FALSE = 0
TRUE = 1
UNKNOWN = 'X'


def nand3(a, b):
    """Three-valued NAND operation.

    Truth table:
        0,0 -> 1    0,1 -> 1    1,0 -> 1    1,1 -> 0
        0,X -> 1    X,0 -> 1    (if either input is 0, output is 1)
        1,X -> X    X,1 -> X    (if one is 1 and other is X, output is X)
        X,X -> X                (if both are X, output is X)
    """
    # If either input is 0, output is always 1
    if a == FALSE or b == FALSE:
        return TRUE
    # If both inputs are 1, output is 0
    if a == TRUE and b == TRUE:
        return FALSE
    # Otherwise (involves X), output is X
    return UNKNOWN


def parse_value(value_str):
    """Parse a value string to 0, 1, or 'X'."""
    value_str = value_str.strip().upper()
    if value_str == 'X':
        return UNKNOWN
    return TRUE if value_str == '1' else FALSE


def load_inputs(filepaths):
    """Load input values from one or more input files.

    Each file should have lines in the format: label,value
    where value is 0, 1, or X.
    """
    nodes = {}
    for filepath in filepaths:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    label, value = line.split(',')
                    nodes[label] = parse_value(value)
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
                nodes[label] = nand3(nodes[a], nodes[b])

    # Extract output bits and assemble hash
    result = []
    has_unknown = False
    for word in range(8):
        value = 0
        word_unknown_bits = []
        for bit in range(32):
            bit_val = nodes[f"OUTPUT-W{word}-B{bit}"]
            if bit_val == UNKNOWN:
                has_unknown = True
                word_unknown_bits.append(bit)
            elif bit_val == TRUE:
                value |= (1 << bit)
        if word_unknown_bits:
            result.append(f"{value:08x}[X@{','.join(map(str, word_unknown_bits))}]")
        else:
            result.append(f"{value:08x}")

    print(''.join(result))


if __name__ == "__main__":
    main()
