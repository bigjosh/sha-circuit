#!/usr/bin/env python3
"""
Generate an HTML/JavaScript interactive circuit visualization.

Creates visualization.html that can be opened in any browser.
"""

import argparse
import json
from collections import defaultdict


def load_layer0(input_files=None):
    """Load inputs and constants from input files."""
    layer0 = set()
    layer0.add('CONST-0')
    layer0.add('CONST-1')

    if input_files is None:
        input_files = ['constants-bits.txt']

    for input_file in input_files:
        try:
            with open(input_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split(',')
                        if len(parts) >= 1:
                            layer0.add(parts[0])
        except FileNotFoundError:
            pass

    # If no input files loaded, generate defaults
    if len(layer0) <= 2:
        for i in range(64):
            for b in range(32):
                layer0.add(f'K-{i}-B{b}')
        for i in range(8):
            for b in range(32):
                layer0.add(f'H-INIT-{i}-B{b}')
        for w in range(16):
            for b in range(32):
                layer0.add(f'INPUT-W{w}-B{b}')

    return layer0


def load_circuit(circuit_file):
    """Load circuit and compute layers."""
    gates = []
    dependencies = {}
    dependents = defaultdict(list)

    with open(circuit_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split(',')
                if len(parts) == 3:
                    label, a, b = parts
                    gates.append((label, a, b))
                    dependencies[label] = [a, b]
                    dependents[a].append(label)
                    dependents[b].append(label)

    return gates, dependencies, dependents


def compute_layers(gates, layer0):
    """Compute layer for each gate."""
    layers = {label: 0 for label in layer0}
    layer_gates = defaultdict(list)

    for label, a, b in gates:
        layer = max(layers.get(a, 0), layers.get(b, 0)) + 1
        layers[label] = layer
        layer_gates[layer].append(label)

    return layers, layer_gates


def generate_html(circuit_file, layers, layer_gates, dependencies, dependents, layer0, output_file):
    """Generate HTML visualization."""

    max_layer = max(layers.values())
    max_width = max(len(layer0), max(len(gates) for gates in layer_gates.values()))

    # Prepare data for JavaScript
    gate_data = []

    # Add layer 0 explicitly (inputs and constants)
    layer0_sorted = sorted(layer0)
    for x_idx, label in enumerate(layer0_sorted):
        gate_info = {
            'label': label,
            'layer': 0,
            'x': x_idx,
            'type': (
                'input' if label.startswith('INPUT-') else
                'const'
            ),
            'deps': [],
            'users': dependents.get(label, [])
        }
        gate_data.append(gate_info)

    # Add other layers (NAND gates)
    for layer in range(1, max_layer + 1):
        gates = sorted(layer_gates.get(layer, []))
        for x_idx, label in enumerate(gates):
            gate_info = {
                'label': label,
                'layer': layer,
                'x': x_idx,
                'type': (
                    'output' if label.startswith('OUTPUT-') else
                    'gate'
                ),
                'deps': dependencies.get(label, []),
                'users': dependents.get(label, [])
            }
            gate_data.append(gate_info)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Circuit Visualization - {circuit_file}</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background: #181818;
            color: #fff;
            font-family: monospace;
            overflow: hidden;
        }}
        #info {{
            position: fixed;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.8);
            padding: 10px;
            border-radius: 5px;
            z-index: 100;
        }}
        #canvas {{
            border: 1px solid #444;
            cursor: crosshair;
        }}
        #controls {{
            position: fixed;
            bottom: 10px;
            left: 10px;
            background: rgba(0,0,0,0.8);
            padding: 10px;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div id="info">
        <div>Circuit: {circuit_file}</div>
        <div>Gates: {len(gate_data):,}</div>
        <div>Layers: {max_layer}</div>
        <div>Max width: {max_width}</div>
        <div id="selected-info" style="margin-top: 10px; color: yellow;"></div>
        <div id="hover-info" style="margin-top: 10px;"></div>
    </div>

    <div id="controls">
        <div>Mouse: Hover to highlight | Click input to trace | Wheel: Zoom | Drag: Pan</div>
        <div>R: Reset view | +/-: Zoom | <button id="findInputs">Find Inputs</button></div>
    </div>

    <canvas id="canvas"></canvas>

    <script>
        const gates = {json.dumps(gate_data)};

        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        const hoverInfo = document.getElementById('hover-info');
        const selectedInfo = document.getElementById('selected-info');

        // State
        let zoom = 1;
        let offsetX = 10;
        let offsetY = 50;  // Start with layer 0 visible with margin
        let pixelSize = 2;
        let hoveredGate = null;
        let isDragging = false;
        let lastX = 0;
        let lastY = 0;
        let selectedInput = null;
        let highlightedGates = new Set();

        // Gate lookup
        const gateMap = {{}};
        gates.forEach(g => gateMap[g.label] = g);

        // Colors
        const COLORS = {{
            input: 'rgb(0, 255, 0)',
            const: 'rgb(255, 255, 0)',
            output: 'rgb(255, 0, 0)',
            gate: 'rgb(0, 100, 255)',
            hover: 'rgb(255, 255, 0)',
            bg: 'rgb(20, 20, 20)'
        }};

        function resize() {{
            canvas.width = window.innerWidth - 40;
            canvas.height = window.innerHeight - 80;
            draw();
        }}

        function worldToScreen(x, y) {{
            return [
                (x * pixelSize * zoom) + offsetX,
                (y * pixelSize * zoom) + offsetY
            ];
        }}

        function screenToWorld(sx, sy) {{
            return [
                (sx - offsetX) / (pixelSize * zoom),
                (sy - offsetY) / (pixelSize * zoom)
            ];
        }}

        function findGateAt(sx, sy) {{
            const [wx, wy] = screenToWorld(sx, sy);
            for (const gate of gates) {{
                const gx = gate.x;
                const gy = gate.layer;
                if (gx <= wx && wx < gx + 1 && gy <= wy && wy < gy + 1) {{
                    return gate;
                }}
            }}
            return null;
        }}

        function getAllDependencies(label, visited = new Set()) {{
            if (visited.has(label)) return visited;
            visited.add(label);

            const gate = gateMap[label];
            if (gate && gate.deps) {{
                gate.deps.forEach(dep => {{
                    if (!visited.has(dep)) {{
                        getAllDependencies(dep, visited);
                    }}
                }});
            }}
            return visited;
        }}

        function getAllDependents(label, visited = new Set()) {{
            if (visited.has(label)) return visited;
            visited.add(label);

            const gate = gateMap[label];
            if (gate && gate.users) {{
                gate.users.forEach(user => {{
                    if (!visited.has(user)) {{
                        getAllDependents(user, visited);
                    }}
                }});
            }}
            return visited;
        }}

        function draw() {{
            ctx.fillStyle = COLORS.bg;
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Draw gates
            const cellSize = Math.max(1, Math.floor(pixelSize * zoom));
            const drawSize = Math.max(1, cellSize - 1);  // Leave 1px margin
            gates.forEach(gate => {{
                const [sx, sy] = worldToScreen(gate.x, gate.layer);

                // Only draw if on screen
                if (sx >= -10 && sx < canvas.width + 10 && sy >= -10 && sy < canvas.height + 10) {{
                    // Use yellow if this gate is highlighted, otherwise normal color
                    ctx.fillStyle = highlightedGates.has(gate.label) ? COLORS.hover : COLORS[gate.type];
                    ctx.fillRect(Math.floor(sx), Math.floor(sy), drawSize, drawSize);
                }}
            }});

            // Draw hover highlights
            if (hoveredGate) {{
                const [hsx, hsy] = worldToScreen(hoveredGate.x, hoveredGate.layer);
                const hcx = hsx + drawSize / 2;  // Center X
                const hcy = hsy + drawSize / 2;  // Center Y

                // Draw dependency lines (direct inputs only)
                ctx.strokeStyle = COLORS.hover;
                ctx.lineWidth = 1;

                // Draw lines to direct dependencies (inputs)
                if (hoveredGate.deps) {{
                    hoveredGate.deps.forEach(depLabel => {{
                        const dep = gateMap[depLabel];
                        if (dep) {{
                            const [dsx, dsy] = worldToScreen(dep.x, dep.layer);
                            const dcx = dsx + drawSize / 2;
                            const dcy = dsy + drawSize / 2;
                            ctx.beginPath();
                            ctx.moveTo(hcx, hcy);
                            ctx.lineTo(dcx, dcy);
                            ctx.stroke();
                        }}
                    }});
                }}

                // Draw lines to direct dependents (gates that use this)
                if (hoveredGate.users) {{
                    hoveredGate.users.forEach(userLabel => {{
                        const user = gateMap[userLabel];
                        if (user) {{
                            const [usx, usy] = worldToScreen(user.x, user.layer);
                            const ucx = usx + drawSize / 2;
                            const ucy = usy + drawSize / 2;
                            ctx.beginPath();
                            ctx.moveTo(hcx, hcy);
                            ctx.lineTo(ucx, ucy);
                            ctx.stroke();
                        }}
                    }});
                }}

                // Highlight gate
                ctx.strokeStyle = COLORS.hover;
                ctx.strokeRect(hsx - 1, hsy - 1, drawSize + 2, drawSize + 2);
            }}
        }}

        // Event handlers
        canvas.addEventListener('mousemove', (e) => {{
            if (isDragging) {{
                offsetX += e.clientX - lastX;
                offsetY += e.clientY - lastY;
                lastX = e.clientX;
                lastY = e.clientY;
                draw();
                return;
            }}

            const rect = canvas.getBoundingClientRect();
            const gate = findGateAt(e.clientX - rect.left, e.clientY - rect.top);

            if (gate !== hoveredGate) {{
                hoveredGate = gate;
                if (gate) {{
                    const numDeps = gate.deps ? gate.deps.length : 0;
                    const numUsers = gate.users ? gate.users.length : 0;

                    let inputsHtml = '';
                    if (gate.deps && gate.deps.length > 0) {{
                        inputsHtml = '<div>Inputs:</div>';
                        gate.deps.forEach((dep, idx) => {{
                            inputsHtml += `<div>&nbsp;&nbsp;[${{idx}}] ${{dep}}</div>`;
                        }});
                    }}

                    hoverInfo.innerHTML = `
                        <div><b>${{gate.label}}</b></div>
                        <div>Layer: ${{gate.layer}}</div>
                        <div>Direct outputs: ${{numUsers}}</div>
                        ${{inputsHtml}}
                    `;
                }} else {{
                    hoverInfo.innerHTML = '';
                }}
                draw();
            }}
        }});

        canvas.addEventListener('wheel', (e) => {{
            e.preventDefault();
            const oldZoom = zoom;
            zoom *= e.deltaY < 0 ? 1.1 : 0.9;
            zoom = Math.max(0.1, Math.min(10, zoom));

            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            offsetX = mx - (mx - offsetX) * (zoom / oldZoom);
            offsetY = my - (my - offsetY) * (zoom / oldZoom);
            draw();
        }});

        canvas.addEventListener('mousedown', (e) => {{
            isDragging = true;
            lastX = e.clientX;
            lastY = e.clientY;
        }});

        canvas.addEventListener('mouseup', () => {{
            isDragging = false;
        }});

        canvas.addEventListener('mouseleave', () => {{
            isDragging = false;
            hoveredGate = null;
            hoverInfo.innerHTML = '';
            draw();
        }});

        canvas.addEventListener('click', (e) => {{
            const rect = canvas.getBoundingClientRect();
            const gate = findGateAt(e.clientX - rect.left, e.clientY - rect.top);

            if (gate && gate.type === 'input') {{
                // Clear previous highlights
                highlightedGates.clear();
                selectedInput = gate.label;

                // Get all recursive dependents
                const dependents = getAllDependents(gate.label);

                // Highlight all dependents
                dependents.forEach(dep => highlightedGates.add(dep));

                // Update info display
                selectedInfo.innerHTML = `
                    <div><b>Selected: ${{gate.label}}</b></div>
                    <div>Dependent gates: ${{dependents.size - 1}}</div>
                `;

                console.log(`Selected input: ${{gate.label}}`);
                console.log(`Highlighted ${{dependents.size}} dependent gates`);

                draw();
            }}
        }});

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'r' || e.key === 'R') {{
                zoom = 1;
                offsetX = 0;
                offsetY = 0;
                draw();
            }} else if (e.key === '+' || e.key === '=') {{
                zoom *= 1.2;
                draw();
            }} else if (e.key === '-' || e.key === '_') {{
                zoom /= 1.2;
                draw();
            }}
        }});

        document.getElementById('findInputs').addEventListener('click', () => {{
            // Find first input gate
            const firstInput = gates.find(g => g.type === 'input');
            if (firstInput) {{
                // Center view on the input area
                zoom = 2;  // Zoom in a bit
                const [sx, sy] = worldToScreen(firstInput.x, firstInput.layer);
                offsetX = canvas.width / 2 - (firstInput.x * pixelSize * zoom);
                offsetY = 50;  // Keep layer 0 near top
                draw();
                console.log(`Found inputs starting at x=${{firstInput.x}}, layer=${{firstInput.layer}}`);
            }}
        }});

        window.addEventListener('resize', resize);
        resize();
    </script>
