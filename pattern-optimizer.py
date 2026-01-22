#!/usr/bin/env python3
"""
Pattern-based NAND optimizer that recognizes high-level structures
like MAJ and CH and replaces them with more efficient implementations.

The MAJ function using XOR form takes 14 NANDs per bit.
Using OR form it takes only 6 NANDs per bit.

Similarly, other SHA-256 patterns may be optimizable.
"""

import argparse
from collections import defaultdict
import sys


class PatternOptimizer:
    def __init__(self, verbose=True):
        self.gates = []
        self.output_labels = set()
        self.verbose = verbose
        self.counter = 0

    def log(self, msg):
        if self.verbose:
            print(msg, flush=True)

    def temp_label(self, prefix):
        self.counter += 1
        return f"{prefix}-OPT{self.counter}"

    def load(self, nands_file):
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
        with open(filename, 'w') as f:
            for label, a, b in self.gates:
                f.write(f"{label},{a},{b}\n")

    def analyze_patterns(self):
        """Analyze the circuit to find optimizable patterns."""
        gate_map = {g[0]: (g[1], g[2]) for g in self.gates}

        # Find NOT gates
        not_of = {}
        for label, a, b in self.gates:
            if a == b:
                not_of[label] = a

        # Find AND gates: NOT(NAND(a,b))
        and_gates = {}  # label -> (a, b)
        for label, a, b in self.gates:
            if a == b and a in gate_map:
                inner_a, inner_b = gate_map[a]
                if inner_a != inner_b:  # inner is NAND, not NOT
                    and_gates[label] = (inner_a, inner_b)

        # Find XOR gates
        xor_gates = {}
        for label, p, q in self.gates:
            if p not in gate_map or q not in gate_map:
                continue
            p_a, p_b = gate_map[p]
            q_a, q_b = gate_map[q]

            common = None
            a_cand = None
            b_cand = None

            if p_b == q_b:
                common, a_cand, b_cand = p_b, p_a, q_a
            elif p_b == q_a:
                common, a_cand, b_cand = p_b, p_a, q_b
            elif p_a == q_b:
                common, a_cand, b_cand = p_a, p_b, q_a
            elif p_a == q_a:
                common, a_cand, b_cand = p_a, p_b, q_b

            if common and common in gate_map:
                t_a, t_b = gate_map[common]
                if set([t_a, t_b]) == set([a_cand, b_cand]):
                    xor_gates[label] = (min(a_cand, b_cand), max(a_cand, b_cand))

        self.log(f"Found {len(not_of)} NOT gates")
        self.log(f"Found {len(and_gates)} AND gates")
        self.log(f"Found {len(xor_gates)} XOR gates")

        return not_of, and_gates, xor_gates

    def find_maj_patterns(self, and_gates, xor_gates):
        """Find MAJ patterns: XOR(XOR(AND(a,b), AND(a,c)), AND(b,c)).

        Returns list of (maj_label, a, b, c, gates_involved)
        """
        gate_map = {g[0]: (g[1], g[2]) for g in self.gates}
        maj_patterns = []

        # Reverse map: what label computes AND(x,y)?
        and_by_inputs = {}
        for label, (a, b) in and_gates.items():
            key = (min(a, b), max(a, b))
            and_by_inputs[key] = label

        # For each XOR gate, check if it's the final MAJ XOR
        # MAJ final = XOR(intermediate, AND(b,c))
        # intermediate = XOR(AND(a,b), AND(a,c))

        for maj_cand, (xor_in1, xor_in2) in xor_gates.items():
            # Check if one input is an AND and the other is an XOR
            if xor_in1 in and_gates and xor_in2 in xor_gates:
                bc_and_label = xor_in1
                intermediate = xor_in2
            elif xor_in2 in and_gates and xor_in1 in xor_gates:
                bc_and_label = xor_in2
                intermediate = xor_in1
            else:
                continue

            # Get the AND inputs: should be (b, c)
            b, c = and_gates[bc_and_label]

            # Check if intermediate is XOR(AND(a,b), AND(a,c))
            inter_in1, inter_in2 = xor_gates[intermediate]

            if inter_in1 not in and_gates or inter_in2 not in and_gates:
                continue

            ab_a, ab_b = and_gates[inter_in1]
            ac_a, ac_b = and_gates[inter_in2]

            # Find common element 'a' between the two ANDs
            ab_set = {ab_a, ab_b}
            ac_set = {ac_a, ac_b}

            common = ab_set & ac_set
            if len(common) != 1:
                continue

            a = common.pop()
            ab_other = (ab_set - {a}).pop()
            ac_other = (ac_set - {a}).pop()

            # Check if ab_other and ac_other match b and c
            if {ab_other, ac_other} != {b, c}:
                continue

            # Found MAJ pattern!
            maj_patterns.append({
                'maj_label': maj_cand,
                'a': a,
                'b': b,
                'c': c,
                'bc_and': bc_and_label,
                'intermediate': intermediate,
                'ab_and': inter_in1,
                'ac_and': inter_in2,
            })

        return maj_patterns

    def rewrite_maj_efficient(self, maj_patterns):
        """Rewrite MAJ patterns using the efficient OR form.

        Efficient MAJ implementation (6 NANDs):
        1. ab_nand = NAND(a, b)
        2. ac_nand = NAND(a, c)
        3. bc_nand = NAND(b, c)
        4. x = NAND(ab_nand, ac_nand)
        5. not_x = NAND(x, x)
        6. maj = NAND(not_x, bc_nand)

        Original uses 14 NANDs per MAJ bit.
        """
        if not maj_patterns:
            return 0

        gate_map = {g[0]: (g[1], g[2]) for g in self.gates}
        use_count = defaultdict(int)
        for label, a, b in self.gates:
            use_count[a] += 1
            use_count[b] += 1
        for label in self.output_labels:
            use_count[label] += 1

        # Collect all labels involved in MAJ patterns
        gates_to_remove = set()
        replacements = {}  # old_label -> new_label or new_implementation

        # For each MAJ pattern, we need to:
        # 1. Keep the ab_nand, ac_nand, bc_nand (the first NAND of each AND)
        # 2. Replace the rest with efficient implementation

        for pattern in maj_patterns:
            maj_label = pattern['maj_label']
            a, b, c = pattern['a'], pattern['b'], pattern['c']

            # Find the inner NAND gates for each AND
            ab_and_label = pattern['ab_and']
            ac_and_label = pattern['ac_and']
            bc_and_label = pattern['bc_and']

            # The AND gate is NOT(NAND(x,y)), so it's NAND(t,t) where t=NAND(x,y)
            if ab_and_label not in gate_map:
                continue

            ab_and_inner, _ = gate_map[ab_and_label]  # The NOT's input
            if ab_and_inner not in gate_map:
                continue
            # ab_and_inner should be the NAND(a,b) gate

            ac_and_inner, _ = gate_map[ac_and_label]
            bc_and_inner, _ = gate_map[bc_and_label]

            # We need to trace back to the actual NAND gates
            # This is complex because we need the original NAND(a,b), etc.

            # For now, let's just track that we found the pattern
            # Full rewriting requires careful handling

        self.log(f"Found {len(maj_patterns)} MAJ patterns")
        return 0  # For now, return without modification

    def pass_general_cse(self):
        """Standard CSE pass."""
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

    def pass_double_negation(self):
        """Eliminate NOT(NOT(x)) = x."""
        gate_map = {g[0]: (g[1], g[2]) for g in self.gates}

        not_of = {}
        for label, a, b in self.gates:
            if a == b:
                not_of[label] = a

        replacements = {}
        for label, a, b in self.gates:
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

    def pass_constant_folding(self):
        """Fold constants."""
        known = {'CONST-0': False, 'CONST-1': True}
        replacements = {}

        for label, a, b in self.gates:
            ra = replacements.get(a, a)
            rb = replacements.get(b, b)

            a_val = known.get(ra)
            b_val = known.get(rb)

            if a_val == False or b_val == False:
                if label not in self.output_labels:
                    replacements[label] = 'CONST-1'
                    known[label] = True
            elif a_val == True and b_val == True:
                if label not in self.output_labels:
                    replacements[label] = 'CONST-0'
                    known[label] = False

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
        """Run all optimization passes."""
        total_eliminated = 0
        iteration = 0

        # First analyze patterns
        not_of, and_gates, xor_gates = self.analyze_patterns()

        # Find and potentially rewrite MAJ patterns
        maj_patterns = self.find_maj_patterns(and_gates, xor_gates)
        self.log(f"Identified {len(maj_patterns)} MAJ patterns in circuit")

        # Run standard optimization passes
        while True:
            iteration += 1
            start_count = len(self.gates)

            passes = [
                ('Constant folding', self.pass_constant_folding),
                ('Double negation', self.pass_double_negation),
                ('CSE', self.pass_general_cse),
                ('Dead code', self.pass_dead_code),
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

        return total_eliminated


def main():
    parser = argparse.ArgumentParser(description="Pattern-based NAND optimizer")
    parser.add_argument("--input", "-i", default="nands-super.txt", help="Input file")
    parser.add_argument("--output", "-o", default="nands-pattern.txt", help="Output file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output")
    args = parser.parse_args()

    optimizer = PatternOptimizer(verbose=not args.quiet)

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
