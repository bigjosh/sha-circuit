"""Debug the round 62 difference."""

# State before round 62 (both match):
# a=5e8d0156 b=f41fc3ea c=04441c0e d=e923abc6 e=8511bf70 f=1c71eb3c g=aaefa044 h=08e0e6ea
a = 0x5e8d0156
b = 0xf41fc3ea
c = 0x04441c0e
d = 0xe923abc6
e = 0x8511bf70
f = 0x1c71eb3c
g = 0xaaefa044
h = 0x08e0e6ea

# K values
MY_K62 = 0xbef9a3f9
KEANE_K62 = 0xbef9a3f7

# W[62] - both match
W62 = 0x44bcec5d

print("K[62] difference:")
print(f"  My K[62]:    {MY_K62:08x}")
print(f"  Keane K[62]: {KEANE_K62:08x}")
print(f"  Difference:  {MY_K62 - KEANE_K62}")
print()

# Helper functions - my implementation
def my_rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF

def my_ch(e, f, g):
    return (e & f) ^ ((~e & 0xFFFFFFFF) & g)

# Keane's implementation
def keane_rotr(num, shift, size=32):
    return (num >> shift) | (num << size - shift)

def keane_capsigma1(num):
    return (keane_rotr(num, 6) ^ keane_rotr(num, 11) ^ keane_rotr(num, 25))

def keane_ch(x, y, z):
    return (x & y) ^ (~x & z)

# Compare capsigma1
my_S1 = my_rotr(e, 6) ^ my_rotr(e, 11) ^ my_rotr(e, 25)
keane_S1 = keane_capsigma1(e)
print("Sigma1 comparison:")
print(f"  My S1:    {my_S1:08x} ({my_S1})")
print(f"  Keane S1: {keane_S1:08x} ({keane_S1})")
print(f"  Match: {my_S1 == keane_S1}")
print()

# Compare ch
my_ch_val = my_ch(e, f, g)
keane_ch_val = keane_ch(e, f, g)
print("Ch comparison:")
print(f"  My ch:    {my_ch_val:08x} ({my_ch_val})")
print(f"  Keane ch: {keane_ch_val:08x} ({keane_ch_val})")
print(f"  Match: {my_ch_val == keane_ch_val}")
print()

# temp1 = h + S1 + ch + K[62] + W[62]
my_temp1 = (h + my_S1 + my_ch_val + MY_K62 + W62) & 0xFFFFFFFF
keane_temp1 = (h + keane_S1 + keane_ch_val + KEANE_K62 + W62) % (2**32)

print("temp1 comparison:")
print(f"  My temp1:    {my_temp1:08x}")
print(f"  Keane temp1: {keane_temp1:08x}")
print(f"  Difference:  {my_temp1 - keane_temp1}")
print()

# So the K value difference of 2 propagates to temp1!
print("Since K[62] differs by 2, temp1 also differs by 2.")
print("This causes e and a to differ by 2 after round 62.")
print()
print("This means MY K constants are WRONG (or keanemind's are wrong but produce correct results)")
