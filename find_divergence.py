"""Find where my implementation diverges from the reference."""

import struct

K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f9, 0xc67178f2
]

H_INIT = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]


def rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF


def shr(x, n):
    return x >> n


# Compute using Python hashlib internals...
# Actually, let's use the reference implementation from PyCryptodome which we can instrument

# Better yet, let me use a pure Python implementation known to work
# From https://github.com/keanemind/Python-SHA-256

def sha256_reference():
    """Reference implementation from a known-working source."""
    import hashlib
    # Can't instrument hashlib, so let's use a different approach

    # Let me implement SHA-256 using an alternative formula and compare

    # Actually, let's just carefully verify my W schedule

    message = b""

    # Pad
    msg_len = len(message)
    message += b'\x80'
    while (len(message) % 64) != 56:
        message += b'\x00'
    message += struct.pack('>Q', msg_len * 8)

    # Parse
    w = list(struct.unpack('>16I', message[:64]))

    print("W schedule comparison:")
    print("My W values vs what they should be:")

    # For empty message, W[0] = 0x80000000, W[1..14] = 0, W[15] = 0
    expected_w = [0x80000000] + [0] * 14 + [0]

    for i in range(16):
        match = "OK" if w[i] == expected_w[i] else f"MISMATCH (expected {expected_w[i]:08x})"
        print(f"  W[{i:2d}] = {w[i]:08x} {match}")

    # Extend
    for i in range(16, 64):
        s0 = rotr(w[i-15], 7) ^ rotr(w[i-15], 18) ^ shr(w[i-15], 3)
        s1 = rotr(w[i-2], 17) ^ rotr(w[i-2], 19) ^ shr(w[i-2], 10)
        w.append((w[i-16] + s0 + w[i-7] + s1) & 0xFFFFFFFF)

    print()
    print("Extended W values (sampling):")
    for i in [16, 17, 18, 30, 31, 32, 62, 63]:
        print(f"  W[{i:2d}] = {w[i]:08x}")

    # Check W[63] which reference says is 996066459 = 0x3b5ec49b
    print()
    print(f"W[63]: mine={w[63]:08x} ref=3b5ec49b match={w[63] == 0x3b5ec49b}")

    return w


sha256_reference()
