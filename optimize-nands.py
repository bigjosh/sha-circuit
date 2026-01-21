#!/usr/bin/env python3
"""
NAND gate optimizer for SHA-256 circuit.

Applies multiple optimization passes to reduce gate count without altering function.

Usage:
    python optimize-nands.py
    python optimize-nands.py -i nands.txt -o nands-optimized.txt
"""

import argparse
import os
from collections import defaultdict


class NandOptimizer:
    def __init__(self):
        self.gates = []  # List of (label, a, b)
        self.output_labels = set()  # Labels that are circuit outputs

    def load(self, nands_file):
        """Load NAND gates from file."""
        self.gates = []
        with open(nands_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    label, a, b = line.split(',')
                    self.gates.append((label, a, b))

        # Identify output labels (OUTPUT-W*-B*)
        self.output_labels = {label for label, _, _ in self.gates
                             if label.startswith('OUTPUT-')}

        return len(self.gates)

    def save(self, filename):
        """Save NAND gates to file."""
        with open(filename, 'w') as f:
            for label, a, b in self.gates:
                f.write(f"{label},{a},{b}\n")

    def get_gate_map(self):
        """Build label -> (a, b) map from current gates."""
        return {label: (a, b) for label, a, b in self.gates}

    def apply_replacements(self, replacements):
        """Apply label replacements throughout the circuit."""
        if not replacements:
            return 0

        new_gates = []
        eliminated = 0
        for label, a, b in self.gates:
            # Skip gates that have been replaced
            if label in replacements:
                eliminated += 1
                continue

            # Apply replacements to inputs
            a = replacements.get(a, a)
            b = replacements.get(b, b)
            new_gates.append((label, a, b))

        self.gates = new_gates
        return eliminated

    def pass_canonicalize(self):
        """Canonicalize gate inputs (sort a, b alphabetically for consistent hashing)."""
        new_gates = []
        for label, a, b in self.gates:
            if a > b:
                a, b = b, a
            new_gates.append((label, a, b))
        self.gates = new_gates
        return 0

    def pass_cse(self):
        """Common subexpression elimination - merge identical gates."""
        gate_map = self.get_gate_map()

        # Map (a, b) -> first label that computes it
        expr_to_label = {}
        replacements = {}

        for label, a, b in self.gates:
            # Apply any pending replacements to inputs
            while a in replacements:
                a = replacements[a]
            while b in replacements:
                b = replacements[b]

            # Canonicalize for lookup
            key = (min(a, b), max(a, b))

            if key in expr_to_label:
                # This expression already computed
                existing = expr_to_label[key]
                # Don't replace output labels
                if label not in self.output_labels:
                    replacements[label] = existing
            else:
                expr_to_label[key] = label

        return self.apply_replacements(replacements)

    def pass_dead_code(self):
        """Remove gates whose outputs are never used."""
        gate_map = self.get_gate_map()

        # Find all used labels (working backward from outputs)
        used = set(self.output_labels)

        # Work backward through gates to find all dependencies
        for label, a, b in reversed(self.gates):
            if label in used:
                used.add(a)
                used.add(b)

        # Keep only used gates
        new_gates = [(label, a, b) for label, a, b in self.gates if label in used]
        eliminated = len(self.gates) - len(new_gates)
        self.gates = new_gates
        return eliminated

    def pass_double_negation(self):
        """Eliminate double negation: NOT(NOT(x)) = x.

        NAND(x,x) = NOT(x)
        If we have: t = NAND(x,x) and out = NAND(t,t), then out = x
        We can replace 'out' with 'x' and eliminate the out gate.
        We keep 't' since it may be used elsewhere or 'x' might need it.
        """
        gate_map = self.get_gate_map()

        # Find all NOT gates: where a == b
        not_gates = {}  # label -> input it's the NOT of
        for label, a, b in self.gates:
            if a == b:
                not_gates[label] = a

        # Find double-NOT patterns: NAND(t,t) where t is NAND(x,x)
        # Only replace if x is NOT a gate (i.e., it's an input/constant)
        # OR if x is a gate that has other uses
        replacements = {}
        for label, a, b in self.gates:
            if a == b and a in not_gates:
                # This is NOT(NOT(x)) = x
                original = not_gates[a]
                # Only safe to replace if original is an input (not a gate)
                # or if it's a gate that will survive (has other users)
                if original not in gate_map:
                    # original is an input/constant - safe to replace
                    if label not in self.output_labels:
                        replacements[label] = original

        return self.apply_replacements(replacements)

    def pass_redundant_copy(self):
        """Remove redundant copy chains where double-NOT copies are unnecessary.

        If we have: t = NOT(x), out = NOT(t) = x, and out is only used as
        an input to gates that could use x directly, we can eliminate the copy.
        """
        gate_map = self.get_gate_map()

        # Count uses of each gate
        use_count = defaultdict(int)
        for label, a, b in self.gates:
            use_count[a] += 1
            use_count[b] += 1
        for label in self.output_labels:
            use_count[label] += 1

        # Find NOT gates
        not_gates = {}
        for label, a, b in self.gates:
            if a == b:
                not_gates[label] = a

        # Find double-NOT (copy) patterns where intermediate NOT is only used once
        replacements = {}
        gates_to_remove = set()
        for label, a, b in self.gates:
            if a == b and a in not_gates:
                # label = NOT(NOT(original))
                original = not_gates[a]
                intermediate = a
                # If intermediate is only used by this gate, and original is a gate
                if use_count[intermediate] == 1 and original in gate_map:
                    # We can replace label with original and remove intermediate
                    if label not in self.output_labels:
                        replacements[label] = original
                        gates_to_remove.add(intermediate)

        if not replacements:
            return 0

        new_gates = []
        for label, a, b in self.gates:
            if label in replacements or label in gates_to_remove:
                continue
            a = replacements.get(a, a)
            b = replacements.get(b, b)
            new_gates.append((label, a, b))

        eliminated = len(self.gates) - len(new_gates)
        self.gates = new_gates
        return eliminated

    def pass_constant_folding(self):
        """Fold constant expressions involving CONST-0 and CONST-1."""
        # NAND(0, x) = 1
        # NAND(1, 1) = 0
        # NAND(0, 0) = 1

        known = {'CONST-0': False, 'CONST-1': True}
        replacements = {}

        for label, a, b in self.gates:
            # Resolve through any existing replacements
            ra = replacements.get(a, a)
            rb = replacements.get(b, b)

            a_val = known.get(ra)
            b_val = known.get(rb)

            if a_val == False or b_val == False:
                # NAND(0, x) = 1
                if label not in self.output_labels:
                    replacements[label] = 'CONST-1'
                    known[label] = True
            elif a_val == True and b_val == True:
                # NAND(1, 1) = 0
                if label not in self.output_labels:
                    replacements[label] = 'CONST-0'
                    known[label] = False

        return self.apply_replacements(replacements)

    def pass_identity_and(self):
        """Simplify NAND(x, CONST-1) = NOT(x)."""
        # If we have NAND(x, 1) followed by NAND(result, result), that's just NOT(NOT(x)) = x
        # This is handled by double_negation after we identify the NOT
        return 0

    def pass_algebraic(self):
        """Apply algebraic simplifications: NAND(x, NOT(x)) = 1."""
        gate_map = self.get_gate_map()

        # Find NOT gates
        not_of = {}  # label -> what it's the NOT of
        for label, a, b in self.gates:
            if a == b:
                not_of[label] = a

        replacements = {}
        for label, a, b in self.gates:
            # NAND(x, NOT(x)) = 1
            if a in not_of and not_of[a] == b:
                if label not in self.output_labels:
                    replacements[label] = 'CONST-1'
            elif b in not_of and not_of[b] == a:
                if label not in self.output_labels:
                    replacements[label] = 'CONST-1'

        return self.apply_replacements(replacements)

    def pass_share_inverters(self):
        """Share NOT gates - if multiple gates compute NOT(x), keep only one."""
        gate_map = self.get_gate_map()

        # Find all NOT gates grouped by input
        not_gates = defaultdict(list)  # input -> [labels that compute NOT(input)]
        for label, a, b in self.gates:
            if a == b:
                not_gates[a].append(label)

        # For inputs with multiple NOT gates, keep the first and replace others
        replacements = {}
        for input_signal, labels in not_gates.items():
            if len(labels) > 1:
                # Keep the first non-output one, or just the first if all are outputs
                canonical = None
                for l in labels:
                    if l not in self.output_labels:
                        canonical = l
                        break
                if canonical is None:
                    canonical = labels[0]

                for other in labels:
                    if other != canonical and other not in self.output_labels:
                        replacements[other] = canonical

        return self.apply_replacements(replacements)

    def pass_renumber(self):
        """Renumber temporary labels to be sequential (cosmetic only)."""
        counter = 0
        label_map = {}
        new_gates = []

        for label, a, b in self.gates:
            # Map inputs
            a = label_map.get(a, a)
            b = label_map.get(b, b)

            # Map output label
            if label.startswith('OUTPUT-') or not ('-T' in label):
                new_label = label
            else:
                counter += 1
                prefix = label.rsplit('-T', 1)[0]
                new_label = f"{prefix}-T{counter}"

            label_map[label] = new_label
            new_gates.append((new_label, a, b))

        self.gates = new_gates
        return 0

    def optimize(self, verbose=True):
        """Run all optimization passes until no more improvements."""
        total_eliminated = 0
        iteration = 0

        while True:
            iteration += 1
            eliminated_this_round = 0

            # Canonicalize first for consistent CSE
            self.pass_canonicalize()

            # Run optimization passes in order
            passes = [
                ('Constant folding', self.pass_constant_folding),
                ('Algebraic', self.pass_algebraic),
                ('Double negation', self.pass_double_negation),
                ('Redundant copy', self.pass_redundant_copy),
                ('Share inverters', self.pass_share_inverters),
                ('CSE', self.pass_cse),
                ('Dead code', self.pass_dead_code),
            ]

            for name, pass_fn in passes:
                before = len(self.gates)
                pass_fn()
                eliminated = before - len(self.gates)
                if eliminated > 0:
                    eliminated_this_round += eliminated
                    if verbose:
                        print(f"  {name}: eliminated {eliminated} gates")

            if eliminated_this_round == 0:
                break

            total_eliminated += eliminated_this_round
            if verbose:
                print(f"  Iteration {iteration}: {eliminated_this_round} gates eliminated, {len(self.gates)} remaining")

        # Final cosmetic pass
        self.pass_renumber()

        return total_eliminated


def main():
    parser = argparse.ArgumentParser(description="Optimize NAND circuit")
    parser.add_argument("--input", "-i", default="nands.txt", help="Input file")
    parser.add_argument("--output", "-o", default="nands-optimized.txt", help="Output file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")
    args = parser.parse_args()

    optimizer = NandOptimizer()

    print(f"Loading {args.input}...")
    initial_count = optimizer.load(args.input)
    print(f"Initial gate count: {initial_count:,}")

    print("\nOptimizing...")
    optimizer.optimize(verbose=not args.quiet)

    final_count = len(optimizer.gates)
    reduction = initial_count - final_count
    percent = (reduction / initial_count) * 100 if initial_count > 0 else 0

    print(f"\nOptimization complete!")
    print(f"  Initial gates:  {initial_count:,}")
    print(f"  Final gates:    {final_count:,}")
    print(f"  Eliminated:     {reduction:,} ({percent:.2f}%)")

    optimizer.save(args.output)
    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
