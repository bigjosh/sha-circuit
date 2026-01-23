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
- **VALUE**: `0` or `1`

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
python eval-nands.py -d ./circuit_dir
python eval-nands.py -n nands-optimized.txt   # Use a different NAND file
```

NOTE: Importantly, this program is essentially just the single expression....

```
nodes[label] = not (nodes[a] and nodes[b])
```

...applied consecutively to each line in the `nands.txt` file so it is very easy to verify.

#### optimize-nands.py

Basic NAND circuit optimizer with standard optimization passes.

```bash
python optimize-nands.py
python optimize-nands.py -i nands.txt -o nands-optimized.txt
python optimize-nands.py -q   # Quiet mode
```

Applies multiple optimization passes:
- **Constant folding**: Simplifies expressions with CONST-0/CONST-1
- **Algebraic**: NAND(x, NOT(x)) = 1
- **Double negation**: NOT(NOT(x)) = x
- **Redundant copy**: Removes unnecessary copy chains
- **Share inverters**: Merges duplicate NOT gates
- **CSE**: Common subexpression elimination
- **Dead code**: Removes unused gates

#### advanced-optimizer.py

Advanced optimizer with more aggressive optimization techniques.

```bash
python advanced-optimizer.py
python advanced-optimizer.py -i nands.txt -o nands-optimized.txt
```

Additional optimizations beyond the basic optimizer:
- **Deep double negation**: More aggressive NOT(NOT(x)) elimination
- **AND/OR simplification**: Recognizes and simplifies AND(x,x) and OR(x,x) patterns
- **XOR chain optimization**: Identifies and shares XOR subexpressions
- **NAND identity**: Merges NAND(x, CONST-1) with equivalent NOT(x) gates

#### maj-rewriter.py

Specialized optimizer that rewrites MAJ (majority) function patterns.

```bash
python maj-rewriter.py
python maj-rewriter.py -i nands-optimized.txt -o nands-maj-opt.txt
```

The MAJ function `MAJ(a,b,c) = (a AND b) XOR (a AND c) XOR (b AND c)` is used 2,048 times in SHA-256 (64 rounds × 32 bits). The standard XOR-based implementation uses 14 NANDs per bit, but an equivalent OR-based form uses only 6 NANDs:

```
MAJ(a,b,c) = OR(OR(AND(a,b), AND(a,c)), AND(b,c))

Efficient NAND implementation (6 gates):
1. ab_nand = NAND(a, b)
2. ac_nand = NAND(a, c)
3. bc_nand = NAND(b, c)
4. x = NAND(ab_nand, ac_nand)
5. not_x = NAND(x, x)
6. maj = NAND(not_x, bc_nand)
```

This single optimization saves ~14,000 gates.

#### constant-propagation.py

Constant propagation optimizer that loads actual bit values from constants-bits.txt and propagates them through the circuit.

```bash
python constant-propagation.py
python constant-propagation.py -i nands-optimized.txt -o nands-const-prop.txt
```

Unlike basic constant folding which only knows about CONST-0 and CONST-1 labels, this optimizer:
- Loads actual constant bit values from constants-bits.txt (K-* and H-INIT-* constants)
- Propagates these known values through the circuit
- Applies NAND simplification rules:
  - `NAND(0, x) = 1` → replace with CONST-1
  - `NAND(x, 0) = 1` → replace with CONST-1
  - `NAND(1, 1) = 0` → replace with CONST-0

This catches optimizations missed by basic constant folding and saves ~5,300 gates.

#### iterative-optimize.py

Runs constant propagation and standard optimization passes iteratively until convergence.

```bash
python iterative-optimize.py
python iterative-optimize.py -i nands-optimized.txt -o nands-final.txt
python iterative-optimize.py --max-rounds 10  # Limit iterations
```

Alternates between constant propagation and standard optimizations to find opportunities that each pass exposes for the other, automatically stopping when no more improvements are found.

#### verify-circuit.py

Verification tool that tests the NAND circuit against Python's reference SHA-256.

```bash
python verify-circuit.py -n nands-optimized.txt
python verify-circuit.py -n nands-optimized.txt --tests 20  # More random tests
python verify-circuit.py -n nands-optimized.txt -v          # Verbose output
```

Runs multiple test cases including edge cases (empty message, single char) and random inputs to verify the optimized circuit produces correct SHA-256 hashes.

### Optimization Results

Starting from 510,208 NAND gates (old) / 461,568 (with CH optimization), the optimization pipeline achieves:

| Stage | Old Pipeline | New Pipeline (CH-opt) | Reduction |
|-------|--------------|----------------------|-----------|
| Original (nands.txt) | 510,208 | 461,568 | - |
| Basic optimizer | 422,248 | 412,008 | 10% / 11% |
| Advanced optimizer | 270,680 | 260,440 | 47% / 44% |
| MAJ rewriter | 256,249 | 246,072 | 50% / 47% |
| Constant propagation | 250,931 | **241,057** | 51% / **52.8%** |

**Best result: 241,057 gates (52.8% reduction from original 510,208)**
**Total savings: 269,151 gates**

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

## Complete Workflow

```bash
# 1. Generate word-level circuit (one-time)
python sha256_circuit_generator.py

