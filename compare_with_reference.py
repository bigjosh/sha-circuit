"""Compare my values with the reference from the gist."""

# Reference values from the gist (after each round, state is [a,b,c,d,e,f,g,h])
# Round 1 (which is round 0 in 0-indexed):
# [2080933965, 1779033703, 3144134277, 1013904242, 415752866, 1359893119, 2600822924, 528734635]

ref_round0 = [2080933965, 1779033703, 3144134277, 1013904242, 415752866, 1359893119, 2600822924, 528734635]

print("Reference after round 0:")
for i, v in enumerate(ref_round0):
    print(f"  {['a','b','c','d','e','f','g','h'][i]} = {v:08x} (decimal: {v})")

print()

# My values after round 0:
# R00: a=7c08884d b=6a09e667 c=bb67ae85 d=3c6ef372 e=18c7e2a2 f=510e527f g=9b05688c h=1f83d9ab
my_round0 = [0x7c08884d, 0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0x18c7e2a2, 0x510e527f, 0x9b05688c, 0x1f83d9ab]

print("My values after round 0:")
for i, v in enumerate(my_round0):
    print(f"  {['a','b','c','d','e','f','g','h'][i]} = {v:08x} (decimal: {v})")

print()
print("Comparison:")
for i, name in enumerate(['a','b','c','d','e','f','g','h']):
    match = "OK" if ref_round0[i] == my_round0[i] else "MISMATCH"
    print(f"  {name}: ref={ref_round0[i]:08x} mine={my_round0[i]:08x} {match}")

# Hmm, let's check if 'b' after round 0 should be the original 'a' (i.e., H0)
print()
print("Checking if b after round 0 = initial a (H0):")
H0 = 0x6a09e667
print(f"  H0 = {H0:08x} = {H0}")
print(f"  ref b = {ref_round0[1]:08x} = {ref_round0[1]}")
print(f"  my b  = {my_round0[1]:08x} = {my_round0[1]}")

# The reference b (1779033703 = 0x6a09e667) matches H0! So the reference is correct.
# But wait, 1779033703 in hex is...
print(f"  1779033703 in hex = {1779033703:08x}")
