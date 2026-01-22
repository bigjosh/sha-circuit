#!/usr/bin/env python3
"""
Constant propagation optimizer.

Loads actual constant values from constants-bits.txt and propagates them
through the circuit, applying these NAND simplifications:
  - NAND(0, x) = 1
  - NAND(x, 0) = 1
  - NAND(1, 1) = 0

This catches optimizations missed by basic constant folding which only
knows about CONST-0 and CONST-1 labels.

Usage:
    python constant-propagation.py
    python constant-propagation.py -i nands.txt -o nands-const-prop.txt
"""

import argparse
from collections import defaultdict


class ConstantPropagator:
    def __init__(self, verbose=True):
        self.gates = []
        self.output_labels = set()
        self.verbose = verbose
        self.constant_values = {}  # label -> True/False

    def log(self, msg):
        if self.verbose:
            print(msg, flush=True)

    def load_constants(self, constants_file):
        """Load constant bit values from file."""
        self.constant_values = {}

        # Always include these
        self.constant_values['CONST-0'] = False
        self.constant_values['CONST-1'] = True

        try:
            with open(constants_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split(',')
                        if len(parts) == 2:
                            label, value = parts
                            self.constant_values[label] = (value == '1')
        except FileNotFoundError:
            self.log(f"Warning: {constants_file} not found, using CONST-0/CONST-1 only")

        self.log(f"Loaded {len(self.constant_values):,} constant values")

        # Debug: verify CONST-0 and CONST-1
        self.log(f"  CONST-0 = {self.constant_values.get('CONST-0')}")
        self.log(f"  CONST-1 = {self.constant_values.get('CONST-1')}")

        # Count values
        zeros = sum(1 for v in self.constant_values.values() if v is False)
        ones = sum(1 for v in self.constant_values.values() if v is True)
        self.log(f"  {zeros} constants with value 0, {ones} with value 1")

    def load_circuit(self, nands_file):
        """Load NAND circuit."""
        self.gates = []
        with open(nands_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(',')
                    if len(parts) == 3:
                        label, a, b = parts
                        self.gates.append((label, a, b))

        self.output_labels = {label for label, _, _ in self.gates
                            if label.startswith('OUTPUT-')}
        return len(self.gates)

    def save(self, filename):
        """Save circuit to file."""
        with open(filename, 'w') as f:
            for label, a, b in self.gates:
                f.write(f"{label},{a},{b}\n")

    def propagate_constants(self):
        """Propagate constant values through circuit."""
        known = dict(self.constant_values)  # Start with loaded constants
        replacements = {}
        changed = True
        iterations = 0

        # Track statistics
        const_0_count = 0
        const_1_count = 0

        while changed:
            iterations += 1
            changed = False
            new_known = 0

            for label, a, b in self.gates:
                if label in replacements or label in known:
                    continue  # Already processed

                # Resolve inputs through replacements
                while a in replacements:
                    a = replacements[a]
                while b in replacements:
                    b = replacements[b]

                a_val = known.get(a)
                b_val = known.get(b)

                # Apply NAND constant folding rules
                if a_val is False or b_val is False:
                    # NAND(x, 0) = 1 or NAND(0, x) = 1
                    if label not in self.output_labels:
                        replacements[label] = 'CONST-1'
                        known[label] = True
                        changed = True
                        new_known += 1
                        const_1_count += 1
                elif a_val is True and b_val is True:
                    # NAND(1, 1) = 0
                    if label not in self.output_labels:
                        replacements[label] = 'CONST-0'
                        known[label] = False
                        changed = True
                        new_known += 1
                        const_0_count += 1
                elif a_val is not None and b_val is not None:
                    # Both known, compute result
                    result = not (a_val and b_val)
                    known[label] = result
                    # Don't replace, but now we know the value for downstream

            if new_known > 0:
                self.log(f"  Iteration {iterations}: discovered {new_known} constant gates")
            else:
                self.log(f"  Iteration {iterations}: discovered 0 new constants (converged)")

        self.log(f"Total constant propagation iterations: {iterations}")
        self.log(f"Found {len(replacements):,} gates that can be replaced with constants")
        self.log(f"  Replacing with CONST-0: {const_0_count:,}")
        self.log(f"  Replacing with CONST-1: {const_1_count:,}")

        return replacements

    def apply_replacements(self, replacements):
        """Apply constant replacements to circuit."""
        if not replacements:
            return 0

        def resolve(x):
            visited = set()
            orig_x = x
            while x in replacements and x not in visited:
                visited.add(x)
                x = replacements[x]
            return x

        # Debug: check for CONST-0 in replacements
        const_0_replacements = [k for k, v in replacements.items() if v == 'CONST-0']
        const_1_replacements = [k for k, v in replacements.items() if v == 'CONST-1']
        self.log(f"  Debug: {len(const_0_replacements)} gates -> CONST-0")
        self.log(f"  Debug: {len(const_1_replacements)} gates -> CONST-1")

        # Check if ALL gates that would use CONST-0 are themselves replaced
        if const_0_replacements:
            total_users = 0
            replaced_users = 0
            for const_0_gate in const_0_replacements[:10]:  # Check first 10
                users = [label for label, a, b in self.gates if a == const_0_gate or b == const_0_gate]
                total_users += len(users)
                replaced_users += sum(1 for u in users if u in replacements)

            self.log(f"    Checked {min(10, len(const_0_replacements))} CONST-0 gates: {total_users} total users, {replaced_users} also replaced")
            if total_users > 0 and replaced_users == total_users:
                self.log(f"    ALL users of CONST-0 gates are themselves replaced! This explains why CONST-0 doesn't appear.")

        new_gates = []
        const_0_uses = 0
        const_1_uses = 0

        for label, a, b in self.gates:
            if label in replacements:
                continue  # Skip gates being replaced

            new_a = resolve(a)
            new_b = resolve(b)

            if new_a == 'CONST-0' or new_b == 'CONST-0':
                const_0_uses += 1
            if new_a == 'CONST-1' or new_b == 'CONST-1':
                const_1_uses += 1

            new_gates.append((label, new_a, new_b))

        self.log(f"  Debug: After replacement, {const_0_uses} gates use CONST-0")
        self.log(f"  Debug: After replacement, {const_1_uses} gates use CONST-1")

        eliminated = len(self.gates) - len(new_gates)
        self.gates = new_gates
        return eliminated

    def pass_dead_code(self):
        """Remove unused gates."""
        used = set(self.output_labels)

        for label, a, b in reversed(self.gates):
            if label in used:
                used.add(a)
                used.add(b)

        new_gates = [(l, a, b) for l, a, b in self.gates if l in used]
        eliminated = len(self.gates) - len(new_gates)
        self.gates = new_gates
        return eliminated

    def pass_cse(self):
        """Common subexpression elimination."""
        expr_to_label = {}
        replacements = {}

        for label, a, b in self.gates:
            while a in replacements:
                a = replacements[a]
            while b in replacements:
                b = replacements[b]

            key = (min(a, b), max(a, b))

            if key in expr_to_label:
                existing = expr_to_label[key]
                if label not in self.output_labels:
                    replacements[label] = existing
            else:
                expr_to_label[key] = label

        if not replacements:
            return 0

        def resolve(x):
            visited = set()
            while x in replacements and x not in visited:
                visited.add(x)
                x = replacements[x]
            return x

        new_gates = []
        for label, a, b in self.gates:
            if label in replacements:
                continue
            new_gates.append((label, resolve(a), resolve(b)))

        eliminated = len(self.gates) - len(new_gates)
        self.gates = new_gates
        return eliminated

    def optimize(self):
        """Run constant propagation optimization."""
        initial = len(self.gates)

        # Propagate constants
        self.log("\nPropagating constants...")
        replacements = self.propagate_constants()

        # Apply replacements
        if replacements:
            self.log("\nApplying constant replacements...")
            eliminated = self.apply_replacements(replacements)
            self.log(f"  Eliminated {eliminated:,} gates")

        # Clean up with standard passes
        self.log("\nCleaning up...")
        cse = self.pass_cse()
        if cse:
            self.log(f"  CSE: eliminated {cse:,}")

        dead = self.pass_dead_code()
        if dead:
            self.log(f"  Dead code: eliminated {dead:,}")

        final = len(self.gates)
        total_eliminated = initial - final

        return total_eliminated


def main():
    parser = argparse.ArgumentParser(description="Constant propagation optimizer")
    parser.add_argument("--input", "-i", default="ga-nands.txt",
                        help="Input NAND file")
    parser.add_argument("--constants", "-c", default="constants-bits.txt",
                        help="Constants file")
    parser.add_argument("--output", "-o", default="nands-const-prop.txt",
                        help="Output file")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress output")
    args = parser.parse_args()

    propagator = ConstantPropagator(verbose=not args.quiet)

    print(f"Loading constants from {args.constants}...")
    propagator.load_constants(args.constants)

    print(f"Loading circuit from {args.input}...")
    initial_count = propagator.load_circuit(args.input)
    print(f"  Initial gates: {initial_count:,}")

    eliminated = propagator.optimize()

    final_count = len(propagator.gates)
    percent = (eliminated / initial_count) * 100 if initial_count > 0 else 0

    print(f"\nOptimization complete!")
    print(f"  Initial gates:  {initial_count:,}")
    print(f"  Final gates:    {final_count:,}")
    print(f"  Eliminated:     {eliminated:,} ({percent:.2f}%)")

    propagator.save(args.output)
    print(f"\nSaved to {args.output}")

    return 0


if __name__ == "__main__":
    exit(main())
