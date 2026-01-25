# SHA-256 NAND Circuit

A complete implementation of SHA-256 as a circuit of NAND gates.

We also have tools for doing experiments on bound and unbound bits in the input and out bits of the hash. 

## Quick Start

```bash
# Build the optimized circuit (one-time)
python sha256_circuit_generator.py
python expand-words.py -i constants.txt -o constants-bits.txt --add-constants
python expand-words.py -i results.txt -o results-bits.txt
python optimized-converter.py
python optimize-nands.py

# Hash a message
python generate-input.py "hello"
python expand-words.py -i input.txt -o input-bits.txt
python eval-nands.py -n nands-optimized-final.txt
# Output: 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
```

## Data Flow

![Data Flow Diagram](data-flow.svg)

## File Formats

### Word-Level Files

**input.txt** - 16 input words (512-bit message block with SHA-256 padding)
```
INPUT-W0,6a6f7368
INPUT-W1,80000000
...
INPUT-W15,00000020
```

**constants.txt** - 64 round constants (K-0..K-63) + 8 initial hash values (H-INIT-0..H-INIT-7)
```
K-0,428a2f98
K-1,71374491
...
H-INIT-0,6a09e667
```

**functions.txt** - Circuit operations (XOR, AND, OR, NOT, ADD, ROTR, SHR, COPY, MAJ, CH)
```
R0-S1-ROTR6,ROTR6,R63-VAR-E
R0-CH,CH,R63-VAR-E,R63-VAR-F,R63-VAR-G
...
```

**results.txt** - 8 output words (all unknown, computed by circuit)
```
OUTPUT-W0,XXXXXXXX
OUTPUT-W1,XXXXXXXX
...
OUTPUT-W7,XXXXXXXX
```

### Bit-Level Files

**constants-bits.txt** / **input-bits.txt** - Individual bits (0, 1, or X for unknown)
```
CONST-0,0
CONST-1,1
K-0-B0,0
K-0-B1,0
...
```

**nands.txt** / **nands-optimized-final.txt** - NAND gates
```
LABEL,INPUT_A,INPUT_B
```

**results-bits.txt** - Output specification (256 bits)
```
OUTPUT-W0-B0,X
OUTPUT-W0-B1,X
...
OUTPUT-W7-B31,X
```
The `X` indicates expected value is unknown (computed by circuit).

## Programs

### Build Pipeline

**`sha256_circuit_generator.py`**
- Generates the SHA-256 circuit from specification. Produces word-level operations (ADD, XOR, ROTR, etc.), round constants K0-K63, initial hash values H0-H7, and output labels.
- Inputs: (none)
- Outputs: `functions.txt`, `constants.txt`, `results.txt`

**`expand-words.py`**
- Expands 32-bit words to individual bits. Each word becomes 32 bit lines. Supports unknown bytes (`XX` in hex → `X` bits).
- Inputs: word-level file (`constants.txt`, `input.txt`, or `results.txt`)
- Outputs: bit-level file (`constants-bits.txt`, `input-bits.txt`, or `results-bits.txt`)
- Flags: `-c` adds CONST-0 and CONST-1 (use for constants only)

**`optimized-converter.py`**
- Converts word-level operations to NAND gates using optimized decompositions (4-NAND XOR, 13-NAND full adder, etc.).
- Inputs: `functions.txt`
- Outputs: `nands.txt`

**`optimize-nands.py`**
- Applies optimization passes (CSE, constant folding, dead code elimination, etc.) iteratively until convergence. Reduces gate count by ~22%.
- Inputs: `nands.txt`, `constants-bits.txt`, `results-bits.txt`
- Outputs: `nands-optimized-final.txt`

### Input Generation

**`generate-input.py`**
- Creates padded SHA-256 message block from ASCII text or hex string. Supports unknown bytes (`?` in ASCII, `XX` in hex).
- Inputs: command line argument (ASCII string or `--hex`)
- Outputs: `input.txt`

### Evaluation & Verification

**`eval-nands.py`**
- Evaluates the NAND circuit with given inputs. Supports three-valued logic (0, 1, X). Outputs hash in hex with `x` for unknown nibbles.
- Inputs: `nands*.txt`, `constants-bits.txt`, `input-bits.txt`, `results-bits.txt`
- Outputs: hash (stdout)

