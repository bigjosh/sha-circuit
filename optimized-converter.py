#!/usr/bin/env python3
"""
Optimized converter for SHA-256 functions to NAND gates.

Uses more efficient gate-level implementations:
- Maj(a,b,c) uses OR form (6 NANDs) instead of XOR form (14 NANDs)
- Ch(e,f,g) uses efficient MUX-like form
- Better sharing of intermediate results

Usage:
    python optimized-converter.py
"""

import argparse
from collections import defaultdict


class OptimizedNandConverter:
    def __init__(self):
        self.nands = []
        self.counter = 0
        self.word_bits = {}
        # Track computed expressions for sharing
        self.expr_cache = {}  # (op, sorted_inputs) -> label

    def temp_label(self, prefix):
        """Generate a unique temporary label."""
        self.counter += 1
        return f"{prefix}-T{self.counter}"

    def emit(self, label, a, b):
        """Emit a NAND gate, with optional CSE."""
        # Canonicalize for CSE
        key = (min(a, b), max(a, b))

        # Check if we've already computed this
        if key in self.expr_cache:
            # Return existing label instead of creating new gate
            return self.expr_cache[key]

        self.nands.append((label, a, b))
        self.expr_cache[key] = label
        return label

    def nand(self, prefix, a, b):
        """Create a NAND gate with auto-generated label and CSE."""
        key = (min(a, b), max(a, b))
        if key in self.expr_cache:
            return self.expr_cache[key]
        return self.emit(self.temp_label(prefix), a, b)

    def not_gate(self, prefix, a):
        """NOT(A) = NAND(A, A)"""
        return self.nand(prefix, a, a)

    def and_gate(self, prefix, a, b):
        """AND(A, B) = NOT(NAND(A, B))"""
        t = self.nand(prefix, a, b)
        return self.not_gate(prefix, t)

    def or_gate(self, prefix, a, b):
        """OR(A, B) = NAND(NOT(A), NOT(B))"""
        na = self.not_gate(prefix, a)
        nb = self.not_gate(prefix, b)
        return self.nand(prefix, na, nb)

    def or_of_nands(self, prefix, nand_a_b, nand_c_d):
        """Compute OR(AND(a,b), AND(c,d)) efficiently.

        Given NAND(a,b) and NAND(c,d), computes OR(AND(a,b), AND(c,d))
        which equals NAND(NAND(a,b), NAND(c,d)).
        """
        # OR(NOT(nand_a_b), NOT(nand_c_d)) = OR(AND(a,b), AND(c,d))
        # = NAND(nand_a_b, nand_c_d)
        return self.nand(prefix, nand_a_b, nand_c_d)

    def xor_gate(self, prefix, a, b):
        """XOR(A, B) = NAND(NAND(A, NAND(A,B)), NAND(B, NAND(A,B)))"""
        nab = self.nand(prefix, a, b)
        t1 = self.nand(prefix, a, nab)
        t2 = self.nand(prefix, b, nab)
        return self.nand(prefix, t1, t2)

    def xor3_gate(self, prefix, a, b, c):
        """Three-input XOR: A XOR B XOR C"""
        # Standard cascaded XOR
        ab_xor = self.xor_gate(prefix, a, b)
        return self.xor_gate(prefix, ab_xor, c)

    def maj_gate(self, prefix, a, b, c):
        """Majority function: MAJ(a,b,c) = (a AND b) OR (a AND c) OR (b AND c).

        Efficient implementation using only 6 NANDs:
        1. ab_nand = NAND(a, b)
        2. ac_nand = NAND(a, c)
        3. bc_nand = NAND(b, c)
        4. x = NAND(ab_nand, ac_nand) = OR(AND(a,b), AND(a,c))
        5. not_x = NOT(x)
        6. maj = NAND(not_x, bc_nand)
        """
        ab_nand = self.nand(prefix, a, b)
        ac_nand = self.nand(prefix, a, c)
        bc_nand = self.nand(prefix, b, c)
        x = self.nand(prefix, ab_nand, ac_nand)  # OR(AND(a,b), AND(a,c))
        not_x = self.not_gate(prefix, x)
        return self.nand(prefix, not_x, bc_nand)

    def ch_gate(self, prefix, e, f, g):
        """Choice function: CH(e,f,g) = (e AND f) XOR (NOT(e) AND g).

        Efficient implementation:
        Ch(e,f,g) can be computed as: g XOR (e AND (f XOR g))
        But that's 10 gates. Let's try the standard form optimized:

        Standard: (e AND f) XOR (NOT(e) AND g)
        - e AND f = NOT(NAND(e,f))
        - NOT(e) computed once
        - NOT(e) AND g = NOT(NAND(NOT(e), g))
        - XOR of results

        Total: 9 gates (1 for ef_nand, 1 for NOT(e), 1 for neg_and_nand,
                       2 for ANDs, 4 for XOR)

        Actually can be optimized using direct NAND structure.
        """
        # Standard implementation optimized for NAND
        ef_nand = self.nand(prefix, e, f)  # NAND(e, f)
        not_e = self.not_gate(prefix, e)    # NOT(e)
        not_e_g_nand = self.nand(prefix, not_e, g)  # NAND(NOT(e), g)

        # We have ef_nand = NOT(AND(e,f)) and not_e_g_nand = NOT(AND(NOT(e), g))
        # Now XOR(AND(e,f), AND(NOT(e),g))

        # For XOR(x, y) where we have NAND results:
        # XOR = NAND(NAND(x, NAND(x,y)), NAND(y, NAND(x,y)))
        # Here x = NOT(ef_nand) = AND(e,f), y = NOT(not_e_g_nand) = AND(NOT(e),g)

        # XOR(NOT(a), NOT(b)) = XOR(a, b) in terms of NANDs:
        # Let p = ef_nand = NOT(AND(e,f)), q = not_e_g_nand = NOT(AND(NOT(e),g))
        # XOR(NOT(p), NOT(q)) where p=ef_nand, q=not_e_g_nand

        # Actually simpler:
        # x = AND(e,f), y = AND(NOT(e), g)
        # We have NAND(e,f) and NAND(NOT(e),g)
        # x = NOT(ef_nand), y = NOT(not_e_g_nand)
        # XOR(x, y):
        #   xy_nand = NAND(x, y) = NAND(NOT(ef_nand), NOT(not_e_g_nand))
        #           = OR(ef_nand, not_e_g_nand) [by De Morgan]
        #   ... this is getting complex

        # Let's just use standard XOR of the AND results
        ef_and = self.not_gate(prefix, ef_nand)  # AND(e, f)
        neg_and = self.not_gate(prefix, not_e_g_nand)  # AND(NOT(e), g)

        return self.xor_gate(prefix, ef_and, neg_and)

    def half_adder(self, prefix, a, b):
        """Half adder: returns (sum, carry)"""
        s = self.xor_gate(prefix, a, b)
        c = self.and_gate(prefix, a, b)
        return s, c

    def full_adder(self, prefix, a, b, cin):
        """Full adder: returns (sum, cout)"""
        # Optimized full adder using shared NAND
        ab_nand = self.nand(prefix, a, b)
        t1 = self.nand(prefix, a, ab_nand)
        t2 = self.nand(prefix, b, ab_nand)
        ab_xor = self.nand(prefix, t1, t2)  # a XOR b

        # Sum = (a XOR b) XOR cin
        xc_nand = self.nand(prefix, ab_xor, cin)
        t3 = self.nand(prefix, ab_xor, xc_nand)
        t4 = self.nand(prefix, cin, xc_nand)
        s = self.nand(prefix, t3, t4)  # sum

        # Cout = (a AND b) OR (cin AND (a XOR b))
        # = NOT(NAND(NAND(a,b), NAND(cin, a XOR b)))
        # ab_nand is NOT(a AND b)
        # xc_nand is NOT(cin AND (a XOR b))
        cout = self.nand(prefix, ab_nand, xc_nand)

        return s, cout

    def register_word(self, label, bit_labels):
        """Register a word-level label with its bit labels."""
        self.word_bits[label] = bit_labels

    def get_bits(self, label):
        """Get bit labels for a word-level label."""
        if label in self.word_bits:
            return self.word_bits[label]
        return [f"{label}-B{i}" for i in range(32)]

    def convert_not(self, out_label, in_label):
        """Convert NOT operation to NANDs."""
        in_bits = self.get_bits(in_label)
        out_bits = []
        for i in range(32):
            out_bit = f"{out_label}-B{i}"
            self.emit(out_bit, in_bits[i], in_bits[i])
            out_bits.append(out_bit)
        self.register_word(out_label, out_bits)

    def convert_and(self, out_label, in_a, in_b):
        """Convert AND operation to NANDs."""
        a_bits = self.get_bits(in_a)
        b_bits = self.get_bits(in_b)
        out_bits = []
        for i in range(32):
            prefix = f"{out_label}-B{i}"
            result = self.and_gate(prefix, a_bits[i], b_bits[i])
            # Map to expected output label
            out_bit = f"{out_label}-B{i}"
            if result != out_bit:
                t = self.not_gate(prefix, result)
                self.emit(out_bit, t, t)
            out_bits.append(out_bit)
        self.register_word(out_label, out_bits)

    def convert_or(self, out_label, in_a, in_b):
        """Convert OR operation to NANDs."""
        a_bits = self.get_bits(in_a)
        b_bits = self.get_bits(in_b)
        out_bits = []
        for i in range(32):
            prefix = f"{out_label}-B{i}"
            result = self.or_gate(prefix, a_bits[i], b_bits[i])
            out_bit = f"{out_label}-B{i}"
            if result != out_bit:
                t = self.not_gate(prefix, result)
                self.emit(out_bit, t, t)
            out_bits.append(out_bit)
        self.register_word(out_label, out_bits)

    def convert_xor(self, out_label, in_a, in_b):
        """Convert XOR operation to NANDs."""
        a_bits = self.get_bits(in_a)
        b_bits = self.get_bits(in_b)
        out_bits = []
        for i in range(32):
            prefix = f"{out_label}-B{i}"
            nab = self.nand(prefix, a_bits[i], b_bits[i])
            t1 = self.nand(prefix, a_bits[i], nab)
            t2 = self.nand(prefix, b_bits[i], nab)
            out_bit = self.emit(f"{out_label}-B{i}", t1, t2)
            out_bits.append(out_bit)
        self.register_word(out_label, out_bits)

    def convert_maj(self, out_label, in_a, in_b, in_c):
        """Convert MAJ (majority) function using efficient 6-NAND implementation."""
        a_bits = self.get_bits(in_a)
        b_bits = self.get_bits(in_b)
        c_bits = self.get_bits(in_c)
        out_bits = []

        for i in range(32):
            prefix = f"{out_label}-B{i}"
            result = self.maj_gate(prefix, a_bits[i], b_bits[i], c_bits[i])
            out_bit = f"{out_label}-B{i}"
            if result != out_bit:
                t = self.not_gate(prefix, result)
                self.emit(out_bit, t, t)
            out_bits.append(out_bit)
        self.register_word(out_label, out_bits)

    def convert_ch(self, out_label, in_e, in_f, in_g):
        """Convert CH (choice) function."""
        e_bits = self.get_bits(in_e)
        f_bits = self.get_bits(in_f)
        g_bits = self.get_bits(in_g)
        out_bits = []

        for i in range(32):
            prefix = f"{out_label}-B{i}"
            result = self.ch_gate(prefix, e_bits[i], f_bits[i], g_bits[i])
            out_bit = f"{out_label}-B{i}"
            if result != out_bit:
                t = self.not_gate(prefix, result)
                self.emit(out_bit, t, t)
            out_bits.append(out_bit)
        self.register_word(out_label, out_bits)

    def convert_add(self, out_label, in_a, in_b):
        """Convert ADD operation to NANDs."""
        a_bits = self.get_bits(in_a)
        b_bits = self.get_bits(in_b)
        out_bits = []
        carry = "CONST-0"

        for i in range(32):
            prefix = f"{out_label}-B{i}"
            s, carry = self.full_adder(prefix, a_bits[i], b_bits[i], carry)
            out_bit = f"{out_label}-B{i}"
            if s != out_bit:
                t = self.not_gate(prefix, s)
                self.emit(out_bit, t, t)
            out_bits.append(out_bit)

        self.register_word(out_label, out_bits)

    def convert_rotr(self, out_label, in_label, n):
        """Convert ROTR - pure rewiring, no gates needed!"""
        in_bits = self.get_bits(in_label)
        out_bits = []
        for i in range(32):
            src_bit = (i + n) % 32
            # Just use the input bit directly - no copy needed
            out_bits.append(in_bits[src_bit])
        self.register_word(out_label, out_bits)

    def convert_shr(self, out_label, in_label, n):
        """Convert SHR - rewiring with zeros."""
        in_bits = self.get_bits(in_label)
        out_bits = []
        for i in range(32):
            src_idx = i + n
            if src_idx < 32:
                out_bits.append(in_bits[src_idx])
            else:
                out_bits.append("CONST-0")
        self.register_word(out_label, out_bits)

    def convert_copy(self, out_label, in_label):
        """Convert COPY - just alias, no gates needed."""
        in_bits = self.get_bits(in_label)
        self.register_word(out_label, in_bits)

    def convert_function(self, label, func, inputs):
        """Convert a single function to NANDs."""
        if func == "XOR":
            self.convert_xor(label, inputs[0], inputs[1])
        elif func == "AND":
            self.convert_and(label, inputs[0], inputs[1])
        elif func == "OR":
            self.convert_or(label, inputs[0], inputs[1])
        elif func == "NOT":
            self.convert_not(label, inputs[0])
        elif func == "ADD":
            self.convert_add(label, inputs[0], inputs[1])
        elif func == "COPY":
            self.convert_copy(label, inputs[0])
        elif func == "MAJ":
            self.convert_maj(label, inputs[0], inputs[1], inputs[2])
        elif func == "CH":
            self.convert_ch(label, inputs[0], inputs[1], inputs[2])
        elif func.startswith("ROTR"):
            n = int(func[4:])
            self.convert_rotr(label, inputs[0], n)
        elif func.startswith("SHR"):
            n = int(func[3:])
            self.convert_shr(label, inputs[0], n)
        else:
            raise ValueError(f"Unknown function: {func}")


def main():
    parser = argparse.ArgumentParser(description="Optimized functions to NAND converter")
    parser.add_argument("--input", "-i", default="functions.txt", help="Input file")
    parser.add_argument("--output", "-o", default="nands-optimized-new.txt", help="Output file")
    args = parser.parse_args()

    converter = OptimizedNandConverter()

    with open(args.input, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line:
                parts = line.split(',')
                label = parts[0]
                func = parts[1]
                inputs = parts[2:] if len(parts) > 2 else []
                converter.convert_function(label, func, inputs)

            if line_num % 500 == 0:
                print(f"Processed {line_num} functions...")

    with open(args.output, 'w') as f:
        for label, a, b in converter.nands:
            f.write(f"{label},{a},{b}\n")

    print(f"Generated {args.output} ({len(converter.nands)} NAND gates)")


if __name__ == "__main__":
    main()
