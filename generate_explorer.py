#!/usr/bin/env python3
"""
Generate Circuit Explorer HTML
Combines preprocessing with HTML template to create standalone viewer.
"""

import argparse
import json
import os
import sys
import time

from layout_engine import LayoutEngine
from wire_router import WireRouter
from tile_generator import generate_single_file_data


def generate_explorer(
    input_files: list = None,
    nands_file: str = 'nands-optimized-final.txt',
    template_file: str = 'circuit-explorer-template.html',
    output_file: str = 'circuit-explorer.html',
    max_gates: int = None
):
    """Generate the circuit explorer HTML file."""
    if input_files is None:
        input_files = ['input-bits.txt', 'constants-bits.txt']

    start_time = time.time()
    print("=" * 60)
    print("Circuit Explorer Generator")
    print("=" * 60)

    # Phase 1: Load circuit
    print("\n[Phase 1] Loading circuit...")
    engine = LayoutEngine()
    for input_file in input_files:
        engine.load_inputs(input_file)

    if max_gates:
        print(f"  Limiting to {max_gates} gates")
        with open(nands_file, 'r') as f:
            for i, line in enumerate(f):
                if i >= max_gates:
                    break
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
        print(f"  Loaded {len(engine.nands)} gates")
    else:
        engine.load_nands(nands_file)

    # Phase 2: Compute layout
    print("\n[Phase 2] Computing layout...")
    engine.compute_layers()
    engine.assign_positions()

    # Phase 3: Route wires
    print("\n[Phase 3] Routing wires...")
    router = WireRouter(engine)
    router.route_all_wires()

    # Phase 4: Generate embedded data
    print("\n[Phase 4] Generating data...")
    circuit_data = generate_single_file_data(engine, router)

    # Phase 5: Generate HTML
    print("\n[Phase 5] Generating HTML...")
    with open(template_file, 'r', encoding='utf-8') as f:
        template = f.read()

    # Inject circuit data
    circuit_json = json.dumps(circuit_data)
    html = template.replace('%%CIRCUIT_DATA%%', circuit_json)

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    file_size = os.path.getsize(output_file)
    total_time = time.time() - start_time

    print("\n" + "=" * 60)
    print("Generation Complete!")
    print("=" * 60)
    print(f"  Output: {output_file}")
    print(f"  Size: {file_size / 1024 / 1024:.1f} MB")
    print(f"  Time: {total_time:.1f}s")
    print(f"  Gates: {len(engine.nands)}")
    print(f"  Wires: {len(router.all_segments)}")
    print(f"\nOpen {output_file} in a browser to view the circuit.")


def main():
    parser = argparse.ArgumentParser(description='Generate circuit explorer HTML')
    parser.add_argument('--inputs', '-i', action='append', default=None,
                        help='Input file(s) containing bit values (can be specified multiple times)')
    parser.add_argument('--nands', default='nands-optimized-final.txt', help='NAND gates file')
    parser.add_argument('--template', default='circuit-explorer-template.html', help='HTML template')
    parser.add_argument('--output', default='circuit-explorer.html', help='Output HTML file')
    parser.add_argument('--max-gates', type=int, help='Limit gates (for testing)')

    args = parser.parse_args()

    # Use provided input files or defaults
    input_files = args.inputs if args.inputs else ['input-bits.txt', 'constants-bits.txt']

    generate_explorer(
        input_files=input_files,
        nands_file=args.nands,
        template_file=args.template,
        output_file=args.output,
        max_gates=args.max_gates
    )


if __name__ == '__main__':
    main()
