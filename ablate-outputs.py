#!/usr/bin/env python3
"""
Remove output bits from results-bits.txt to enable dead code elimination.

Creates a new results file with fewer outputs. When the optimizer runs with
this reduced results file, it will eliminate gates that only feed removed outputs.

Output bits are numbered 0-255 where:
  - Bit 0 = OUTPUT-W7-B0 (LSB of hash)
  - Bit 255 = OUTPUT-W0-B31 (MSB of hash)

NOTE: Due to SHA-256's avalanche property, most gates contribute to multiple
output bits. Ablating provides modest savings (~0.5-1% reduction):
  256 bits: 230,549 gates (full circuit)
  128 bits: 229,453 gates (0.48% saved)
   32 bits: 228,810 gates (0.75% saved)
    1 bit:  228,674 gates (0.81% saved)

Usage:
    python ablate-outputs.py --keep 128 -o results-ablated.txt
    python optimize-nands.py -r results-ablated.txt
"""

import argparse


def bit_index_to_output_label(bit_idx):
    """Convert bit index (0=LSB, 255=MSB) to OUTPUT-Wx-By label."""
    # Bit 0 is OUTPUT-W7-B0, Bit 255 is OUTPUT-W0-B31
    word = 7 - (bit_idx // 32)
    bit = bit_idx % 32
    return f"OUTPUT-W{word}-B{bit}"


def main():
    parser = argparse.ArgumentParser(
        description="Remove output bits from results file to enable dead code elimination",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ablate-outputs.py --keep 128                    # Keep 128 MSBs
  python ablate-outputs.py --keep 32 -o results-32.txt   # Keep 32 MSBs (1 word)
  python ablate-outputs.py --remove 64                   # Remove 64 LSBs

After ablation, run optimizer with the new results file:
  python optimize-nands.py -r results-ablated.txt
"""
    )
    parser.add_argument("--input", "-i", default="results-bits.txt",
                        help="Input results file (default: results-bits.txt)")
    parser.add_argument("--output", "-o", default="results-ablated.txt",
                        help="Output results file (default: results-ablated.txt)")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--remove", "-r", type=int,
                       help="Number of LSBs to remove (0-256)")
    group.add_argument("--keep", "-k", type=int,
                       help="Number of MSBs to keep (0-256)")

    args = parser.parse_args()

    # Calculate which bits to remove
    if args.remove is not None:
        num_remove = args.remove
    else:
        num_remove = 256 - args.keep

    if num_remove < 0 or num_remove > 256:
        print(f"Error: Must remove between 0 and 256 bits")
        return 1

    # Build set of output labels to remove
    labels_to_remove = set()
    for i in range(num_remove):
        labels_to_remove.add(bit_index_to_output_label(i))

    # Read results file and filter
    output_lines = []
    removed_count = 0

    with open(args.input, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            label, value = line.split(',')

            if label in labels_to_remove:
                removed_count += 1
            else:
                output_lines.append(f"{label},{value}")

    # Write output
    with open(args.output, 'w') as f:
        f.write('\n'.join(output_lines))

    kept = 256 - num_remove
    print(f"Ablated results: {args.output}")
    print(f"  Removed: {removed_count} output bits (LSBs)")
    print(f"  Kept: {kept} output bits (MSBs)")
    print(f"\nNext: python optimize-nands.py -r {args.output}")


if __name__ == "__main__":
    main()