# 2. Create input for your message
python generate-input.py "hello"

# 3. Verify with word-level evaluator
python eval-functions.py
# Output: 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824

# 4. Convert to bit-level representation
python expand-constants.py
python expand-input.py
python convert-to-nands.py

# 5. Verify with NAND evaluator
python eval-nands.py
# Output: 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824

# 6. Optimize the circuit (optional but recommended)
python optimize-nands.py                    # Basic optimizer: 510K -> 422K gates
python advanced-optimizer.py                # Advanced optimizer: 422K -> 270K gates
python maj-rewriter.py                      # MAJ rewriter: 270K -> 256K gates
python constant-propagation.py              # Constant propagation: 256K -> 251K gates

# Alternative: Use iterative optimizer (runs all passes until convergence)
python iterative-optimize.py -i nands-optimized.txt -o nands-final.txt

# 7. Verify optimized circuit
python verify-circuit.py -n nands-final.txt
python eval-nands.py -n nands-final.txt
# Output: 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824

# 8. Verify against reference
python -c "import hashlib; print(hashlib.sha256(b'hello').hexdigest())"
# Output: 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
```

## Circuit Statistics

| File | Lines | Description |
|------|-------|-------------|
| constants.txt | 72 | 64 K + 8 H_INIT |
| functions.txt | 2,672 | Word-level operations (with native CH) |
| constants-bits.txt | 2,306 | 72×32 + 2 special constants |
| input-bits.txt | 512 | 16×32 bits |
| nands.txt | 461,568 | NAND gates (unoptimized, with 4-NAND CH) |
| nands-optimized.txt | 246,072 | After basic/advanced/MAJ optimizers |
| nands-final-ch4.txt | 241,057 | Fully optimized (~52.8% smaller) |

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
python analyze-layers.py -n nands-final.txt
python analyze-layers.py -n nands-final.txt -v  # Verbose output
```

Computes layers where:
- **Layer 0**: Input bits and constant bits
- **Layer N**: Gates where `max(layer(input_a), layer(input_b)) = N-1`

The maximum layer number represents the critical path depth (longest dependency chain).

### generate-visualization.py

Generate an interactive HTML visualization of the circuit.

```bash
python generate-visualization.py
python generate-visualization.py -n nands-final.txt -o visualization.html
python generate-visualization.py -n nands-final.txt -c constants-bits.txt
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

### visualize-circuit.py

Alternative pygame-based interactive visualizer (requires pygame installation).

```bash
pip install pygame
python visualize-circuit.py
python visualize-circuit.py -n nands-final.txt
```

Similar features to the HTML version but runs as a native application. Use the HTML version if pygame installation is problematic.
