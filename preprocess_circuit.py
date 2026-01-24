#!/usr/bin/env python3
"""
Preprocess Circuit - Main preprocessing script for NAND circuit visualization.
Runs layout computation, wire routing, and generates output for the HTML viewer.
"""

import argparse
import json
import os
import sys
import time

from layout_engine import LayoutEngine
from wire_router import WireRouter
from tile_generator import TileGenerator, generate_single_file_data


def preprocess_circuit(
    input_files: list = None,
    nands_file: str = 'nands-optimized-final.txt',
    output_dir: str = 'circuit-data',
    generate_tiles: bool = True,
    generate_embedded: bool = True,
    max_gates: int = None
):
    """
    Preprocess the circuit for visualization.

    Args:
        input_files: List of input file paths (e.g., ['input-bits.txt', 'constants-bits.txt'])
        nands_file: Path to NAND gates file
        output_dir: Directory for output files
        generate_tiles: Whether to generate tile files
        generate_embedded: Whether to generate embedded JSON for single-file HTML
        max_gates: Limit number of gates (for testing)
    """
    if input_files is None:
        input_files = ['input-bits.txt', 'constants-bits.txt']

    start_time = time.time()
    print("=" * 60)
    print("NAND Circuit Preprocessor")
    print("=" * 60)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Phase 1: Load and parse circuit
    print("\n[Phase 1] Loading circuit files...")
    phase_start = time.time()

    engine = LayoutEngine()
    for input_file in input_files:
        engine.load_inputs(input_file)

    # Load NANDs (with optional limit for testing)
    if max_gates:
        print(f"  (Limiting to first {max_gates} gates)")
        with open(nands_file, 'r') as f:
            lines = f.readlines()[:max_gates]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) >= 3:
                label = parts[0]
                input_a = parts[1]
                input_b = parts[2]
                engine.nands[label] = (input_a, input_b)
                engine.node_type[label] = 'nand'
                engine.fanout[input_a].append(label)
                engine.fanout[input_b].append(label)
                engine.fanin[label] = [input_a, input_b]
                if label.startswith('OUTPUT-'):
                    engine.outputs.add(label)
        print(f"  Loaded {len(engine.nands)} NAND gates (limited)")
    else:
        engine.load_nands(nands_file)

    print(f"  Phase 1 completed in {time.time() - phase_start:.2f}s")

    # Phase 2: Compute topological layers
    print("\n[Phase 2] Computing topological layers...")
    phase_start = time.time()

    num_layers = engine.compute_layers()

    print(f"  Phase 2 completed in {time.time() - phase_start:.2f}s")

    # Phase 3: Assign positions
    print("\n[Phase 3] Assigning gate positions...")
    phase_start = time.time()

    engine.assign_positions()

    print(f"  Phase 3 completed in {time.time() - phase_start:.2f}s")

    # Phase 4: Route wires
    print("\n[Phase 4] Routing wires...")
    phase_start = time.time()

    router = WireRouter(engine)
    router.route_all_wires()

    print(f"  Phase 4 completed in {time.time() - phase_start:.2f}s")

    # Phase 5: Generate output
    print("\n[Phase 5] Generating output...")
    phase_start = time.time()

    if generate_tiles:
        print("  Generating tiles...")
        generator = TileGenerator(engine, router)
        generator.generate(output_dir)

    if generate_embedded:
        print("  Generating embedded data...")
        embedded_data = generate_single_file_data(engine, router)
        embedded_path = os.path.join(output_dir, 'circuit-embedded.json')
        with open(embedded_path, 'w') as f:
            json.dump(embedded_data, f)
        print(f"  Embedded data: {os.path.getsize(embedded_path) / 1024 / 1024:.1f} MB")

    print(f"  Phase 5 completed in {time.time() - phase_start:.2f}s")

    # Summary
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print("Preprocessing Complete!")
    print("=" * 60)
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Circuit dimensions: {engine.width} x {engine.height} pixels")
    print(f"  Layers: {num_layers}")
    print(f"  Gates: {len(engine.nands)}")
    print(f"  Wire segments: {len(router.all_segments)}")
    print(f"  Output directory: {output_dir}")

    return embedded_data if generate_embedded else None


def main():
    parser = argparse.ArgumentParser(description='Preprocess NAND circuit for visualization')
    parser.add_argument('--inputs', '-i', action='append', default=None,
                        help='Input file(s) containing bit values (can be specified multiple times)')
    parser.add_argument('--nands', default='nands-optimized-final.txt', help='NAND gates file')
    parser.add_argument('--output', default='circuit-data', help='Output directory')
    parser.add_argument('--no-tiles', action='store_true', help='Skip tile generation')
    parser.add_argument('--no-embedded', action='store_true', help='Skip embedded JSON generation')
    parser.add_argument('--max-gates', type=int, help='Limit number of gates (for testing)')

    args = parser.parse_args()

    # Use provided input files or defaults
    input_files = args.inputs if args.inputs else ['input-bits.txt', 'constants-bits.txt']

    preprocess_circuit(
        input_files=input_files,
        nands_file=args.nands,
        output_dir=args.output,
        generate_tiles=not args.no_tiles,
        generate_embedded=not args.no_embedded,
        max_gates=args.max_gates
    )


if __name__ == '__main__':
    main()
