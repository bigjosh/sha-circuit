#!/usr/bin/env python3
"""
SHA-256 NAND Circuit Optimization Pipeline

A comprehensive workflow that takes constants-bits.txt and the circuit definition,
applies all optimization strategies, and produces an optimized nands-bits.txt file.

Optimization stages:
1. Initial conversion with optimized primitives (MAJ=6, CH=9, Full Adder=13)
2. Basic optimizations (CSE, constant folding, dead code elimination)
3. Advanced pattern matching optimizations
4. XOR(0, x) = x sharing optimization
5. XOR(1, x) = NOT(x) optimization
6. Identity pattern elimination: NOT(NOT(x)) = x
7. Constant propagation
8. Iterative refinement until convergence

Usage:
    python optimization-pipeline.py -f functions.txt -c constants-bits.txt -o nands-optimized.txt
"""

import argparse
import os
import shutil
import subprocess
import sys
import random
import hashlib


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


def load_inputs(filenames):
    """Load input values from one or more input files.

    Each file should have lines in the format: label,value
    where value is 0 or 1.
    """
    values = {'CONST-0': 0, 'CONST-1': 1}
    for filename in filenames:
        try:
            with open(filename) as f:
                for line in f:
                    if line.strip():
                        parts = line.strip().split(',')
                        if len(parts) >= 2:
                            values[parts[0]] = int(parts[1])
        except FileNotFoundError:
            pass
    return values


def simulate_circuit(gates, input_values, const_values):
    """Simulate circuit and return output values."""
    values = {}
    values.update(const_values)
    values.update(input_values)

    for label, a, b in gates:
        a_val = values.get(a, 0)
        b_val = values.get(b, 0)
        values[label] = 1 - (a_val & b_val)  # NAND

    return values


def verify_circuit_file(nands_file, input_files, num_tests=5):
    """Verify circuit using the external verify-circuit.py script."""
    cmd = [sys.executable, "verify-circuit.py", "-n", nands_file, "-t", str(num_tests)]
    for input_file in input_files:
        cmd.extend(["-i", input_file])
    result = subprocess.run(cmd, capture_output=True, text=True)
    success = result.returncode == 0
    output = result.stdout + result.stderr
    return success, output.strip()


# ============== OPTIMIZATION PASSES ==============

def optimize_cse(gates):
    """Common Subexpression Elimination."""
    seen = {}  # (min(a,b), max(a,b)) -> label
    replacements = {}
    optimized = []

    for label, a, b in gates:
        key = (min(a, b), max(a, b))

        if key in seen:
            replacements[label] = seen[key]
        else:
            seen[key] = label
            # Apply replacements to inputs
            a_new = replacements.get(a, a)
            b_new = replacements.get(b, b)
            optimized.append((label, a_new, b_new))

    return optimized


def optimize_constant_folding(gates, const_values):
    """Fold constant expressions and propagate constant values."""
    known = dict(const_values)
    first_pass = []

    # First pass: evaluate constants
    for label, a, b in gates:
        a_val = known.get(a)
        b_val = known.get(b)

        if a_val is not None and b_val is not None:
            # Both inputs are constants
            result = 1 - (a_val & b_val)
            known[label] = result
        elif a_val == 0 or b_val == 0:
            # NAND(x, 0) = 1
            known[label] = 1
        else:
            first_pass.append((label, a, b))

    # Second pass: replace references to folded constants with CONST-0 or CONST-1
    optimized = []
    for label, a, b in first_pass:
        a_new = a
        b_new = b

        if a in known:
            a_new = f"CONST-{known[a]}"
        if b in known:
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
    """Remove NOT(NOT(x)) = x patterns.

    Pattern: NAND(CONST-1, NAND(CONST-1, x)) = NOT(NOT(x)) = x
    """
    gate_map = {label: (a, b) for label, a, b in gates}

    replacements = {}

    for label, a, b in gates:
        # Look for NAND(CONST-1, inner) or NAND(inner, CONST-1)
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

        # Found: label = NOT(NOT(x)) = x
        if not label.startswith("OUTPUT-"):
            replacements[label] = x

    if not replacements:
        return gates

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
        a_new = resolve(a)
        b_new = resolve(b)
        optimized.append((label, a_new, b_new))

    return optimized


def optimize_xor_with_zero(gates):
    """Optimize XOR(x, 0) = x patterns.

    XOR structure: NAND(NAND(a, t), NAND(b, t)) where t = NAND(a, b)
    If one input is CONST-0, the XOR simplifies to identity.
    """
    gate_map = {label: (a, b) for label, a, b in gates}

    def identify_xor(label):
        """Return (a, b) if label is XOR(a, b), else None."""
        if label not in gate_map:
            return None
        x, y = gate_map[label]
        if x not in gate_map or y not in gate_map:
            return None

        x_a, x_b = gate_map[x]
        y_a, y_b = gate_map[y]

        # Find shared input t
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

    # Find XOR(x, CONST-0) patterns
    replacements = {}

    for label, _, _ in gates:
        xor_inputs = identify_xor(label)
        if xor_inputs:
            a, b = xor_inputs
            if a == 'CONST-0' and not label.startswith("OUTPUT-"):
                replacements[label] = b
            elif b == 'CONST-0' and not label.startswith("OUTPUT-"):
                replacements[label] = a

    if not replacements:
        return gates

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
        a_new = resolve(a)
        b_new = resolve(b)
        optimized.append((label, a_new, b_new))

    return optimized


