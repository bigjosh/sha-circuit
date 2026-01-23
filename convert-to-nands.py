#!/usr/bin/env python3
"""
Convert functions.txt to NAND-only representation.

Reads functions.txt and outputs nands.txt where each line is a NAND gate:
    label,inputA,inputB

Usage:
    python convert-to-nands.py
    python convert-to-nands.py -o nands.txt
"""

import argparse


class NandConverter:
    def __init__(self):
        self.nands = []  # List of (label, inputA, inputB)
        self.counter = 0  # For generating unique intermediate labels
        # Maps word-level labels to their bit-level equivalents
        # e.g., "INPUT-W0" -> ["INPUT-W0-B0", "INPUT-W0-B1", ..., "INPUT-W0-B31"]
        self.word_bits = {}

    def temp_label(self, prefix):
        """Generate a unique temporary label."""
        self.counter += 1
        return f"{prefix}-T{self.counter}"

    def emit(self, label, a, b):
        """Emit a NAND gate."""
        self.nands.append((label, a, b))
        return label

    def nand(self, prefix, a, b):
        """Create a NAND gate with auto-generated label."""
        return self.emit(self.temp_label(prefix), a, b)

    def not_gate(self, prefix, a):
        """NOT(A) = NAND(A, A)"""
        return self.emit(self.temp_label(prefix), a, a)

    def and_gate(self, prefix, a, b):
        """AND(A, B) = NOT(NAND(A, B))"""
        t = self.nand(prefix, a, b)
        return self.not_gate(prefix, t)

    def or_gate(self, prefix, a, b):
        """OR(A, B) = NAND(NOT(A), NOT(B))"""
        na = self.not_gate(prefix, a)
        nb = self.not_gate(prefix, b)
        return self.nand(prefix, na, nb)

    def xor_gate(self, prefix, a, b):
        """XOR(A, B) = NAND(NAND(A, NAND(A,B)), NAND(B, NAND(A,B)))"""
        nab = self.nand(prefix, a, b)
        t1 = self.nand(prefix, a, nab)
        t2 = self.nand(prefix, b, nab)
        return self.nand(prefix, t1, t2)

    def half_adder(self, prefix, a, b):
        """Half adder: returns (sum, carry)"""
        s = self.xor_gate(prefix, a, b)
        c = self.and_gate(prefix, a, b)
        return s, c

    def full_adder(self, prefix, a, b, cin):
        """Optimized full adder: 13 NANDs (was 15).

        Uses shared intermediate values to reduce gate count:
        - XOR(a,b) computation includes NAND(a,b) which is reused for AND(a,b)
        - XOR result with cin includes NAND(xor,cin) which is reused for AND(cin,xor)
        """
        # XOR(a,b) - 4 gates
        nand_ab = self.nand(prefix, a, b)
        t1 = self.nand(prefix, a, nand_ab)
        t2 = self.nand(prefix, b, nand_ab)
        xor_ab = self.nand(prefix, t1, t2)

        # XOR(xor_ab, cin) for sum - 4 gates
        nand_xor_cin = self.nand(prefix, xor_ab, cin)
        t3 = self.nand(prefix, xor_ab, nand_xor_cin)
        t4 = self.nand(prefix, cin, nand_xor_cin)
        s = self.nand(prefix, t3, t4)

        # AND(a,b) - 1 gate (reuses nand_ab from XOR)
        and_ab = self.nand(prefix, nand_ab, nand_ab)

        # AND(cin, xor_ab) - 1 gate (reuses nand_xor_cin from XOR)
        and_cin = self.nand(prefix, nand_xor_cin, nand_xor_cin)

        # OR(and_ab, and_cin) for cout - 3 gates
        t5 = self.nand(prefix, and_ab, and_ab)
        t6 = self.nand(prefix, and_cin, and_cin)
        cout = self.nand(prefix, t5, t6)

        return s, cout

    def register_word(self, label, bit_labels):
        """Register a word-level label with its bit labels."""
        self.word_bits[label] = bit_labels

    def get_bits(self, label):
        """Get bit labels for a word-level label."""
        if label in self.word_bits:
            return self.word_bits[label]
        # Assume it's an input/constant that follows naming convention
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
            t = self.nand(prefix, a_bits[i], b_bits[i])
            out_bit = self.emit(f"{out_label}-B{i}", t, t)
            out_bits.append(out_bit)
        self.register_word(out_label, out_bits)

    def convert_or(self, out_label, in_a, in_b):
        """Convert OR operation to NANDs."""
        a_bits = self.get_bits(in_a)
        b_bits = self.get_bits(in_b)
        out_bits = []
        for i in range(32):
            prefix = f"{out_label}-B{i}"
            na = self.not_gate(prefix, a_bits[i])
            nb = self.not_gate(prefix, b_bits[i])
            out_bit = self.emit(f"{out_label}-B{i}", na, nb)
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

    def convert_add(self, out_label, in_a, in_b):
        """Convert ADD operation to NANDs (ripple-carry adder)."""
        a_bits = self.get_bits(in_a)
        b_bits = self.get_bits(in_b)
        out_bits = []
        carry = "CONST-0"  # Initial carry is 0

        for i in range(32):
            prefix = f"{out_label}-B{i}"
            s, carry = self.full_adder(prefix, a_bits[i], b_bits[i], carry)
            # full_adder returns a temp label for sum, copy to final label
            out_bit = f"{out_label}-B{i}"
            # Double NOT to copy: NOT(NOT(x)) = x
            t = self.emit(self.temp_label(prefix), s, s)
            self.emit(out_bit, t, t)
            out_bits.append(out_bit)

        self.register_word(out_label, out_bits)

    def convert_rotr(self, out_label, in_label, n):
        """Convert ROTR operation - pure rewiring."""
        in_bits = self.get_bits(in_label)
        out_bits = []
        for i in range(32):
            # Output bit i = input bit (i + n) % 32
            src_bit = (i + n) % 32
            out_bit = f"{out_label}-B{i}"
            # Double NOT to "copy" the bit
            t = self.emit(self.temp_label(f"{out_label}-B{i}"), in_bits[src_bit], in_bits[src_bit])
            self.emit(out_bit, t, t)
            out_bits.append(out_bit)
        self.register_word(out_label, out_bits)

    def convert_shr(self, out_label, in_label, n):
        """Convert SHR operation - rewiring with zeros."""
        in_bits = self.get_bits(in_label)
        out_bits = []
        for i in range(32):
            out_bit = f"{out_label}-B{i}"
            src_idx = i + n
            if src_idx < 32:
                # Copy from input
                t = self.emit(self.temp_label(f"{out_label}-B{i}"), in_bits[src_idx], in_bits[src_idx])
                self.emit(out_bit, t, t)
            else:
                # Zero - double NOT of CONST-0
                t = self.emit(self.temp_label(f"{out_label}-B{i}"), "CONST-0", "CONST-0")
                self.emit(out_bit, t, t)
            out_bits.append(out_bit)
        self.register_word(out_label, out_bits)

    def convert_copy(self, out_label, in_label):
        """Convert COPY operation - double NOT each bit."""
        in_bits = self.get_bits(in_label)
        out_bits = []
        for i in range(32):
            out_bit = f"{out_label}-B{i}"
            t = self.emit(self.temp_label(f"{out_label}-B{i}"), in_bits[i], in_bits[i])
            self.emit(out_bit, t, t)
            out_bits.append(out_bit)
        self.register_word(out_label, out_bits)

    def convert_ch(self, out_label, e_label, f_label, g_label):
        """Convert CH operation to optimal 4-NAND form.

        CH(e,f,g) = (e AND f) XOR ((NOT e) AND g)
        Equivalent to: if e then f else g (2:1 MUX)

        Optimal 4-NAND implementation per bit:
        1. nand_ef = NAND(e, f)
        2. not_e = NAND(e, e)
        3. nand_noteg = NAND(not_e, g)
        4. result = NAND(nand_ef, nand_noteg)

        Saves 5 NANDs per bit vs standard implementation (9 → 4).
        """
        e_bits = self.get_bits(e_label)
        f_bits = self.get_bits(f_label)
        g_bits = self.get_bits(g_label)
        out_bits = []

        for i in range(32):
            prefix = f"{out_label}-B{i}"

            # 1. NAND(e, f)
            nand_ef = self.nand(prefix, e_bits[i], f_bits[i])

            # 2. NOT(e) = NAND(e, e)
            not_e = self.nand(prefix, e_bits[i], e_bits[i])

            # 3. NAND(NOT(e), g)
            nand_noteg = self.nand(prefix, not_e, g_bits[i])

            # 4. result = NAND(nand_ef, nand_noteg)
            out_bit = f"{out_label}-B{i}"
            self.emit(out_bit, nand_ef, nand_noteg)
            out_bits.append(out_bit)

        self.register_word(out_label, out_bits)

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
        elif func == "CH":
            self.convert_ch(label, inputs[0], inputs[1], inputs[2])
        elif func == "COPY":
            self.convert_copy(label, inputs[0])
        elif func.startswith("ROTR"):
            n = int(func[4:])
            self.convert_rotr(label, inputs[0], n)
        elif func.startswith("SHR"):
            n = int(func[3:])
            self.convert_shr(label, inputs[0], n)
        else:
            raise ValueError(f"Unknown function: {func}")


def main():
    parser = argparse.ArgumentParser(description="Convert functions.txt to NAND gates")
    parser.add_argument("--input", "-i", default="functions.txt", help="Input file")
    parser.add_argument("--output", "-o", default="nands.txt", help="Output file")
    args = parser.parse_args()

    converter = NandConverter()

    # Process functions.txt
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

    # Write output
    with open(args.output, 'w') as f:
        for label, a, b in converter.nands:
            f.write(f"{label},{a},{b}\n")

    print(f"Generated {args.output} ({len(converter.nands)} NAND gates)")


if __name__ == "__main__":
    main()
