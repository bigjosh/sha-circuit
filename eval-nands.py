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
    python eval-nands.py -i input-bits.txt -i constants-bits.txt -r results-bits.txt
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


def load_results(filepath):
    """Load output labels from results-bits.txt file.

    Returns list of (label, expected_value) tuples in file order.
    """
    results = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                label, expected = line.split(',')
                results.append((label, expected.upper()))
    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate NAND circuit")
    parser.add_argument("--inputs", "-i", action="append", default=None,
                        help="Input file(s) containing bit values (can be specified multiple times)")
    parser.add_argument("--dir", "-d", default=".", help="Directory containing circuit files (used if -i not specified)")
    parser.add_argument("--nands", "-n", default=None, help="Path to NAND file (default: nands.txt in dir)")
    parser.add_argument("--results", "-r", default=None, help="Results file specifying outputs (default: results-bits.txt in dir)")
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

    # Load results specification
    results_path = args.results if args.results else os.path.join(args.dir, "results-bits.txt")
    results = load_results(results_path)

    # Extract output bits based on results file
    # Group into words (assuming OUTPUT-W{word}-B{bit} format)
    words = {}
    for label, _ in results:
        # Parse OUTPUT-W{word}-B{bit}
        if label.startswith("OUTPUT-W") and "-B" in label:
            parts = label.split("-")
            word = int(parts[1][1:])  # W0 -> 0
            bit = int(parts[2][1:])   # B0 -> 0
            if word not in words:
                words[word] = {}
            words[word][bit] = nodes.get(label, UNKNOWN)

    # Assemble hash output
    result = []
    total_unknown = 0
    total_bits = len(results)

    for word in sorted(words.keys()):
        word_bits = words[word]
        word_hex = []
        for nibble in range(8):  # 8 nibbles per 32-bit word, MSB first
            nibble_idx = 7 - nibble
            nibble_value = 0
            nibble_has_unknown = False
            for bit_in_nibble in range(4):
                bit = nibble_idx * 4 + bit_in_nibble
                if bit in word_bits:
                    bit_val = word_bits[bit]
                    if bit_val == UNKNOWN:
                        nibble_has_unknown = True
                        total_unknown += 1
                    elif bit_val == TRUE:
                        nibble_value |= (1 << bit_in_nibble)
                else:
                    # Bit not in results file - treat as not present
                    pass
            if nibble_has_unknown:
                word_hex.append('x')
            else:
                word_hex.append(f"{nibble_value:x}")
        result.append(''.join(word_hex))

    hash_str = ''.join(result)
    print(hash_str)
    if total_unknown > 0:
        print(f"({total_unknown}/{total_bits} bits unknown)")


if __name__ == "__main__":
    main()
