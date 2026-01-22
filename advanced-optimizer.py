#!/usr/bin/env python3
"""
Advanced NAND gate optimizer for SHA-256 circuit.

Applies aggressive multi-level optimizations to minimize gate count.

Usage:
    python advanced-optimizer.py
    python advanced-optimizer.py -i nands-optimized.txt -o nands-final.txt
"""

import argparse
from collections import defaultdict
import sys


class AdvancedOptimizer:
    def __init__(self, verbose=True):
        self.gates = []  # List of (label, a, b)
        self.output_labels = set()
        self.verbose = verbose

    def log(self, msg):
        if self.verbose:
            print(msg)

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

    def get_gate_map(self):
        """Build label -> (a, b) map from current gates."""
        return {label: (a, b) for label, a, b in self.gates}

    def get_use_count(self):
        """Count how many times each label is used as input."""
        use_count = defaultdict(int)
        for label, a, b in self.gates:
            use_count[a] += 1
            use_count[b] += 1
        for label in self.output_labels:
            use_count[label] += 1
        return use_count

    def apply_replacements(self, replacements):
        """Apply label replacements throughout the circuit."""
        if not replacements:
            return 0

        # Build transitive closure
        def resolve(label):
            visited = set()
            while label in replacements and label not in visited:
                visited.add(label)
                label = replacements[label]
            return label

        new_gates = []
        eliminated = 0
        for label, a, b in self.gates:
            if label in replacements:
                eliminated += 1
                continue

            a = resolve(a)
            b = resolve(b)
            new_gates.append((label, a, b))

        self.gates = new_gates
        return eliminated

    def pass_canonicalize(self):
        """Canonicalize gate inputs (sort alphabetically)."""
        new_gates = []
        for label, a, b in self.gates:
            if a > b:
                a, b = b, a
            new_gates.append((label, a, b))
        self.gates = new_gates
        return 0

    def pass_cse(self):
        """Common subexpression elimination."""
        expr_to_label = {}
        replacements = {}

        for label, a, b in self.gates:
            # Resolve through replacements
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

        return self.apply_replacements(replacements)

    def pass_dead_code(self):
        """Remove gates whose outputs are never used."""
        used = set(self.output_labels)

        for label, a, b in reversed(self.gates):
            if label in used:
                used.add(a)
                used.add(b)

        new_gates = [(label, a, b) for label, a, b in self.gates if label in used]
        eliminated = len(self.gates) - len(new_gates)
        self.gates = new_gates
        return eliminated

    def pass_constant_folding(self):
        """Fold constant expressions."""
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

        return self.apply_replacements(replacements)

    def pass_double_negation(self):
        """Eliminate double negation: NOT(NOT(x)) = x."""
        gate_map = self.get_gate_map()

        not_gates = {}
        for label, a, b in self.gates:
            if a == b:
                not_gates[label] = a

        replacements = {}
        for label, a, b in self.gates:
            if a == b and a in not_gates:
                original = not_gates[a]
                if label not in self.output_labels:
                    replacements[label] = original

        return self.apply_replacements(replacements)

    def pass_share_inverters(self):
        """Share NOT gates computing the same thing."""
        not_gates = defaultdict(list)
        for label, a, b in self.gates:
            if a == b:
                not_gates[a].append(label)

        replacements = {}
        for input_signal, labels in not_gates.items():
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

        return self.apply_replacements(replacements)

    def pass_algebraic(self):
        """Apply algebraic simplifications."""
        gate_map = self.get_gate_map()

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
            # NAND(x, x) = NOT(x) - handled by share_inverters
            # NAND(x, 1) = NOT(x) - check if we can simplify chains

        return self.apply_replacements(replacements)

    def pass_redundant_and_chain(self):
        """Optimize redundant AND chains: AND(x, x) = x."""
        gate_map = self.get_gate_map()

        # AND(a,b) = NOT(NAND(a,b)) = NAND(NAND(a,b), NAND(a,b))
        # Find patterns: NAND(t,t) where t = NAND(a,b)
        # If a == b, then NAND(a,a) is NOT(a), and NOT(NOT(a)) = a

        not_gates = {}
        for label, a, b in self.gates:
            if a == b:
                not_gates[label] = a

        # Find NOT(NAND(x,x)) = NOT(NOT(x)) = x
        replacements = {}
        for label, a, b in self.gates:
            if a == b and a in not_gates:
                # This is NOT(NOT(something))
                original = not_gates[a]
                if label not in self.output_labels:
                    replacements[label] = original

        return self.apply_replacements(replacements)

    def pass_nand_to_identity(self):
        """Simplify NAND with constant 1: NAND(x, 1) = NOT(x)."""
        gate_map = self.get_gate_map()
        use_count = self.get_use_count()

        # Find NOT gates and gates that compute NOT via NAND(x, CONST-1)
        not_gates = {}  # label -> what it's the NOT of
        for label, a, b in self.gates:
            if a == b:
                not_gates[label] = a
            elif a == 'CONST-1':
                not_gates[label] = b
            elif b == 'CONST-1':
                not_gates[label] = a

        # Now find if there are equivalent NOT computations we can merge
        not_of = defaultdict(list)  # input -> [labels that are NOT of it]
        for label, inv_of in not_gates.items():
            not_of[inv_of].append(label)

        replacements = {}
        for input_sig, labels in not_of.items():
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

        return self.apply_replacements(replacements)

    def pass_xor_chain_optimization(self):
        """Recognize and optimize XOR chains.

        XOR(a,b) in NAND:
          t1 = NAND(a,b)
          t2 = NAND(a,t1)
          t3 = NAND(b,t1)
          out = NAND(t2,t3)

        XOR(XOR(a,b),c) normally takes 8 NANDs but can be done in 6
        if we recognize the pattern and share intermediate results.
        """
        gate_map = self.get_gate_map()
        use_count = self.get_use_count()

        # Find XOR gates (4-gate pattern)
        # Pattern: out = NAND(NAND(a,t1), NAND(b,t1)) where t1 = NAND(a,b)

        xor_outputs = {}  # out_label -> (a, b)

        for label, p, q in self.gates:
            if p not in gate_map or q not in gate_map:
                continue

            p_a, p_b = gate_map[p]
            q_a, q_b = gate_map[q]

            # Check if this is NAND(NAND(a,t), NAND(b,t)) pattern
            # where t = NAND(a,b)

            # p = NAND(x1, x2), q = NAND(y1, y2)
            # We need: one input of p equals one input of q (that's t)
            # And the other inputs are a and b respectively
            # And t = NAND(a, b)

            common = None
            a_cand = None
            b_cand = None

            if p_b == q_b:
                common = p_b
                a_cand = p_a
                b_cand = q_a
            elif p_b == q_a:
                common = p_b
                a_cand = p_a
                b_cand = q_b
            elif p_a == q_b:
                common = p_a
                a_cand = p_b
                b_cand = q_a
            elif p_a == q_a:
                common = p_a
                a_cand = p_b
                b_cand = q_b

            if common and common in gate_map:
                t_a, t_b = gate_map[common]
                if (t_a == a_cand and t_b == b_cand) or (t_a == b_cand and t_b == a_cand):
                    xor_outputs[label] = (min(a_cand, b_cand), max(a_cand, b_cand))

        # Now look for XOR chains: XOR(XOR(a,b), c)
        # These happen when one input to an XOR is itself an XOR output

        # For now, just track - we'll use this info for CSE on XOR patterns
        # Check if any two XORs compute the same thing
        xor_by_inputs = defaultdict(list)
        for label, (a, b) in xor_outputs.items():
            xor_by_inputs[(a, b)].append(label)

        replacements = {}
        for key, labels in xor_by_inputs.items():
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

        return self.apply_replacements(replacements)

    def pass_deep_double_negation(self):
        """More aggressive double negation elimination.

        Look for patterns where we have:
        t1 = NOT(x)
        t2 = NOT(t1) = x
        And t2 is only used in contexts where we could use x directly.
        """
        gate_map = self.get_gate_map()
        use_count = self.get_use_count()

        not_gates = {}
        for label, a, b in self.gates:
            if a == b:
                not_gates[label] = a

        replacements = {}
        for label, a, b in self.gates:
            if a == b and a in not_gates:
                original = not_gates[a]
                # This is NOT(NOT(original))
                # Can replace label with original regardless of whether original is a gate
                if label not in self.output_labels:
                    replacements[label] = original

        return self.apply_replacements(replacements)

    def pass_and_simplification(self):
        """Optimize AND(x, x) = x patterns.

        AND is: NAND(NAND(a,b), NAND(a,b)) or equivalently NOT(NAND(a,b))
        If a == b, then NAND(a,a) = NOT(a), and AND(a,a) = a
        """
        gate_map = self.get_gate_map()

        # Find AND gates: NAND(t, t) where t is some NAND output
        replacements = {}
        for label, a, b in self.gates:
            if a == b and a in gate_map:
                inner_a, inner_b = gate_map[a]
                if inner_a == inner_b:
                    # AND(x, x) = NOT(NOT(x)) = x
                    if label not in self.output_labels:
                        replacements[label] = inner_a

        return self.apply_replacements(replacements)

    def pass_or_simplification(self):
        """Recognize OR gates and simplify OR(x, x) = x.

        OR(a,b) = NAND(NOT(a), NOT(b)) = NAND(NAND(a,a), NAND(b,b))
        """
        gate_map = self.get_gate_map()

        replacements = {}
        for label, a, b in self.gates:
            if a in gate_map and b in gate_map:
                a_inner_a, a_inner_b = gate_map[a]
                b_inner_a, b_inner_b = gate_map[b]

                # Check if both inputs are NOT gates
                if a_inner_a == a_inner_b and b_inner_a == b_inner_b:
                    # This is OR(a_inner_a, b_inner_a)
                    if a_inner_a == b_inner_a:
                        # OR(x, x) = x
                        if label not in self.output_labels:
                            replacements[label] = a_inner_a

        return self.apply_replacements(replacements)

    def pass_idempotent(self):
        """Simplify idempotent operations: NAND(x, x) where x is known."""
        # This is NOT(x), already handled elsewhere
        return 0

    def pass_absorption(self):
        """Apply absorption law: a AND (a OR b) = a, a OR (a AND b) = a.

        In NAND form this is complex but we can detect some patterns.
        """
        # Complex to implement correctly, skip for now
        return 0

    def pass_reconvergent_fanout(self):
        """Optimize reconvergent fanout patterns.

        When the same signal feeds multiple paths that reconverge,
        there may be redundant computation.
        """
        gate_map = self.get_gate_map()
        use_count = self.get_use_count()

        # Track which gates use which primary inputs
        # This is expensive so we do it conservatively

        # For now, just ensure CSE catches these
        return self.pass_cse()

    def pass_demorgan(self):
        """Apply De Morgan's law for optimization.

        NOT(AND(a,b)) = OR(NOT(a), NOT(b)) = NAND(a,b)
        NOT(OR(a,b)) = AND(NOT(a), NOT(b))

        Look for patterns like NOT(NAND(NOT(a), NOT(b))) which is AND(a,b)
        """
        gate_map = self.get_gate_map()

        not_gates = {}
        for label, a, b in self.gates:
            if a == b:
                not_gates[label] = a

        replacements = {}
        for label, a, b in self.gates:
            if a == b:  # This is NOT(a)
                inner = a
                if inner in gate_map:
                    inner_a, inner_b = gate_map[inner]
                    # Check if inner is NAND(NOT(x), NOT(y))
                    if inner_a in not_gates and inner_b in not_gates:
                        x = not_gates[inner_a]
                        y = not_gates[inner_b]
                        # NOT(NAND(NOT(x), NOT(y))) = NOT(NOT(AND(x,y))) = AND(x,y)
                        # Which is NOT(NAND(x,y))
                        # We could potentially optimize this but it's complex
                        pass

        return self.apply_replacements(replacements)

    def pass_cleanup_copies(self):
        """Remove unnecessary copy operations (double-NOT of gate outputs).

        Pattern: t = NOT(g), out = NOT(t) where out just copies g
        If g is only used via this copy chain, we might be able to rename.
        """
        gate_map = self.get_gate_map()
        use_count = self.get_use_count()

        not_gates = {}
        for label, a, b in self.gates:
            if a == b:
                not_gates[label] = a

        replacements = {}
        for label, a, b in self.gates:
            if a == b and a in not_gates:
                original = not_gates[a]
                intermediate = a
                # If intermediate is only used once (by this gate)
                if use_count[intermediate] == 1:
                    if label not in self.output_labels:
                        replacements[label] = original

        return self.apply_replacements(replacements)

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

            # Canonicalize for consistent CSE
            self.pass_canonicalize()

            # Core optimization passes
            passes = [
                ('Constant folding', self.pass_constant_folding),
                ('Algebraic', self.pass_algebraic),
                ('Double negation', self.pass_double_negation),
                ('Deep double negation', self.pass_deep_double_negation),
                ('Share inverters', self.pass_share_inverters),
                ('NAND to identity', self.pass_nand_to_identity),
                ('AND simplification', self.pass_and_simplification),
                ('OR simplification', self.pass_or_simplification),
                ('XOR chain', self.pass_xor_chain_optimization),
                ('Cleanup copies', self.pass_cleanup_copies),
                ('CSE', self.pass_cse),
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
            self.log(f"  Iteration {iteration}: {eliminated_this_round} eliminated, {len(self.gates)} remaining")

        # Final cosmetic pass
        self.pass_renumber()

        return total_eliminated


def main():
    parser = argparse.ArgumentParser(description="Advanced NAND circuit optimizer")
    parser.add_argument("--input", "-i", default="nands-optimized.txt", help="Input file")
    parser.add_argument("--output", "-o", default="nands-final.txt", help="Output file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")
    args = parser.parse_args()

    optimizer = AdvancedOptimizer(verbose=not args.quiet)

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
