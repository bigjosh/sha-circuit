#!/usr/bin/env python3
"""
Deep analysis of the NAND circuit to identify optimization opportunities.

Analyzes:
1. Gate distribution by operation type (based on label patterns)
2. Fan-out distribution (how many gates use each signal)
3. Critical path analysis
4. Subexpression patterns
5. Bit-position specific patterns
"""

from collections import defaultdict, Counter
import re


def load_circuit(filename):
    """Load NAND circuit."""
    gates = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                label, a, b = line.split(',')
                gates.append((label, a, b))
    return gates


def analyze_gate_distribution(gates):
    """Analyze where gates come from based on label patterns."""
    print("\n" + "="*60)
    print("GATE DISTRIBUTION BY OPERATION TYPE")
    print("="*60)

    patterns = {
        'ADD': r'-ADD-',
        'XOR': r'-XOR',
        'AND': r'-AND-',
        'OR': r'-OR-',
        'CH': r'-CH-',
        'MAJ': r'-MAJ',
        'S0': r'-S0-',  # Sigma0
        'S1': r'-S1-',  # Sigma1
        'S2': r'-S2-',  # sigma0 (lowercase)
        'S3': r'-S3-',  # sigma1 (lowercase)
        'OUTPUT': r'^OUTPUT-',
        'MSG-W': r'^W\d+',  # Message schedule
        'ROUND': r'^R\d+',  # Round operations
    }

    counts = defaultdict(int)
    uncategorized = []

    for label, a, b in gates:
        found = False
        for name, pattern in patterns.items():
            if re.search(pattern, label):
                counts[name] += 1
                found = True
                break
        if not found:
            counts['OTHER'] += 1
            if len(uncategorized) < 20:
                uncategorized.append(label)

    total = len(gates)
    for name, count in sorted(counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / total
        print(f"  {name:12s}: {count:,} gates ({pct:.1f}%)")

    if uncategorized:
        print(f"\n  Sample uncategorized labels:")
        for label in uncategorized[:10]:
            print(f"    - {label}")

    return counts


def analyze_fanout(gates):
    """Analyze fan-out distribution."""
    print("\n" + "="*60)
    print("FAN-OUT DISTRIBUTION")
    print("="*60)

    usage_count = defaultdict(int)
    for label, a, b in gates:
        usage_count[a] += 1
        usage_count[b] += 1

    fanout_dist = Counter(usage_count.values())

    print("  Fan-out | Count | Percentage")
    print("  --------+-------+-----------")
    total = sum(fanout_dist.values())
    cumulative = 0
    for fanout in sorted(fanout_dist.keys()):
        count = fanout_dist[fanout]
        cumulative += count
        pct = 100 * count / total
        cum_pct = 100 * cumulative / total
        if fanout <= 10 or count > 100:
            print(f"  {fanout:7d} | {count:5d} | {pct:5.1f}% (cum: {cum_pct:.1f}%)")

    # Find high fan-out signals
    high_fanout = [(label, count) for label, count in usage_count.items() if count >= 20]
    high_fanout.sort(key=lambda x: -x[1])

    print(f"\n  High fan-out signals (>= 20):")
    for label, count in high_fanout[:20]:
        print(f"    {label}: {count} uses")

    return usage_count


def analyze_not_gates(gates):
    """Find NOT gates (NAND(x,x))."""
    print("\n" + "="*60)
    print("NOT GATE ANALYSIS")
    print("="*60)

    not_gates = [(label, a) for label, a, b in gates if a == b]
    print(f"  Total NOT gates: {len(not_gates):,}")

    # Find chains of NOTs
    gate_map = {label: (a, b) for label, a, b in gates}
    double_nots = 0
    for label, inp in not_gates:
        if inp in gate_map:
            a, b = gate_map[inp]
            if a == b:  # Input is also a NOT
                double_nots += 1

    print(f"  Double NOT chains: {double_nots:,}")

    return not_gates


def analyze_constant_usage(gates):
    """Analyze how constants are used."""
    print("\n" + "="*60)
    print("CONSTANT USAGE ANALYSIS")
    print("="*60)

    const_usage = defaultdict(list)
    for label, a, b in gates:
        if a.startswith("CONST-") or a.startswith("K-") or a.startswith("H-INIT-"):
            const_usage[a].append(label)
        if b.startswith("CONST-") or b.startswith("K-") or b.startswith("H-INIT-"):
            const_usage[b].append(label)

    print(f"  Unique constants used: {len(const_usage)}")

    # Top constants by usage
    by_usage = sorted(const_usage.items(), key=lambda x: -len(x[1]))
    print(f"\n  Top constants by usage:")
    for const, users in by_usage[:15]:
        print(f"    {const}: {len(users)} uses")

    return const_usage


def find_repeated_patterns(gates):
    """Find repeated 2-gate and 3-gate patterns."""
    print("\n" + "="*60)
    print("REPEATED PATTERN ANALYSIS")
    print("="*60)

    gate_map = {label: (a, b) for label, a, b in gates}

    # Find patterns where same inputs are used
    input_pairs = defaultdict(list)
    for label, a, b in gates:
        # Normalize order for NAND (commutative)
        key = tuple(sorted([a, b]))
        input_pairs[key].append(label)

    # Find duplicates
    duplicates = [(key, labels) for key, labels in input_pairs.items() if len(labels) > 1]
    duplicates.sort(key=lambda x: -len(x[1]))

    print(f"  Input pairs used multiple times: {len(duplicates)}")

    if duplicates:
        print(f"\n  Top duplicated input pairs:")
        for (a, b), labels in duplicates[:10]:
            print(f"    NAND({a}, {b}): {len(labels)} times")
            for label in labels[:3]:
                print(f"      - {label}")

    return duplicates


def analyze_bit_patterns(gates):
    """Analyze patterns specific to bit positions."""
    print("\n" + "="*60)
    print("BIT POSITION ANALYSIS")
    print("="*60)

    # Extract bit position from labels
    bit_pattern = re.compile(r'-B(\d+)')

    gates_per_bit = defaultdict(int)
    for label, a, b in gates:
        match = bit_pattern.search(label)
        if match:
            bit = int(match.group(1))
            gates_per_bit[bit] += 1

    print("  Gates per bit position:")
    for bit in range(32):
        count = gates_per_bit.get(bit, 0)
        bar = '*' * (count // 500)
        print(f"    Bit {bit:2d}: {count:6,} {bar}")

    return gates_per_bit


def analyze_layer_distribution(gates):
    """Analyze circuit depth and layer sizes."""
    print("\n" + "="*60)
    print("LAYER/DEPTH ANALYSIS")
    print("="*60)

    gate_map = {label: (a, b) for label, a, b in gates}

    # Compute layer for each gate
    layers = {}

    def get_layer(label):
        if label in layers:
            return layers[label]
        if label not in gate_map:
            layers[label] = 0
            return 0
        a, b = gate_map[label]
        layer = max(get_layer(a), get_layer(b)) + 1
        layers[label] = layer
        return layer

    # Compute all layers
    import sys
    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(10000)

    try:
        for label, _, _ in gates:
            get_layer(label)
    except RecursionError:
        print("  Warning: Hit recursion limit during layer analysis")
        sys.setrecursionlimit(old_limit)
        return {}

    sys.setrecursionlimit(old_limit)

    # Layer statistics
    layer_counts = Counter(layers.values())
    max_layer = max(layer_counts.keys())

    print(f"  Maximum depth (critical path): {max_layer}")
    print(f"  Number of layers with gates: {len(layer_counts)}")

    # Find widest layers
    widest = sorted(layer_counts.items(), key=lambda x: -x[1])[:10]
    print(f"\n  Widest layers:")
    for layer, count in widest:
        print(f"    Layer {layer}: {count} gates")

    return layers


def find_xor_chains(gates):
    """Find XOR operations and chains."""
    print("\n" + "="*60)
    print("XOR PATTERN ANALYSIS")
    print("="*60)

    gate_map = {label: (a, b) for label, a, b in gates}

    def identify_xor(label):
        """Check if gate is XOR output."""
        if label not in gate_map:
            return None
        x, y = gate_map[label]
        if x not in gate_map or y not in gate_map:
            return None
        x_a, x_b = gate_map[x]
        y_a, y_b = gate_map[y]

        # Find common input t
        t = None
        a, b = None, None
        if x_b == y_b:
            t, a, b = x_b, x_a, y_a
        elif x_b == y_a:
            t, a, b = x_b, x_a, y_b
        elif x_a == y_b:
            t, a, b = x_a, x_b, y_a
        elif x_a == y_a:
            t, a, b = x_a, x_b, y_b
        else:
            return None

        if t not in gate_map:
            return None
        t_a, t_b = gate_map[t]
        if {t_a, t_b} == {a, b}:
            return (a, b)
        return None

    xor_count = 0
    xor_of_xor = 0  # 3-input XOR chains

    xor_inputs = []

    for label, _, _ in gates:
        result = identify_xor(label)
        if result:
            xor_count += 1
            a, b = result
            xor_inputs.append((label, a, b))

            # Check if inputs are also XORs
            if identify_xor(a) or identify_xor(b):
                xor_of_xor += 1

    print(f"  Total XOR patterns: {xor_count:,}")
    print(f"  XOR chains (XOR of XOR): {xor_of_xor:,}")

    # Find common XOR inputs
    input_counts = defaultdict(int)
    for _, a, b in xor_inputs:
        input_counts[a] += 1
        input_counts[b] += 1

    high_count = [(inp, c) for inp, c in input_counts.items() if c >= 5]
    high_count.sort(key=lambda x: -x[1])

    print(f"\n  Signals used in multiple XORs (>=5):")
    for inp, count in high_count[:15]:
        print(f"    {inp}: {count} XORs")

    return xor_inputs


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Deep circuit analysis")
    parser.add_argument("--nands", "-n", default="nands-xor-final.txt", help="NAND circuit file")
    args = parser.parse_args()

    print(f"Loading {args.nands}...")
    gates = load_circuit(args.nands)
    print(f"Loaded {len(gates):,} gates")

    analyze_gate_distribution(gates)
    analyze_fanout(gates)
    analyze_not_gates(gates)
    analyze_constant_usage(gates)
    find_repeated_patterns(gates)
    analyze_bit_patterns(gates)
    find_xor_chains(gates)
    analyze_layer_distribution(gates)

    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
