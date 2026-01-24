#!/usr/bin/env python3
"""
Generate an interactive HTML circuit explorer for NAND gate circuits.

Features:
- SVG-based rendering with pan and zoom
- Click wires to highlight them (and their source/destination)
- Proper routing channels between layers (no wires crossing gates)
- Inputs at top, outputs at bottom
"""

import json
from collections import defaultdict
import sys


def load_inputs(input_files):
    """Load input values from one or more input files."""
    inputs = {}
    for input_file in input_files:
        with open(input_file) as f:
            for line in f:
                if line.strip():
                    parts = line.strip().split(',')
                    if len(parts) >= 2:
                        inputs[parts[0]] = int(parts[1])
    return inputs


def load_circuit(nands_file, input_files):
    """Load circuit and inputs."""
    inputs = load_inputs(input_files)

    gates = []
    with open(nands_file) as f:
        for line in f:
            if line.strip():
                parts = line.strip().split(',')
                if len(parts) == 3:
                    gates.append((parts[0], parts[1], parts[2]))

    return gates, inputs


def compute_layout(gates, input_values):
    """Compute gate positions and wire routes."""
    gate_set = {g[0] for g in gates}
    gate_map = {g[0]: (g[1], g[2]) for g in gates}

    # Find inputs and constants from gate references
    inputs = set()
    const_refs = set()
    for _, a, b in gates:
        for inp in [a, b]:
            if inp not in gate_set:
                if inp.startswith('INPUT-'):
                    inputs.add(inp)
                else:
                    const_refs.add(inp)

    # Compute layers (topological depth)
    layer = {}
    for inp in inputs:
        layer[inp] = 0
    for c in const_refs:
        layer[c] = 0

    def get_layer(label):
        if label in layer:
            return layer[label]
        if label not in gate_map:
            layer[label] = 0
            return 0
        a, b = gate_map[label]
        l = max(get_layer(a), get_layer(b)) + 1
        layer[label] = l
        return l

    for label, _, _ in gates:
        get_layer(label)

    # Group gates by layer
    layers = defaultdict(list)
    for label, a, b in gates:
        layers[layer[label]].append((label, a, b))

    inputs = sorted(inputs)
    outputs = sorted([g[0] for g in gates if g[0].startswith('OUTPUT-')])

    return layers, inputs, outputs, const_refs, layer, gate_map, input_values


