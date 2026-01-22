# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

We have an SHA-256 circuit representation expressed as a directed acyclic graph (DAG) of NAND gates. 

The circuit is contained in two files:

- "constant-bits.txt" that defines constants. Each line is one constant in the format {label},{value} where value is 0 or 1.
- "nands-optimized.txt" the defines the NAND gates. Each line is one NAND gate in the format {label},{input A},{input B} where both inputs are labels that have been previously Defined. 

## Goal

Our goal is to reduce the number of NAND gates required to represent this function by applying aggressive optimizations. 

There is an existing program `optimize-nands.py` that created the `nands-optimized.txt` from `nands.txt` using straightforward optimizations. We want to go much farther and be much more aggressive in finding other optimizations we can apply. The only constraint is that the optimizations *must not* alter the functionality. You should test with a few randomly generated inputs to ensure that the outputs do not change after making optimizations. 

