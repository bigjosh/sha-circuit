#!/usr/bin/env python3
"""
Optimize NAND circuit by applying multiple optimization passes.

Reads a NAND circuit and constant values, applies optimizations iteratively
until convergence, and outputs the optimized circuit.

Optimization passes:
- CSE: Common subexpression elimination
- Share inverters: Merge duplicate NOT gates
- NAND to identity: Merge equivalent NOT gates (NAND(x,x) and NAND(x,1))
- XOR chain: Deduplicate XOR patterns with same inputs
- XOR(0, x) = x: Remove identity XOR operations
- XOR(1, x) = NOT(x): Simplify XOR with constant 1
- Algebraic: NAND(x, NOT(x)) = 1
- Constant folding: Evaluate gates with known inputs (supports 0, 1, X)
- Dead code elimination: Remove gates not needed for outputs
- Identity patterns: NOT(NOT(x)) = x
- Double NOT: More aggressive double negation elimination
- AND(x,x) = x: Simplify redundant AND operations
- OR(x,x) = x: Simplify redundant OR operations
- Cleanup copies: Remove unnecessary copy chains

Supports three-valued logic (0, 1, X) where X = unbound/unknown.

Usage:
    python optimize-nands.py
    python optimize-nands.py -n nands.txt -i constants-bits.txt -o nands-optimized-final.txt
"""

import argparse
import sys


# Constants for three-valued logic
FALSE = 0
TRUE = 1
UNKNOWN = 'X'


def count_gates(filename):
    """Count NAND gates in a circuit file."""
    with open(filename) as f:
        return sum(1 for line in f if line.strip())


def load_circuit(filename):
    """Load NAND circuit."""
    gates = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split(',')
                if len(parts) == 3:
                    gates.append((parts[0], parts[1], parts[2]))
    return gates


def save_circuit(filename, gates):
    """Save NAND circuit."""
    with open(filename, 'w') as f:
        for label, a, b in gates:
            f.write(f"{label},{a},{b}\n")


def is_output_label(label):
    """Check if a label is a circuit output (should not be replaced/deleted)."""
    if label.startswith("OUTPUT-"):
        return True
    if label.startswith("FINAL-H") and "-ADD-B" in label:
        parts = label.split("-ADD-B")
        if len(parts) == 2 and "-T" not in parts[1]:
            return True
    return False


def parse_value(value_str):
    """Parse a value string to 0, 1, or 'X'."""
    value_str = value_str.strip().upper()
    if value_str == 'X':
        return UNKNOWN
    return TRUE if value_str == '1' else FALSE


def load_inputs(filenames):
    """Load input values from one or more input files."""
    values = {'CONST-0': FALSE, 'CONST-1': TRUE}
    for filename in filenames:
        try:
            with open(filename) as f:
                for line in f:
                    if line.strip():
                        parts = line.strip().split(',')
                        if len(parts) >= 2:
                            values[parts[0]] = parse_value(parts[1])
        except FileNotFoundError:
            pass
    return values


def nand3(a, b):
    """Three-valued NAND operation."""
    if a == FALSE or b == FALSE:
        return TRUE
    if a == TRUE and b == TRUE:
        return FALSE
    return UNKNOWN


# ============== OPTIMIZATION PASSES ==============

def optimize_cse(gates):
    """Common Subexpression Elimination."""
    seen = {}
    replacements = {}
    optimized = []

    for label, a, b in gates:
        a_new = replacements.get(a, a)
        b_new = replacements.get(b, b)
        key = (min(a_new, b_new), max(a_new, b_new))

        if key in seen and not is_output_label(label):
            replacements[label] = seen[key]
        else:
            if key not in seen:
                seen[key] = label
            optimized.append((label, a_new, b_new))

    return optimized