def generate_html(nands_file, input_files, output_file, max_gates=None):
    """Generate interactive HTML explorer."""
    print("Loading circuit...")
    gates, input_values = load_circuit(nands_file, input_files)

    if max_gates and len(gates) > max_gates:
        print(f"Limiting to {max_gates} gates")
        gates = gates[:max_gates]

    print(f"Processing {len(gates)} gates...")
    layers, inputs, outputs, const_refs, layer_nums, gate_map, input_values = compute_layout(gates, input_values)

    num_layers = max(layers.keys()) + 1 if layers else 1
    max_width = max(len(layers[l]) for l in layers) if layers else 1

    print(f"Layers: {num_layers}, max width: {max_width}")

    # Layout parameters
    GATE_W = 24
    GATE_H = 32
    H_SPACING = 20
    # Wire channel height - scales with circuit complexity
    max_fanout = max(sum(1 for g in gates if g[1] == label or g[2] == label) for label in set(g[0] for g in gates)) if gates else 1
    V_CHANNEL = max(40, min(80, max_fanout * 4))  # Space for horizontal wire routing
    MARGIN = 40
    INPUT_AREA = 50
    OUTPUT_AREA = 40

    cell_w = GATE_W + H_SPACING
    cell_h = GATE_H + V_CHANNEL

    num_cols = max(len(inputs), len(outputs), max_width)
    svg_w = num_cols * cell_w + 2 * MARGIN
    svg_h = INPUT_AREA + num_layers * cell_h + OUTPUT_AREA + 2 * MARGIN

    print(f"SVG size: {svg_w} x {svg_h}")

    # Compute positions
    gate_pos = {}  # label -> (cx, cy)
    input_pos = {}  # label -> (x, y_out)
    output_pos = {}  # label -> (x, y_in)

    # Input positions
    inp_start = MARGIN + (svg_w - 2 * MARGIN - len(inputs) * cell_w) // 2
    for i, inp in enumerate(inputs):
        x = inp_start + i * cell_w + cell_w // 2
        y = MARGIN + INPUT_AREA
        input_pos[inp] = (x, y)

    # Gate positions - gates are placed at the TOP of each cell, channel is BELOW
    for l in sorted(layers.keys()):
        layer_gates = layers[l]
        # Gate center Y: margin + input area + layer * cell_h + half gate height
        base_y = MARGIN + INPUT_AREA + l * cell_h + GATE_H // 2 + 10
        start_x = MARGIN + (svg_w - 2 * MARGIN - len(layer_gates) * cell_w) // 2

        for i, (label, a, b) in enumerate(layer_gates):
            cx = start_x + i * cell_w + cell_w // 2
            cy = base_y
            gate_pos[label] = (cx, cy)

    # Output positions
    out_y = MARGIN + INPUT_AREA + num_layers * cell_h + 10
    out_start = MARGIN + (svg_w - 2 * MARGIN - len(outputs) * cell_w) // 2
    for i, out in enumerate(outputs):
        x = out_start + i * cell_w + cell_w // 2
        output_pos[out] = (x, out_y)

    # Build wire data
    wires = []
    wire_id = 0

    # Track allocation for horizontal wires in each channel
    # Each layer L has a channel below it (between layer L and L+1)
    channel_tracks = defaultdict(int)  # channel_layer -> next track offset

    def get_channel_y(layer_idx, track_offset):
        """Get Y coordinate for a horizontal wire in the channel below layer_idx."""
        # Channel starts after the gate body (gate center + half height + bubble)
        gate_bottom = MARGIN + INPUT_AREA + layer_idx * cell_h + GATE_H + 20
        channel_height = V_CHANNEL - 10
        return gate_bottom + (track_offset % max(1, channel_height // 4)) * 4

    def allocate_track(layer_idx):
        """Allocate a track in the channel below layer_idx."""
        track = channel_tracks[layer_idx]
        channel_tracks[layer_idx] += 1
        return track

    for label, (a, b) in gate_map.items():
        if label not in gate_pos:
            continue

        dest_cx, dest_cy = gate_pos[label]
        # Input pin positions (at top of gate body)
        body_h = GATE_H - 8
        gate_top = dest_cy - body_h // 2
        in_a_x = dest_cx - GATE_W // 4
        in_b_x = dest_cx + GATE_W // 4
        in_y = gate_top - 6  # Top of input stubs

        dest_layer = layer_nums[label]

        for src, dest_x in [(a, in_a_x), (b, in_b_x)]:
            src_layer = layer_nums.get(src, 0)

            if src in gate_pos:
                src_cx, src_cy = gate_pos[src]
                src_x = src_cx
                # Output is below bubble: mid_y + w/2 + bubble_r*2 + 6
                src_body_h = GATE_H - 8
                src_mid_y = src_cy
                src_curve_bottom = src_mid_y + GATE_W // 2
                bubble_r = 3
                src_y = src_curve_bottom + bubble_r * 2 + 7  # Below output stub

                # Route through the channel immediately below the source layer
                # Use the channel just below src_layer for horizontal routing
                track = allocate_track(src_layer)
                channel_y = get_channel_y(src_layer, track)

                # For multi-layer spans, route down through gate gaps
                if dest_layer > src_layer + 1:
                    # Need to route through intermediate layers
                    # Go down to channel, horizontal to align with dest, then down
                    points = [(src_x, src_y), (src_x, channel_y), (dest_x, channel_y)]
                    # Continue down to destination
                    points.append((dest_x, in_y))
                else:
                    # Single layer hop - simple routing
                    points = [
                        (src_x, src_y),
                        (src_x, channel_y),
                        (dest_x, channel_y),
                        (dest_x, in_y)
                    ]

                wires.append({
                    'id': wire_id,
                    'src': src,
                    'dest': label,
                    'points': points
                })

            elif src in input_pos:
                src_x, src_y = input_pos[src]
                # Use channel at layer 0 (just below inputs)
                track = allocate_track(-1)  # Special channel for inputs
                channel_y = MARGIN + INPUT_AREA // 2 + (track % (INPUT_AREA // 5)) * 4

                wires.append({
                    'id': wire_id,
                    'src': src,
                    'dest': label,
                    'points': [
                        (src_x, src_y - INPUT_AREA + 10),
                        (src_x, channel_y),
                        (dest_x, channel_y),
                        (dest_x, in_y)
                    ]
                })

            elif src in input_values:
                # Constant - draw indicator directly above input
                wires.append({
                    'id': wire_id,
                    'src': src,
                    'dest': label,
                    'const_val': input_values[src],
                    'points': [
                        (dest_x, in_y - 8),
                        (dest_x, in_y)
                    ]
                })

            wire_id += 1

    # Output wires
    for out in outputs:
        if out in gate_pos and out in output_pos:
            src_cx, src_cy = gate_pos[out]
            dest_x, dest_y = output_pos[out]
            src_y = src_cy + GATE_H // 2 + 4

            wires.append({
                'id': wire_id,
                'src': out,
                'dest': f'OUT_{out}',
                'points': [
                    (src_cx, src_y),
                    (src_cx, dest_y),
                    (dest_x, dest_y)
                ]
            })
            wire_id += 1

    print(f"Generated {len(wires)} wires")

    # Generate HTML
    html = generate_html_content(svg_w, svg_h, gate_pos, input_pos, output_pos,
                                  wires, input_values, GATE_W, GATE_H, layers)

    with open(output_file, 'w') as f:
        f.write(html)

    print(f"Saved {output_file}")


def generate_html_content(svg_w, svg_h, gate_pos, input_pos, output_pos, wires, input_values, gate_w, gate_h, layers):
    """Generate the HTML content."""

    # Build SVG elements for gates
    gate_elements = []
    for label, (cx, cy) in gate_pos.items():
        # Gate dimensions
        w = gate_w
        h = gate_h - 8  # Body height (excluding stubs)
        top = cy - h // 2
        left = cx - w // 2
        right = cx + w // 2
        mid_y = cy  # Where curve starts
        curve_bottom = mid_y + w // 2  # Bottom of D curve
        bubble_r = 3
        bubble_cy = curve_bottom + bubble_r + 1

        gate_elements.append(f'''
        <g class="gate" data-label="{label}">
            <!-- NAND body: flat top, straight sides, curved bottom -->
            <path d="M {left} {top}
                     L {right} {top}
                     L {right} {mid_y}
                     A {w//2} {w//2} 0 0 1 {left} {mid_y}
                     Z" fill="white" stroke="black" stroke-width="1"/>
            <!-- Inversion bubble at output -->
            <circle cx="{cx}" cy="{bubble_cy}" r="{bubble_r}" fill="white" stroke="black" stroke-width="1"/>
            <!-- Input stubs at top -->
            <line x1="{cx - w//4}" y1="{top - 6}" x2="{cx - w//4}" y2="{top}" stroke="black" stroke-width="1"/>
            <line x1="{cx + w//4}" y1="{top - 6}" x2="{cx + w//4}" y2="{top}" stroke="black" stroke-width="1"/>
            <!-- Output stub below bubble -->
            <line x1="{cx}" y1="{bubble_cy + bubble_r}" x2="{cx}" y2="{bubble_cy + bubble_r + 6}" stroke="black" stroke-width="1"/>
        </g>''')

    # Input ports
    input_elements = []
    for label, (x, y) in input_pos.items():
        input_elements.append(f'''
        <g class="input-port" data-label="{label}">
            <rect x="{x - 4}" y="{y - 40}" width="8" height="8" fill="white" stroke="black" stroke-width="1"/>
            <line x1="{x}" y1="{y - 32}" x2="{x}" y2="{y}" stroke="black" stroke-width="1"/>
        </g>''')

    # Output ports
    output_elements = []
    for label, (x, y) in output_pos.items():
        output_elements.append(f'''
        <g class="output-port" data-label="{label}">
            <line x1="{x}" y1="{y}" x2="{x}" y2="{y + 8}" stroke="black" stroke-width="1"/>
            <rect x="{x - 4}" y="{y + 8}" width="8" height="8" fill="white" stroke="black" stroke-width="1"/>
        </g>''')

    # Wires
    wire_elements = []
    for wire in wires:
        points = wire['points']
        path_d = f"M {points[0][0]} {points[0][1]}"
        for p in points[1:]:
            path_d += f" L {p[0]} {p[1]}"

        wire_class = "wire"
        extra = ""
        if 'const_val' in wire:
            wire_class = "wire const-wire"
            # Add constant indicator
            cx, cy = points[0]
            r = 4
            fill = "black" if wire['const_val'] == 1 else "white"
            extra = f'<circle cx="{cx}" cy="{cy - 5}" r="{r}" fill="{fill}" stroke="black" stroke-width="1" class="const-indicator"/>'

        wire_elements.append(f'''
        <g class="{wire_class}" data-wire-id="{wire['id']}" data-src="{wire['src']}" data-dest="{wire['dest']}">
            <path d="{path_d}" fill="none" stroke="black" stroke-width="1" class="wire-path"/>
            <path d="{path_d}" fill="none" stroke="transparent" stroke-width="8" class="wire-hitbox"/>
            {extra}
        </g>''')

    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>NAND Circuit Explorer</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            overflow: hidden;
        }}
        #container {{
            width: 100vw;
            height: 100vh;
            overflow: hidden;
            cursor: grab;
        }}
        #container.dragging {{ cursor: grabbing; }}
        #svg-container {{
            transform-origin: 0 0;
        }}
        svg {{
            background: white;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }}
        .wire-path {{ pointer-events: none; }}
        .wire-hitbox {{ pointer-events: stroke; cursor: pointer; }}
        .wire.selected .wire-path {{ stroke: #e63946; stroke-width: 2; }}
        .wire:hover .wire-path {{ stroke: #457b9d; stroke-width: 2; }}
        .gate {{ pointer-events: none; }}
        .gate.highlighted path {{ fill: #ffd166 !important; stroke: #e63946 !important; stroke-width: 2; }}
        .gate.highlighted circle {{ fill: #ffd166 !important; stroke: #e63946 !important; }}
        .input-port.highlighted rect {{ fill: #a8dadc !important; stroke: #1d3557 !important; stroke-width: 2; }}
        .output-port.highlighted rect {{ fill: #a8dadc !important; stroke: #1d3557 !important; stroke-width: 2; }}
        #controls {{
            position: fixed;
            top: 10px;
            left: 10px;
            background: rgba(26, 26, 46, 0.95);
            padding: 15px;
            border-radius: 8px;
            z-index: 100;
            min-width: 200px;
        }}
        #controls h3 {{ margin-bottom: 10px; font-size: 14px; }}
        #controls p {{ font-size: 12px; margin: 5px 0; color: #aaa; }}
        #info {{
            position: fixed;
            bottom: 10px;
            left: 10px;
            background: rgba(26, 26, 46, 0.95);
            padding: 15px;
            border-radius: 8px;
            z-index: 100;
            font-size: 12px;
            min-width: 250px;
        }}
        #info .label {{ color: #888; }}
        #info .value {{ color: #4ecdc4; font-family: monospace; }}
        #zoom-controls {{
            position: fixed;
            top: 10px;
            right: 10px;
            background: rgba(26, 26, 46, 0.95);
            padding: 10px;
            border-radius: 8px;
            z-index: 100;
        }}
        #zoom-controls button {{
            width: 36px;
            height: 36px;
            font-size: 18px;
            margin: 2px;
            border: none;
            background: #333;
            color: #fff;
            border-radius: 4px;
            cursor: pointer;
        }}
        #zoom-controls button:hover {{ background: #555; }}
        #zoom-level {{ display: block; text-align: center; margin-top: 5px; font-size: 12px; }}
    </style>
</head>
<body>
    <div id="controls">
        <h3>NAND Circuit Explorer</h3>
        <p>Gates: {len(gate_pos)}</p>
        <p>Wires: {len(wires)}</p>
        <p>Layers: {len(layers)}</p>
        <hr style="margin: 10px 0; border-color: #333;">
        <p>Scroll / +/- : Zoom</p>
        <p>Drag : Pan</p>
        <p>Click wire : Select</p>
        <p>0 : Fit to view</p>
        <p>Esc : Deselect</p>
    </div>
    <div id="zoom-controls">
        <button id="zoom-in">+</button>
        <button id="zoom-out">-</button>
        <button id="zoom-fit">Fit</button>
        <span id="zoom-level">100%</span>
    </div>
    <div id="info">
        <p><span class="label">Selected:</span> <span class="value" id="sel-wire">None</span></p>
        <p><span class="label">Source:</span> <span class="value" id="sel-src">-</span></p>
        <p><span class="label">Destination:</span> <span class="value" id="sel-dest">-</span></p>
    </div>
    <div id="container">
        <div id="svg-container">
            <svg width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">
                <defs>
                    <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                        <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#f0f0f0" stroke-width="0.5"/>
                    </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#grid)"/>
                <g id="wires">
                    {''.join(wire_elements)}
                </g>
                <g id="gates">
                    {''.join(gate_elements)}
                </g>
                <g id="inputs">
                    {''.join(input_elements)}
                </g>
                <g id="outputs">
                    {''.join(output_elements)}
                </g>
            </svg>
        </div>
    </div>
    <script>
        const container = document.getElementById('container');
        const svgContainer = document.getElementById('svg-container');
        const svg = document.querySelector('svg');

        let scale = 1;
        let panX = 0;
        let panY = 0;
        let isDragging = false;
        let startX, startY;

        const SVG_W = {svg_w};
        const SVG_H = {svg_h};

        function updateTransform() {{
            svgContainer.style.transform = `translate(${{panX}}px, ${{panY}}px) scale(${{scale}})`;
            document.getElementById('zoom-level').textContent = Math.round(scale * 100) + '%';
        }}

        function fitToView() {{
            const containerRect = container.getBoundingClientRect();
            const scaleX = containerRect.width / SVG_W;
            const scaleY = containerRect.height / SVG_H;
            scale = Math.min(scaleX, scaleY) * 0.95;
            panX = (containerRect.width - SVG_W * scale) / 2;
            panY = (containerRect.height - SVG_H * scale) / 2;
            updateTransform();
        }}

        // Mouse wheel zoom
        container.addEventListener('wheel', (e) => {{
            e.preventDefault();
            const rect = container.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
            const newScale = Math.max(0.1, Math.min(10, scale * zoomFactor));

            // Zoom toward mouse position
            panX = mouseX - (mouseX - panX) * (newScale / scale);
            panY = mouseY - (mouseY - panY) * (newScale / scale);
            scale = newScale;

            updateTransform();
        }});

        // Pan with mouse drag
        container.addEventListener('mousedown', (e) => {{
            if (e.target.classList.contains('wire-hitbox')) return;
            isDragging = true;
            startX = e.clientX - panX;
            startY = e.clientY - panY;
            container.classList.add('dragging');
        }});

        document.addEventListener('mousemove', (e) => {{
            if (!isDragging) return;
            panX = e.clientX - startX;
            panY = e.clientY - startY;
            updateTransform();
        }});

        document.addEventListener('mouseup', () => {{
            isDragging = false;
            container.classList.remove('dragging');
        }});

        // Zoom buttons
        document.getElementById('zoom-in').addEventListener('click', () => {{
            scale = Math.min(10, scale * 1.2);
            updateTransform();
        }});

        document.getElementById('zoom-out').addEventListener('click', () => {{
            scale = Math.max(0.1, scale / 1.2);
            updateTransform();
        }});

        document.getElementById('zoom-fit').addEventListener('click', fitToView);

        // Wire selection - track selected net (all wires from same source)
        let selectedNet = null;  // The source label of selected net

        function clearHighlights() {{
            document.querySelectorAll('.highlighted').forEach(el => el.classList.remove('highlighted'));
            document.querySelectorAll('.wire.selected').forEach(el => el.classList.remove('selected'));
        }}

        function highlightElement(label) {{
            // Try to find gate, input, or output with this label
            const gate = document.querySelector(`.gate[data-label="${{label}}"]`);
            if (gate) gate.classList.add('highlighted');
            const input = document.querySelector(`.input-port[data-label="${{label}}"]`);
            if (input) input.classList.add('highlighted');
            const output = document.querySelector(`.output-port[data-label="${{label}}"]`);
            if (output) output.classList.add('highlighted');
        }}

        function selectNet(sourceLabel) {{
            // Find all wires from this source
            const wires = document.querySelectorAll(`.wire[data-src="${{sourceLabel}}"]`);
            const destinations = [];

            wires.forEach(wire => {{
                wire.classList.add('selected');
                destinations.push(wire.dataset.dest);
            }});

            // Highlight source
            highlightElement(sourceLabel);

            // Highlight all destinations
            destinations.forEach(dest => highlightElement(dest));

            // Update info panel
            document.getElementById('sel-wire').textContent = sourceLabel;
            document.getElementById('sel-src').textContent = sourceLabel;
            document.getElementById('sel-dest').textContent = destinations.length + ' destination(s)';

            return sourceLabel;
        }}

        document.querySelectorAll('.wire').forEach(wire => {{
            wire.addEventListener('click', (e) => {{
                e.stopPropagation();

                const clickedSource = wire.dataset.src;

                // Clear previous highlights
                clearHighlights();

                // Toggle selection
                if (selectedNet === clickedSource) {{
                    selectedNet = null;
                    document.getElementById('sel-wire').textContent = 'None';
                    document.getElementById('sel-src').textContent = '-';
                    document.getElementById('sel-dest').textContent = '-';
                }} else {{
                    selectedNet = selectNet(clickedSource);
                }}
            }});
        }});

        // Click on background to deselect
        container.addEventListener('click', (e) => {{
            if (e.target === container || e.target === svgContainer || e.target === svg) {{
                if (selectedNet) {{
                    clearHighlights();
                    selectedNet = null;
                    document.getElementById('sel-wire').textContent = 'None';
                    document.getElementById('sel-src').textContent = '-';
                    document.getElementById('sel-dest').textContent = '-';
                }}
            }}
        }});

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {{
            if (e.key === '+' || e.key === '=') {{
                scale = Math.min(10, scale * 1.2);
                updateTransform();
            }} else if (e.key === '-') {{
                scale = Math.max(0.1, scale / 1.2);
                updateTransform();
            }} else if (e.key === '0') {{
                fitToView();
            }} else if (e.key === 'Escape' && selectedNet) {{
                clearHighlights();
                selectedNet = null;
                document.getElementById('sel-wire').textContent = 'None';
                document.getElementById('sel-src').textContent = '-';
                document.getElementById('sel-dest').textContent = '-';
            }}
        }});

        // Initial fit
        fitToView();
    </script>
</body>
</html>'''

    return html


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate interactive NAND circuit explorer")
    parser.add_argument("-n", "--nands", default="nands-optimized-final.txt", help="NAND gates file")
    parser.add_argument("-i", "--inputs", action="append", default=None,
                        help="Input file(s) containing bit values (can be specified multiple times)")
    parser.add_argument("-o", "--output", default="circuit-explorer.html", help="Output HTML file")
    parser.add_argument("-m", "--max-gates", type=int, default=None, help="Maximum number of gates")
    args = parser.parse_args()

    # Use provided input files or default to constants-bits.txt
    input_files = args.inputs if args.inputs else ["constants-bits.txt"]
    generate_html(args.nands, input_files, args.output, args.max_gates)
