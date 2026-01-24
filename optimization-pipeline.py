#!/usr/bin/env python3
"""
SHA-256 NAND Circuit Optimization Pipeline

The recommended workflow for generating the most optimized circuit:

    python optimization-pipeline.py -v

This will:
1. Convert functions.txt -> NANDs using optimized primitives (MAJ=6, CH=4, FA=13)
2. Apply all optimization passes iteratively until convergence
3. Verify the result against reference SHA-256
4. Output to nands-optimized-final.txt

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
    python optimization-pipeline.py -v                    # Best flow: functions.txt -> optimized
    python optimization-pipeline.py -n nands.txt -v       # Optimize existing NAND file
    python optimization-pipeline.py -f functions.txt -i constants-bits.txt -o output.txt -v
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


# Constants for three-valued logic
FALSE = 0
TRUE = 1
UNKNOWN = 'X'


def is_output_label(label):
    """Check if a label is a circuit output (should not be replaced/deleted)."""
    if label.startswith("OUTPUT-"):
        return True
    # Also check for FINAL-H*-ADD-B* format (before renaming)
    # Output format: FINAL-H0-ADD-B0 through FINAL-H7-ADD-B31
    # Intermediate format: FINAL-H0-ADD-B0-T123
    if label.startswith("FINAL-H") and "-ADD-B" in label:
        # Check it's not an intermediate (has -T suffix)
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
    """Load input values from one or more input files.

    Each file should have lines in the format: label,value
    where value is 0, 1, or X.
    """
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


def simulate_circuit(gates, input_values, const_values):
    """Simulate circuit and return output values using three-valued logic."""
    values = {}
    values.update(const_values)
    values.update(input_values)

    for label, a, b in gates:
        a_val = values.get(a, FALSE)
        b_val = values.get(b, FALSE)
        values[label] = nand3(a_val, b_val)

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
    """Common Subexpression Elimination.

    Never replace output labels - they are the circuit's actual outputs.
    """
    seen = {}  # (min(a,b), max(a,b)) -> label
    replacements = {}
    optimized = []

    for label, a, b in gates:
        # Apply replacements to inputs first
        a_new = replacements.get(a, a)
        b_new = replacements.get(b, b)

        key = (min(a_new, b_new), max(a_new, b_new))

        if key in seen and not is_output_label(label):
            # This is a duplicate - replace with existing
            replacements[label] = seen[key]
        else:
            # Keep this gate (either new expression or it's an output)
            if key not in seen:
                seen[key] = label
            optimized.append((label, a_new, b_new))

    return optimized


def optimize_constant_folding(gates, const_values):
    """Fold constant expressions and propagate constant values.

    Handles three-valued logic (0, 1, X):
    - NAND(0, x) = 1 for any x (including X) - CAN fold
    - NAND(1, 1) = 0 - CAN fold
    - NAND(1, X) = X - CANNOT fold (X means unknown, gate still needed)
    - NAND(X, X) = X - CANNOT fold

    X values are NOT folded because they represent "unknown at optimization time"
    - the gate still performs computation at runtime.
    """
    known = dict(const_values)
    first_pass = []

    # First pass: evaluate constants
    for label, a, b in gates:
        a_val = known.get(a)
        b_val = known.get(b)

        # If either input is 0, output is 1 - can fold even with X
        if a_val == FALSE or b_val == FALSE:
            known[label] = TRUE
        elif a_val is not None and b_val is not None:
            # Both inputs are known (0, 1, or X)
            if a_val == TRUE and b_val == TRUE:
                # NAND(1,1) = 0 - can fold
                known[label] = FALSE
            elif a_val == UNKNOWN or b_val == UNKNOWN:
                # At least one is X, neither is 0
                # Result is X - do NOT fold, keep the gate
                first_pass.append((label, a, b))
            else:
                # Standard NAND with known 0/1 values
                known[label] = nand3(a_val, b_val)
        else:
            first_pass.append((label, a, b))

    # Second pass: replace references to folded constants (only 0 and 1, not X)
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
        if not is_output_label(label):
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
            if a == 'CONST-0' and not is_output_label(label):
                replacements[label] = b
            elif b == 'CONST-0' and not is_output_label(label):
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


def optimize_share_inverters(gates):
    """Share NOT gates computing the same thing.

    If multiple gates compute NOT(x), keep only one and redirect others.
    NOT is implemented as NAND(x, x) or NAND(x, CONST-1).
    """
    gate_map = {label: (a, b) for label, a, b in gates}

    # Find all NOT gates and group by what they invert
    not_of = {}  # input_signal -> [labels that are NOT of it]
    for label, a, b in gates:
        if a == b:
            # NAND(x, x) = NOT(x)
            not_of.setdefault(a, []).append(label)
        elif a == 'CONST-1':
            # NAND(CONST-1, x) = NOT(x)
            not_of.setdefault(b, []).append(label)
        elif b == 'CONST-1':
            # NAND(x, CONST-1) = NOT(x)
            not_of.setdefault(a, []).append(label)

    # For each input with multiple NOT gates, keep one canonical version
    replacements = {}
    for input_sig, labels in not_of.items():
        if len(labels) > 1:
            # Pick canonical (prefer non-output)
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


def optimize_algebraic(gates):
    """Apply algebraic simplifications.

    NAND(x, NOT(x)) = 1 (always true, since x AND NOT(x) = 0)
    """
    gate_map = {label: (a, b) for label, a, b in gates}

    # Find NOT gates
    not_of = {}  # label -> what it's the NOT of
    for label, a, b in gates:
        if a == b:
            not_of[label] = a
        elif a == 'CONST-1':
            not_of[label] = b
        elif b == 'CONST-1':
            not_of[label] = a

    replacements = {}
    for label, a, b in gates:
        # Check NAND(x, NOT(x)) = 1
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
        a_new = resolve(a)
        b_new = resolve(b)
        optimized.append((label, a_new, b_new))

    return optimized


def optimize_and_simplification(gates):
    """Optimize AND(x, x) = x patterns.

    AND is: NOT(NAND(a,b)) = NAND(NAND(a,b), NAND(a,b))
    If a == b, then NAND(a,a) = NOT(a), and AND(a,a) = NOT(NOT(a)) = a

    Pattern: NAND(t, t) where t = NAND(x, x)
    This is NOT(NOT(x)) = x
    """
    gate_map = {label: (a, b) for label, a, b in gates}

    replacements = {}
    for label, a, b in gates:
        if a == b and a in gate_map:
            inner_a, inner_b = gate_map[a]
            if inner_a == inner_b:
                # AND(x, x) = NOT(NOT(x)) = x
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
        a_new = resolve(a)
        b_new = resolve(b)
        optimized.append((label, a_new, b_new))

    return optimized


def optimize_or_simplification(gates):
    """Recognize OR gates and simplify OR(x, x) = x.

    OR(a,b) = NAND(NOT(a), NOT(b)) = NAND(NAND(a,a), NAND(b,b))
    If a == b, then OR(a,a) = a
    """
    gate_map = {label: (a, b) for label, a, b in gates}

    replacements = {}
    for label, a, b in gates:
        if a in gate_map and b in gate_map:
            a_inner_a, a_inner_b = gate_map[a]
            b_inner_a, b_inner_b = gate_map[b]

            # Check if both inputs are NOT gates (NAND(x,x))
            if a_inner_a == a_inner_b and b_inner_a == b_inner_b:
                # This is OR(a_inner_a, b_inner_a)
                if a_inner_a == b_inner_a:
                    # OR(x, x) = x
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
        a_new = resolve(a)
        b_new = resolve(b)
        optimized.append((label, a_new, b_new))

    return optimized


def optimize_double_not(gates):
    """More aggressive double negation elimination.

    Pattern: NOT(NOT(x)) = x where NOT can be:
    - NAND(x, x)
    - NAND(x, CONST-1)
    - NAND(CONST-1, x)
    """
    gate_map = {label: (a, b) for label, a, b in gates}

    # Find all NOT gates (any form)
    not_gates = {}  # label -> what it's NOT of
    for label, a, b in gates:
        if a == b:
            not_gates[label] = a
        elif a == 'CONST-1':
            not_gates[label] = b
        elif b == 'CONST-1':
            not_gates[label] = a

    replacements = {}
    for label, a, b in gates:
        # Check if this gate is a NOT
        inner = None
        if a == b:
            inner = a
        elif a == 'CONST-1':
            inner = b
        elif b == 'CONST-1':
            inner = a

        if inner and inner in not_gates:
            # This is NOT(NOT(original))
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
        a_new = resolve(a)
        b_new = resolve(b)
        optimized.append((label, a_new, b_new))

    return optimized


def optimize_xor_chain(gates):
    """Recognize and deduplicate XOR patterns.

    XOR(a,b) in NAND:
      t = NAND(a,b)
      x = NAND(a,t)
      y = NAND(b,t)
      out = NAND(x,y)

    If multiple XOR gates compute the same thing, replace duplicates.
    """
    gate_map = {label: (a, b) for label, a, b in gates}

    def identify_xor(label):
        """Return (a, b) if label is XOR(a,b), else None."""
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
            return (min(a, b), max(a, b))  # Canonicalize
        return None

    # Find all XOR outputs
    xor_outputs = {}  # label -> (a, b) canonical
    for label, _, _ in gates:
        xor_inputs = identify_xor(label)
        if xor_inputs:
            xor_outputs[label] = xor_inputs

    # Group by inputs to find duplicates
    xor_by_inputs = {}  # (a, b) -> [labels]
    for label, inputs in xor_outputs.items():
        xor_by_inputs.setdefault(inputs, []).append(label)

    # Replace duplicates with canonical version
    replacements = {}
    for inputs, labels in xor_by_inputs.items():
        if len(labels) > 1:
            # Pick canonical (prefer non-output)
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
        a_new = resolve(a)
        b_new = resolve(b)
        optimized.append((label, a_new, b_new))

    return optimized


def optimize_nand_to_identity(gates):
    """Merge equivalent NOT gates.

    NOT can be computed as:
    - NAND(x, x)
    - NAND(x, CONST-1)
    - NAND(CONST-1, x)

    If multiple gates compute NOT(x) using different forms, merge them.
    """
    gate_map = {label: (a, b) for label, a, b in gates}

    # Find all NOT gates and what they invert
    not_of = {}  # label -> what it's the NOT of
    for label, a, b in gates:
        if a == b:
            not_of[label] = a
        elif a == 'CONST-1':
            not_of[label] = b
        elif b == 'CONST-1':
            not_of[label] = a

    # Group by what they invert
    inverts = {}  # input_signal -> [labels]
    for label, inv_of in not_of.items():
        inverts.setdefault(inv_of, []).append(label)

    # Merge duplicates
    replacements = {}
    for input_sig, labels in inverts.items():
        if len(labels) > 1:
            # Pick canonical (prefer non-output)
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
        a_new = resolve(a)
        b_new = resolve(b)
        optimized.append((label, a_new, b_new))

    return optimized


def optimize_cleanup_copies(gates):
    """Remove unnecessary copy operations.

    Pattern: t = NOT(g), out = NOT(t) where out just copies g.
    If t is only used once (by this NOT), we can replace out with g.
    """
    gate_map = {label: (a, b) for label, a, b in gates}

    # Count usage of each label
    use_count = {}
    for label, a, b in gates:
        use_count[a] = use_count.get(a, 0) + 1
        use_count[b] = use_count.get(b, 0) + 1

    # Find NOT gates
    not_gates = {}
    for label, a, b in gates:
        if a == b:
            not_gates[label] = a

    replacements = {}
    for label, a, b in gates:
        if a == b and a in not_gates:
            original = not_gates[a]
            intermediate = a
            # If intermediate is only used once (by this gate)
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
        # Note: XOR optimizations must run BEFORE constant folding to find CONST-0/1 patterns
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