**`verify-circuit.py`**
- Tests circuit against Python's hashlib.sha256 with fixed and random messages.
- Inputs: `nands*.txt`, `constants-bits.txt`
- Outputs: pass/fail (stdout)

### Utilities

**`ablate-outputs.py`**
- Removes output bits from results file to enable dead code elimination for partial hash computation.
- Inputs: `results-bits.txt`
- Outputs: `results-ablated.txt`

**`analyze-layers.py`**
- Computes circuit depth (critical path length) and layer statistics.
- Inputs: `nands*.txt`
- Outputs: depth analysis (stdout)

## Three-Valued Logic

The circuit supports three-valued logic where `X` represents an unknown value:

| A | B | NAND |
|---|---|------|
| 0 | * | 1 |
| * | 0 | 1 |
| 1 | 1 | 0 |
| 1 | X | X |
| X | 1 | X |
| X | X | X |

Key insight: If either input is 0, output is always 1.

### Unknown Input Bytes

Use `?` in ASCII or `XX` in hex to mark unknown bytes:

```bash
python generate-input.py "hel?o"              # ASCII with unknown byte
python generate-input.py --hex "68656cXX6f"   # Hex with unknown byte
```

Output uses lowercase `x` for nibbles containing unknown bits:
```
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
(256/256 bits unknown)
```

Due to SHA-256's avalanche effect, any unknown input bit causes all 256 output bits to become unknown.

## Optimizations

### NAND Decomposition

| Operation | NANDs/bit | Notes |
|-----------|-----------|-------|
| NOT(A) | 1 | `NAND(A,A)` |
| AND(A,B) | 2 | `NOT(NAND(A,B))` |
| OR(A,B) | 3 | `NAND(NOT(A), NOT(B))` |
| XOR(A,B) | 4 | Uses shared NAND |
| ROTR/SHR | 0 | Pure rewiring |
| Full Adder | 13 | Optimized (was 15) |
| MAJ(A,B,C) | 6 | OR-based form (was 14) |
| CH(E,F,G) | 4 | MUX form (was 9) |

### Optimization Passes

The optimizer applies these passes iteratively until convergence:

- **CSE**: Common subexpression elimination
- **Share inverters**: Merge duplicate NOT gates
- **Constant folding**: Evaluate gates with known inputs
- **Dead code elimination**: Remove unused gates
- **Identity patterns**: NOT(NOT(x)) = x
- **XOR optimizations**: XOR(0,x)=x, XOR(1,x)=NOT(x)
- **Algebraic**: NAND(x, NOT(x)) = 1

### Results

| Stage | Gates | Reduction |
|-------|-------|-----------|
| Initial (optimized-converter.py) | 295,200 | - |
| After optimization | 230,549 | 22% |

## Circuit Statistics

| File | Contents |
|------|----------|
| functions.txt | 2,416 operations |
| constants.txt | 72 words (64 K + 8 H) |
| results.txt | 8 words (output specification) |
| constants-bits.txt | 2,306 bits |
| input-bits.txt | 512 bits |
| results-bits.txt | 256 output labels |
| nands.txt | 295,200 gates |
| **nands-optimized-final.txt** | **230,549 gates** |

## Verification

```bash
python verify-circuit.py -n nands-optimized-final.txt -t 20
# Runs 25 tests (5 fixed + 20 random) against hashlib.sha256
# Output: "All tests passed!"
```

### Hash a Single Message (one-liner)

```bash
# Replace "your message" with your input (max 55 bytes)
python generate-input.py "your message" -o /tmp/in.txt && python expand-words.py -i /tmp/in.txt -o /tmp/in-bits.txt && python eval-nands.py -n nands-optimized-final.txt -i constants-bits.txt -i /tmp/in-bits.txt

# Example with "hello":
python generate-input.py "hello" -o /tmp/in.txt && python expand-words.py -i /tmp/in.txt -o /tmp/in-bits.txt && python eval-nands.py -n nands-optimized-final.txt -i constants-bits.txt -i /tmp/in-bits.txt
# Output: 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824

# Verify against Python's hashlib:
python -c "import hashlib; print(hashlib.sha256(b'hello').hexdigest())"
# Output: 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
```
