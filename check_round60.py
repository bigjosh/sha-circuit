"""Check round 60."""

# Reference shows after "Round 61" (which is round 60 in 0-indexed):
# [4095722474, 71311374, 3911220166, 3891856828, 477227836, 2867478596, 149616362, 3802292956]

after_r60 = [4095722474, 71311374, 3911220166, 3891856828, 477227836, 2867478596, 149616362, 3802292956]
print("Reference after round 60 (0-indexed):")
print(f"  a={after_r60[0]:08x} b={after_r60[1]:08x} c={after_r60[2]:08x} d={after_r60[3]:08x}")
print(f"  e={after_r60[4]:08x} f={after_r60[5]:08x} g={after_r60[6]:08x} h={after_r60[7]:08x}")

# My trace after round 60:
# R60: a=f41fc3ea b=04441c0e c=e923abc6 d=e7ec45bc e=1c71eb3c f=aaefa044 g=08e0e6ea h=e2a91edc
my_r60 = [0xf41fc3ea, 0x04441c0e, 0xe923abc6, 0xe7ec45bc, 0x1c71eb3c, 0xaaefa044, 0x08e0e6ea, 0xe2a91edc]
print()
print("My trace after round 60 (0-indexed):")
print(f"  a={my_r60[0]:08x} b={my_r60[1]:08x} c={my_r60[2]:08x} d={my_r60[3]:08x}")
print(f"  e={my_r60[4]:08x} f={my_r60[5]:08x} g={my_r60[6]:08x} h={my_r60[7]:08x}")

print()
print("Comparison:")
for i, name in enumerate(['a','b','c','d','e','f','g','h']):
    match = "OK" if after_r60[i] == my_r60[i] else "MISMATCH"
    print(f"  {name}: ref={after_r60[i]:08x} mine={my_r60[i]:08x} {match}")
