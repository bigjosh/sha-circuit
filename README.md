# SHA-256 Circuit Representation

A circuit representation of the SHA-256 hash function, expressed as a directed acyclic graph of nodes. Each node is either a constant value or a function applied to previous nodes.

## File Formats

All values are 32-bit unsigned integers represented as 8-character lowercase hex strings with zero padding.

### input.txt

The 16 input words (512-bit message block with SHA-256 padding).

```
LABEL,VALUE
```

- **LABEL**: `INPUT-W0` through `INPUT-W15`
- **VALUE**: 32-bit hex value

Example for message "josh":
```
INPUT-W0,6a6f7368
INPUT-W1,80000000
INPUT-W2,00000000
...
INPUT-W15,00000020
```

### constants.txt

Round constants and initial hash values.

```
LABEL,VALUE
```

Contains:
- 64 round constants: `K-0` through `K-63`
- 8 initial hash values: `H-INIT-0` through `H-INIT-7`

### functions.txt

Function nodes defining the circuit operations. One node per line, evaluated in order.

```
LABEL,FUNCTION,INPUT1,INPUT2,...
```

- **LABEL**: Human-readable identifier (e.g., `R0-S1-ROTR6`, `MSG-W16`)
- **FUNCTION**: Operation to perform
- **INPUTS**: Labels of previously defined nodes

#### Supported Functions

| Function | Inputs | Description |
|----------|--------|-------------|
| `XOR` | 2 | Bitwise exclusive OR |
| `AND` | 2 | Bitwise AND |
| `OR` | 2 | Bitwise OR |
| `NOT` | 1 | Bitwise complement |
| `ADD` | 2 | 32-bit addition (mod 2³²) |
| `ROTR{n}` | 1 | Right rotation by n bits |
| `SHR{n}` | 1 | Right shift by n bits |
| `COPY` | 1 | Identity (for labeling) |

#### Output Nodes

The final 8 nodes are the hash output: `OUTPUT-W0` through `OUTPUT-W7`.

## Utilities

### generate-input.py

Generate `input.txt` from ASCII text or hex input.

```bash
# ASCII text
python generate-input.py "hello"

# Hex string
python generate-input.py --hex "68656c6c6f"
python generate-input.py -x 0x68656c6c6f

# Custom output file
python generate-input.py -o my_input.txt "hello"

# From stdin
echo -n "hello" | python generate-input.py --stdin
```

**Note**: Maximum message length is 55 bytes (single 512-bit block).

### eval-functions.py

Evaluate the circuit and output the hash.

```bash
# Basic usage
python eval-functions.py

# From different directory
python eval-functions.py -d ./circuit_dir

# Verbose output
python eval-functions.py --verbose
```

Output is a 64-character lowercase hex string.

### sha256_circuit_generator.py

Generate all three circuit files for a given message.

```bash
python sha256_circuit_generator.py "message" [output_dir]
```

## Example

```bash
# Generate input for "josh"
python generate-input.py "josh"

# Evaluate circuit
python eval-functions.py
# Output: 386a85d8c88778b00b1355608363c7e3078857f3e9633cfd0802d3bf1c0b5b83

# Verify
python -c "import hashlib; print(hashlib.sha256(b'josh').hexdigest())"
# Output: 386a85d8c88778b00b1355608363c7e3078857f3e9633cfd0802d3bf1c0b5b83
```
