#!/usr/bin/env python3
"""
XOR Chain Sharing Optimizer

Optimizes NAND circuits by recognizing and refactoring XOR patterns
that share common inputs.

XOR pattern (4 NANDs):
  t = NAND(a,b)
  x = NAND(a,t)
  y = NAND(b,t)
  result = NAND(x,y)

Optimization opportunities:
1. XOR(CONST-0, x) = x (identity, can eliminate 4 NANDs)
2. XOR(CONST-1, x) = NOT(x) (can reduce 4 NANDs to 1)
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

    Returns (a, b, [t, x, y]) if XOR pattern, None otherwise.
    """
    if label not in gate_map:
        return None

    # result = NAND(x,y)
    x, y = gate_map[label]

    if x not in gate_map or y not in gate_map:
        return None

    # x = NAND(a,t) and y = NAND(b,t)
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


def optimize_xor_patterns(gates):
    """Optimize XOR patterns in the circuit."""
    gate_map = {label: (a, b) for label, a, b in gates}

    # Build usage count for all gates
    usage_count = defaultdict(int)
    for label, a, b in gates:
        usage_count[a] += 1
        usage_count[b] += 1

    # Find all XOR patterns
    xor_gates = {}
    for label, _, _ in gates:
        xor_info = identify_xor_pattern(label, gate_map)
        if xor_info:
            a, b, intermediates = xor_info
            xor_gates[label] = (a, b, intermediates)

    print(f"Found {len(xor_gates):,} XOR patterns")

    # Track replacements
    replacements = {}  # Maps old label to new label

    # Helper function to resolve replacements
    def resolve(label):
        """Resolve a label through replacement chain."""
        seen = set()
        while label in replacements:
            if label in seen:
                break  # Cycle detection
            seen.add(label)
            label = replacements[label]
        return label

    # Optimize XOR(CONST-0, x) = x (identity)
    identity_optimized = 0
    for label, (a, b, intermediates) in xor_gates.items():
        if a == "CONST-0":
            replacements[label] = b
            identity_optimized += 1
        elif b == "CONST-0":
            replacements[label] = a
            identity_optimized += 1

    print(f"  XOR(CONST-0, x) identity: {identity_optimized} patterns")

    # Optimize XOR(CONST-1, x) = NOT(x)
    not_gates = []
    not_optimized = 0
    for label, (a, b, intermediates) in xor_gates.items():
        if label in replacements:
            continue

        if a == "CONST-1":
            not_gate = f"{label}-OPT-NOT"
            not_gates.append((not_gate, b, b))
            replacements[label] = not_gate
            not_optimized += 1
        elif b == "CONST-1":
            not_gate = f"{label}-OPT-NOT"
            not_gates.append((not_gate, a, a))
            replacements[label] = not_gate
            not_optimized += 1

    print(f"  XOR(CONST-1, x) to NOT: {not_optimized} patterns")

    # Apply replacements and build new circuit
    optimized_gates = []
    gates_removed = 0

    for label, a, b in gates:
        # Skip if this gate is being replaced
        if label in replacements:
            gates_removed += 1
            continue

        # Resolve inputs through replacement chain
        a_resolved = resolve(a)
        b_resolved = resolve(b)

        optimized_gates.append((label, a_resolved, b_resolved))

    # Add new NOT gates
    optimized_gates.extend(not_gates)

    # Run dead code elimination to remove unreferenced intermediates
    print(f"\n  Running dead code elimination...")
    optimized_gates = eliminate_dead_code(optimized_gates)

    print(f"\nOptimization summary:")
    print(f"  Initial gates:  {len(gates):,}")
    print(f"  Final gates:    {len(optimized_gates):,}")
    print(f"  Eliminated:     {len(gates) - len(optimized_gates):,} ({100*(len(gates) - len(optimized_gates))/len(gates):.2f}%)")

    return optimized_gates


def eliminate_dead_code(gates):
    """Remove gates that don't contribute to outputs."""
    # Find all output gates (OUTPUT-W*)
    outputs = {label for label, _, _ in gates if label.startswith("OUTPUT-")}

    # Build dependency graph
    gate_map = {label: (a, b) for label, a, b in gates}
    needed = set(outputs)
    stack = list(outputs)

    # Trace backwards from outputs
    while stack:
        label = stack.pop()
        if label not in gate_map:
            continue
        a, b = gate_map[label]
        for inp in [a, b]:
            if inp not in needed and inp in gate_map:
                needed.add(inp)
                stack.append(inp)

    # Keep only needed gates
    kept_gates = [(label, a, b) for label, a, b in gates if label in needed]
    removed = len(gates) - len(kept_gates)
    if removed > 0:
        print(f"    Removed {removed:,} dead gates")
    return kept_gates


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Optimize XOR patterns in NAND circuit")
    parser.add_argument("--input", "-i", default="nands.txt", help="Input NAND file")
    parser.add_argument("--output", "-o", default="nands-xor-opt.txt", help="Output file")
    args = parser.parse_args()

    print(f"Loading {args.input}...")
    gates = load_circuit(args.input)
    print(f"  Loaded {len(gates):,} gates\n")

    print("Optimizing XOR patterns...")
    optimized = optimize_xor_patterns(gates)

    print(f"\nWriting {args.output}...")
    with open(args.output, 'w') as f:
        for label, a, b in optimized:
            f.write(f"{label},{a},{b}\n")

    print(f"Done! Saved to {args.output}")


if __name__ == "__main__":
    main()