def optimize_constant_folding(gates, const_values):
    """Fold constant expressions and propagate constant values."""
    known = dict(const_values)
    first_pass = []

    for label, a, b in gates:
        a_val = known.get(a)
        b_val = known.get(b)

        if a_val == FALSE or b_val == FALSE:
            known[label] = TRUE
        elif a_val is not None and b_val is not None:
            if a_val == TRUE and b_val == TRUE:
                known[label] = FALSE
            elif a_val == UNKNOWN or b_val == UNKNOWN:
                first_pass.append((label, a, b))
            else:
                known[label] = nand3(a_val, b_val)
        else:
            first_pass.append((label, a, b))

    optimized = []
    for label, a, b in first_pass:
        a_new = a
        b_new = b

        if a in known and known[a] != UNKNOWN:
            a_new = f"CONST-{known[a]}"
        if b in known and known[b] != UNKNOWN:
            b_new = f"CONST-{known[b]}"

        optimized.append((label, a_new, b_new))

    return optimized, known


def rename_outputs(gates):
    """Rename FINAL-H*-ADD-B* labels to OUTPUT-W*-B* format."""
    import re
    pattern = re.compile(r'^FINAL-H(\d+)-ADD-B(\d+)$')

    renames = {}
    for label, a, b in gates:
        m = pattern.match(label)
        if m:
            word = int(m.group(1))
            bit = int(m.group(2))
            renames[label] = f"OUTPUT-W{word}-B{bit}"

    if not renames:
        return gates

    def resolve(label):
        return renames.get(label, label)

    return [(resolve(label), resolve(a), resolve(b)) for label, a, b in gates]


def optimize_dead_code(gates):
    """Remove gates not needed for outputs."""
    outputs = {label for label, _, _ in gates if label.startswith("OUTPUT-") or label.startswith("FINAL-H")}
    gate_map = {label: (a, b) for label, a, b in gates}

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

    return [(label, a, b) for label, a, b in gates if label in needed]


def optimize_identity_patterns(gates):
    """Remove NOT(NOT(x)) = x patterns."""
    gate_map = {label: (a, b) for label, a, b in gates}
    replacements = {}

    for label, a, b in gates:
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
        x = None
        if inner_a == 'CONST-1' and inner_b != 'CONST-1':
            x = inner_b
        elif inner_b == 'CONST-1' and inner_a != 'CONST-1':
            x = inner_a
        else:
            continue

        if not is_output_label(label):
            replacements[label] = x

    if not replacements:
        return gates

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
        optimized.append((label, resolve(a), resolve(b)))

    return optimized


def optimize_xor_with_zero(gates):
    """Optimize XOR(x, 0) = x patterns."""
    gate_map = {label: (a, b) for label, a, b in gates}

    def identify_xor(label):
        if label not in gate_map:
            return None
        x, y = gate_map[label]
        if x not in gate_map or y not in gate_map:
            return None

        x_a, x_b = gate_map[x]
        y_a, y_b = gate_map[y]

        t, a, b = None, None, None
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

    replacements = {}
    for label, _, _ in gates:
        xor_inputs = identify_xor(label)
        if xor_inputs:
            a, b = xor_inputs
            if a == 'CONST-0' and not is_output_label(label):
                replacements[label] = b
            elif b == 'CONST-0' and not is_output_label(label):
                replacements[label] = a

    if not replacements:
        return gates

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
        optimized.append((label, resolve(a), resolve(b)))

    return optimized


