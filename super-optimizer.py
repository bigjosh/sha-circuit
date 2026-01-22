#!/usr/bin/env python3
"""
Super aggressive NAND gate optimizer.

Uses multiple techniques including:
- Global CSE with hash consing
- Pattern-based rewriting
- Dead code elimination
- Constant propagation
"""

import argparse
from collections import defaultdict
import sys


class SuperOptimizer:
    def __init__(self, verbose=True):
        self.gates = []
        self.output_labels = set()
        self.verbose = verbose

    def log(self, msg):
        if self.verbose:
            print(msg, flush=True)

    def load(self, nands_file):
        """Load NAND gates from file."""
        self.gates = []
        with open(nands_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    label, a, b = line.split(',')
                    self.gates.append((label, a, b))

        self.output_labels = {label for label, _, _ in self.gates
                             if label.startswith('OUTPUT-')}
        return len(self.gates)

    def save(self, filename):
        """Save NAND gates to file."""
        with open(filename, 'w') as f:
            for label, a, b in self.gates:
                f.write(f"{label},{a},{b}\n")

    def global_cse_and_simplify(self):
        """Perform global CSE using hash consing with simplification."""
        # Build a canonical form for each gate
        # Two gates are equivalent if they compute the same function

        # We'll do this iteratively: assign each gate a canonical hash
        # based on its inputs, and merge equivalents

        eliminated_total = 0
        iteration = 0

        while True:
            iteration += 1

            # Build maps
            gate_map = {g[0]: (g[1], g[2]) for g in self.gates}

            # Compute canonical form for each gate
            # A NOT gate NAND(x,x) is NOT(x)
            # NAND(a,b) = NAND(b,a) so we canonicalize

            # Map: canonical_key -> first_label
            canon_to_label = {}
            replacements = {}

            # Also track NOT gates
            not_of = {}  # label -> what it's NOT of
            not_label = {}  # x -> label of NOT(x)

            for label, a, b in self.gates:
                # Resolve through replacements
                while a in replacements:
                    a = replacements[a]
                while b in replacements:
                    b = replacements[b]

                # Check for constant folding
                if a == 'CONST-0' or b == 'CONST-0':
                    if label not in self.output_labels:
                        replacements[label] = 'CONST-1'
                        continue

                if a == 'CONST-1' and b == 'CONST-1':
                    if label not in self.output_labels:
                        replacements[label] = 'CONST-0'
                        continue

                # Handle NAND(x, CONST-1) = NOT(x)
                if a == 'CONST-1' and b != 'CONST-1':
                    # This is NOT(b), check if we have it
                    if b in not_label:
                        if label not in self.output_labels:
                            replacements[label] = not_label[b]
                            continue
                    else:
                        not_label[b] = label
                        not_of[label] = b
                elif b == 'CONST-1' and a != 'CONST-1':
                    if a in not_label:
                        if label not in self.output_labels:
                            replacements[label] = not_label[a]
                            continue
                    else:
                        not_label[a] = label
                        not_of[label] = a

                # Check for NOT gate: NAND(x, x) = NOT(x)
                if a == b:
                    # This is NOT(a)
                    # Check for double negation
                    if a in not_of:
                        # NOT(NOT(x)) = x
                        original = not_of[a]
                        if label not in self.output_labels:
                            replacements[label] = original
                            continue

                    # Check if we already have NOT(a)
                    if a in not_label:
                        if label not in self.output_labels:
                            replacements[label] = not_label[a]
                            continue

                    not_of[label] = a
                    not_label[a] = label

                # Canonicalize key
                key = (min(a, b), max(a, b))

                if key in canon_to_label:
                    if label not in self.output_labels:
                        replacements[label] = canon_to_label[key]
                else:
                    canon_to_label[key] = label

            if not replacements:
                break

            # Apply replacements
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
                a = resolve(a)
                b = resolve(b)
                new_gates.append((label, a, b))

            eliminated = len(self.gates) - len(new_gates)
            self.gates = new_gates
            eliminated_total += eliminated

            self.log(f"  CSE iteration {iteration}: eliminated {eliminated}")

            if eliminated == 0:
                break

        return eliminated_total

    def dead_code_elimination(self):
        """Remove gates not contributing to outputs."""
        used = set(self.output_labels)

        for label, a, b in reversed(self.gates):
            if label in used:
                used.add(a)
                used.add(b)

        new_gates = [(l, a, b) for l, a, b in self.gates if l in used]
        eliminated = len(self.gates) - len(new_gates)
        self.gates = new_gates
        return eliminated

    def find_and_share_nands(self):
        """Find NAND(a,b) computations that could be shared."""
        # Look for cases where we compute NAND(a,b) multiple times
        # but with different labels

        nand_by_inputs = defaultdict(list)
        for label, a, b in self.gates:
            key = (min(a, b), max(a, b))
            nand_by_inputs[key].append(label)

        replacements = {}
        for key, labels in nand_by_inputs.items():
            if len(labels) > 1:
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

    def algebraic_simplifications(self):
        """Apply algebraic simplifications."""
        gate_map = {g[0]: (g[1], g[2]) for g in self.gates}

        # Find NOT gates
        not_of = {}
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

            # NAND(NOT(x), NOT(x)) = NOT(NOT(x)) = x (if x is primary input or CONST)
            if a == b and a in not_of:
                original = not_of[a]
                if label not in self.output_labels:
                    replacements[label] = original

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

    def reconvergent_path_optimization(self):
        """Optimize reconvergent paths where the same signal appears multiple times."""
        # This is a more sophisticated version of CSE
        # Look for gates where both inputs are derived from the same source

        gate_map = {g[0]: (g[1], g[2]) for g in self.gates}

        # Build reverse dependency map
        derived_from = defaultdict(set)  # label -> set of primary inputs it depends on

        # Find primary inputs (not computed by any gate)
        all_outputs = {g[0] for g in self.gates}
        primary_inputs = set()
        for label, a, b in self.gates:
            if a not in all_outputs:
                primary_inputs.add(a)
            if b not in all_outputs:
                primary_inputs.add(b)

        # Initialize with primary inputs
        for p in primary_inputs:
            derived_from[p] = {p}

        # Propagate (limited depth to avoid explosion)
        for label, a, b in self.gates:
            deps_a = derived_from.get(a, set())
            deps_b = derived_from.get(b, set())
            derived_from[label] = deps_a | deps_b

        # No direct optimization from this, but helps with analysis
        return 0

    def pass_renumber(self):
        """Renumber temporary labels sequentially."""
        counter = 0
        label_map = {}
        new_gates = []

        for label, a, b in self.gates:
            a = label_map.get(a, a)
            b = label_map.get(b, b)

            if label.startswith('OUTPUT-') or '-T' not in label:
                new_label = label
            else:
                counter += 1
                prefix = label.rsplit('-T', 1)[0]
                new_label = f"{prefix}-T{counter}"

            label_map[label] = new_label
            new_gates.append((new_label, a, b))

        self.gates = new_gates
        return 0

    def optimize(self):
        """Run all optimization passes until convergence."""
        total_eliminated = 0
        iteration = 0

        while True:
            iteration += 1
            start_count = len(self.gates)

            # Run optimization passes
            passes = [
                ('Global CSE', self.global_cse_and_simplify),
                ('Algebraic', self.algebraic_simplifications),
                ('Share NANDs', self.find_and_share_nands),
                ('Dead code', self.dead_code_elimination),
            ]

            for name, pass_fn in passes:
                before = len(self.gates)
                result = pass_fn()
                eliminated = before - len(self.gates)
                if eliminated > 0:
                    self.log(f"  {name}: eliminated {eliminated} gates")

            eliminated_this_round = start_count - len(self.gates)
            if eliminated_this_round == 0:
                break

            total_eliminated += eliminated_this_round
            self.log(f"  Round {iteration}: {eliminated_this_round} eliminated, {len(self.gates)} remaining")

        # Final cosmetic pass
        self.pass_renumber()

        return total_eliminated


def main():
    parser = argparse.ArgumentParser(description="Super NAND circuit optimizer")
    parser.add_argument("--input", "-i", default="nands-final.txt", help="Input file")
    parser.add_argument("--output", "-o", default="nands-super.txt", help="Output file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")
    args = parser.parse_args()

    optimizer = SuperOptimizer(verbose=not args.quiet)

    print(f"Loading {args.input}...")
    initial_count = optimizer.load(args.input)
    print(f"Initial gate count: {initial_count:,}")

    print("\nOptimizing...")
    optimizer.optimize()

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
