#!/usr/bin/env python3
"""
Rewrite MAJ (majority) patterns to use efficient OR-based implementation.

Standard MAJ using XOR: 14 NANDs per bit
Efficient MAJ using OR: 6 NANDs per bit
Potential savings: 8 NANDs × 2048 bits = 16,384 gates

The MAJ pattern is:
  - ab_and = AND(a, b) = NOT(NAND(a,b))
  - ac_and = AND(a, c) = NOT(NAND(a,c))
  - bc_and = AND(b, c) = NOT(NAND(b,c))
  - t1 = XOR(ab_and, ac_and)
  - maj = XOR(t1, bc_and)

Efficient implementation:
  - ab_nand = NAND(a, b)
  - ac_nand = NAND(a, c)
  - bc_nand = NAND(b, c)
  - x = NAND(ab_nand, ac_nand)  [= OR(AND(a,b), AND(a,c))]
  - not_x = NOT(x)
  - maj = NAND(not_x, bc_nand)
"""

import argparse
from collections import defaultdict


class MAJRewriter:
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
        return f"{prefix}-MAJOPT{self.counter}"

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

    def find_and_rewrite_maj(self):
        """Find MAJ patterns and rewrite them."""
        gate_map = {g[0]: (g[1], g[2]) for g in self.gates}
        gate_index = {g[0]: i for i, g in enumerate(self.gates)}

        # Track use counts
        use_count = defaultdict(int)
        for label, a, b in self.gates:
            use_count[a] += 1
            use_count[b] += 1
        for label in self.output_labels:
            use_count[label] += 1

        # Find NOT gates: NAND(x, x)
        not_of = {}  # label -> what it's NOT of
        for label, a, b in self.gates:
            if a == b:
                not_of[label] = a

        # Find AND gates: NOT(NAND(x, y)) where result is NOT's output
        # AND = NAND(t, t) where t = NAND(a, b)
        and_gates = {}  # and_label -> (a, b, nand_label)
        for label, a, b in self.gates:
            if a == b and a in gate_map:
                inner_a, inner_b = gate_map[a]
                if inner_a != inner_b:  # The inner is a real NAND, not a NOT
                    and_gates[label] = (inner_a, inner_b, a)  # a is the nand_label

        # Find XOR gates
        def find_xor_inputs(label):
            if label not in gate_map:
                return None
            p, q = gate_map[label]
            if p not in gate_map or q not in gate_map:
                return None

            p_a, p_b = gate_map[p]
            q_a, q_b = gate_map[q]

            common = None
            a_cand = b_cand = None

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
                    return (a_cand, b_cand, p, q, common)
            return None

        xor_gates = {}  # label -> (a, b, nand_with_a, nand_with_b, common_nand)
        for label, _, _ in self.gates:
            result = find_xor_inputs(label)
            if result:
                xor_gates[label] = result

        # Find MAJ patterns
        maj_patterns = []

        for maj_cand in xor_gates:
            xor_a, xor_b, _, _, _ = xor_gates[maj_cand]

            # One input should be an AND, other should be an XOR
            if xor_a in and_gates and xor_b in xor_gates:
                bc_and_label = xor_a
                inter_xor = xor_b
            elif xor_b in and_gates and xor_a in xor_gates:
                bc_and_label = xor_b
                inter_xor = xor_a
            else:
                continue

            bc_a, bc_b, bc_nand = and_gates[bc_and_label]
            inter_xa, inter_xb, _, _, _ = xor_gates[inter_xor]

            # inter_xa and inter_xb should both be AND gates
            if inter_xa not in and_gates or inter_xb not in and_gates:
                continue

            ab_a, ab_b, ab_nand = and_gates[inter_xa]
            ac_a, ac_b, ac_nand = and_gates[inter_xb]

            # Find common element 'a'
            ab_set = {ab_a, ab_b}
            ac_set = {ac_a, ac_b}
            common = ab_set & ac_set

            if len(common) != 1:
                continue

            a = common.pop()
            b_from_ab = (ab_set - {a}).pop()
            c_from_ac = (ac_set - {a}).pop()

            # Verify (b, c) matches the bc AND gate
            if {b_from_ab, c_from_ac} != {bc_a, bc_b}:
                continue

            # Determine actual b and c
            b = b_from_ab
            c = c_from_ac

            # We found a MAJ pattern!
            maj_patterns.append({
                'maj_label': maj_cand,
                'a': a, 'b': b, 'c': c,
                'ab_nand': ab_nand,
                'ac_nand': ac_nand,
                'bc_nand': bc_nand,
                'ab_and': inter_xa,
                'ac_and': inter_xb,
                'bc_and': bc_and_label,
                'inter_xor': inter_xor,
            })

        self.log(f"Found {len(maj_patterns)} MAJ patterns to optimize")

        if not maj_patterns:
            return 0

        # Now rewrite each MAJ pattern
        # We need to:
        # 1. Keep ab_nand, ac_nand, bc_nand (already computed)
        # 2. Replace the rest with efficient implementation
        # 3. Make maj_label point to the new efficient result

        gates_to_remove = set()
        new_gates_to_add = []

        for pattern in maj_patterns:
            maj_label = pattern['maj_label']
            ab_nand = pattern['ab_nand']
            ac_nand = pattern['ac_nand']
            bc_nand = pattern['bc_nand']

            # Mark gates for removal (the ones we're replacing)
            # These are the AND gates (double-NOT), the intermediate XOR, and the final XOR
            gates_to_remove.add(pattern['ab_and'])
            gates_to_remove.add(pattern['ac_and'])
            gates_to_remove.add(pattern['bc_and'])
            gates_to_remove.add(pattern['inter_xor'])
            gates_to_remove.add(maj_label)

            # Also remove the intermediate gates of the XORs
            # The XOR is built from: out = NAND(NAND(a,t), NAND(b,t)) where t=NAND(a,b)
            # We need to remove those intermediate NANDs too

            # Get the gates involved in inter_xor and maj (final xor)
            for xor_label in [pattern['inter_xor'], maj_label]:
                if xor_label in gate_map:
                    p, q = gate_map[xor_label]
                    gates_to_remove.add(p)
                    gates_to_remove.add(q)
                    # Don't remove the common NAND (t) if it's ab_nand, ac_nand, etc.
                    if p in gate_map:
                        p_a, p_b = gate_map[p]
                        # The common NAND is shared and might be one of ab/ac/bc_nand
                        if p_a == p_b:  # p is a NOT gate
                            pass  # might be double-NOT, be careful

            # Add efficient implementation
            prefix = maj_label.rsplit('-', 1)[0] if '-' in maj_label else maj_label

            # x = NAND(ab_nand, ac_nand) = OR(AND(a,b), AND(a,c))
            x_label = self.temp_label(prefix)
            new_gates_to_add.append((x_label, ab_nand, ac_nand))

            # not_x = NOT(x) = NAND(x, x)
            not_x_label = self.temp_label(prefix)
            new_gates_to_add.append((not_x_label, x_label, x_label))

            # maj = NAND(not_x, bc_nand)
            # Use the original maj_label to maintain references
            new_gates_to_add.append((maj_label, not_x_label, bc_nand))

        # Don't remove gates that are outputs or used by non-removed gates
        # This is tricky - we need to be careful about dependencies

        # For safety, let's just add new gates and do CSE/dead code elimination later
        # Instead of removing, we'll replace

        # Build new gate list
        # First, find all gates involved in the patterns
        pattern_labels = set()
        for pattern in maj_patterns:
            pattern_labels.add(pattern['ab_and'])
            pattern_labels.add(pattern['ac_and'])
            pattern_labels.add(pattern['bc_and'])
            pattern_labels.add(pattern['inter_xor'])
            # DON'T add maj_label here - we want to replace it

        # For each maj_label, we'll redirect it to new implementation
        replacements = {}

        # Create mapping from old maj to new implementation
        new_gates = []
        new_gate_idx = len(self.gates)

        for pattern in maj_patterns:
            maj_label = pattern['maj_label']
            ab_nand = pattern['ab_nand']
            ac_nand = pattern['ac_nand']
            bc_nand = pattern['bc_nand']

            prefix = maj_label

            # Efficient MAJ: 3 gates total (we reuse ab_nand, ac_nand, bc_nand)
            x_label = f"{prefix}-OPTX"
            not_x_label = f"{prefix}-OPTNX"

            new_gates.append((x_label, ab_nand, ac_nand))
            new_gates.append((not_x_label, x_label, x_label))
            new_gates.append((maj_label, not_x_label, bc_nand))

            replacements[maj_label] = maj_label  # Keep the label, new implementation

        # Now rebuild the gate list
        # Keep all gates except those we're replacing
        kept_gates = []
        removed_count = 0

        for label, a, b in self.gates:
            if label in replacements and label in [p['maj_label'] for p in maj_patterns]:
                # This is an old MAJ output - skip it, we'll add the new one
                removed_count += 1
                continue

            # Check if this gate is an internal gate of a MAJ pattern
            is_internal = False
            for pattern in maj_patterns:
                # Internal gates: ab_and, ac_and, bc_and, inter_xor, and the XOR internals
                if label in [pattern['ab_and'], pattern['ac_and'], pattern['bc_and'],
                            pattern['inter_xor']]:
                    is_internal = True
                    break

                # Also check XOR internal gates
                maj = pattern['maj_label']
                inter = pattern['inter_xor']
                if maj in gate_map:
                    p, q = gate_map[maj]
                    if label in [p, q]:
                        is_internal = True
                        break
                if inter in gate_map:
                    p, q = gate_map[inter]
                    if label in [p, q]:
                        is_internal = True
                        break

            if is_internal:
                removed_count += 1
                continue

            kept_gates.append((label, a, b))

        # Add new MAJ implementations at the appropriate positions
        # We need to insert them after their dependencies (ab_nand, ac_nand, bc_nand)

        # For simplicity, find where each MAJ should be inserted
        final_gates = kept_gates.copy()
        new_gate_positions = []

        for pattern in maj_patterns:
            maj_label = pattern['maj_label']
            ab_nand = pattern['ab_nand']
            ac_nand = pattern['ac_nand']
            bc_nand = pattern['bc_nand']

            # Find the latest position of the three NANDs
            max_pos = -1
            for i, (label, _, _) in enumerate(final_gates):
                if label in [ab_nand, ac_nand, bc_nand]:
                    max_pos = max(max_pos, i)

            prefix = maj_label
            x_label = f"{prefix}-OPTX"
            not_x_label = f"{prefix}-OPTNX"

            new_gate_positions.append((max_pos + 1, [
                (x_label, ab_nand, ac_nand),
                (not_x_label, x_label, x_label),
                (maj_label, not_x_label, bc_nand),
            ]))

        # Sort by position and insert
        new_gate_positions.sort(key=lambda x: x[0], reverse=True)

        for pos, gates_to_insert in new_gate_positions:
            for gate in reversed(gates_to_insert):
                final_gates.insert(pos, gate)

        old_count = len(self.gates)
        self.gates = final_gates

        # The savings: for each MAJ, we removed ~11 gates and added 3
        # (Each MAJ had: 3 AND gates (6 gates), 2 XOR gates (8 gates) = 14 gates internal
        #  We keep 3 NANDs, add 3 new = 6 total)

        self.log(f"Removed {removed_count} gates from old MAJ patterns")
        self.log(f"Added {len(maj_patterns) * 3} new efficient MAJ gates")

        return removed_count - len(maj_patterns) * 3

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
                if label not in self.output_labels:
                    replacements[label] = expr_to_label[key]
            else:
                expr_to_label[key] = label

        if not replacements:
            return 0

        def resolve(x):
            seen = set()
            while x in replacements and x not in seen:
                seen.add(x)
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

    def optimize(self):
        """Run the MAJ rewriting optimization."""
        initial = len(self.gates)

        # Rewrite MAJ patterns
        self.find_and_rewrite_maj()

        # Clean up
        iteration = 0
        while True:
            iteration += 1
            before = len(self.gates)

            cse = self.pass_cse()
            if cse > 0:
                self.log(f"  CSE: eliminated {cse}")

            dead = self.pass_dead_code()
            if dead > 0:
                self.log(f"  Dead code: eliminated {dead}")

            if before == len(self.gates):
                break

        return initial - len(self.gates)


def main():
    parser = argparse.ArgumentParser(description="MAJ pattern rewriter")
    parser.add_argument("--input", "-i", default="nands-super.txt", help="Input file")
    parser.add_argument("--output", "-o", default="nands-maj-opt.txt", help="Output file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output")
    args = parser.parse_args()

    rewriter = MAJRewriter(verbose=not args.quiet)

    print(f"Loading {args.input}...")
    initial_count = rewriter.load(args.input)
    print(f"Initial gate count: {initial_count:,}")

    print("\nOptimizing MAJ patterns...")
    saved = rewriter.optimize()

    final_count = len(rewriter.gates)
    reduction = initial_count - final_count
    percent = (reduction / initial_count) * 100 if initial_count > 0 else 0

    print(f"\nOptimization complete!")
    print(f"  Initial gates:  {initial_count:,}")
    print(f"  Final gates:    {final_count:,}")
    print(f"  Eliminated:     {reduction:,} ({percent:.2f}%)")

    rewriter.save(args.output)
    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