def optimize_xor_with_one(gates):
    """Optimize XOR(x, CONST-1) = NOT(x) patterns."""
    gate_map = {label: (a, b) for label, a, b in gates}

    def identify_xor(label):
        if label not in gate_map:
            return None
        x, y = gate_map[label]
        if x not in gate_map or y not in gate_map:
            return None

        x_a, x_b = gate_map[x]
        y_a, y_b = gate_map[y]

        t, a, b = None, None, None
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

    xor_replacements = {}
    for label, _, _ in gates:
        result = identify_xor(label)
        if result:
            a, b, _ = result
            if a == 'CONST-1':
                xor_replacements[label] = (b, f"{label}-NOT")
            elif b == 'CONST-1':
                xor_replacements[label] = (a, f"{label}-NOT")

    if not xor_replacements:
        return gates

    label_mapping = {old: new for old, (_, new) in xor_replacements.items()}

    def resolve(label):
        return label_mapping.get(label, label)

    optimized = []
    for label, a, b in gates:
        if label in xor_replacements:
            input_val, new_label = xor_replacements[label]
            optimized.append((new_label, input_val, input_val))
        else:
            optimized.append((label, resolve(a), resolve(b)))

    return optimized


def optimize_share_inverters(gates):
    """Share NOT gates computing the same thing."""
    not_of = {}
    for label, a, b in gates:
        if a == b:
            not_of.setdefault(a, []).append(label)
        elif a == 'CONST-1':
            not_of.setdefault(b, []).append(label)
        elif b == 'CONST-1':
            not_of.setdefault(a, []).append(label)

    replacements = {}
    for input_sig, labels in not_of.items():
        if len(labels) > 1:
            canonical = None
            for l in labels:
                if not l.startswith("OUTPUT-"):
                    canonical = l
                    break
            if canonical is None:
                canonical = labels[0]

            for other in labels:
                if other != canonical and not other.startswith("OUTPUT-"):
                    replacements[other] = canonical

    if not replacements:
        return gates

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
        optimized.append((label, resolve(a), resolve(b)))

    return optimized


def optimize_algebraic(gates):
    """Apply algebraic simplifications: NAND(x, NOT(x)) = 1."""
    gate_map = {label: (a, b) for label, a, b in gates}

    not_of = {}
    for label, a, b in gates:
        if a == b:
            not_of[label] = a
        elif a == 'CONST-1':
            not_of[label] = b
        elif b == 'CONST-1':
            not_of[label] = a

    replacements = {}
    for label, a, b in gates:
        if a in not_of and not_of[a] == b:
            if not is_output_label(label):
                replacements[label] = 'CONST-1'
        elif b in not_of and not_of[b] == a:
            if not is_output_label(label):
                replacements[label] = 'CONST-1'

    if not replacements:
        return gates

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
        optimized.append((label, resolve(a), resolve(b)))

    return optimized


def optimize_and_simplification(gates):
    """Optimize AND(x, x) = x patterns."""
    gate_map = {label: (a, b) for label, a, b in gates}

    replacements = {}
    for label, a, b in gates:
        if a == b and a in gate_map:
            inner_a, inner_b = gate_map[a]
            if inner_a == inner_b:
                if not is_output_label(label):
                    replacements[label] = inner_a

    if not replacements:
        return gates

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
        optimized.append((label, resolve(a), resolve(b)))

    return optimized


def optimize_or_simplification(gates):
    """Recognize OR gates and simplify OR(x, x) = x."""
    gate_map = {label: (a, b) for label, a, b in gates}

    replacements = {}
    for label, a, b in gates:
        if a in gate_map and b in gate_map:
            a_inner_a, a_inner_b = gate_map[a]
            b_inner_a, b_inner_b = gate_map[b]

            if a_inner_a == a_inner_b and b_inner_a == b_inner_b:
                if a_inner_a == b_inner_a:
                    if not is_output_label(label):
                        replacements[label] = a_inner_a

    if not replacements:
        return gates

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
        optimized.append((label, resolve(a), resolve(b)))

    return optimized


def optimize_double_not(gates):
    """More aggressive double negation elimination."""
    gate_map = {label: (a, b) for label, a, b in gates}

    not_gates = {}
    for label, a, b in gates:
        if a == b:
            not_gates[label] = a
        elif a == 'CONST-1':
            not_gates[label] = b
        elif b == 'CONST-1':
            not_gates[label] = a

    replacements = {}
    for label, a, b in gates:
        inner = None
        if a == b:
            inner = a
        elif a == 'CONST-1':
            inner = b
        elif b == 'CONST-1':
            inner = a

        if inner and inner in not_gates:
            original = not_gates[inner]
            if not is_output_label(label):
                replacements[label] = original

    if not replacements:
        return gates

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
        optimized.append((label, resolve(a), resolve(b)))

    return optimized


