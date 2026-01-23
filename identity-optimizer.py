#!/usr/bin/env python3
"""
Optimize identity patterns: NOT(NOT(x)) = x

Pattern: NAND(CONST-1, NAND(CONST-1, x)) = NOT(NOT(x)) = x

These patterns appear when XOR(x, 0) is computed using the standard
XOR template with CONST-1 for one input (which makes it an identity).

We can eliminate both gates and rewire directly to x.
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


def find_identity_patterns(gates):
    """Find NAND(CONST-1, NAND(CONST-1, x)) = x patterns."""
    gate_map = {label: (a, b) for label, a, b in gates}

    identities = []  # List of (outer_label, inner_label, original_x)

    for label, a, b in gates:
        # Looking for NAND(CONST-1, inner) where inner = NAND(CONST-1, x)
        inner = None
        if a == 'CONST-1' and b != 'CONST-1':
            inner = b
        elif b == 'CONST-1' and a != 'CONST-1':
            inner = a
        else:
            continue

        if inner not in gate_map:
            continue

        inner_a, inner_b = gate_map[inner]

        # Check if inner is NAND(CONST-1, x)
        x = None
        if inner_a == 'CONST-1' and inner_b != 'CONST-1':
            x = inner_b
        elif inner_b == 'CONST-1' and inner_a != 'CONST-1':
            x = inner_a
        else:
            continue

        # Found: label = NAND(CONST-1, inner) where inner = NAND(CONST-1, x)
        # This means label = NOT(NOT(x)) = x
        identities.append((label, inner, x))

    return identities


def optimize_identities(gates):
    """Remove identity patterns and rewire."""
    identities = find_identity_patterns(gates)

    print(f"Found {len(identities)} identity patterns (NOT(NOT(x)) = x)")

    if not identities:
        return gates

    # Show some examples
    print("\nExamples:")
    for outer, inner, x in identities[:10]:
        print(f"  {outer} = NOT(NOT({x})) -> just use {x}")

    # Build replacement map: outer_label -> x
    replacements = {}
    inner_gates_to_remove = set()

    for outer, inner, x in identities:
        if not outer.startswith("OUTPUT-"):
            replacements[outer] = x
            inner_gates_to_remove.add(inner)

    print(f"\nCreated {len(replacements)} replacements")

    # Apply replacements
    def resolve(label):
        seen = set()
        while label in replacements:
            if label in seen:
                break
            seen.add(label)
            label = replacements[label]
        return label

    optimized = []
    for label, a, b in gates:
        if label in replacements:
            continue

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
    print(f"Dead code elimination removed {len(optimized) - len(final)} gates")

    return final


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Optimize identity patterns")
    parser.add_argument("--input", "-i", default="nands-advanced-reopt.txt", help="Input file")
    parser.add_argument("--output", "-o", default="nands-identity-opt.txt", help="Output file")
    args = parser.parse_args()

    print(f"Loading {args.input}...")
    gates = load_circuit(args.input)
    print(f"  Loaded {len(gates):,} gates")

    print("\nFinding identity patterns...")
    optimized = optimize_identities(gates)

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
