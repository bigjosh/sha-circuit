"""
SHA-256 Circuit Generator

Generates a circuit representation of SHA-256 as three files:
- input.txt: 16 input words (INPUT-W0 through INPUT-W15)
- constants.txt: Round constants (K0-K63) and initial hash values (H0-H7)
- functions.txt: All bit-level operations with human-readable labels

All values are 32-bit unsigned integers, exported as zero-padded hex strings.
Function nodes use bit-level logic: AND, OR, XOR, NOT
"""

# SHA-256 Constants
K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2  # K[62] = 0xbef9a3f7
]

# Initial hash values
H_INIT = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
]


class CircuitGenerator:
    def __init__(self):
        self.functions = []  # List of (label, function, [inputs])
        self.node_counter = 0

    def add_function(self, label, func, inputs):
        """Add a function node to the circuit."""
        self.functions.append((label, func, inputs))
        return label

    def make_temp_label(self, prefix):
        """Generate a unique temporary label."""
        self.node_counter += 1
        return f"{prefix}-T{self.node_counter}"

    # Bit-level primitives
    def bit_xor(self, label, a, b):
        """XOR two 32-bit values (bit by bit)."""
        return self.add_function(label, "XOR", [a, b])

    def bit_and(self, label, a, b):
        """AND two 32-bit values (bit by bit)."""
        return self.add_function(label, "AND", [a, b])

    def bit_or(self, label, a, b):
        """OR two 32-bit values (bit by bit)."""
        return self.add_function(label, "OR", [a, b])

    def bit_not(self, label, a):
        """NOT a 32-bit value (bit by bit)."""
        return self.add_function(label, "NOT", [a])

    def xor3(self, label_prefix, a, b, c):
        """XOR three values."""
        t1 = self.bit_xor(f"{label_prefix}-XOR1", a, b)
        return self.bit_xor(f"{label_prefix}-XOR2", t1, c)

    # SHA-256 specific operations
    def rotr(self, label_prefix, x, n):
        """Right rotate by n bits: ROTR(x, n) = (x >> n) | (x << (32-n))."""
        # For circuit representation, ROTR is a rewiring operation
        # We represent it as a function that the evaluator understands
        return self.add_function(f"{label_prefix}-ROTR{n}", f"ROTR{n}", [x])

    def shr(self, label_prefix, x, n):
        """Right shift by n bits: SHR(x, n) = x >> n."""
        return self.add_function(f"{label_prefix}-SHR{n}", f"SHR{n}", [x])

    def add32(self, label_prefix, a, b):
        """32-bit addition modulo 2^32."""
        # Addition is complex at bit level - we'll use ADD as a primitive
        # that the evaluator implements as ripple-carry or similar
        return self.add_function(f"{label_prefix}-ADD", "ADD", [a, b])

    def add32_multi(self, label_prefix, values):
        """Add multiple 32-bit values."""
        if len(values) == 0:
            raise ValueError("Need at least one value")
        if len(values) == 1:
            return values[0]

        result = values[0]
        for i, v in enumerate(values[1:], 1):
            result = self.add32(f"{label_prefix}-S{i}", result, v)
        return result

    # SHA-256 functions
    def ch(self, label_prefix, x, y, z):
        """Ch(x,y,z) = (x AND y) XOR (NOT x AND z)."""
        xy = self.bit_and(f"{label_prefix}-CH-XY", x, y)
        not_x = self.bit_not(f"{label_prefix}-CH-NX", x)
        not_x_z = self.bit_and(f"{label_prefix}-CH-NXZ", not_x, z)
        return self.bit_xor(f"{label_prefix}-CH", xy, not_x_z)

    def maj(self, label_prefix, x, y, z):
        """Maj(x,y,z) = (x AND y) XOR (x AND z) XOR (y AND z)."""
        xy = self.bit_and(f"{label_prefix}-MAJ-XY", x, y)
        xz = self.bit_and(f"{label_prefix}-MAJ-XZ", x, z)
        yz = self.bit_and(f"{label_prefix}-MAJ-YZ", y, z)
        t1 = self.bit_xor(f"{label_prefix}-MAJ-T1", xy, xz)
        return self.bit_xor(f"{label_prefix}-MAJ", t1, yz)

    def sigma0(self, label_prefix, x):
        """Σ0(x) = ROTR(x,2) XOR ROTR(x,13) XOR ROTR(x,22)."""
        r2 = self.rotr(f"{label_prefix}-S0", x, 2)
        r13 = self.rotr(f"{label_prefix}-S0", x, 13)
        r22 = self.rotr(f"{label_prefix}-S0", x, 22)
        return self.xor3(f"{label_prefix}-S0", r2, r13, r22)

    def sigma1(self, label_prefix, x):
        """Σ1(x) = ROTR(x,6) XOR ROTR(x,11) XOR ROTR(x,25)."""
        r6 = self.rotr(f"{label_prefix}-S1", x, 6)
        r11 = self.rotr(f"{label_prefix}-S1", x, 11)
        r25 = self.rotr(f"{label_prefix}-S1", x, 25)
        return self.xor3(f"{label_prefix}-S1", r6, r11, r25)

    def sigma0_small(self, label_prefix, x):
        """σ0(x) = ROTR(x,7) XOR ROTR(x,18) XOR SHR(x,3)."""
        r7 = self.rotr(f"{label_prefix}-s0", x, 7)
        r18 = self.rotr(f"{label_prefix}-s0", x, 18)
        s3 = self.shr(f"{label_prefix}-s0", x, 3)
        return self.xor3(f"{label_prefix}-s0", r7, r18, s3)

    def sigma1_small(self, label_prefix, x):
        """σ1(x) = ROTR(x,17) XOR ROTR(x,19) XOR SHR(x,10)."""
        r17 = self.rotr(f"{label_prefix}-s1", x, 17)
        r19 = self.rotr(f"{label_prefix}-s1", x, 19)
        s10 = self.shr(f"{label_prefix}-s1", x, 10)
        return self.xor3(f"{label_prefix}-s1", r17, r19, s10)

    def generate_message_schedule(self):
        """Generate the 64-word message schedule W[0..63]."""
        W = []

        # W[0..15] = input words
        for i in range(16):
            W.append(f"INPUT-W{i}")

        # W[16..63] = σ1(W[i-2]) + W[i-7] + σ0(W[i-15]) + W[i-16]
        for i in range(16, 64):
            prefix = f"W{i}"

            s1 = self.sigma1_small(prefix, W[i-2])
            s0 = self.sigma0_small(prefix, W[i-15])

            # W[i] = σ1(W[i-2]) + W[i-7] + σ0(W[i-15]) + W[i-16]
            w_new = self.add32_multi(prefix, [s1, W[i-7], s0, W[i-16]])

            # Give the final W value a clear label
            final_label = f"MSG-W{i}"
            self.add_function(final_label, "COPY", [w_new])
            W.append(final_label)

        return W

    def generate_compression(self, W):
        """Generate the 64 rounds of compression."""
        # Initialize working variables from initial hash constants
        a, b, c, d, e, f, g, h = [f"H-INIT-{i}" for i in range(8)]

        for i in range(64):
            prefix = f"R{i}"

            # T1 = h + Σ1(e) + Ch(e,f,g) + K[i] + W[i]
            s1 = self.sigma1(prefix, e)
            ch = self.ch(prefix, e, f, g)
            t1 = self.add32_multi(f"{prefix}-T1", [h, s1, ch, f"K-{i}", W[i]])

            # T2 = Σ0(a) + Maj(a,b,c)
            s0 = self.sigma0(prefix, a)
            maj = self.maj(prefix, a, b, c)
            t2 = self.add32(f"{prefix}-T2", s0, maj)

            # Update working variables
            h_new = g
            g_new = f
            f_new = e
            e_new = self.add32(f"{prefix}-E", d, t1)
            d_new = c
            c_new = b
            b_new = a
            a_new = self.add32(f"{prefix}-A", t1, t2)

            # Create labeled copies for clarity
            self.add_function(f"{prefix}-VAR-A", "COPY", [a_new])
            self.add_function(f"{prefix}-VAR-B", "COPY", [b_new])
            self.add_function(f"{prefix}-VAR-C", "COPY", [c_new])
            self.add_function(f"{prefix}-VAR-D", "COPY", [d_new])
            self.add_function(f"{prefix}-VAR-E", "COPY", [e_new])
            self.add_function(f"{prefix}-VAR-F", "COPY", [f_new])
            self.add_function(f"{prefix}-VAR-G", "COPY", [g_new])
            self.add_function(f"{prefix}-VAR-H", "COPY", [h_new])

            a = f"{prefix}-VAR-A"
            b = f"{prefix}-VAR-B"
            c = f"{prefix}-VAR-C"
            d = f"{prefix}-VAR-D"
            e = f"{prefix}-VAR-E"
            f_var = f"{prefix}-VAR-F"
            g = f"{prefix}-VAR-G"
            h = f"{prefix}-VAR-H"
            f = f_var  # Rename to avoid conflict with Python's f-string

        return a, b, c, d, e, f, g, h

    def generate_final_hash(self, final_vars):
        """Add final working variables to initial hash values for output."""
        a, b, c, d, e, f, g, h = final_vars
        var_labels = [a, b, c, d, e, f, g, h]

        for i in range(8):
            result = self.add32(f"FINAL-H{i}", f"H-INIT-{i}", var_labels[i])
            self.add_function(f"OUTPUT-W{i}", "COPY", [result])

    def generate(self):
        """Generate the complete SHA-256 circuit."""
        W = self.generate_message_schedule()
        final_vars = self.generate_compression(W)
        self.generate_final_hash(final_vars)
        return self.functions


