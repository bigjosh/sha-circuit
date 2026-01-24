# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

We have an SHA-256 circuit representation expressed as a directed acyclic graph (DAG) of NAND gates.

The circuit is contained in two types of files:

- **Input files** (e.g., `input-bits.txt`, `constants-bits.txt`) that define input values. Each line is one input in the format `{label},{value}` where value is 0 or 1. All processing programs accept one or more input files via the `-i` flag.
- **NAND gates files** (e.g., `nands-optimized.txt`) that define a circuit of NAND gates. Each line is one NAND gate in the format `{label},{input A},{input B}` where both inputs are labels that have been previously defined.

## File Format

Both input files and constant files use the same unified format:
```
label,value
```
Where:
- `label` is a unique identifier for the signal
- `value` is 0, 1, or X (unbound/unknown)

Examples:
- `input-bits.txt`: `INPUT-W0-B0,0` or `INPUT-W0-B0,X`
- `constants-bits.txt`: `CONST-0,0` or `K-0-B0,1`

## Three-Valued Logic

The circuit supports three-valued logic where `X` represents an unbound or unknown value. X values propagate through NAND gates according to:

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

Key insight: If either input is 0, the output is always 1 (regardless of X).

## Goal

Our goal is to reduce the number of NAND gates required to represent this function by applying aggressive optimizations.

There is an existing program `optimization-pipeline.py` that created `nands-optimized.txt` from `nands.txt` using various optimizations. We want to go much farther and be much more aggressive in finding other optimizations we can apply. The only constraint is that the optimizations *must not* alter the functionality. You should test with a few randomly generated inputs to ensure that the outputs do not change after making optimizations. 