</body>
</html>"""

    with open(output_file, 'w') as f:
        f.write(html)


def main():
    parser = argparse.ArgumentParser(description="Generate HTML circuit visualization")
    parser.add_argument("--nands", "-n", default="ga-nands.txt",
                        help="NAND circuit file")
    parser.add_argument("--inputs", "-i", action="append", default=None,
                        help="Input file(s) containing bit values (can be specified multiple times)")
    parser.add_argument("--output", "-o", default="visualization.html",
                        help="Output HTML file")
    args = parser.parse_args()

    print(f"Loading circuit from {args.nands}...")
    # Use provided input files or default to constants-bits.txt
    input_files = args.inputs if args.inputs else ["constants-bits.txt"]
    layer0 = load_layer0(input_files)
    gates, dependencies, dependents = load_circuit(args.nands)
    print(f"  Loaded {len(gates):,} gates")

    print("Computing layers...")
    layers, layer_gates = compute_layers(gates, layer0)
    max_layer = max(layers.values())
    print(f"  Max layer: {max_layer}")

    print(f"\nGenerating {args.output}...")
    generate_html(args.nands, layers, layer_gates, dependencies, dependents, layer0, args.output)

    print(f"\nDone! Open {args.output} in your browser.")

    return 0


if __name__ == "__main__":
    exit(main())
