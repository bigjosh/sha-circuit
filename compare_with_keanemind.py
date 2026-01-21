"""Compare my implementation with keanemind's working implementation."""

import struct

# My constants
MY_K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f9, 0xc67178f2
]

MY_H_INIT = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]


def my_rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF


def my_sha256_rounds(message):
    """Return state after each round."""
    H = list(MY_H_INIT)

    ml = len(message) * 8
    message = bytearray(message)
    message.append(0x80)
    while len(message) % 64 != 56:
        message.append(0x00)
    message.extend(ml.to_bytes(8, 'big'))

    W = list(struct.unpack('>16I', bytes(message[:64])))
    for j in range(16, 64):
        s0 = my_rotr(W[j-15], 7) ^ my_rotr(W[j-15], 18) ^ (W[j-15] >> 3)
        s1 = my_rotr(W[j-2], 17) ^ my_rotr(W[j-2], 19) ^ (W[j-2] >> 10)
        W.append((W[j-16] + s0 + W[j-7] + s1) & 0xFFFFFFFF)

    a, b, c, d, e, f, g, h = H
    states = [(a, b, c, d, e, f, g, h)]

    for j in range(64):
        S1 = my_rotr(e, 6) ^ my_rotr(e, 11) ^ my_rotr(e, 25)
        ch = (e & f) ^ ((~e & 0xFFFFFFFF) & g)
        temp1 = (h + S1 + ch + MY_K[j] + W[j]) & 0xFFFFFFFF
        S0 = my_rotr(a, 2) ^ my_rotr(a, 13) ^ my_rotr(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        temp2 = (S0 + maj) & 0xFFFFFFFF

        h = g
        g = f
        f = e
        e = (d + temp1) & 0xFFFFFFFF
        d = c
        c = b
        b = a
        a = (temp1 + temp2) & 0xFFFFFFFF

        states.append((a, b, c, d, e, f, g, h))

    return states, W


# Keanemind's functions
def _rotate_right(num, shift, size=32):
    return (num >> shift) | (num << size - shift)

def _sigma0(num):
    return (_rotate_right(num, 7) ^ _rotate_right(num, 18) ^ (num >> 3))

def _sigma1(num):
    return (_rotate_right(num, 17) ^ _rotate_right(num, 19) ^ (num >> 10))

def _capsigma0(num):
    return (_rotate_right(num, 2) ^ _rotate_right(num, 13) ^ _rotate_right(num, 22))

def _capsigma1(num):
    return (_rotate_right(num, 6) ^ _rotate_right(num, 11) ^ _rotate_right(num, 25))

def _ch(x, y, z):
    return (x & y) ^ (~x & z)

def _maj(x, y, z):
    return (x & y) ^ (x & z) ^ (y & z)


KEANE_K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
]


def keane_sha256_rounds(message):
    """Keanemind's implementation with round states."""
    if isinstance(message, str):
        message = bytearray(message, 'ascii')
    elif isinstance(message, bytes):
        message = bytearray(message)

    length = len(message) * 8
    message.append(0x80)
    while (len(message) * 8 + 64) % 512 != 0:
        message.append(0x00)
    message += length.to_bytes(8, 'big')

    blocks = []
    for i in range(0, len(message), 64):
        blocks.append(message[i:i+64])

    h0 = 0x6a09e667
    h1 = 0xbb67ae85
    h2 = 0x3c6ef372
    h3 = 0xa54ff53a
    h5 = 0x9b05688c  # Note: h4 and h5 are swapped in assignment
    h4 = 0x510e527f
    h6 = 0x1f83d9ab
    h7 = 0x5be0cd19

    for message_block in blocks:
        message_schedule = []
        for t in range(0, 64):
            if t <= 15:
                message_schedule.append(bytes(message_block[t*4:(t*4)+4]))
            else:
                term1 = _sigma1(int.from_bytes(message_schedule[t-2], 'big'))
                term2 = int.from_bytes(message_schedule[t-7], 'big')
                term3 = _sigma0(int.from_bytes(message_schedule[t-15], 'big'))
                term4 = int.from_bytes(message_schedule[t-16], 'big')
                schedule = ((term1 + term2 + term3 + term4) % 2**32).to_bytes(4, 'big')
                message_schedule.append(schedule)

        W = [int.from_bytes(w, 'big') for w in message_schedule]

        a = h0
        b = h1
        c = h2
        d = h3
        e = h4
        f = h5
        g = h6
        h = h7

        states = [(a, b, c, d, e, f, g, h)]

        for t in range(64):
            t1 = ((h + _capsigma1(e) + _ch(e, f, g) + KEANE_K[t] +
                   int.from_bytes(message_schedule[t], 'big')) % 2**32)
            t2 = (_capsigma0(a) + _maj(a, b, c)) % 2**32

            h = g
            g = f
            f = e
            e = (d + t1) % 2**32
            d = c
            c = b
            b = a
            a = (t1 + t2) % 2**32

            states.append((a, b, c, d, e, f, g, h))

        return states, W


# Compare
my_states, my_W = my_sha256_rounds(b"")
keane_states, keane_W = keane_sha256_rounds(b"")

print("Comparing W schedules:")
for i in range(64):
    match = "OK" if my_W[i] == keane_W[i] else "MISMATCH"
    if my_W[i] != keane_W[i]:
        print(f"  W[{i}]: mine={my_W[i]:08x} keane={keane_W[i]:08x} {match}")
print("W schedule match:", my_W == keane_W)
print()

print("Comparing round states:")
first_diff = None
for i in range(65):
    my_state = my_states[i]
    keane_state = keane_states[i]
    if my_state != keane_state:
        if first_diff is None:
            first_diff = i
        if i <= first_diff + 2 or i >= 63:
            print(f"State {i} (after round {i-1 if i > 0 else 'init'}):")
            print(f"  Mine:  a={my_state[0]:08x} b={my_state[1]:08x} c={my_state[2]:08x} d={my_state[3]:08x}")
            print(f"         e={my_state[4]:08x} f={my_state[5]:08x} g={my_state[6]:08x} h={my_state[7]:08x}")
            print(f"  Keane: a={keane_state[0]:08x} b={keane_state[1]:08x} c={keane_state[2]:08x} d={keane_state[3]:08x}")
            print(f"         e={keane_state[4]:08x} f={keane_state[5]:08x} g={keane_state[6]:08x} h={keane_state[7]:08x}")
