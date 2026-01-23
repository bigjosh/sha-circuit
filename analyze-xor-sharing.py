#!/usr/bin/env python3
"""
Analyze XOR sharing opportunities in the NAND circuit.

XOR(a,b) uses 4 NANDs with this structure:
  t = NAND(a,b)
  x = NAND(a,t)
  y = NAND(b,t)
  result = NAND(x,y)

If we have multiple XORs sharing an input, we might be able to optimize.
"""

from collections import defaultdict


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


def identify_xor_pattern(label, gate_map):
    """Check if a gate is the output of an XOR pattern.

    XOR pattern:
      t = NAND(a,b)
      x = NAND(a,t)
      y = NAND(b,t)
      result = NAND(x,y)

    Returns (a, b, intermediate_gates) if XOR pattern, None otherwise.
    """
    if label not in gate_map:
        return None

    # result = NAND(x,y)
    x, y = gate_map[label]

    if x not in gate_map or y not in gate_map:
        return None

    # x = NAND(a,t) and y = NAND(b,t)
    # or x = NAND(t,a) and y = NAND(t,b)
    x_a, x_b = gate_map[x]
    y_a, y_b = gate_map[y]

    # Find common input (should be t)
    t = None
    a, b = None, None

    if x_b == y_b:
        t = x_b
        a, b = x_a, y_a
    elif x_b == y_a:
        t = x_b
        a, b = x_a, y_b
    elif x_a == y_b:
        t = x_a
        a, b = x_b, y_a
    elif x_a == y_a:
        t = x_a
        a, b = x_b, y_b
    else:
        return None

    if t not in gate_map:
        return None

    # t = NAND(a,b)
    t_a, t_b = gate_map[t]
    if {t_a, t_b} == {a, b}:
        return (a, b, [t, x, y])

    return None


def analyze_xor_sharing(gates):
    """Find XOR sharing opportunities."""
    gate_map = {label: (a, b) for label, a, b in gates}

    # Find all XOR outputs
    xor_gates = {}
    for label, _, _ in gates:
        xor_info = identify_xor_pattern(label, gate_map)
        if xor_info:
            a, b, intermediates = xor_info
            xor_gates[label] = (a, b, intermediates)

    print(f"Found {len(xor_gates):,} XOR patterns in circuit")

    # Group XORs by their inputs
    input_pairs = defaultdict(list)
    for label, (a, b, _) in xor_gates.items():
        key = tuple(sorted([a, b]))
        input_pairs[key].append(label)

    # Find shared single inputs
    shared_a = defaultdict(list)
    shared_b = defaultdict(list)

    for label, (a, b, _) in xor_gates.items():
        shared_a[a].append(label)
        shared_b[b].append(label)

    # Report duplicates
    duplicates = sum(1 for labels in input_pairs.values() if len(labels) > 1)
    print(f"  Duplicate XOR(a,b): {duplicates} pairs")

    # Report sharing
    shared_a_count = sum(1 for labels in shared_a.values() if len(labels) > 1)
    shared_b_count = sum(1 for labels in shared_b.values() if len(labels) > 1)
    print(f"  XORs sharing first input: {shared_a_count} groups")
    print(f"  XORs sharing second input: {shared_b_count} groups")

    # Find largest sharing groups
    all_shared = {}
    for input_val, labels in shared_a.items():
        if len(labels) > 1:
            all_shared[input_val] = labels
    for input_val, labels in shared_b.items():
        if len(labels) > 1 and input_val not in all_shared:
            all_shared[input_val] = labels

    if all_shared:
        print(f"\n  Largest sharing groups:")
        sorted_groups = sorted(all_shared.items(), key=lambda x: -len(x[1]))
        for input_val, labels in sorted_groups[:10]:
            print(f"    {input_val}: {len(labels)} XORs share this input")
            # Show a few examples
            for label in labels[:3]:
                a, b, _ = xor_gates[label]
                other = b if a == input_val else a
                print(f"      - {label}: XOR({input_val}, {other})")

    # Estimate potential savings
    # If XORs share an input, we might save 1-2 NANDs per shared XOR
    total_shared_xors = sum(len(labels) - 1 for labels in all_shared.values())
    estimated_savings_low = total_shared_xors * 1  # Conservative: 1 NAND per shared XOR
    estimated_savings_high = total_shared_xors * 2  # Optimistic: 2 NANDs per shared XOR

    print(f"\nPotential savings:")
    print(f"  Conservative (1 NAND/shared): {estimated_savings_low:,} gates")
    print(f"  Optimistic (2 NANDs/shared):  {estimated_savings_high:,} gates")

    return xor_gates, all_shared


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze XOR sharing opportunities")
    parser.add_argument("--nands", "-n", default="nands.txt", help="NAND circuit file")
    args = parser.parse_args()

    print(f"Loading {args.nands}...")
    gates = load_circuit(args.nands)
    print(f"  Loaded {len(gates):,} gates")

    print(f"\nAnalyzing XOR patterns...")
    xor_gates, shared_groups = analyze_xor_sharing(gates)

    return 0


if __name__ == "__main__":
    exit(main())
