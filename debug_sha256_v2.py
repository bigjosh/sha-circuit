"""Debug SHA-256 - check NOT implementation."""

import hashlib

def test_not():
    """Test NOT with mask."""
    x = 0x510e527f

    # Python ~ on unsigned
    not1 = (~x) & 0xFFFFFFFF

    # Using XOR with all 1s
    not2 = x ^ 0xFFFFFFFF

    print(f"x     = {x:08x}")
    print(f"~x    = {not1:08x}")
    print(f"x^fff = {not2:08x}")


def ch_correct(x, y, z):
    """Ch as defined in FIPS-180: (x AND y) XOR ((NOT x) AND z)"""
    return (x & y) ^ ((~x & 0xFFFFFFFF) & z)


def ch_alternate(x, y, z):
    """Ch alternate form: z XOR (x AND (y XOR z))"""
    return z ^ (x & (y ^ z))


def test_ch():
    """Test Ch function."""
    x = 0x510e527f
    y = 0x9b05688c
    z = 0x1f83d9ab

    c1 = ch_correct(x, y, z)
    c2 = ch_alternate(x, y, z)

    print(f"Ch correct:   {c1:08x}")
    print(f"Ch alternate: {c2:08x}")


if __name__ == "__main__":
    test_not()
    print()
    test_ch()
