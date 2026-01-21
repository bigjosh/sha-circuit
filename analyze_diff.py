"""Analyze the differences word by word."""

import hashlib

def my_sha256(message):
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

    H_INIT = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    ]

    def rotr(x, n):
        return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF

    def shr(x, n):
        return x >> n

    h = list(H_INIT)

    msg_len = len(message)
    message += b'\x80'
    while (len(message) % 64) != 56:
        message += b'\x00'
    message += struct.pack('>Q', msg_len * 8)

    w = list(struct.unpack('>16I', message[:64]))
    for i in range(16, 64):
        s0 = rotr(w[i-15], 7) ^ rotr(w[i-15], 18) ^ shr(w[i-15], 3)
        s1 = rotr(w[i-2], 17) ^ rotr(w[i-2], 19) ^ shr(w[i-2], 10)
        w.append((w[i-16] + s0 + w[i-7] + s1) & 0xFFFFFFFF)

    a, b, c, d, e, f, g, hh = h

    for i in range(64):
        S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
        ch = (e & f) ^ ((~e & 0xFFFFFFFF) & g)
        temp1 = (hh + S1 + ch + K[i] + w[i]) & 0xFFFFFFFF
        S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        temp2 = (S0 + maj) & 0xFFFFFFFF

        hh = g
        g = f
        f = e
        e = (d + temp1) & 0xFFFFFFFF
        d = c
        c = b
        b = a
        a = (temp1 + temp2) & 0xFFFFFFFF

    final = [
        (h[0] + a) & 0xFFFFFFFF,
        (h[1] + b) & 0xFFFFFFFF,
        (h[2] + c) & 0xFFFFFFFF,
        (h[3] + d) & 0xFFFFFFFF,
        (h[4] + e) & 0xFFFFFFFF,
        (h[5] + f) & 0xFFFFFFFF,
        (h[6] + g) & 0xFFFFFFFF,
        (h[7] + hh) & 0xFFFFFFFF,
    ]

    return final


# Compare word by word for empty string
ref_hex = hashlib.sha256(b"").hexdigest()
ref_words = [int(ref_hex[i:i+8], 16) for i in range(0, 64, 8)]

my_words = my_sha256(b"")

print("Word-by-word comparison for empty string:")
print(f"Idx   Expected    Got         XOR diff")
for i in range(8):
    diff = ref_words[i] ^ my_words[i]
    match = "OK" if diff == 0 else ""
    print(f"{i}     {ref_words[i]:08x}    {my_words[i]:08x}    {diff:08x} {match}")

# Let's look at what the final working variables should be
# If H[0] = H_INIT[0] + a, then a = H[0] - H_INIT[0]
print()
print("Implied final working variables:")
H_INIT = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
var_names = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

print("Expected (from reference):")
for i in range(8):
    v = (ref_words[i] - H_INIT[i]) & 0xFFFFFFFF
    print(f"  {var_names[i]} = {v:08x}")

print()
print("Got (from my implementation):")
for i in range(8):
    v = (my_words[i] - H_INIT[i]) & 0xFFFFFFFF
    print(f"  {var_names[i]} = {v:08x}")
