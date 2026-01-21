"""Verify bit operations."""

def rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF


def shr(x, n):
    return x >> n


# Test ROTR with known values
x = 0xabcdef12

print("ROTR tests:")
print(f"  ROTR({x:08x}, 2) = {rotr(x, 2):08x}")
print(f"  ROTR({x:08x}, 13) = {rotr(x, 13):08x}")
print(f"  ROTR({x:08x}, 22) = {rotr(x, 22):08x}")

# Manual verification of ROTR(0xabcdef12, 2):
# x >> 2 = 0x2af37bc4
# x << 30 = 0x80000000
# result = 0x2af37bc4 | 0x80000000 = 0xaaf37bc4

print()
print("Manual verification of ROTR(0xabcdef12, 2):")
print(f"  x >> 2 = {x >> 2:08x}")
print(f"  x << 30 = {(x << 30) & 0xFFFFFFFF:08x}")
print(f"  result = {rotr(x, 2):08x}")
print(f"  expected = 0xaaf37bc4" if rotr(x, 2) == 0xaaf37bc4 else f"  ERROR: got {rotr(x, 2):08x}")

# Test Sigma0
def sigma0(x):
    return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22)

def sigma1(x):
    return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25)

H0 = 0x6a09e667

print()
print(f"Sigma0({H0:08x}):")
print(f"  ROTR(x,2)  = {rotr(H0, 2):08x}")
print(f"  ROTR(x,13) = {rotr(H0, 13):08x}")
print(f"  ROTR(x,22) = {rotr(H0, 22):08x}")
print(f"  Sigma0     = {sigma0(H0):08x}")
