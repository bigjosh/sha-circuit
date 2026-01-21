"""Binary search for first diverging round."""

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


# Compute W
message = bytearray(b"")
ml = 0
message.append(0x80)
while len(message) % 64 != 56:
    message.append(0x00)
message.extend(ml.to_bytes(8, 'big'))

W = list(struct.unpack('>16I', bytes(message)))
for j in range(16, 64):
    s0 = rotr(W[j-15], 7) ^ rotr(W[j-15], 18) ^ (W[j-15] >> 3)
    s1 = rotr(W[j-2], 17) ^ rotr(W[j-2], 19) ^ (W[j-2] >> 10)
    W.append((W[j-16] + s0 + W[j-7] + s1) & 0xFFFFFFFF)

# Reference values from gist:
# Round 1 (index 0): [2080933965, 1779033703, 3144134277, 1013904242, 415752866, 1359893119, 2600822924, 528734635]
# Round 2 (index 1): [2632279248, 2080933965, 1779033703, 3144134277, 536982102, 415752866, 1359893119, 2600822924]
# Round 64 (index 63): [2040978907, 3717492111, 1586299222, 4095722474, 3600805733, 3382061760, 2232532848, 477227836]

ref_states = {
    0: [2080933965, 1779033703, 3144134277, 1013904242, 415752866, 1359893119, 2600822924, 528734635],
    1: [2632279248, 2080933965, 1779033703, 3144134277, 536982102, 415752866, 1359893119, 2600822924],
    63: [2040978907, 3717492111, 1586299222, 4095722474, 3600805733, 3382061760, 2232532848, 477227836],
}

# Run my implementation and compare
a, b, c, d, e, f, g, h = H_INIT

first_diverge = None
for j in range(64):
    S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
    ch = (e & f) ^ ((~e & 0xFFFFFFFF) & g)
    temp1 = (h + S1 + ch + K[j] + W[j]) & 0xFFFFFFFF
    S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
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

    state = [a, b, c, d, e, f, g, h]

    if j in ref_states:
        ref = ref_states[j]
        match = state == ref
        status = "OK" if match else "MISMATCH"
        print(f"Round {j:2d}: {status}")
        if not match:
            print(f"  Mine: {[f'{x:08x}' for x in state]}")
            print(f"  Ref:  {[f'{x:08x}' for x in ref]}")

    # Check for first divergence from known pattern
    if j >= 2 and first_diverge is None:
        # We know rounds 0 and 1 are OK, so check from round 2
        # Simple check: if a value seems very different, flag it
        pass

# Just print all states
print()
print("All states (my implementation):")
a, b, c, d, e, f, g, h = H_INIT
for j in range(64):
    S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
    ch = (e & f) ^ ((~e & 0xFFFFFFFF) & g)
    temp1 = (h + S1 + ch + K[j] + W[j]) & 0xFFFFFFFF
    S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
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

    # Print compact hash of state
    state_hash = (a + b + c + d + e + f + g + h) & 0xFFFFFFFF
    print(f"R{j:02d}: sum={state_hash:08x} a={a:08x}")
