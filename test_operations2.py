"""Test all operations individually."""

def rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF

def ch(e, f, g):
    return ((e & f) ^ ((~e) & g)) & 0xFFFFFFFF

def maj(a, b, c):
    return ((a & b) ^ (a & c) ^ (b & c)) & 0xFFFFFFFF

def sigma0(a):
    return rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)

def sigma1(e):
    return rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)


# Test with initial values
H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
K0 = 0x428a2f98
W0 = 0x80000000  # For empty message

a, b, c, d, e, f, g, h = H

print("Round 0 computation:")
print(f"Initial: a={a:08x} e={e:08x} h={h:08x}")
print()

# S1 = Sigma1(e)
S1 = sigma1(e)
print(f"Sigma1(e) = rotr({e:08x},6) XOR rotr({e:08x},11) XOR rotr({e:08x},25)")
print(f"          = {rotr(e,6):08x} XOR {rotr(e,11):08x} XOR {rotr(e,25):08x}")
print(f"          = {S1:08x}")
print()

# Ch
ch_val = ch(e, f, g)
print(f"Ch(e,f,g) = ({e:08x} AND {f:08x}) XOR (NOT {e:08x} AND {g:08x})")
print(f"          = {e & f:08x} XOR {(~e) & g & 0xFFFFFFFF:08x}")
print(f"          = {ch_val:08x}")
print()

# temp1
temp1 = (h + S1 + ch_val + K0 + W0) & 0xFFFFFFFF
print(f"temp1 = h + S1 + ch + K[0] + W[0]")
print(f"      = {h:08x} + {S1:08x} + {ch_val:08x} + {K0:08x} + {W0:08x}")
print(f"      = {temp1:08x}")
print()

# S0 = Sigma0(a)
S0 = sigma0(a)
print(f"Sigma0(a) = rotr({a:08x},2) XOR rotr({a:08x},13) XOR rotr({a:08x},22)")
print(f"          = {rotr(a,2):08x} XOR {rotr(a,13):08x} XOR {rotr(a,22):08x}")
print(f"          = {S0:08x}")
print()

# Maj
maj_val = maj(a, b, c)
print(f"Maj(a,b,c) = ({a:08x} AND {b:08x}) XOR ({a:08x} AND {c:08x}) XOR ({b:08x} AND {c:08x})")
print(f"           = {a & b:08x} XOR {a & c:08x} XOR {b & c:08x}")
print(f"           = {maj_val:08x}")
print()

# temp2
temp2 = (S0 + maj_val) & 0xFFFFFFFF
print(f"temp2 = S0 + maj = {S0:08x} + {maj_val:08x} = {temp2:08x}")
print()

# New values
new_a = (temp1 + temp2) & 0xFFFFFFFF
new_e = (d + temp1) & 0xFFFFFFFF

print(f"new a = temp1 + temp2 = {temp1:08x} + {temp2:08x} = {new_a:08x}")
print(f"new e = d + temp1 = {d:08x} + {temp1:08x} = {new_e:08x}")
print()
print(f"Expected after round 0: a=7c08884d e=18c7e2a2")
print(f"Computed: a={new_a:08x} e={new_e:08x}")
print(f"Match: {new_a == 0x7c08884d and new_e == 0x18c7e2a2}")
