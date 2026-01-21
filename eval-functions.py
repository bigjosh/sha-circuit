#!/usr/bin/env python3
"""
Evaluate SHA-256 circuit from input.txt, constants.txt, and functions.txt.

Outputs the resulting hash (from OUTPUT-W0 through OUTPUT-W7) as a hex string.

Usage:
    python eval-functions.py
    python eval-functions.py -d ./circuit_dir
    python eval-functions.py --verbose
"""

import argparse
import sys
import os


def load_nodes_from_file(filename):
    """Load constant nodes from a file. Format: LABEL,HEXVALUE"""
    nodes = {}
    with open(filename, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) != 2:
                print(f"Error: Invalid format in {filename} line {line_num}: {line}",
                      file=sys.stderr)
                sys.exit(1)
            label, value = parts
            try:
                nodes[label] = int(value, 16)
            except ValueError:
                print(f"Error: Invalid hex value in {filename} line {line_num}: {value}",
                      file=sys.stderr)
                sys.exit(1)
    return nodes


def load_functions(filename):
    """Load function definitions from file. Format: LABEL,FUNC,INPUT1,INPUT2,..."""
    functions = []
    with open(filename, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) < 2:
                print(f"Error: Invalid format in {filename} line {line_num}: {line}",
                      file=sys.stderr)
                sys.exit(1)
            label = parts[0]
            func = parts[1]
            inputs = parts[2:] if len(parts) > 2 else []
            functions.append((label, func, inputs, line_num))
    return functions


def rotr(x, n):
    """Right rotate 32-bit value by n bits."""
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF


def shr(x, n):
    """Right shift 32-bit value by n bits."""
    return x >> n


def evaluate(nodes, func, inputs, label, line_num):
    """Evaluate a function with given inputs."""
    # Resolve input values
    values = []
    for inp in inputs:
        if inp not in nodes:
            print(f"Error: Unknown input '{inp}' for function '{label}' at line {line_num}",
                  file=sys.stderr)
            sys.exit(1)
        values.append(nodes[inp])

    # Execute function
    if func == "XOR":
        if len(values) != 2:
            print(f"Error: XOR requires 2 inputs, got {len(values)} at line {line_num}",
                  file=sys.stderr)
            sys.exit(1)
        return values[0] ^ values[1]

    elif func == "AND":
        if len(values) != 2:
            print(f"Error: AND requires 2 inputs, got {len(values)} at line {line_num}",
                  file=sys.stderr)
            sys.exit(1)
        return values[0] & values[1]

    elif func == "OR":
        if len(values) != 2:
            print(f"Error: OR requires 2 inputs, got {len(values)} at line {line_num}",
                  file=sys.stderr)
            sys.exit(1)
        return values[0] | values[1]

    elif func == "NOT":
        if len(values) != 1:
            print(f"Error: NOT requires 1 input, got {len(values)} at line {line_num}",
                  file=sys.stderr)
            sys.exit(1)
        return (~values[0]) & 0xFFFFFFFF

    elif func == "ADD":
        if len(values) != 2:
            print(f"Error: ADD requires 2 inputs, got {len(values)} at line {line_num}",
                  file=sys.stderr)
            sys.exit(1)
        return (values[0] + values[1]) & 0xFFFFFFFF

    elif func == "COPY":
        if len(values) != 1:
            print(f"Error: COPY requires 1 input, got {len(values)} at line {line_num}",
                  file=sys.stderr)
            sys.exit(1)
        return values[0]

    elif func.startswith("ROTR"):
        if len(values) != 1:
            print(f"Error: ROTR requires 1 input, got {len(values)} at line {line_num}",
                  file=sys.stderr)
            sys.exit(1)
        try:
            n = int(func[4:])
        except ValueError:
            print(f"Error: Invalid ROTR amount in '{func}' at line {line_num}",
                  file=sys.stderr)
            sys.exit(1)
        return rotr(values[0], n)

    elif func.startswith("SHR"):
        if len(values) != 1:
            print(f"Error: SHR requires 1 input, got {len(values)} at line {line_num}",
                  file=sys.stderr)
            sys.exit(1)
        try:
            n = int(func[3:])
        except ValueError:
            print(f"Error: Invalid SHR amount in '{func}' at line {line_num}",
                  file=sys.stderr)
            sys.exit(1)
        return shr(values[0], n)

    else:
        print(f"Error: Unknown function '{func}' at line {line_num}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate SHA-256 circuit and output hash",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python eval-functions.py
  python eval-functions.py -d ./my_circuit
  python eval-functions.py --verbose
"""
    )

    parser.add_argument("--dir", "-d", default=".",
                        help="Directory containing input.txt, constants.txt, functions.txt (default: .)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show progress and statistics")
    parser.add_argument("--input", "-i", default="input.txt",
                        help="Input file name (default: input.txt)")
    parser.add_argument("--constants", "-c", default="constants.txt",
                        help="Constants file name (default: constants.txt)")
    parser.add_argument("--functions", "-f", default="functions.txt",
                        help="Functions file name (default: functions.txt)")

    args = parser.parse_args()

    # Build file paths
    input_file = os.path.join(args.dir, args.input)
    constants_file = os.path.join(args.dir, args.constants)
    functions_file = os.path.join(args.dir, args.functions)

    # Check files exist
    for filepath in [input_file, constants_file, functions_file]:
        if not os.path.exists(filepath):
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            sys.exit(1)

    # Load nodes
    if args.verbose:
        print(f"Loading {input_file}...", file=sys.stderr)
    nodes = load_nodes_from_file(input_file)
    input_count = len(nodes)

    if args.verbose:
        print(f"Loading {constants_file}...", file=sys.stderr)
    nodes.update(load_nodes_from_file(constants_file))
    constants_count = len(nodes) - input_count

    if args.verbose:
        print(f"Loading {functions_file}...", file=sys.stderr)
    functions = load_functions(functions_file)

    if args.verbose:
        print(f"Loaded {input_count} inputs, {constants_count} constants, {len(functions)} functions",
              file=sys.stderr)
        print(f"Evaluating circuit...", file=sys.stderr)

    # Evaluate all functions in order
    for label, func, inputs, line_num in functions:
        result = evaluate(nodes, func, inputs, label, line_num)
        nodes[label] = result

    # Collect output words
    output_words = []
    for i in range(8):
        label = f"OUTPUT-W{i}"
        if label not in nodes:
            print(f"Error: Output node '{label}' not found", file=sys.stderr)
            sys.exit(1)
        output_words.append(nodes[label])

    # Format as hex string
    hash_hex = ''.join(f'{w:08x}' for w in output_words)

    if args.verbose:
        print(f"Result:", file=sys.stderr)

    print(hash_hex)


if __name__ == "__main__":
    main()
