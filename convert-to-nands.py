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
        """Full adder: returns (sum, cout)"""
        # sum = a XOR b XOR cin
        ab_xor = self.xor_gate(prefix, a, b)
        s = self.xor_gate(prefix, ab_xor, cin)
        # cout = (a AND b) OR (cin AND (a XOR b))
        ab_and = self.and_gate(prefix, a, b)
        cin_ab = self.and_gate(prefix, cin, ab_xor)
        cout = self.or_gate(prefix, ab_and, cin_ab)
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
            # Rename sum to final output bit label
            out_bit = f"{out_label}-B{i}"
            self.emit(out_bit, s, s)  # NAND(s,s) = NOT(s), then we need s
            # Actually, just alias it - but we can't alias in NAND-only
            # So we use double-NOT: NOT(NOT(s)) = s
            out_bits.append(s)  # Use s directly since it's already labeled

        # Re-register with correct bit labels
        # The full_adder returns temp labels, we need to map them
        final_bits = []
        for i, s in enumerate(out_bits):
            out_bit = f"{out_label}-B{i}"
            # Double NOT to copy: NOT(NOT(x)) = x
            t = self.emit(self.temp_label(f"{out_label}-B{i}"), s, s)
            self.emit(out_bit, t, t)
            final_bits.append(out_bit)

        self.register_word(out_label, final_bits)

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
