#!/usr/bin/env python3
"""
Generate input.txt for SHA-256 circuit from ASCII text or hex string.

Supports unknown bytes using '?' in ASCII mode or 'XX' in hex mode.
Unknown bytes become 'X' bits when expanded.

Usage:
    python generate-input.py "hello"             # ASCII text
    python generate-input.py "hel?o"             # With unknown byte (? = unknown)
    python generate-input.py --hex "68656c6c6f"  # Hex string
    python generate-input.py --hex "68656cXX6f"  # Hex with unknown byte
    python generate-input.py -o output.txt "hello"  # Custom output file
"""

import argparse
import sys


# Sentinel for unknown byte
UNKNOWN = None


def parse_input(input_str, is_hex):
    """Parse input string to list of bytes (int or None for unknown)."""
    if is_hex:
        # Remove any spaces or 0x prefix
        hex_str = input_str.replace(" ", "").replace("0x", "").replace("0X", "")
        if len(hex_str) % 2 != 0:
            hex_str = "0" + hex_str  # Pad with leading zero if odd length

        result = []
        i = 0
        while i < len(hex_str):
            pair = hex_str[i:i+2].upper()
            if pair == "XX" or pair == "??":
                result.append(UNKNOWN)
            else:
                try:
                    result.append(int(pair, 16))
                except ValueError:
                    print(f"Error: Invalid hex pair '{pair}' at position {i}", file=sys.stderr)
                    sys.exit(1)
            i += 2
        return result
    else:
        # ASCII mode: '?' means unknown byte
        result = []
        for char in input_str:
            if char == '?':
                result.append(UNKNOWN)
            else:
                result.append(ord(char))
        return result


def pad_message(message):
    """Apply SHA-256 padding to message. Returns list of bytes (int or None for unknown)."""
    ml = len(message) * 8  # Message length in bits (unknowns still count as 8 bits)

    # Append bit '1' (as 0x80 byte)
    padded = list(message)
    padded.append(0x80)

    # Append zeros until length is 448 bits (mod 512) = 56 bytes (mod 64)
    while len(padded) % 64 != 56:
        padded.append(0x00)

    # Append original length as 64-bit big-endian
    length_bytes = ml.to_bytes(8, 'big')
    padded.extend(length_bytes)

    if len(padded) > 64:
        print(f"Error: Message too long. Maximum length is 55 bytes for single-block SHA-256.",
              file=sys.stderr)
        print(f"       Your message is {len(message)} bytes.", file=sys.stderr)
        sys.exit(1)

    return padded


def byte_to_hex(b):
    """Convert byte to hex string. None -> 'XX'."""
    if b is UNKNOWN:
        return "XX"
    return f"{b:02x}"


def generate_input_lines(padded_message):
    """Generate input.txt lines from padded message."""
    lines = []
    for i in range(16):
        # Extract 4 bytes as hex string
        bytes_slice = padded_message[i*4:(i+1)*4]
        hex_str = "".join(byte_to_hex(b) for b in bytes_slice)
        lines.append(f"INPUT-W{i},{hex_str}")
    return lines


def format_message_repr(message):
    """Format message for display, showing ? for unknowns."""
    chars = []
    for b in message:
        if b is UNKNOWN:
            chars.append('?')
        elif 32 <= b < 127:
            chars.append(chr(b))
        else:
            chars.append(f'\\x{b:02x}')
    return ''.join(chars)


def format_message_hex(message):
    """Format message as hex, showing XX for unknowns."""
    return "".join(byte_to_hex(b) for b in message)


def count_unknowns(message):
    """Count unknown bytes in message."""
    return sum(1 for b in message if b is UNKNOWN)


def main():
    parser = argparse.ArgumentParser(
        description="Generate input.txt for SHA-256 circuit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate-input.py "hello"
  python generate-input.py "hel?o"           # '?' = unknown byte
  python generate-input.py --hex "48454c4c4f"
  python generate-input.py --hex "4845XX4c4f" # 'XX' = unknown byte
  python generate-input.py -o my_input.txt "test"
  echo -n "hello" | python generate-input.py --stdin
"""
    )

    parser.add_argument("input", nargs="?", default=None,
                        help="Input string (ASCII text or hex with --hex flag). Use '?' for unknown bytes.")
    parser.add_argument("--hex", "-x", action="store_true",
                        help="Interpret input as hexadecimal string (use XX for unknown bytes)")
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

    # Parse to bytes (list of int or None)
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
        num_unknown = count_unknowns(message)
        print(f"Generated {args.output}")
        print(f"  Message: {format_message_repr(message)}")
        print(f"  Length: {len(message)} bytes")
        print(f"  Hex: {format_message_hex(message)}")
        if num_unknown > 0:
            print(f"  Unknown bytes: {num_unknown} ({num_unknown * 8} unknown bits)")


if __name__ == "__main__":
    main()
