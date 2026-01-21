"""Compare final round values."""

# Reference final state (after round 64, which is round index 63):
# [2040978907, 3717492111, 1586299222, 4095722474, 3600805733, 3382061760, 2232532848, 477227836]

ref_final = [2040978907, 3717492111, 1586299222, 4095722474, 3600805733, 3382061760, 2232532848, 477227836]

print("Reference final state (after round 63):")
for i, v in enumerate(ref_final):
    print(f"  {['a','b','c','d','e','f','g','h'][i]} = {v:08x} (decimal: {v})")

# My values after round 63:
# R63: a=0196c6da b=dd946d91 c=5e8d0156 d=f41fc3ea e=dedff065 f=c9962ac2 g=8511bf70 h=1c71eb3c
my_final = [0x0196c6da, 0xdd946d91, 0x5e8d0156, 0xf41fc3ea, 0xdedff065, 0xc9962ac2, 0x8511bf70, 0x1c71eb3c]

print()
print("My final state (after round 63):")
for i, v in enumerate(my_final):
    print(f"  {['a','b','c','d','e','f','g','h'][i]} = {v:08x} (decimal: {v})")

print()
print("Comparison:")
mismatches = 0
for i, name in enumerate(['a','b','c','d','e','f','g','h']):
    match = "OK" if ref_final[i] == my_final[i] else "MISMATCH"
    if match != "OK":
        mismatches += 1
    print(f"  {name}: ref={ref_final[i]:08x} mine={my_final[i]:08x} {match}")

print(f"\nTotal mismatches: {mismatches}")

# Let's also verify the expected hash
H_INIT = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]

print()
print("Expected hash from reference final state:")
ref_hash = []
for i in range(8):
    h = (H_INIT[i] + ref_final[i]) & 0xFFFFFFFF
    ref_hash.append(h)
print(''.join(f'{h:08x}' for h in ref_hash))

print()
print("Hash from my final state:")
my_hash = []
for i in range(8):
    h = (H_INIT[i] + my_final[i]) & 0xFFFFFFFF
    my_hash.append(h)
print(''.join(f'{h:08x}' for h in my_hash))

print()
print("Expected: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
