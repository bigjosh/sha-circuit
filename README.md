## TLDR

You can jump direct to the [Complete Workflow](Complete Workflow) if you want to generate an SHA256 hash via NAND gates using your own input.

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
```

NOTE: Importantly, this program is essentially just the single expression....

```
nodes[label] = not (nodes[a] and nodes[b])
```

...applied consecutively to each line in the `nands.txt` file so it is very easy to verify. 

### NAND Decomposition

| Operation | NANDs/bit | Formula |
|-----------|-----------|---------|
| NOT(A) | 1 | `NAND(A,A)` |
| AND(A,B) | 2 | `NAND(NAND(A,B), NAND(A,B))` |
| OR(A,B) | 3 | `NAND(NAND(A,A), NAND(B,B))` |
| XOR(A,B) | 4 | `NAND(NAND(A,t), NAND(B,t))` where `t=NAND(A,B)` |
| ROTR/SHR | 2 | Rewiring with double-NOT to copy bits |
| ADD | ~9 | Full adder per bit (ripple-carry) |

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

# 6. Verify against reference
python -c "import hashlib; print(hashlib.sha256(b'hello').hexdigest())"
# Output: 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
```

## Circuit Statistics

| File | Lines | Description |
|------|-------|-------------|
| constants.txt | 72 | 64 K + 8 H_INIT |
| functions.txt | 2,864 | Word-level operations |
| constants-bits.txt | 2,306 | 72×32 + 2 special constants |
| input-bits.txt | 512 | 16×32 bits |
| nands.txt | 529,408 | NAND gates |