def optimize_xor_chain(gates):
    """Recognize and deduplicate XOR patterns."""
    gate_map = {label: (a, b) for label, a, b in gates}

    def identify_xor(label):
        if label not in gate_map:
            return None
        x, y = gate_map[label]
        if x not in gate_map or y not in gate_map:
            return None

        x_a, x_b = gate_map[x]
        y_a, y_b = gate_map[y]

        t, a, b = None, None, None
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
            return (min(a, b), max(a, b))
        return None

    xor_outputs = {}
    for label, _, _ in gates:
        xor_inputs = identify_xor(label)
        if xor_inputs:
            xor_outputs[label] = xor_inputs

    xor_by_inputs = {}
    for label, inputs in xor_outputs.items():
        xor_by_inputs.setdefault(inputs, []).append(label)

    replacements = {}
    for inputs, labels in xor_by_inputs.items():
        if len(labels) > 1:
            canonical = None
            for l in labels:
                if not is_output_label(l):
                    canonical = l
                    break
            if canonical is None:
                canonical = labels[0]

            for other in labels:
                if other != canonical and not is_output_label(other):
                    replacements[other] = canonical

    if not replacements:
        return gates

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
        optimized.append((label, resolve(a), resolve(b)))

    return optimized


def optimize_nand_to_identity(gates):
    """Merge equivalent NOT gates."""
    not_of = {}
    for label, a, b in gates:
        if a == b:
            not_of[label] = a
        elif a == 'CONST-1':
            not_of[label] = b
        elif b == 'CONST-1':
            not_of[label] = a

    inverts = {}
    for label, inv_of in not_of.items():
        inverts.setdefault(inv_of, []).append(label)

    replacements = {}
    for input_sig, labels in inverts.items():
        if len(labels) > 1:
            canonical = None
            for l in labels:
                if not is_output_label(l):
                    canonical = l
                    break
            if canonical is None:
                canonical = labels[0]

            for other in labels:
                if other != canonical and not is_output_label(other):
                    replacements[other] = canonical

    if not replacements:
        return gates

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
        optimized.append((label, resolve(a), resolve(b)))

    return optimized


def optimize_cleanup_copies(gates):
    """Remove unnecessary copy operations."""
    gate_map = {label: (a, b) for label, a, b in gates}

    use_count = {}
    for label, a, b in gates:
        use_count[a] = use_count.get(a, 0) + 1
        use_count[b] = use_count.get(b, 0) + 1

    not_gates = {}
    for label, a, b in gates:
        if a == b:
            not_gates[label] = a

    replacements = {}
    for label, a, b in gates:
        if a == b and a in not_gates:
            original = not_gates[a]
            intermediate = a
            if use_count.get(intermediate, 0) == 1:
                if not is_output_label(label):
                    replacements[label] = original

    if not replacements:
        return gates

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
        optimized.append((label, resolve(a), resolve(b)))

    return optimized


def run_optimization_pass(gates, const_values, pass_name, optimize_func, *args):
    """Run a single optimization pass and report results."""
    before = len(gates)

    if args:
        result = optimize_func(gates, *args)
        if isinstance(result, tuple):
            gates = result[0]
        else:
            gates = result
    else:
        gates = optimize_func(gates)

    after = len(gates)
    saved = before - after

    if saved > 0:
        print(f"  {pass_name}: {before:,} -> {after:,} (-{saved:,})")
    else:
        print(f"  {pass_name}: no change")

    return gates


