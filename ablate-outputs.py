#!/usr/bin/env python3
"""
Remove output nodes from circuit to enable dead code elimination.

Renames OUTPUT-Wx-By labels to REMOVED-Wx-By so the optimizer's dead code
elimination pass will remove gates that only contribute to ablated outputs.

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
    python ablate-outputs.py -n nands-optimized-final.txt --keep 128 -o ablated.txt
    python optimize-nands.py -n ablated.txt -i constants-bits.txt -o ablated-opt.txt
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
        description="Remove output nodes to enable dead code elimination",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ablate-outputs.py -n nands-optimized-final.txt --keep 128  # Keep 128 MSBs
  python ablate-outputs.py -n nands-optimized-final.txt --keep 32   # Keep 32 MSBs (1 word)
  python ablate-outputs.py -n nands-optimized-final.txt --remove 64 # Remove 64 LSBs

After ablation, run optimize-nands.py to eliminate dead gates.
Note: SHA-256's diffusion limits savings to ~1 gate per removed output bit.
"""
    )
    parser.add_argument("--nands", "-n", default="nands.txt",
                        help="Input NAND file (default: nands.txt)")
    parser.add_argument("--output", "-o", default="nands-ablated.txt",
                        help="Output NAND file (default: nands-ablated.txt)")

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

    # Build set of output labels to rename
    labels_to_remove = set()
    for i in range(num_remove):
        labels_to_remove.add(bit_index_to_output_label(i))

    # Read and process nands file
    output_lines = []
    renamed_count = 0

    with open(args.nands, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            label, a, b = line.split(',')

            # Rename removed outputs to REMOVED- prefix
            if label in labels_to_remove:
                label = label.replace("OUTPUT-", "REMOVED-")
                renamed_count += 1

            output_lines.append(f"{label},{a},{b}")

    # Write output
    with open(args.output, 'w') as f:
        f.write('\n'.join(output_lines))

    kept = 256 - num_remove
    print(f"Ablated circuit: {args.output}")
    print(f"  Removed: {num_remove} output bits (LSBs)")
    print(f"  Kept: {kept} output bits (MSBs)")
    print(f"  Gates renamed: {renamed_count}")
    print(f"\nNext: run optimize-nands.py to eliminate dead gates")


if __name__ == "__main__":
    main()
