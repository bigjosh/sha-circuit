"""Debug SHA-256 implementation step by step."""

import hashlib

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
    0x90befffa, 0xa4506ceb, 0xbef9a3f9, 0xc67178f2
]

H_INIT = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
]


def rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF


def shr(x, n):
    return x >> n


def ch(x, y, z):
    return (x & y) ^ ((~x) & z)


def maj(x, y, z):
    return (x & y) ^ (x & z) ^ (y & z)


def sigma0(x):
    return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22)


def sigma1(x):
    return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25)


def sigma0_small(x):
    return rotr(x, 7) ^ rotr(x, 18) ^ shr(x, 3)


def sigma1_small(x):
    return rotr(x, 17) ^ rotr(x, 19) ^ shr(x, 10)


def sha256_single_block(message_bytes):
    """Compute SHA-256 for a single block (for debugging)."""
    # Pad the message
    ml = len(message_bytes) * 8
    padded = message_bytes + b'\x80'
    while len(padded) % 64 != 56:
        padded += b'\x00'
    padded += ml.to_bytes(8, 'big')

    # Parse into 32-bit words
    W = []
    for i in range(0, 64, 4):
        W.append(int.from_bytes(padded[i:i+4], 'big'))

    print("Input words W[0..15]:")
    for i in range(16):
        print(f"  W[{i}] = {W[i]:08x}")

    # Extend to 64 words
    for i in range(16, 64):
        s0 = sigma0_small(W[i-15])
        s1 = sigma1_small(W[i-2])
        W.append((W[i-16] + s0 + W[i-7] + s1) & 0xFFFFFFFF)

    print("\nMessage schedule W[16..63]:")
    for i in range(16, 64):
        print(f"  W[{i}] = {W[i]:08x}")

    # Initialize working variables
    a, b, c, d, e, f, g, h = H_INIT

    print(f"\nInitial state: a={a:08x} b={b:08x} c={c:08x} d={d:08x}")
    print(f"               e={e:08x} f={f:08x} g={g:08x} h={h:08x}")

    # Compression rounds
    for i in range(64):
        S1 = sigma1(e)
        ch_val = ch(e, f, g)
        temp1 = (h + S1 + ch_val + K[i] + W[i]) & 0xFFFFFFFF
        S0 = sigma0(a)
        maj_val = maj(a, b, c)
        temp2 = (S0 + maj_val) & 0xFFFFFFFF

        h = g
        g = f
        f = e
        e = (d + temp1) & 0xFFFFFFFF
        d = c
        c = b
        b = a
        a = (temp1 + temp2) & 0xFFFFFFFF

        if i < 4 or i >= 60:
            print(f"Round {i:2d}: a={a:08x} b={b:08x} c={c:08x} d={d:08x} e={e:08x} f={f:08x} g={g:08x} h={h:08x}")

    # Final hash
    H = [
        (H_INIT[0] + a) & 0xFFFFFFFF,
        (H_INIT[1] + b) & 0xFFFFFFFF,
        (H_INIT[2] + c) & 0xFFFFFFFF,
        (H_INIT[3] + d) & 0xFFFFFFFF,
        (H_INIT[4] + e) & 0xFFFFFFFF,
        (H_INIT[5] + f) & 0xFFFFFFFF,
        (H_INIT[6] + g) & 0xFFFFFFFF,
        (H_INIT[7] + h) & 0xFFFFFFFF,
    ]

    hash_str = ''.join(f'{x:08x}' for x in H)
    return hash_str


if __name__ == "__main__":
    message = b"josh"
    print(f"Message: {message}")
    print(f"Reference: {hashlib.sha256(message).hexdigest()}")
    print()
    result = sha256_single_block(message)
    print(f"\nComputed: {result}")
