"""Debug round 62."""

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


def rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF


# Compute W for empty message
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

# Reference shows after round 61 (0-indexed):
# a=5e8d0156 b=f41fc3ea c=04441c0e d=e923abc6 e=8511bf70 f=1c71eb3c g=aaefa044 h=08e0e6ea
a = 0x5e8d0156
b = 0xf41fc3ea
c = 0x04441c0e
d = 0xe923abc6
e = 0x8511bf70
f = 0x1c71eb3c
g = 0xaaefa044
h = 0x08e0e6ea

j = 62  # Round 62 (0-indexed)

print(f"=== Round {j} ===")
print(f"Before: a={a:08x} b={b:08x} c={c:08x} d={d:08x}")
print(f"        e={e:08x} f={f:08x} g={g:08x} h={h:08x}")
print(f"K[{j}] = {K[j]:08x}")
print(f"W[{j}] = {W[j]:08x}")
print()

# S1 = Sigma1(e)
S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
print(f"S1 = Sigma1(e) = rotr({e:08x}, 6) XOR rotr({e:08x}, 11) XOR rotr({e:08x}, 25)")
print(f"   = {rotr(e, 6):08x} XOR {rotr(e, 11):08x} XOR {rotr(e, 25):08x}")
print(f"   = {S1:08x}")
print()

# Ch
ch = (e & f) ^ ((~e & 0xFFFFFFFF) & g)
print(f"ch = (e AND f) XOR ((NOT e) AND g)")
print(f"   = ({e:08x} AND {f:08x}) XOR ((NOT {e:08x}) AND {g:08x})")
print(f"   = {e & f:08x} XOR {(~e & 0xFFFFFFFF) & g:08x}")
print(f"   = {ch:08x}")
print()

# temp1
temp1 = (h + S1 + ch + K[j] + W[j]) & 0xFFFFFFFF
print(f"temp1 = h + S1 + ch + K[{j}] + W[{j}]")
print(f"      = {h:08x} + {S1:08x} + {ch:08x} + {K[j]:08x} + {W[j]:08x}")
# Show step by step
sum1 = h + S1
print(f"      h + S1 = {sum1:08x} (raw: {sum1})")
sum2 = (sum1 + ch) & 0xFFFFFFFF
print(f"      + ch = {sum2:08x}")
sum3 = (sum2 + K[j]) & 0xFFFFFFFF
print(f"      + K[{j}] = {sum3:08x}")
sum4 = (sum3 + W[j]) & 0xFFFFFFFF
print(f"      + W[{j}] = {sum4:08x}")
print(f"      = {temp1:08x}")
print()

# S0 = Sigma0(a)
S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
print(f"S0 = Sigma0(a) = rotr({a:08x}, 2) XOR rotr({a:08x}, 13) XOR rotr({a:08x}, 22)")
print(f"   = {rotr(a, 2):08x} XOR {rotr(a, 13):08x} XOR {rotr(a, 22):08x}")
print(f"   = {S0:08x}")
print()

# Maj
maj = (a & b) ^ (a & c) ^ (b & c)
print(f"maj = (a AND b) XOR (a AND c) XOR (b AND c)")
print(f"    = ({a:08x} AND {b:08x}) XOR ({a:08x} AND {c:08x}) XOR ({b:08x} AND {c:08x})")
print(f"    = {a & b:08x} XOR {a & c:08x} XOR {b & c:08x}")
print(f"    = {maj:08x}")
print()

# temp2
temp2 = (S0 + maj) & 0xFFFFFFFF
print(f"temp2 = S0 + maj = {S0:08x} + {maj:08x} = {temp2:08x}")
print()

# New state
new_h = g
new_g = f
new_f = e
new_e = (d + temp1) & 0xFFFFFFFF
new_d = c
new_c = b
new_b = a
new_a = (temp1 + temp2) & 0xFFFFFFFF

print(f"new a = temp1 + temp2 = {temp1:08x} + {temp2:08x} = {new_a:08x}")
print(f"new e = d + temp1 = {d:08x} + {temp1:08x} = {new_e:08x}")
print()
print(f"After:  a={new_a:08x} b={new_b:08x} c={new_c:08x} d={new_d:08x}")
print(f"        e={new_e:08x} f={new_f:08x} g={new_g:08x} h={new_h:08x}")
print()
print("Expected (from reference):")
print(f"        a=dd946d8f b=5e8d0156 c=f41fc3ea d=04441c0e")
print(f"        e=c9962ac0 f=8511bf70 g=1c71eb3c h=aaefa044")
print()
print(f"My a:       {new_a:08x}")
print(f"Expected a: dd946d8f")
print(f"Diff:       {new_a - 0xdd946d8f}")