def optimize_xor_with_one(gates):
    """Optimize XOR(x, CONST-1) = NOT(x) patterns.

    XOR with 1 is equivalent to NOT, saving 3 NANDs per occurrence.
    """
    gate_map = {label: (a, b) for label, a, b in gates}

    def identify_xor(label):
        """Return (a, b, intermediates) if label is XOR(a,b), else None."""
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

    # Find XOR(CONST-1, x) patterns
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

    # Build new circuit with NOT gates replacing XORs
    label_mapping = {old: new for old, (_, new) in xor_replacements.items()}

    def resolve(label):
        return label_mapping.get(label, label)

    optimized = []
    for label, a, b in gates:
        if label in xor_replacements:
            input_val, new_label = xor_replacements[label]
            optimized.append((new_label, input_val, input_val))
        else:
            a_new = resolve(a)
            b_new = resolve(b)
            optimized.append((label, a_new, b_new))

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

    # First, rename outputs to standard format
    gates = rename_outputs(gates)

    for iteration in range(1, max_iterations + 1):
        print(f"\n--- Iteration {iteration} ---")
        initial_count = len(gates)

        # Run all optimization passes
        gates = run_optimization_pass(gates, const_values, "CSE", optimize_cse)
        gates, known = optimize_constant_folding(gates, const_values)
        print(f"  Constant folding: applied")
        gates = run_optimization_pass(gates, const_values, "Dead code elimination", optimize_dead_code)
        gates = run_optimization_pass(gates, const_values, "Identity patterns", optimize_identity_patterns)
        gates = run_optimization_pass(gates, const_values, "XOR(0,x)=x", optimize_xor_with_zero)
        gates = run_optimization_pass(gates, const_values, "XOR(1,x)=NOT(x)", optimize_xor_with_one)
        gates = run_optimization_pass(gates, const_values, "Dead code (cleanup)", optimize_dead_code)

        final_count = len(gates)
        saved = initial_count - final_count

        print(f"\n  Iteration {iteration} total: {initial_count:,} -> {final_count:,} (-{saved:,})")

        if saved == 0:
            print("\nConverged - no more improvements possible")
            break

    return gates


# ============== MAIN PIPELINE ==============

def main():
    parser = argparse.ArgumentParser(description="SHA-256 NAND Circuit Optimization Pipeline")
    parser.add_argument("--functions", "-f", default="functions.txt",
                        help="Input functions file")
    parser.add_argument("--inputs", "-i", action="append", default=None,
                        help="Input file(s) containing constant bit values (can be specified multiple times)")
    parser.add_argument("--input-nands", "-n", default=None,
                        help="Skip conversion, start from existing NAND file")
    parser.add_argument("--output", "-o", default="nands-optimized-final.txt",
                        help="Output optimized NAND file")
    parser.add_argument("--verify", "-v", action="store_true",
                        help="Verify circuit correctness")
    parser.add_argument("--tests", "-t", type=int, default=5,
                        help="Number of verification tests")
    args = parser.parse_args()

    print("=" * 60)
    print("SHA-256 NAND Circuit Optimization Pipeline")
    print("=" * 60)

    # Determine input files
    if args.inputs:
        input_files = args.inputs
    else:
        input_files = ["constants-bits.txt"]

    # Load inputs (constants)
    print(f"\nLoading inputs from {input_files}...")
    const_values = load_inputs(input_files)
    print(f"  Loaded {len(const_values)} values")

    # Get initial circuit
    if args.input_nands:
        print(f"\nLoading existing NAND circuit from {args.input_nands}...")
        gates = load_circuit(args.input_nands)
        print(f"  Loaded {len(gates):,} gates")
    else:
        # Convert from functions
        print(f"\nConverting {args.functions} to NANDs...")
        temp_nands = "temp_converted_nands.txt"
        result = subprocess.run(
            [sys.executable, "optimized-converter.py", "-i", args.functions, "-o", temp_nands],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Conversion failed: {result.stderr}")
            return 1

        gates = load_circuit(temp_nands)
        print(f"  Generated {len(gates):,} gates")
        os.remove(temp_nands)

    initial_count = len(gates)

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

    # Verify if requested
    if args.verify:
        print(f"\nVerifying circuit ({args.tests} tests)...")
        success, output = verify_circuit_file(args.output, input_files, args.tests)
        for line in output.split('\n'):
            if line.strip():
                print(f"  {line}")
        if not success:
            return 1

    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