def generate_input_file(message=b""):
    """Generate input.txt with padded message block."""
    # Pad message according to SHA-256 spec
    ml = len(message) * 8  # Message length in bits

    # Append bit '1' to message
    padded = message + b'\x80'

    # Append zeros until message is 448 bits (mod 512) = 56 bytes (mod 64)
    while len(padded) % 64 != 56:
        padded += b'\x00'

    # Append original length as 64-bit big-endian
    padded += ml.to_bytes(8, 'big')

    # Convert to 32-bit words
    words = []
    for i in range(0, 64, 4):
        word = int.from_bytes(padded[i:i+4], 'big')
        words.append(word)

    lines = []
    for i, word in enumerate(words):
        lines.append(f"INPUT-W{i},{word:08x}")

    return lines


def generate_constants_file():
    """Generate constants.txt with round constants and initial hash values."""
    lines = []

    # Round constants K[0..63]
    for i, k in enumerate(K):
        lines.append(f"K-{i},{k:08x}")

    # Initial hash values H[0..7]
    for i, h in enumerate(H_INIT):
        lines.append(f"H-INIT-{i},{h:08x}")

    return lines


def generate_functions_file():
    """Generate functions.txt with all circuit operations."""
    gen = CircuitGenerator()
    functions = gen.generate()

    lines = []
    for label, func, inputs in functions:
        line = f"{label},{func},{','.join(inputs)}"
        lines.append(line)

    return lines


def write_files(output_dir=".", message=b""):
    """Write all three circuit files."""
    import os

    os.makedirs(output_dir, exist_ok=True)

    # Write input.txt
    input_lines = generate_input_file(message)
    with open(os.path.join(output_dir, "input.txt"), "w") as f:
        f.write("\n".join(input_lines))

    # Write constants.txt
    const_lines = generate_constants_file()
    with open(os.path.join(output_dir, "constants.txt"), "w") as f:
        f.write("\n".join(const_lines))

    # Write functions.txt
    func_lines = generate_functions_file()
    with open(os.path.join(output_dir, "functions.txt"), "w") as f:
        f.write("\n".join(func_lines))

    print(f"Generated files in {output_dir}:")
    print(f"  input.txt: {len(input_lines)} lines")
    print(f"  constants.txt: {len(const_lines)} lines")
    print(f"  functions.txt: {len(func_lines)} lines")


if __name__ == "__main__":
    import sys

    message = b"josh" if len(sys.argv) < 2 else sys.argv[1].encode()
    output_dir = "." if len(sys.argv) < 3 else sys.argv[2]

    write_files(output_dir, message)
