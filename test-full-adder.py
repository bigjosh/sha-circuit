#!/usr/bin/env python3
"""
Test different full adder implementations to verify correctness and count gates.
"""


class NANDCounter:
    """Simple NAND gate counter."""
    def __init__(self):
        self.gates = []
        self.counter = 0

    def nand(self, a, b):
        """Emit a NAND gate."""
        self.counter += 1
        label = f"g{self.counter}"
        self.gates.append((label, a, b))
        return label

    def reset(self):
        self.gates = []
        self.counter = 0


def full_adder_current(nc, a, b, cin):
    """Current implementation: 15 NANDs."""
    # XOR(a,b) - 4 gates
    t1 = nc.nand(a, b)
    t2 = nc.nand(a, t1)
    t3 = nc.nand(b, t1)
    xor_ab = nc.nand(t2, t3)

    # XOR(xor_ab, cin) - 4 gates
    t4 = nc.nand(xor_ab, cin)
    t5 = nc.nand(xor_ab, t4)
    t6 = nc.nand(cin, t4)
    sum_out = nc.nand(t5, t6)

    # AND(a,b) - 2 gates
    t7 = nc.nand(a, b)
    and_ab = nc.nand(t7, t7)

    # AND(cin, xor_ab) - 2 gates
    t8 = nc.nand(cin, xor_ab)
    and_cin = nc.nand(t8, t8)

    # OR(and_ab, and_cin) - 3 gates
    t9 = nc.nand(and_ab, and_ab)
    t10 = nc.nand(and_cin, and_cin)
    cout = nc.nand(t9, t10)

    return sum_out, cout


def full_adder_shared(nc, a, b, cin):
    """Optimized with sharing: 13 NANDs."""
    # XOR(a,b) - 4 gates
    nand_ab = nc.nand(a, b)
    t1 = nc.nand(a, nand_ab)
    t2 = nc.nand(b, nand_ab)
    xor_ab = nc.nand(t1, t2)

    # XOR(xor_ab, cin) - 4 gates
    nand_xor_cin = nc.nand(xor_ab, cin)
    t3 = nc.nand(xor_ab, nand_xor_cin)
    t4 = nc.nand(cin, nand_xor_cin)
    sum_out = nc.nand(t3, t4)

    # AND(a,b) - 1 gate (reuse nand_ab)
    and_ab = nc.nand(nand_ab, nand_ab)

    # AND(cin, xor_ab) - 1 gate (reuse nand_xor_cin)
    and_cin = nc.nand(nand_xor_cin, nand_xor_cin)

    # OR(and_ab, and_cin) - 3 gates
    t5 = nc.nand(and_ab, and_ab)
    t6 = nc.nand(and_cin, and_cin)
    cout = nc.nand(t5, t6)

    return sum_out, cout


def full_adder_optimal(nc, a, b, cin):
    """9-NAND optimal full adder."""
    # Three initial NANDs
    nand_ab = nc.nand(a, b)
    nand_ac = nc.nand(a, cin)
    nand_bc = nc.nand(b, cin)

    # Sum computation
    t1 = nc.nand(nand_ab, nand_ac)
    t2 = nc.nand(t1, nand_bc)
    sum_out = nc.nand(t2, t2)  # NOT

    # Carry computation
    t3 = nc.nand(nand_ab, nand_ab)  # a AND b
    t4 = nc.nand(t1, cin)
    cout = nc.nand(t3, t4)

    return sum_out, cout


def evaluate_nands(gates, inputs):
    """Evaluate a NAND circuit."""
    values = dict(inputs)

    for label, a, b in gates:
        a_val = values.get(a, a)
        b_val = values.get(b, b)
        # Convert string to int if needed
        if isinstance(a_val, str):
            a_val = int(a_val)
        if isinstance(b_val, str):
            b_val = int(b_val)
        values[label] = 0 if (a_val and b_val) else 1

    return values


def test_full_adder(name, adder_func):
    """Test a full adder implementation."""
    print(f"\nTesting {name}:")
    print("=" * 60)

    nc = NANDCounter()
    sum_out, cout = adder_func(nc, 'a', 'b', 'cin')
    gate_count = len(nc.gates)

    print(f"Gate count: {gate_count}")

    # Test all 8 input combinations
    passed = 0
    failed = 0

    for a in [0, 1]:
        for b in [0, 1]:
            for cin in [0, 1]:
                nc_test = NANDCounter()
                s, c = adder_func(nc_test, 'a', 'b', 'cin')

                inputs = {'a': a, 'b': b, 'cin': cin}
                values = evaluate_nands(nc_test.gates, inputs)

                result_sum = values[s]
                result_cout = values[c]

                # Expected values
                expected_sum = (a + b + cin) & 1
                expected_cout = (a + b + cin) >> 1

                if result_sum == expected_sum and result_cout == expected_cout:
                    passed += 1
                else:
                    failed += 1
                    print(f"  FAIL: a={a}, b={b}, cin={cin}")
                    print(f"    Expected: sum={expected_sum}, cout={expected_cout}")
                    print(f"    Got:      sum={result_sum}, cout={result_cout}")

    print(f"Tests: {passed} passed, {failed} failed")

    if failed == 0:
        print(f"OK All tests passed with {gate_count} NANDs!")

    return gate_count, failed == 0


if __name__ == "__main__":
    print("Full Adder Implementation Comparison")
    print("=" * 60)

    results = []

    # Test current implementation
    gates, correct = test_full_adder("Current (15 NAND)", full_adder_current)
    results.append(("Current", gates, correct))

    # Test shared implementation
    gates, correct = test_full_adder("Shared (13 NAND)", full_adder_shared)
    results.append(("Shared", gates, correct))

    # Test optimal implementation
    gates, correct = test_full_adder("Optimal (9 NAND)", full_adder_optimal)
    results.append(("Optimal", gates, correct))

    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    for name, gates, correct in results:
        status = "OK" if correct else "FAIL"
        print(f"{status} {name:20s}: {gates} gates")

    # Calculate savings
    if results[0][2] and results[2][2]:  # Both work
        current = results[0][1]
        optimal = results[2][1]
        savings = current - optimal
        print(f"\nSavings: {savings} NANDs per full adder ({savings/current*100:.1f}%)")

        # Estimate circuit impact
        add_gates = 141033  # From current circuit
        full_adder_bits = add_gates / current
        new_add_gates = full_adder_bits * optimal
        total_savings = add_gates - new_add_gates

        print(f"\nEstimated circuit impact:")
        print(f"  Current ADD gates: {add_gates:,}")
        print(f"  With optimal adders: {new_add_gates:,.0f}")
        print(f"  Gates saved: {total_savings:,.0f}")
        print(f"  Overall reduction: {total_savings/250931*100:.1f}% of total circuit")
