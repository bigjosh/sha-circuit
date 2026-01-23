# SHA-256 NAND Circuit Optimization Results

## Summary

**Original Circuit:** 510,208 NAND gates
**Optimized Circuit:** 235,775 NAND gates
**Gates Saved:** 274,433 (53.79% reduction)

## Optimization Techniques Applied

### 1. Basic Optimizations (Already Applied)
- Common Subexpression Elimination (CSE)
- Constant Folding
- Dead Code Elimination

### 2. Function-Level Optimizations (Previous Session)
- **CH Function:** 9 NANDs -> 4 NANDs
- **MAJ Function:** 14 NANDs -> 6 NANDs
- **Full Adder:** 15 NANDs -> 13 NANDs
- **XOR Chain Sharing:** XOR(0, x) = x optimization

### 3. New Optimizations (This Session)

#### XOR(CONST-1, x) = NOT(x) Optimization
- **Savings:** 77 gates
- **File:** `xor1-optimizer.py`
- **Principle:** XOR with 1 is equivalent to NOT, which uses 1 NAND instead of 4

#### Re-running Advanced Optimizer
- **Savings:** 132 gates
- **Principle:** Previous optimizations exposed new CSE opportunities

#### Identity Pattern Elimination (MAJOR)
- **Savings:** 3,881 gates
- **File:** `identity-optimizer.py`
- **Principle:** Found NOT(NOT(x)) = x patterns implemented as NAND(CONST-1, NAND(CONST-1, x))
- **Root Cause:** In sigma functions (s0, s1), the SHR operation produces zeros in high bits. XOR with these zeros was implemented using the standard XOR template with CONST-1, resulting in 2 unnecessary NANDs per bit.

## Analysis Scripts Created

1. **deep-analysis.py** - Comprehensive circuit structure analysis
2. **pattern-finder.py** - Find specific gate patterns
3. **fanout-analysis.py** - Analyze signal fanout distribution
4. **sigma-bit-analysis.py** - Analyze sigma function bit-level structure
5. **round-sharing.py** - Find cross-round sharing opportunities
6. **redundancy-finder.py** - Find potentially redundant patterns
7. **identity-optimizer.py** - Remove NOT(NOT(x)) patterns
8. **xor1-optimizer.py** - Optimize XOR(CONST-1, x) to NOT(x)
9. **mega-optimizer.py** - Iterative multi-pass optimizer

## Circuit Structure Analysis

### Gate Distribution (235,775 gates)
- **ADD operations:** ~70% (largest portion)
- **XOR operations:** ~23%
- **MAJ operations:** ~4%
- **CH operations:** ~2.5%
- **Other:** <1%

### Key Findings
- 3-input XOR cannot be done in fewer than 8 NANDs (appears to be optimal)
- 256 OUTPUT gate double-NOTs cannot be eliminated (they ARE the outputs)
- Cross-round sharing not possible (different data in each round)
- Simulation-based functional equivalence found false positives

## Verification

All optimizations verified using:
```
python verify-circuit.py -n nands-identity-opt.txt --tests 10
```

Results: 15 passed, 0 failed

## Files

- **Best verified circuit:** `nands-identity-opt.txt` (235,775 gates)
- **Original circuit:** `nands.txt` (461,568 gates after initial conversion)

## Techniques Explored But Not Yielding Gains

1. **3-input XOR optimization** - 8 NANDs is already optimal
2. **Carry chain restructuring** - Current implementation is efficient
3. **Functional equivalence merging** - False positives, verification failures
4. **Cross-round sharing** - Data differs between rounds
5. **Duplicate NOT gates** - Already handled by CSE
