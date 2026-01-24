#!/usr/bin/env python3
"""
Analyze the layer structure of a NAND circuit.

A layer consists of all gates that depend only on gates in previous layers:
- Layer 0: Input bits and constant bits
- Layer N: Gates where max(layer(input_a), layer(input_b)) = N-1

This computes the critical path depth and shows gate distribution across layers.

Usage:
    python analyze-layers.py
    python analyze-layers.py -n nands-optimized.txt
    python analyze-layers.py -i constants-bits.txt -i input-bits.txt
    python analyze-layers.py -n nands-ch-opt.txt -v  # verbose output
"""

import argparse
from collections import defaultdict


def load_inputs_from_files(filenames):
    """Load input labels from one or more input files.

    Each file should have lines in the format: label,value
    """
    labels = set()
    labels.add('CONST-0')
    labels.add('CONST-1')

    for filename in filenames:
        try:
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split(',')
                        if len(parts) >= 1:
                            labels.add(parts[0])
        except FileNotFoundError:
            print(f"Warning: Could not find {filename}")
            pass

    return labels


def generate_default_inputs():
    """Generate expected input/constant labels when no input files specified."""
    labels = set()
    labels.add('CONST-0')
    labels.add('CONST-1')

    # Constants
    for i in range(64):
        for b in range(32):
            labels.add(f'K-{i}-B{b}')
    for i in range(8):
        for b in range(32):
            labels.add(f'H-INIT-{i}-B{b}')

    # Inputs
    for w in range(16):
        for b in range(32):
            labels.add(f'INPUT-W{w}-B{b}')

    return labels


def load_circuit(filename):
    """Load circuit gates."""
    gates = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split(',')
                if len(parts) == 3:
                    label, a, b = parts
                    gates.append((label, a, b))
    return gates


def compute_layers(gates, layer0_labels):
    """Compute the layer for each gate.

    Returns:
        layers: dict mapping label -> layer number
        layer_counts: dict mapping layer number -> count of gates
        max_layer: the maximum layer number (critical path depth)
    """
    layers = {}

    # Layer 0: inputs and constants
    for label in layer0_labels:
        layers[label] = 0

    # Compute layer for each gate in order
    for label, a, b in gates:
        layer_a = layers.get(a, -1)
        layer_b = layers.get(b, -1)

        if layer_a == -1 or layer_b == -1:
            # Missing dependency - shouldn't happen in valid circuit
            print(f"Warning: Missing dependency for {label}: {a}={layer_a}, {b}={layer_b}")
            layers[label] = -1
            continue

        # Layer is one more than the max of inputs
        layers[label] = max(layer_a, layer_b) + 1

    # Count gates per layer (excluding layer 0 which is inputs/constants)
    layer_counts = defaultdict(int)
    for label, layer in layers.items():
        if label not in layer0_labels and layer > 0:
            layer_counts[layer] += 1

    max_layer = max(layers.values()) if layers else 0

    return layers, dict(layer_counts), max_layer


def analyze_layers(gates, layers, layer_counts, max_layer, verbose=False):
    """Analyze and print layer statistics."""
    total_gates = len(gates)

    print(f"\n{'='*60}")
    print(f"LAYER ANALYSIS")
    print(f"{'='*60}")
    print(f"Total gates: {total_gates:,}")
    print(f"Total layers: {max_layer} (critical path depth)")
    print(f"{'='*60}\n")

    # Summary by layer ranges
    print("Gates by layer range:")
    print("-" * 40)

    ranges = [
        (1, 100),
        (101, 500),
        (501, 1000),
        (1001, 2000),
        (2001, 5000),
        (5001, 10000),
        (10001, max_layer + 1)
    ]

    for start, end in ranges:
        if start > max_layer:
            break
        actual_end = min(end - 1, max_layer)
        count = sum(layer_counts.get(i, 0) for i in range(start, actual_end + 1))
        if count > 0:
            pct = (count / total_gates) * 100
            print(f"  Layers {start:5d}-{actual_end:5d}: {count:8,} gates ({pct:5.1f}%)")

    print()

    # Find layers with most gates
    print("Largest layers:")
    print("-" * 40)
    sorted_layers = sorted(layer_counts.items(), key=lambda x: -x[1])[:10]
    for layer, count in sorted_layers:
        pct = (count / total_gates) * 100
        print(f"  Layer {layer:5d}: {count:8,} gates ({pct:5.1f}%)")

    print()

    # Layer distribution histogram
    print("Layer distribution (gates per 1000 layers):")
    print("-" * 40)

    bucket_size = max(1, max_layer // 20)
    for bucket_start in range(1, max_layer + 1, bucket_size):
        bucket_end = min(bucket_start + bucket_size - 1, max_layer)
        count = sum(layer_counts.get(i, 0) for i in range(bucket_start, bucket_end + 1))
        bar_len = int(50 * count / total_gates) if total_gates > 0 else 0
        bar = '#' * bar_len
        print(f"  {bucket_start:5d}-{bucket_end:5d}: {bar}")

    print()

    if verbose:
        # Detailed per-layer counts
        print("Detailed layer counts:")
        print("-" * 40)
        for layer in sorted(layer_counts.keys()):
            count = layer_counts[layer]
            if count > 0:
                print(f"  Layer {layer:5d}: {count:,} gates")

    # Output layer statistics
    print("\nOutput gates:")
    print("-" * 40)
    output_layers = []
    for label, a, b in gates:
        if label.startswith('OUTPUT-'):
            output_layers.append(layers.get(label, -1))

    if output_layers:
        min_out = min(output_layers)
        max_out = max(output_layers)
        print(f"  Output layer range: {min_out} - {max_out}")
        print(f"  All outputs at layer: {max_out}" if min_out == max_out else "")


def main():
    parser = argparse.ArgumentParser(description="Analyze circuit layer structure")
    parser.add_argument("--nands", "-n", default="nands-ch-opt.txt",
                        help="NAND circuit file")
    parser.add_argument("--inputs", "-i", action="append", default=None,
                        help="Input file(s) containing bit values (can be specified multiple times)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed per-layer counts")
    args = parser.parse_args()

    print(f"Loading circuit from {args.nands}...")
    gates = load_circuit(args.nands)
    print(f"  Loaded {len(gates):,} gates")

    print(f"Loading inputs...")
    if args.inputs:
        layer0 = load_inputs_from_files(args.inputs)
    else:
        # Default: try to load from default files, fall back to generating labels
        try:
            layer0 = load_inputs_from_files(["constants-bits.txt", "input-bits.txt"])
        except:
            layer0 = generate_default_inputs()
    print(f"  Layer 0 has {len(layer0):,} signals (inputs)")

    print(f"\nComputing layers...")
    layers, layer_counts, max_layer = compute_layers(gates, layer0)

    analyze_layers(gates, layers, layer_counts, max_layer, args.verbose)

    return 0


if __name__ == "__main__":
    exit(main())
