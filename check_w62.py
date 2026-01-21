"""Check W[62] computation."""

import struct

def rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF

# Empty message padding
message = bytearray(b"")
ml = 0
message.append(0x80)
while len(message) % 64 != 56:
    message.append(0x00)
message.extend(ml.to_bytes(8, 'big'))

W = list(struct.unpack('>16I', bytes(message)))

# Print W[0..15]
print("W[0..15]:")
for i in range(16):
    print(f"  W[{i:2d}] = {W[i]:08x}")

# Extend
for j in range(16, 64):
    s0 = rotr(W[j-15], 7) ^ rotr(W[j-15], 18) ^ (W[j-15] >> 3)
    s1 = rotr(W[j-2], 17) ^ rotr(W[j-2], 19) ^ (W[j-2] >> 10)
    W.append((W[j-16] + s0 + W[j-7] + s1) & 0xFFFFFFFF)

print()
print("W[60..63]:")
for i in range(60, 64):
    print(f"  W[{i:2d}] = {W[i]:08x}")

# What does the reference say?
# The gist says for round 64 (index 63): Schedule word: 996066459 = 0x3b5ec49b
# So W[63] should be 0x3b5ec49b
print()
print(f"W[63] computed: {W[63]:08x}")
print(f"W[63] expected: 3b5ec49b")
print(f"Match: {W[63] == 0x3b5ec49b}")

# Check round 62's W
# The gist shows intermediate values for rounds 1, 2, and 64
# We need to verify W[62]
print()
print(f"W[62] computed: {W[62]:08x}")
