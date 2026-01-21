"""Compare round 1 values."""

# Reference after round 2 (which is index 1):
# [2632279248, 2080933965, 1779033703, 3144134277, 536982102, 415752866, 1359893119, 2600822924]

ref_round1 = [2632279248, 2080933965, 1779033703, 3144134277, 536982102, 415752866, 1359893119, 2600822924]

print("Reference after round 1:")
for i, v in enumerate(ref_round1):
    print(f"  {['a','b','c','d','e','f','g','h'][i]} = {v:08x}")

# My values after round 1:
# R01: a=9ce564d0 b=7c08884d c=6a09e667 d=bb67ae85 e=2001b256 f=18c7e2a2 g=510e527f h=9b05688c
my_round1 = [0x9ce564d0, 0x7c08884d, 0x6a09e667, 0xbb67ae85, 0x2001b256, 0x18c7e2a2, 0x510e527f, 0x9b05688c]

print()
print("My values after round 1:")
for i, v in enumerate(my_round1):
    print(f"  {['a','b','c','d','e','f','g','h'][i]} = {v:08x}")

print()
print("Comparison:")
for i, name in enumerate(['a','b','c','d','e','f','g','h']):
    match = "OK" if ref_round1[i] == my_round1[i] else "MISMATCH"
    print(f"  {name}: ref={ref_round1[i]:08x} mine={my_round1[i]:08x} {match}")
