#!/usr/bin/env python3
"""
Generate input.txt for SHA-256 circuit from ASCII text or hex string.

Usage:
    python generate-input.py "hello"           # ASCII text
    python generate-input.py --hex "68656c6c6f"  # Hex string
    python generate-input.py --hex 68656c6c6f    # Hex string (quotes optional)
    python generate-input.py -o output.txt "hello"  # Custom output file
"""

import argparse
import sys


def parse_input(input_str, is_hex):
    """Parse input string to bytes."""
    if is_hex:
        # Remove any spaces or 0x prefix
        hex_str = input_str.replace(" ", "").replace("0x", "").replace("0X", "")
        if len(hex_str) % 2 != 0:
            hex_str = "0" + hex_str  # Pad with leading zero if odd length
        try:
            return bytes.fromhex(hex_str)
        except ValueError as e:
            print(f"Error: Invalid hex string: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        return input_str.encode('utf-8')


def pad_message(message):
    """Apply SHA-256 padding to message. Returns padded bytes (must be single block for now)."""
    ml = len(message) * 8  # Message length in bits

    # Append bit '1' (as 0x80 byte)
    padded = bytearray(message)
    padded.append(0x80)

    # Append zeros until length is 448 bits (mod 512) = 56 bytes (mod 64)
    while len(padded) % 64 != 56:
        padded.append(0x00)

    # Append original length as 64-bit big-endian
    padded.extend(ml.to_bytes(8, 'big'))

    if len(padded) > 64:
        print(f"Error: Message too long. Maximum length is 55 bytes for single-block SHA-256.",
              file=sys.stderr)
        print(f"       Your message is {len(message)} bytes.", file=sys.stderr)
        sys.exit(1)

    return bytes(padded)


def generate_input_lines(padded_message):
    """Generate input.txt lines from padded message."""
    lines = []
    for i in range(16):
        # Extract 4 bytes as big-endian 32-bit word
        word = int.from_bytes(padded_message[i*4:(i+1)*4], 'big')
        lines.append(f"INPUT-W{i},{word:08x}")
    return lines


def main():
    parser = argparse.ArgumentParser(
        description="Generate input.txt for SHA-256 circuit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate-input.py "hello"
  python generate-input.py --hex "48454c4c4f"
  python generate-input.py --hex 0x48454c4c4f
  python generate-input.py -o my_input.txt "test"
  echo -n "hello" | python generate-input.py --stdin
"""
    )

    parser.add_argument("input", nargs="?", default=None,
                        help="Input string (ASCII text or hex with --hex flag)")
    parser.add_argument("--hex", "-x", action="store_true",
                        help="Interpret input as hexadecimal string")
    parser.add_argument("--output", "-o", default="input.txt",
                        help="Output file path (default: input.txt)")
    parser.add_argument("--stdin", action="store_true",
                        help="Read input from stdin")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress informational output")

    args = parser.parse_args()

    # Get input
    if args.stdin:
        input_str = sys.stdin.read()
        # Don't strip - preserve exact input
    elif args.input is not None:
        input_str = args.input
    else:
        parser.print_help()
        sys.exit(1)

    # Parse to bytes
    message = parse_input(input_str, args.hex)

    # Check length
    if len(message) > 55:
        print(f"Error: Message too long ({len(message)} bytes). Maximum is 55 bytes for single-block SHA-256.",
              file=sys.stderr)
        sys.exit(1)

    # Pad message
    padded = pad_message(message)

    # Generate lines
    lines = generate_input_lines(padded)

    # Write output
    with open(args.output, 'w') as f:
        f.write('\n'.join(lines))

    if not args.quiet:
        print(f"Generated {args.output}")
        print(f"  Message: {message!r}")
        print(f"  Length: {len(message)} bytes")
        print(f"  Hex: {message.hex()}")


if __name__ == "__main__":
    main()
