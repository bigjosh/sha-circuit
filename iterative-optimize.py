#!/usr/bin/env python3
"""
Iterative optimizer that alternates between constant propagation and other optimizations.

Runs until convergence (no more improvements found).

Usage:
    python iterative-optimize.py
    python iterative-optimize.py -i nands-const-prop.txt -o nands-final.txt
"""

import argparse
import subprocess
import os


def get_gate_count(filename):
    """Count gates in a file."""
    with open(filename, 'r') as f:
        return sum(1 for line in f if line.strip())


def run_constant_propagation(input_file, output_file):
    """Run constant propagation."""
    result = subprocess.run(
        ['python', 'constant-propagation.py', '-i', input_file, '-o', output_file, '-q'],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def run_standard_optimizer(input_file, output_file):
    """Run standard optimizer."""
    result = subprocess.run(
        ['python', 'optimize-nands.py', '-i', input_file, '-o', output_file],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def verify_circuit(filename):
    """Verify circuit correctness."""
    result = subprocess.run(
        ['python', 'verify-circuit.py', '-n', filename, '-t', '5'],
        capture_output=True,
        text=True
    )
    # Check if all tests passed
    return 'All tests passed' in result.stdout


def main():
    parser = argparse.ArgumentParser(description="Iterative circuit optimizer")
    parser.add_argument("--input", "-i", default="nands-optimized.txt",
                        help="Input NAND file")
    parser.add_argument("--output", "-o", default="nands-final.txt",
                        help="Output file")
    parser.add_argument("--max-rounds", "-m", type=int, default=10,
                        help="Maximum optimization rounds")
    args = parser.parse_args()

    current_file = args.input
    initial_count = get_gate_count(current_file)

    print(f"Starting iterative optimization")
    print(f"Initial gates: {initial_count:,}")
    print(f"=" * 60)

    temp_files = []
    best_file = current_file
    best_count = initial_count

    for round_num in range(1, args.max_rounds + 1):
        print(f"\nRound {round_num}:")

        # Try constant propagation
        const_prop_file = f"temp-round{round_num}-const.txt"
        temp_files.append(const_prop_file)

        print(f"  Running constant propagation...")
        if run_constant_propagation(current_file, const_prop_file):
            const_count = get_gate_count(const_prop_file)
            print(f"    After const prop: {const_count:,} gates")

            if const_count < best_count:
                improvement = best_count - const_count
                print(f"    Improved by {improvement:,} gates!")
                best_file = const_prop_file
                best_count = const_count
                current_file = const_prop_file
            else:
                print(f"    No improvement from constant propagation")
                current_file = const_prop_file
        else:
            print(f"    Constant propagation failed!")
            break

        # Try standard optimizations
        opt_file = f"temp-round{round_num}-opt.txt"
        temp_files.append(opt_file)

        print(f"  Running standard optimizations...")
        if run_standard_optimizer(current_file, opt_file):
            opt_count = get_gate_count(opt_file)
            print(f"    After optimization: {opt_count:,} gates")

            if opt_count < best_count:
                improvement = best_count - opt_count
                print(f"    Improved by {improvement:,} gates!")
                best_file = opt_file
                best_count = opt_count
                current_file = opt_file
            else:
                print(f"    No improvement from standard optimizations")
                current_file = opt_file
        else:
            print(f"    Standard optimization failed!")
            break

        # Check for convergence
        if best_count == get_gate_count(current_file):
            if round_num > 1:  # Need at least 2 rounds to confirm convergence
                prev_round_file = f"temp-round{round_num-1}-opt.txt"
                if os.path.exists(prev_round_file):
                    prev_count = get_gate_count(prev_round_file)
                    if prev_count == best_count:
                        print(f"\n  Converged! No improvements in this round.")
                        break

    print(f"\n" + "=" * 60)
    print(f"Optimization complete!")
    print(f"  Initial gates:  {initial_count:,}")
    print(f"  Final gates:    {best_count:,}")
    print(f"  Total saved:    {initial_count - best_count:,} ({((initial_count - best_count) / initial_count * 100):.2f}%)")

    # Copy best result to output
    print(f"\nVerifying final circuit...")
    if verify_circuit(best_file):
        print(f"  Verification passed!")

        # Copy to output
        with open(best_file, 'r') as f_in:
            with open(args.output, 'w') as f_out:
                f_out.write(f_in.read())

        print(f"\nSaved to {args.output}")
    else:
        print(f"  Verification FAILED!")
        print(f"  NOT saving output - circuit is broken!")
        return 1

    # Cleanup temp files
    print(f"\nCleaning up {len(temp_files)} temporary files...")
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    return 0


if __name__ == "__main__":
    exit(main())
