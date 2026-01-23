#!/usr/bin/env python3
"""
Mega optimizer - iteratively runs all optimization passes until convergence.
"""

import subprocess
import sys
import os
import shutil


def get_gate_count(filename):
    """Count gates in a circuit file."""
    with open(filename) as f:
        return sum(1 for line in f if line.strip())


def run_optimizer(script, input_file, output_file):
    """Run an optimizer script."""
    result = subprocess.run(
        [sys.executable, script, "-i", input_file, "-o", output_file],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  Error running {script}:")
        print(result.stderr[:500])
        return False
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Mega optimizer")
    parser.add_argument("--input", "-i", default="nands-xor-final.txt", help="Input file")
    parser.add_argument("--output", "-o", default="nands-mega-opt.txt", help="Output file")
    parser.add_argument("--max-rounds", type=int, default=10, help="Max optimization rounds")
    args = parser.parse_args()

    # Copy input to working file
    current_file = "nands-mega-working.txt"
    shutil.copy(args.input, current_file)

    initial_count = get_gate_count(current_file)
    print(f"Starting with {initial_count:,} gates")

    optimizers = [
        ("xor-share-optimizer.py", "XOR(0,x)=x"),
        ("xor1-optimizer.py", "XOR(1,x)=NOT(x)"),
        ("optimize-nands.py", "Basic"),
        ("advanced-optimizer.py", "Advanced"),
        ("constant-propagation.py", "Const prop"),
    ]

    for round_num in range(1, args.max_rounds + 1):
        print(f"\n{'='*60}")
        print(f"ROUND {round_num}")
        print(f"{'='*60}")

        round_start = get_gate_count(current_file)
        round_improved = False

        for script, name in optimizers:
            if not os.path.exists(script):
                continue

            before = get_gate_count(current_file)
            temp_output = f"nands-mega-temp-{round_num}.txt"

            print(f"\n  Running {name}...")
            if run_optimizer(script, current_file, temp_output):
                if os.path.exists(temp_output):
                    after = get_gate_count(temp_output)
                    saved = before - after

                    if saved > 0:
                        print(f"    Saved {saved:,} gates ({before:,} -> {after:,})")
                        # Use the improved circuit
                        shutil.copy(temp_output, current_file)
                        round_improved = True
                    else:
                        print(f"    No improvement")
                    os.remove(temp_output)
                else:
                    print(f"    No output file (no changes)")

        round_end = get_gate_count(current_file)
        round_saved = round_start - round_end

        print(f"\nRound {round_num} summary: {round_start:,} -> {round_end:,} ({round_saved:,} saved)")

        if not round_improved:
            print("\nNo improvement this round, stopping.")
            break

    # Final verification
    final_count = get_gate_count(current_file)
    print(f"\n{'='*60}")
    print(f"FINAL RESULTS")
    print(f"{'='*60}")
    print(f"Initial: {initial_count:,}")
    print(f"Final:   {final_count:,}")
    print(f"Saved:   {initial_count - final_count:,} ({100*(initial_count-final_count)/initial_count:.2f}%)")

    # Copy to output
    shutil.copy(current_file, args.output)
    os.remove(current_file)
    print(f"\nSaved to {args.output}")

    # Verify
    print("\nVerifying...")
    result = subprocess.run(
        [sys.executable, "verify-circuit.py", "-n", args.output, "--tests", "10"],
        capture_output=True, text=True
    )
    print(result.stdout)


if __name__ == "__main__":
    main()