def optimize_circuit(gates, const_values, max_iterations=10):
    """Run all optimization passes iteratively until convergence."""
    print(f"\nStarting optimization with {len(gates):,} gates")

    gates = rename_outputs(gates)

    for iteration in range(1, max_iterations + 1):
        print(f"\n--- Iteration {iteration} ---")
        initial_count = len(gates)

        gates = run_optimization_pass(gates, const_values, "CSE", optimize_cse)
        gates = run_optimization_pass(gates, const_values, "Share inverters", optimize_share_inverters)
        gates = run_optimization_pass(gates, const_values, "NAND to identity", optimize_nand_to_identity)
        gates = run_optimization_pass(gates, const_values, "XOR chain", optimize_xor_chain)
        gates = run_optimization_pass(gates, const_values, "XOR(0,x)=x", optimize_xor_with_zero)
        gates = run_optimization_pass(gates, const_values, "XOR(1,x)=NOT(x)", optimize_xor_with_one)
        gates = run_optimization_pass(gates, const_values, "Algebraic (x NAND !x)", optimize_algebraic)
        gates, known = optimize_constant_folding(gates, const_values)
        print(f"  Constant folding: applied")
        gates = run_optimization_pass(gates, const_values, "Dead code elimination", optimize_dead_code)
        gates = run_optimization_pass(gates, const_values, "Identity patterns", optimize_identity_patterns)
        gates = run_optimization_pass(gates, const_values, "Double NOT", optimize_double_not)
        gates = run_optimization_pass(gates, const_values, "AND(x,x)=x", optimize_and_simplification)
        gates = run_optimization_pass(gates, const_values, "OR(x,x)=x", optimize_or_simplification)
        gates = run_optimization_pass(gates, const_values, "Cleanup copies", optimize_cleanup_copies)
        gates = run_optimization_pass(gates, const_values, "Dead code (cleanup)", optimize_dead_code)

        final_count = len(gates)
        saved = initial_count - final_count

        print(f"\n  Iteration {iteration} total: {initial_count:,} -> {final_count:,} (-{saved:,})")

        if saved == 0:
            print("\nConverged - no more improvements possible")
            break

    return gates


def main():
    parser = argparse.ArgumentParser(description="Optimize NAND circuit")
    parser.add_argument("--nands", "-n", default="nands.txt",
                        help="Input NAND circuit file (default: nands.txt)")
    parser.add_argument("--inputs", "-i", action="append", default=None,
                        help="Input file(s) containing constant bit values")
    parser.add_argument("--output", "-o", default="nands-optimized-final.txt",
                        help="Output optimized NAND file (default: nands-optimized-final.txt)")
    args = parser.parse_args()

    print("=" * 60)
    print("NAND Circuit Optimizer")
    print("=" * 60)

    # Determine input files
    if args.inputs:
        input_files = args.inputs
    else:
        input_files = ["constants-bits.txt"]

    # Load inputs (constants)
    print(f"\nLoading constants from {input_files}...")
    const_values = load_inputs(input_files)
    print(f"  Loaded {len(const_values)} values")

    # Load circuit
    print(f"\nLoading circuit from {args.nands}...")
    gates = load_circuit(args.nands)
    initial_count = len(gates)
    print(f"  Loaded {initial_count:,} gates")

    # Run optimization
    gates = optimize_circuit(gates, const_values)

    final_count = len(gates)
    total_saved = initial_count - final_count
    reduction_pct = 100 * total_saved / initial_count if initial_count > 0 else 0

    print("\n" + "=" * 60)
    print("OPTIMIZATION COMPLETE")
    print("=" * 60)
    print(f"  Initial gates:  {initial_count:,}")
    print(f"  Final gates:    {final_count:,}")
    print(f"  Gates saved:    {total_saved:,} ({reduction_pct:.2f}%)")

    # Save result
    print(f"\nSaving to {args.output}...")
    save_circuit(args.output, gates)

    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
