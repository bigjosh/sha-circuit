#!/usr/bin/env python3
"""
Verify NAND circuit correctness by comparing against reference SHA-256 implementation.

Tests with multiple random inputs to ensure circuit produces correct outputs.
Supports three-valued logic: 0, 1, and X (unbound/unknown).

Usage:
    python verify-circuit.py
    python verify-circuit.py -n nands-optimized.txt
    python verify-circuit.py -i constants-bits.txt
    python verify-circuit.py --tests 10
"""

import argparse
import hashlib
import os
import random

# Constants for three-valued logic
FALSE = 0
TRUE = 1
UNKNOWN = 'X'


def nand3(a, b):
    """Three-valued NAND operation."""
    if a == FALSE or b == FALSE:
        return TRUE
    if a == TRUE and b == TRUE:
        return FALSE
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
                    nodes[label] = ('const', parse_value(value))
    return nodes


def load_circuit(nands_file, input_files):
    """Load circuit definition."""
    # Load all inputs (constants, etc.)
    nodes = load_inputs(input_files)

    # Load NAND gates
    gates = []
    with open(nands_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                label, a, b = line.split(',')
                gates.append((label, a, b))

    return nodes, gates


def evaluate_circuit(nodes, gates, input_bits):
    """Evaluate circuit with given input bits using three-valued logic."""
    values = dict(nodes)

    # Set input bits
    for label, value in input_bits.items():
        values[label] = ('const', value)

    # Evaluate gates using three-valued NAND
    for label, a, b in gates:
        a_val = values[a][1] if isinstance(values[a], tuple) else values[a]
        b_val = values[b][1] if isinstance(values[b], tuple) else values[b]
        result = nand3(a_val, b_val)
        values[label] = result

    # Extract output
    result = []
    has_unknown = False
    for word in range(8):
        value = 0
        word_unknown_bits = []
        for bit in range(32):
            label = f"OUTPUT-W{word}-B{bit}"
            v = values[label][1] if isinstance(values[label], tuple) else values[label]
            if v == UNKNOWN:
                has_unknown = True
                word_unknown_bits.append(bit)
            elif v == TRUE:
                value |= (1 << bit)
        if word_unknown_bits:
            result.append(f"{value:08x}[X@{','.join(map(str, word_unknown_bits))}]")
        else:
            result.append(f"{value:08x}")

    return ''.join(result)


def generate_input_bits(message_bytes):
    """Generate input bits from message bytes (with SHA-256 padding)."""
    ml = len(message_bytes) * 8

    padded = bytearray(message_bytes)
    padded.append(0x80)

    while len(padded) % 64 != 56:
        padded.append(0x00)

    padded.extend(ml.to_bytes(8, 'big'))

    input_bits = {}
    for i in range(16):
        word = int.from_bytes(padded[i*4:(i+1)*4], 'big')
        for bit in range(32):
            input_bits[f"INPUT-W{i}-B{bit}"] = (word >> bit) & 1

    return input_bits


def reference_sha256(message_bytes):
    """Compute reference SHA-256 hash."""
    return hashlib.sha256(message_bytes).hexdigest()


def run_test(nodes, gates, message_bytes, verbose=False):
    """Run a single test and return True if passed."""
    input_bits = generate_input_bits(message_bytes)

    circuit_result = evaluate_circuit(nodes, gates, input_bits)
    reference_result = reference_sha256(message_bytes)

    passed = circuit_result == reference_result

    if verbose or not passed:
        status = "PASS" if passed else "FAIL"
        print(f"  {status}: message={message_bytes!r}")
        if not passed:
            print(f"    Circuit:   {circuit_result}")
            print(f"    Reference: {reference_result}")

    return passed


def main():
    parser = argparse.ArgumentParser(description="Verify NAND circuit correctness")
    parser.add_argument("--inputs", "-i", action="append", default=None,
                        help="Input file(s) containing constant bit values (can be specified multiple times)")
    parser.add_argument("--dir", "-d", default=".", help="Directory containing circuit files (used if -i not specified)")
    parser.add_argument("--nands", "-n", default=None, help="Path to NAND file")
    parser.add_argument("--tests", "-t", type=int, default=5, help="Number of random tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    nands_path = args.nands if args.nands else os.path.join(args.dir, "nands.txt")

    # Determine input files
    if args.inputs:
        input_files = args.inputs
    else:
        input_files = [os.path.join(args.dir, "constants-bits.txt")]

    print(f"Loading circuit from {nands_path}...")
    nodes, gates = load_circuit(nands_path, input_files)
    print(f"  {len(gates)} NAND gates loaded")

    # Run tests
    test_messages = [
        b"",                    # Empty message
        b"a",                   # Single char
        b"abc",                 # Simple
        b"hello",               # Hello
        b"The quick brown fox", # Longer
    ]

    # Add random messages
    for _ in range(args.tests):
        length = random.randint(0, 55)
        msg = bytes([random.randint(0, 255) for _ in range(length)])
        test_messages.append(msg)

    print(f"\nRunning {len(test_messages)} tests...")
    passed = 0
    failed = 0

    for msg in test_messages:
        if run_test(nodes, gates, msg, args.verbose):
            passed += 1
        else:
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")

    if failed > 0:
        exit(1)
    else:
        print("All tests passed!")
        exit(0)


if __name__ == "__main__":
    main()
