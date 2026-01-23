#!/usr/bin/env python3
"""
Optimize XOR(CONST-1, x) patterns to NOT(x).

XOR(1, x) = NOT(x)

Standard XOR uses 4 NANDs, but NOT uses only 1 NAND.
Savings: 3 gates per pattern.
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


def identify_xor(label, gate_map):
    """Return (a, b, [intermediates]) if label is XOR(a,b), else None."""
    if label not in gate_map:
        return None
    x, y = gate_map[label]
    if x not in gate_map or y not in gate_map:
        return None
    x_a, x_b = gate_map[x]
    y_a, y_b = gate_map[y]

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
        return (a, b, [t, x, y])
    return None


def optimize_xor1(gates):
    """Optimize XOR(CONST-1, x) to NOT(x)."""
    gate_map = {label: (a, b) for label, a, b in gates}

    # Find XOR(CONST-1, x) patterns
    # For each, we'll replace the XOR output with a NOT
    # and use the NOT's input as the signal to negate

    xor_replacements = {}  # label -> (input_to_negate, new_not_label)

    for label, _, _ in gates:
        result = identify_xor(label, gate_map)
        if not result:
            continue

        a, b, intermediates = result
        if a == 'CONST-1':
            # XOR(1, b) = NOT(b)
            xor_replacements[label] = (b, f"{label}-NOT")
        elif b == 'CONST-1':
            # XOR(a, 1) = NOT(a)
            xor_replacements[label] = (a, f"{label}-NOT")

    print(f"Found {len(xor_replacements)} XOR(CONST-1, x) patterns to optimize")

    if not xor_replacements:
        return gates

    # Build mapping from old label to new label
    label_mapping = {}
    for old_label, (input_val, new_label) in xor_replacements.items():
        label_mapping[old_label] = new_label

    # Resolve through replacement chains
    def resolve(label):
        return label_mapping.get(label, label)

    # Build new circuit, inserting NOT gates where needed
    optimized = []
    inserted_nots = set()

    for label, a, b in gates:
        if label in xor_replacements:
            # This is an XOR we're replacing
            input_val, new_label = xor_replacements[label]

            # Insert the NOT gate here (in place of the XOR output)
            optimized.append((new_label, input_val, input_val))
            continue

        # Resolve inputs
        a_resolved = resolve(a)
        b_resolved = resolve(b)
        optimized.append((label, a_resolved, b_resolved))

    # Dead code elimination
    print("Running dead code elimination...")
    outputs = {l for l, _, _ in optimized if l.startswith("OUTPUT-")}
    gate_map = {l: (a, b) for l, a, b in optimized}

    needed = set(outputs)
    stack = list(outputs)
    while stack:
        label = stack.pop()
        if label not in gate_map:
            continue
        a, b = gate_map[label]
        for inp in [a, b]:
            if inp not in needed and inp in gate_map:
                needed.add(inp)
                stack.append(inp)

    final = [(l, a, b) for l, a, b in optimized if l in needed]
    dead_removed = len(optimized) - len(final)
    print(f"Dead code elimination removed {dead_removed} gates")

    return final


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Optimize XOR(CONST-1, x)")
    parser.add_argument("--input", "-i", default="nands-xor-final.txt", help="Input file")
    parser.add_argument("--output", "-o", default="nands-xor1-opt.txt", help="Output file")
    args = parser.parse_args()

    print(f"Loading {args.input}...")
    gates = load_circuit(args.input)
    print(f"  Loaded {len(gates):,} gates")

    print("\nOptimizing XOR(CONST-1, x)...")
    optimized = optimize_xor1(gates)

    print(f"\nResults:")
    print(f"  Initial gates:  {len(gates):,}")
    print(f"  Final gates:    {len(optimized):,}")
    print(f"  Saved:          {len(gates) - len(optimized):,}")

    print(f"\nWriting {args.output}...")
    with open(args.output, 'w') as f:
        for label, a, b in optimized:
            f.write(f"{label},{a},{b}\n")

    print("Done!")


if __name__ == "__main__":
    main()
