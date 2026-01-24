## TLDR

You can jump direct to the [Complete Workflow](#Complete-Workflow) if you want to generate an SHA256 hash via NAND gates using your own input.

# SHA-256 Circuit Representation

A circuit representation of the SHA-256 hash function, expressed as a directed acyclic graph of nodes. Each node is either a constant value or a function applied to previous nodes.

The circuit can be represented at two levels:
1. **Word-level**: 32-bit operations on labeled nodes
2. **Bit-level**: NAND-only gates operating on individual bits

We have tools to expand/convert the word level files into bitlevel files. 

## Word-Level Representation

### File Formats

All values are 32-bit unsigned integers represented as 8-character lowercase hex strings.

#### input.txt

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

#### constants.txt

Round constants and initial hash values. Taken directly from the SHA256 spec 

```
LABEL,VALUE
```

Contains:
- 64 round constants: `K-0` through `K-63`
- 8 initial hash values: `H-INIT-0` through `H-INIT-7`

#### functions.txt

Function nodes defining the circuit operations. One node per line, evaluated in order.

```
LABEL,FUNCTION,INPUT1,INPUT2,...
```

- **LABEL**: Human-readable identifier (e.g., `R0-S1-ROTR6`, `MSG-W16`)
- **FUNCTION**: Operation to perform
- **INPUTS**: Labels of previously defined nodes

**Supported Functions:**

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

**Output Nodes:** `OUTPUT-W0` through `OUTPUT-W7`

### Word-Level Utilities

#### generate-input.py

Generate `input.txt` from ASCII text or hex input.

```bash
python generate-input.py "hello"              # ASCII text
python generate-input.py --hex "68656c6c6f"   # Hex string
python generate-input.py -o my_input.txt "hello"
echo -n "hello" | python generate-input.py --stdin
```

**Note**: Maximum message length is 55 bytes (single 512-bit block).

#### eval-functions.py

Evaluate the word-level circuit and output the hash.

```bash
python eval-functions.py
python eval-functions.py -d ./circuit_dir
```

#### sha256_circuit_generator.py

Generate constants.txt and functions.txt.

```bash
python sha256_circuit_generator.py
```

## Bit-Level Representation

Convert the word-level circuit to NAND-only gates operating on individual bits.

### File Formats

#### constants-bits.txt

Bit-level expansion of constants. Each 32-bit constant becomes 32 lines.

```
LABEL,VALUE
```

- **LABEL**: `{CONST}-B{bit}` where bit 0 = LSB, bit 31 = MSB
- **VALUE**: `0`, `1`, or `X` (unbound/unknown)

Also includes special constants `CONST-0` and `CONST-1`.

Example:
```
CONST-0,0
CONST-1,1
K-0-B0,0
K-0-B1,0
K-0-B2,0
K-0-B3,1
...
```

#### input-bits.txt

Bit-level expansion of input words. Same format as constants-bits.txt.

```
INPUT-W0-B0,0
INPUT-W0-B1,0
INPUT-W0-B2,1
...
```

### Three-Valued Logic

The circuit supports three-valued logic where `X` represents an unbound or unknown value. This is useful for:
- Analyzing which outputs depend on which inputs
- Partial evaluation when some inputs are unknown
- Circuit optimization and analysis

X values propagate through NAND gates according to:

| A | B | NAND |
|---|---|------|
| 0 | 0 | 1 |
| 0 | 1 | 1 |
| 1 | 0 | 1 |
| 1 | 1 | 0 |
| 0 | X | 1 |
| X | 0 | 1 |
| 1 | X | X |
| X | 1 | X |
| X | X | X |

**Key insight**: If either input is 0, the output is always 1 (regardless of X).

#### nands.txt

NAND-only circuit. Each line is a single NAND gate.

```
LABEL,INPUT_A,INPUT_B
```

The output of `NAND(INPUT_A, INPUT_B)` is stored in `LABEL`.

**Output Nodes:** `OUTPUT-W{0-7}-B{0-31}`

### Bit-Level Utilities

#### expand-constants.py

Convert constants.txt to bit-level representation.

```bash
python expand-constants.py
python expand-constants.py -i constants.txt -o constants-bits.txt
```

#### expand-input.py

Convert input.txt to bit-level representation.

```bash
python expand-input.py
python expand-input.py -i input.txt -o input-bits.txt
```

#### convert-to-nands.py

Convert functions.txt to NAND-only gates.

```bash
python convert-to-nands.py
python convert-to-nands.py -i functions.txt -o nands.txt
```

#### eval-nands.py

Evaluate the NAND circuit and output the hash.

```bash
python eval-nands.py
python eval-nands.py -i input-bits.txt -i constants-bits.txt
python eval-nands.py -i input-bits.txt -i constants-bits.txt -n nands-optimized-final.txt
python eval-nands.py -d ./circuit_dir   # Uses default files in directory
```

NOTE: Importantly, this program is essentially just the single expression....

```
nodes[label] = not (nodes[a] and nodes[b])
```

...applied consecutively to each line in the `nands.txt` file so it is very easy to verify.

#### optimization-pipeline.py

Comprehensive optimization pipeline that combines all optimization strategies into a single tool.

**Recommended usage** (best optimization):
```bash
python optimization-pipeline.py -v
```

This runs the complete optimized workflow:
1. Converts `functions.txt` using `optimized-converter.py` (best primitives)
2. Applies all optimization passes iteratively
3. Verifies correctness against reference SHA-256
4. Outputs to `nands-optimized-final.txt`

**Other usage patterns:**
```bash
# Optimize existing NAND file (less optimal starting point):
python optimization-pipeline.py -n nands.txt -v

# Custom input/output files:
python optimization-pipeline.py -f functions.txt -i constants-bits.txt -o output.txt -v -t 10
```

**Input/Output:**
- **Input**: `functions.txt` (recommended) or existing NAND file via `-n`
- **Input files**: Reads from `-i` specified files for constant/input values (default: `constants-bits.txt`)
- **Output**: Optimized NAND file (default: `nands-optimized-final.txt`)

**Optimization Passes** (applied iteratively until convergence):
1. **Output renaming**: Converts `FINAL-H*-ADD-B*` labels to `OUTPUT-W*-B*`
2. **CSE**: Common subexpression elimination
3. **Constant folding**: Propagates known constant values
4. **Dead code elimination**: Removes gates not needed for outputs
5. **Identity patterns**: Eliminates `NOT(NOT(x)) = x` patterns
6. **XOR(0,x)=x**: Removes identity XOR operations
7. **XOR(1,x)=NOT(x)**: Simplifies XOR with constant 1

#### optimized-converter.py

Converts word-level functions to NAND gates using optimized primitive implementations.

```bash
python optimized-converter.py -i functions.txt -o nands.txt
```

**Input/Output:**
- **Input**: `functions.txt` (word-level functions with labels like `R0-MAJ`, `MSG-W16`)
- **Output**: `nands.txt` with bit-level NAND gates (labels like `FINAL-H0-ADD-B0`)

**Optimized Primitives:**
| Operation | NANDs/bit | Improvement |
|-----------|-----------|-------------|
| MAJ(a,b,c) | 6 | Was 14 (XOR form) |
| CH(e,f,g) | 9 | Was 12 (naive) |
| Full Adder | 13 | Was 15 (standard) |

Note: Output labels use `FINAL-H*-ADD-B*` format. Use `optimization-pipeline.py` to convert to standard `OUTPUT-W*-B*` format.

#### verify-circuit.py

Verification tool that tests the NAND circuit against Python's reference SHA-256.

```bash
python verify-circuit.py -n nands-optimized-final.txt
python verify-circuit.py -n nands-optimized-final.txt -i constants-bits.txt
python verify-circuit.py -n nands-optimized-final.txt --tests 20  # More random tests
python verify-circuit.py -n nands-optimized-final.txt -v          # Verbose output
```

Runs multiple test cases including edge cases (empty message, single char) and random inputs to verify the optimized circuit produces correct SHA-256 hashes.

### Optimization Results

Starting from 461,568 NAND gates, the optimization pipeline achieves significant reductions:

| Stage | Gates | Reduction |
|-------|-------|-----------|
| Original (`nands.txt`) | 461,568 | - |
| Basic optimizer | 412,008 | 11% |
| Advanced optimizer | 260,440 | 44% |
| MAJ rewriter | 246,072 | 47% |
| Constant propagation | 241,057 | 48% |
| Identity pattern elimination | 235,775 | 49% |
| **Full pipeline** | **234,440** | **49.2%** |

**Best result: 234,440 gates (49.2% reduction from original 461,568)**
**Total savings: 227,128 gates**

The optimization pipeline combines:
1. **CSE**: Common subexpression elimination
2. **Constant folding/propagation**: Evaluates known constants
3. **Dead code elimination**: Removes unused gates
4. **Identity patterns**: Eliminates `NOT(NOT(x)) = x` (saves ~4,000 gates)
5. **XOR optimizations**: `XOR(0,x)=x` and `XOR(1,x)=NOT(x)`

### NAND Decomposition

| Operation | NANDs/bit | Formula |
|-----------|-----------|---------|
| NOT(A) | 1 | `NAND(A,A)` |
| AND(A,B) | 2 | `NAND(NAND(A,B), NAND(A,B))` |
| OR(A,B) | 3 | `NAND(NAND(A,A), NAND(B,B))` |
| XOR(A,B) | 4 | `NAND(NAND(A,t), NAND(B,t))` where `t=NAND(A,B)` |
| XOR(A,B,C) | 8 | Two chained 2-input XORs |
| ROTR/SHR | 0 | Pure rewiring (no gates needed after optimization) |
| ADD | 13 | Optimized full adder with gate sharing (was 15) |
| MAJ(A,B,C) | 6 | Optimized OR-based form (was 14 with XOR form) |
| CH(E,F,G) | 4 | Optimal MUX form: `NAND(NAND(e,f), NAND(NOT(e),g))` (was 9) |

**Full Adder Optimization**: The standard full adder implementation uses 15 NANDs (2 XORs + 2 ANDs + 1 OR). By reusing intermediate NAND results from the XOR gates, the optimized implementation reduces this to 13 NANDs while computing the same function. This saves 38,400 gates in the unoptimized circuit (7.5%). After the complete optimization pipeline, final gate counts are nearly identical (~251K gates) because downstream optimizations (CSE, constant propagation) can largely compensate for full adder inefficiencies.

**CH Function Optimization**: The CH (choice) function `CH(e,f,g) = (e AND f) XOR ((NOT e) AND g)` is equivalent to a 2:1 multiplexer: "if e then f else g". The standard decomposition uses 9 NANDs, but recognizing it as a MUX allows a direct 4-NAND implementation. This optimization is implemented natively in the circuit generator and saves 48,640 gates in the unoptimized circuit (9.5%), with 9,874 gates remaining after the full optimization pipeline (3.9% additional reduction).

**XOR Chain Sharing**: Recognizes XOR patterns with constant inputs for specialized optimization. `XOR(CONST-0, x) = x` is the identity operation, eliminating all 4 NANDs. `XOR(CONST-1, x) = NOT(x)` reduces 4 NANDs to 1. In SHA-256, full adders start with carry=0, creating 600 XOR(0,x) patterns throughout the circuit. This optimization eliminates 4,800 gates in the unoptimized circuit (1.0%), with 1,192 gates remaining after the full optimization pipeline (0.5% additional reduction). Total improvement: 53.0% reduction from the original 510,208 gates.

## Complete Workflow

### Data Flow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ WORD LEVEL (32-bit operations)                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  input.txt          constants.txt         functions.txt                     │
│  (16 words)         (72 words)            (2,672 ops)                       │
│  INPUT-W0..W15      K-0..K-63             R0-MAJ, MSG-W16, etc.             │
│  "6a6f7368"         H-INIT-0..H-INIT-7    XOR, AND, ADD, ROTR...            │
│       │                   │                      │                          │
│       ▼                   ▼                      ▼                          │
│  ┌─────────┐        ┌──────────┐          ┌─────────────┐                   │
│  │expand-  │        │expand-   │          │convert-to-  │                   │
│  │input.py │        │constants │          │nands.py  OR │                   │
│  └────┬────┘        │.py       │          │optimized-   │                   │
│       │             └────┬─────┘          │converter.py │                   │
│       │                  │                └──────┬──────┘                   │
├───────┼──────────────────┼───────────────────────┼──────────────────────────┤
│ BIT LEVEL (individual bits, NAND gates only)                                │
├───────┼──────────────────┼───────────────────────┼──────────────────────────┤
│       ▼                  ▼                       ▼                          │
│  input-bits.txt    constants-bits.txt       nands.txt                       │
│  (512 bits)        (2,306 bits)             (461K gates)                    │
│  INPUT-W0-B0       K-0-B0, CONST-0/1        OUTPUT-W0-B0..W7-B31            │
│  0 or 1            H-INIT-0-B0, etc.        label,inputA,inputB             │
│       │                  │                       │                          │
│       │                  │                       ▼                          │
│       │                  │              ┌─────────────────┐                 │
│       │                  │              │optimization-    │                 │
│       │                  └─────────────►│pipeline.py      │                 │
│       │                                 └────────┬────────┘                 │
│       │                                          ▼                          │
│       │                                 nands-optimized-final.txt           │
│       │                                 (234K gates, 49% smaller)           │
│       │                                          │                          │
│       ▼                                          ▼                          │
│  ┌────────────────────────────────────────────────────┐                     │
│  │ eval-nands.py (combines input-bits + constants +   │                     │
│  │                nands to compute SHA-256 hash)      │                     │
│  └────────────────────────────────────────────────────┘                     │
│                           │                                                 │
│                           ▼                                                 │
│                    256-bit hash output                                      │
│                    (8 words × 32 bits)                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Instructions

```bash
# 1. Generate word-level circuit (one-time setup)
python sha256_circuit_generator.py
# Input:  (none - generates from SHA-256 spec)
# Output: constants.txt (72 words), functions.txt (2,672 operations)

# 2. Create input for your message
python generate-input.py "hello"
# Input:  ASCII string or hex
# Output: input.txt (16 words with SHA-256 padding)

# 3. Verify with word-level evaluator (optional)
python eval-functions.py
# Input:  input.txt + constants.txt + functions.txt
# Output: 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824

# 4. Expand to bit-level representation
python expand-constants.py
# Input:  constants.txt (72 words)
# Output: constants-bits.txt (2,306 bits including CONST-0, CONST-1)

python expand-input.py
# Input:  input.txt (16 words)
# Output: input-bits.txt (512 bits)

# 5. Convert functions to NAND gates
python convert-to-nands.py
# Input:  functions.txt (word-level operations)
# Output: nands.txt (461,568 NAND gates)

# 6. Optimize the circuit (RECOMMENDED - saves 49% of gates)
python optimization-pipeline.py -n nands.txt -o nands-optimized-final.txt -v
# Input:  nands.txt + constants-bits.txt
# Output: nands-optimized-final.txt (234,440 gates)

# 7. Evaluate the optimized circuit
python eval-nands.py -n nands-optimized-final.txt
# Input:  input-bits.txt + constants-bits.txt + nands-optimized-final.txt
# Output: 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824

# 8. Verify correctness (tests multiple random inputs)
python verify-circuit.py -n nands-optimized-final.txt
# Input:  constants-bits.txt + nands-optimized-final.txt
# Output: "All tests passed!" (compares against Python's hashlib.sha256)
```

### Quick Start (Minimal Steps)

If you just want to compute a SHA-256 hash using the pre-optimized circuit:

```bash
# Generate input bits for your message
python generate-input.py "your message here"
python expand-input.py

# Evaluate using the optimized circuit (already included in repo)
python eval-nands.py -n nands-optimized-final.txt
```

## Circuit Statistics

| File | Lines | Description |
|------|-------|-------------|
| constants.txt | 72 | 64 round constants (K) + 8 initial hash values (H_INIT) |
| functions.txt | 2,672 | Word-level operations (XOR, AND, ADD, ROTR, etc.) |
| constants-bits.txt | 2,306 | 72×32 bits + CONST-0 + CONST-1 |
| input-bits.txt | 512 | 16 words × 32 bits |
| nands.txt | 461,568 | NAND gates (unoptimized) |
| nands-optimized-final.txt | 234,440 | **Fully optimized (49.2% reduction)** |

### Gate Distribution (Optimized Circuit)

| Operation | Gates | Percentage |
|-----------|-------|------------|
| ADD (32-bit adders) | 141,033 | 55% |
| Sigma functions (XOR chains) | 88,048 | 34% |
| MAJ (majority) | 10,272 | 4% |
| CH (choice) | 16,384 | 6% |
| OUTPUT | 512 | <1% |

## Circuit Visualization

Tools for visualizing the circuit structure and analyzing the dataflow.

### analyze-layers.py

Analyze the layer structure and critical path depth of the circuit.

```bash
python analyze-layers.py
python analyze-layers.py -n nands-optimized-final.txt
python analyze-layers.py -n nands-optimized-final.txt -i constants-bits.txt -i input-bits.txt
python analyze-layers.py -n nands-optimized-final.txt -v  # Verbose output
```

Computes layers where:
- **Layer 0**: Input bits and constant bits
- **Layer N**: Gates where `max(layer(input_a), layer(input_b)) = N-1`

The maximum layer number represents the critical path depth (longest dependency chain).

### generate-visualization.py

Generate an interactive HTML visualization of the circuit.

```bash
python generate-visualization.py
python generate-visualization.py -n nands-optimized-final.txt -o visualization.html
python generate-visualization.py -n nands-optimized-final.txt -i constants-bits.txt -i input-bits.txt
```

Creates a self-contained HTML file with embedded JavaScript that visualizes the circuit as a 2D pixel map:

**Features:**
- Each gate = 1 pixel with color coding:
  - Green = input bits (INPUT-*)
  - Yellow = constant bits (K-*, H-INIT-*, CONST-*)
  - Blue = computation gates
  - Red = output bits (OUTPUT-*)
- **Layer-based layout**: Layer 0 at top, subsequent layers below
- **Interactive controls**:
  - Mouse hover: Show gate details and direct connections
  - Click input bits: Trace all dependent gates (highlights in yellow)
  - Mouse wheel: Zoom in/out
  - Drag: Pan view
  - Keyboard: R (reset view), +/- (zoom)
  - "Find Inputs" button: Navigate to input layer

**Circuit Statistics:**
- Total gates: ~250,000
- Layers: ~5,300 (critical path depth)
- Widest layer: ~1,300 gates
- Fully self-contained (no external dependencies)

Open the generated HTML file in any modern browser to explore the circuit structure interactively.
