"""Verify reference values from the gist."""

# From the gist, this is shown after "Round 62" which means after round index 61 (0-indexed):
# Resulting state: [1586299222, 4095722474, 71311374, 3911220166, 2232532848, 477227836, 2867478596, 149616362]

after_r61 = [1586299222, 4095722474, 71311374, 3911220166, 2232532848, 477227836, 2867478596, 149616362]
print("Reference after round 61 (0-indexed):")
print(f"  a={after_r61[0]:08x} b={after_r61[1]:08x} c={after_r61[2]:08x} d={after_r61[3]:08x}")
print(f"  e={after_r61[4]:08x} f={after_r61[5]:08x} g={after_r61[6]:08x} h={after_r61[7]:08x}")

# My trace after round 61:
# R61: a=5e8d0156 b=f41fc3ea c=04441c0e d=e923abc6 e=8511bf70 f=1c71eb3c g=aaefa044 h=08e0e6ea
my_r61 = [0x5e8d0156, 0xf41fc3ea, 0x04441c0e, 0xe923abc6, 0x8511bf70, 0x1c71eb3c, 0xaaefa044, 0x08e0e6ea]
print()
print("My trace after round 61 (0-indexed):")
print(f"  a={my_r61[0]:08x} b={my_r61[1]:08x} c={my_r61[2]:08x} d={my_r61[3]:08x}")
print(f"  e={my_r61[4]:08x} f={my_r61[5]:08x} g={my_r61[6]:08x} h={my_r61[7]:08x}")

print()
print("Comparison:")
for i, name in enumerate(['a','b','c','d','e','f','g','h']):
    match = "OK" if after_r61[i] == my_r61[i] else "MISMATCH"
    print(f"  {name}: ref={after_r61[i]:08x} mine={my_r61[i]:08x} {match}")
