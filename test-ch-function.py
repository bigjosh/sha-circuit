#!/usr/bin/env python3
"""
Test different CH function implementations to verify correctness and count gates.

CH(e,f,g) = (e AND f) XOR ((NOT e) AND g)
Equivalent to: if e then f else g (2:1 MUX)
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


def ch_current(nc, e, f, g):
    """Current implementation: 9 NANDs.

    CH(e,f,g) = (e AND f) XOR ((NOT e) AND g)
    """
    # e AND f - 2 gates
    t1 = nc.nand(e, f)
    ef_and = nc.nand(t1, t1)

    # NOT e - 1 gate
    not_e = nc.nand(e, e)

    # (NOT e) AND g - 2 gates
    t2 = nc.nand(not_e, g)
    noteg_and = nc.nand(t2, t2)

    # XOR - 4 gates
    t3 = nc.nand(ef_and, noteg_and)
    t4 = nc.nand(ef_and, t3)
    t5 = nc.nand(noteg_and, t3)
    result = nc.nand(t4, t5)

    return result


def ch_mux_4nand(nc, e, f, g):
    """MUX form with 4 NANDs.

    if e then f else g
    """
    # Invert select
    not_e = nc.nand(e, e)

    # Select inputs
    t1 = nc.nand(e, f)       # When e=1, this is NAND(1,f) = NOT(f)
    t2 = nc.nand(not_e, g)   # When e=0, this is NAND(1,g) = NOT(g)

    # Combine: NAND(NOT(f), NOT(g)) when e=?
    # Let's think: when e=1: t1=NOT(f), t2=NOT(0 AND g)=1, so NAND(NOT(f),1)=1
    # Hmm, this might not work directly...
    result = nc.nand(t1, t2)

    return result


def ch_mux_5nand(nc, e, f, g):
    """MUX form with 5 NANDs (if 4 doesn't work).

    Alternative: (e AND f) OR ((NOT e) AND g)
    Using NAND: NAND(NAND(e AND f, e AND f), NAND(NOT_e AND g, NOT_e AND g))
    """
    # e AND f - 2 gates
    t1 = nc.nand(e, f)
    ef_and = nc.nand(t1, t1)

    # (NOT e) AND g - 2 gates
    not_e = nc.nand(e, e)
    t2 = nc.nand(not_e, g)
    noteg_and = nc.nand(t2, t2)

    # OR them - 1 gate
    # OR(a,b) = NAND(NOT(a), NOT(b)) but we need 3 gates
    # Wait, we already have the ANDs, so:
    # OR(a,b) = NOT(NAND(a,b)) but if we already have a and b...
    # Actually: OR(a,b) = NAND(NAND(a,a), NAND(b,b))
    # But ef_and and noteg_and are already positive logic
    # So OR = NAND(NOT(ef_and), NOT(noteg_and))

    # Hmm, let me think differently:
    # We want: (e AND f) OR ((NOT e) AND g)
    # In NAND: NOT(NOT(e AND f) AND NOT((NOT e) AND g))
    # = NAND(NAND(e,f), NAND(NAND(e,e), g))

    t3 = nc.nand(e, f)           # NAND(e,f)
    t4 = nc.nand(e, e)           # NOT(e)
    t5 = nc.nand(t4, g)          # NAND(NOT(e), g)
    result = nc.nand(t3, t5)     # NAND(NAND(e,f), NAND(NOT(e),g))

    return result


def ch_direct_5nand(nc, e, f, g):
    """Direct NAND implementation: 5 NANDs.

    CH = (e AND f) OR ((NOT e) AND g)
    In pure NAND: NAND(NAND(e,f), NAND(NOT(e), g))
    """
    nand_ef = nc.nand(e, f)
    not_e = nc.nand(e, e)
    nand_noteg = nc.nand(not_e, g)
    result = nc.nand(nand_ef, nand_noteg)

    return result


def ch_alternative(nc, e, f, g):
    """Alternative form: g XOR (e AND (f XOR g))

    This was mentioned in the code comments.
    """
    # f XOR g - 4 gates
    t1 = nc.nand(f, g)
    t2 = nc.nand(f, t1)
    t3 = nc.nand(g, t1)
    fxg = nc.nand(t2, t3)

    # e AND (f XOR g) - 2 gates
    t4 = nc.nand(e, fxg)
    e_and_fxg = nc.nand(t4, t4)

    # g XOR (e AND (f XOR g)) - 4 gates
    t5 = nc.nand(g, e_and_fxg)
    t6 = nc.nand(g, t5)
    t7 = nc.nand(e_and_fxg, t5)
    result = nc.nand(t6, t7)

    return result


def evaluate_nands(gates, inputs):
    """Evaluate a NAND circuit."""
    values = dict(inputs)

    for label, a, b in gates:
        a_val = values.get(a, a)
        b_val = values.get(b, b)
        if isinstance(a_val, str):
            a_val = int(a_val)
        if isinstance(b_val, str):
            b_val = int(b_val)
        values[label] = 0 if (a_val and b_val) else 1

    return values


def test_ch_function(name, ch_func):
    """Test a CH function implementation."""
    print(f"\nTesting {name}:")
    print("=" * 60)

    nc = NANDCounter()
    result = ch_func(nc, 'e', 'f', 'g')
    gate_count = len(nc.gates)

    print(f"Gate count: {gate_count}")

    # Test all 8 input combinations
    passed = 0
    failed = 0

    for e in [0, 1]:
        for f in [0, 1]:
            for g in [0, 1]:
                nc_test = NANDCounter()
                output = ch_func(nc_test, 'e', 'f', 'g')

                inputs = {'e': e, 'f': f, 'g': g}
                values = evaluate_nands(nc_test.gates, inputs)

                result_val = values[output]

                # Expected: CH(e,f,g) = (e AND f) XOR ((NOT e) AND g)
                # Also: if e then f else g
                expected = f if e else g

                if result_val == expected:
                    passed += 1
                else:
                    failed += 1
                    print(f"  FAIL: e={e}, f={f}, g={g}")
                    print(f"    Expected: {expected}")
                    print(f"    Got:      {result_val}")

    print(f"Tests: {passed} passed, {failed} failed")

    if failed == 0:
        print(f"OK All tests passed with {gate_count} NANDs!")

    return gate_count, failed == 0


if __name__ == "__main__":
    print("CH Function Implementation Comparison")
    print("=" * 60)

    results = []

    # Test current implementation
    gates, correct = test_ch_function("Current (9 NAND)", ch_current)
    results.append(("Current", gates, correct))

    # Test 4-NAND MUX
    gates, correct = test_ch_function("MUX 4-NAND", ch_mux_4nand)
    results.append(("MUX 4-NAND", gates, correct))

    # Test 5-NAND version
    gates, correct = test_ch_function("MUX 5-NAND", ch_mux_5nand)
    results.append(("MUX 5-NAND", gates, correct))

    # Test direct 5-NAND
    gates, correct = test_ch_function("Direct 5-NAND", ch_direct_5nand)
    results.append(("Direct 5-NAND", gates, correct))

    # Test alternative form
    gates, correct = test_ch_function("Alternative (g XOR ...)", ch_alternative)
    results.append(("Alternative", gates, correct))

    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    for name, gates, correct in results:
        status = "OK" if correct else "FAIL"
        print(f"{status:6s} {name:25s}: {gates} gates")

    # Calculate best savings
    working = [(name, gates) for name, gates, correct in results if correct]
    if len(working) >= 2:
        current = results[0][1]
        best = min(gates for name, gates in working if name != "Current")
        best_name = [name for name, gates in working if gates == best][0]

        savings = current - best
        print(f"\nBest working implementation: {best_name} with {best} gates")
        print(f"Savings: {savings} NANDs per CH ({savings/current*100:.1f}%)")

        # Estimate circuit impact
        ch_count = 2048  # 64 rounds × 32 bits
        total_ch_gates = ch_count * current
        new_ch_gates = ch_count * best
        total_savings = total_ch_gates - new_ch_gates

        print(f"\nEstimated circuit impact:")
        print(f"  Current CH gates: {total_ch_gates:,} (2,048 uses × {current} gates)")
        print(f"  With {best_name}: {new_ch_gates:,}")
        print(f"  Gates saved: {total_savings:,}")
        print(f"  Circuit reduction: {total_savings/250931*100:.1f}% of total")
