#!/usr/bin/env python3
"""
Interactive circuit visualization tool.

Displays the circuit as layers of pixels:
- Layer 0 (inputs/constants) at top
- Subsequent layers below
- Each gate = 1 pixel with 1px margins
- Colors: green=inputs, yellow=constants, red=outputs, blue=gates

Mouse hover shows dependencies with yellow highlight lines.

Usage:
    python visualize-circuit.py
    python visualize-circuit.py -n ga-nands.txt

Controls:
    Mouse hover: Show dependencies
    Mouse wheel: Zoom in/out
    Arrow keys: Pan view
    R: Reset view
    Q/ESC: Quit

Requirements:
    pip install pygame
"""

import argparse
import pygame
import sys
from collections import defaultdict


class CircuitVisualizer:
    def __init__(self, circuit_file='ga-nands.txt', constants_file='constants-bits.txt'):
        self.circuit_file = circuit_file
        self.constants_file = constants_file

        # Circuit data
        self.gates = []
        self.layer0 = set()
        self.layers = {}  # label -> layer number
        self.layer_gates = defaultdict(list)  # layer -> [(label, x_pos)]
        self.dependencies = {}  # label -> [input_a, input_b]
        self.dependents = defaultdict(list)  # label -> [labels that use this]
        self.gate_positions = {}  # label -> (x, y) screen position

        # Display settings
        self.pixel_size = 2  # pixels per gate (with margin)
        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # Colors
        self.COLOR_INPUT = (0, 255, 0)      # Green
        self.COLOR_CONST = (255, 255, 0)    # Yellow
        self.COLOR_OUTPUT = (255, 0, 0)     # Red
        self.COLOR_GATE = (0, 100, 255)     # Blue
        self.COLOR_BG = (20, 20, 20)        # Dark gray
        self.COLOR_HOVER = (255, 255, 0)    # Yellow for dependency lines

        # State
        self.hovered_gate = None
        self.screen = None
        self.clock = None

    def load_layer0(self):
        """Load inputs and constants (layer 0)."""
        layer0 = set()

        # Constants
        layer0.add('CONST-0')
        layer0.add('CONST-1')

        try:
            with open(self.constants_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split(',')
                        if len(parts) >= 1:
                            layer0.add(parts[0])
        except FileNotFoundError:
            # Generate expected constants
            for i in range(64):
                for b in range(32):
                    layer0.add(f'K-{i}-B{b}')
            for i in range(8):
                for b in range(32):
                    layer0.add(f'H-INIT-{i}-B{b}')

        # Inputs
        for w in range(16):
            for b in range(32):
                layer0.add(f'INPUT-W{w}-B{b}')

        self.layer0 = layer0

        # Assign layer 0
        for label in layer0:
            self.layers[label] = 0

    def load_circuit(self):
        """Load circuit and compute layers."""
        print(f"Loading circuit from {self.circuit_file}...")

        with open(self.circuit_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(',')
                    if len(parts) == 3:
                        label, a, b = parts
                        self.gates.append((label, a, b))
                        self.dependencies[label] = [a, b]
                        self.dependents[a].append(label)
                        self.dependents[b].append(label)

        print(f"  Loaded {len(self.gates):,} gates")

        # Compute layers
        print("Computing layers...")
        for label, a, b in self.gates:
            layer_a = self.layers.get(a, 0)
            layer_b = self.layers.get(b, 0)
            layer = max(layer_a, layer_b) + 1
            self.layers[label] = layer
            self.layer_gates[layer].append(label)

        self.max_layer = max(self.layers.values())
        print(f"  Max layer: {self.max_layer}")

        # Calculate max width
        self.max_width = max(len(gates) for gates in self.layer_gates.values())
        print(f"  Max width: {self.max_width} gates")

    def get_color(self, label):
        """Get color for a gate."""
        if label.startswith('INPUT-'):
            return self.COLOR_INPUT
        elif label.startswith('CONST-') or label.startswith('K-') or label.startswith('H-INIT-'):
            return self.COLOR_CONST
        elif label.startswith('OUTPUT-'):
            return self.COLOR_OUTPUT
        else:
            return self.COLOR_GATE

    def compute_layout(self):
        """Compute screen positions for all gates."""
        print("Computing layout...")

        # Position layer 0
        x_pos = 0
        for label in sorted(self.layer0):
            y = 0
            x = x_pos * self.pixel_size
            self.gate_positions[label] = (x, y)
            x_pos += 1

        # Position other layers
        for layer in range(1, self.max_layer + 1):
            gates = self.layer_gates[layer]
            y = layer * self.pixel_size

            for x_idx, label in enumerate(sorted(gates)):
                x = x_idx * self.pixel_size
                self.gate_positions[label] = (x, y)

        print(f"  Positioned {len(self.gate_positions):,} gates")

    def init_display(self):
        """Initialize pygame display."""
        pygame.init()

        # Calculate initial window size (fit to max width, limit height)
        width = min(1920, (self.max_width + 10) * self.pixel_size)
        height = min(1080, (self.max_layer + 10) * self.pixel_size)

        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption(f"Circuit Visualizer - {self.circuit_file}")
        self.clock = pygame.time.Clock()

        print(f"Display initialized: {width}x{height}")

    def world_to_screen(self, x, y):
        """Convert world coordinates to screen coordinates."""
        sx = int((x * self.zoom) + self.offset_x)
        sy = int((y * self.zoom) + self.offset_y)
        return sx, sy

    def screen_to_world(self, sx, sy):
        """Convert screen coordinates to world coordinates."""
        wx = int((sx - self.offset_x) / self.zoom)
        wy = int((sy - self.offset_y) / self.zoom)
        return wx, wy

    def find_gate_at(self, screen_x, screen_y):
        """Find gate at screen position."""
        wx, wy = self.screen_to_world(screen_x, screen_y)

        # Check each gate
        for label, (gx, gy) in self.gate_positions.items():
            # Check if mouse is within gate pixel bounds
            if gx <= wx < gx + self.pixel_size and gy <= wy < gy + self.pixel_size:
                return label

        return None

    def get_all_dependencies(self, label, visited=None):
        """Recursively get all upstream dependencies."""
        if visited is None:
            visited = set()

        if label in visited or label not in self.dependencies:
            return visited

        visited.add(label)

        for dep in self.dependencies.get(label, []):
            if dep not in visited:
                self.get_all_dependencies(dep, visited)

        return visited

    def get_all_dependents(self, label, visited=None):
        """Recursively get all downstream dependents."""
        if visited is None:
            visited = set()

        if label in visited:
            return visited

        visited.add(label)

        for dep in self.dependents.get(label, []):
            if dep not in visited:
                self.get_all_dependents(dep, visited)

        return visited

    def draw(self):
        """Draw the circuit."""
        self.screen.fill(self.COLOR_BG)

        # Draw all gates
        for label, (x, y) in self.gate_positions.items():
            sx, sy = self.world_to_screen(x, y)

            # Only draw if on screen
            screen_w, screen_h = self.screen.get_size()
            if -10 <= sx < screen_w + 10 and -10 <= sy < screen_h + 10:
                color = self.get_color(label)
                size = max(1, int(self.zoom))
                pygame.draw.rect(self.screen, color, (sx, sy, size, size))

        # Draw hover highlights
        if self.hovered_gate:
            # Get dependencies and dependents
            deps = self.get_all_dependencies(self.hovered_gate)
            dependents = self.get_all_dependents(self.hovered_gate)

            # Draw lines to dependencies (upstream - above)
            hx, hy = self.gate_positions[self.hovered_gate]
            h_sx, h_sy = self.world_to_screen(hx, hy)

            for dep_label in deps:
                if dep_label != self.hovered_gate and dep_label in self.gate_positions:
                    dx, dy = self.gate_positions[dep_label]
                    d_sx, d_sy = self.world_to_screen(dx, dy)
                    pygame.draw.line(self.screen, self.COLOR_HOVER, (h_sx, h_sy), (d_sx, d_sy), 1)

            # Draw lines to dependents (downstream - below)
            for dep_label in dependents:
                if dep_label != self.hovered_gate and dep_label in self.gate_positions:
                    dx, dy = self.gate_positions[dep_label]
                    d_sx, d_sy = self.world_to_screen(dx, dy)
                    pygame.draw.line(self.screen, self.COLOR_HOVER, (h_sx, h_sy), (d_sx, d_sy), 1)

            # Highlight the hovered gate
            pygame.draw.rect(self.screen, self.COLOR_HOVER, (h_sx - 1, h_sy - 1,
                                                             int(self.zoom) + 2, int(self.zoom) + 2), 1)

        pygame.display.flip()

    def print_gate_info(self, label):
        """Print information about a gate."""
        layer = self.layers.get(label, -1)
        deps = self.get_all_dependencies(label)
        dependents = self.get_all_dependents(label)

        print(f"\n{'='*60}")
        print(f"Gate: {label}")
        print(f"Layer: {layer}")
        print(f"Recursive dependencies: {len(deps) - 1}")  # -1 to exclude self
        print(f"Recursive dependents: {len(dependents) - 1}")

        if label in self.dependencies:
            a, b = self.dependencies[label]
            print(f"Inputs: {a}, {b}")

        print(f"{'='*60}")

    def run(self):
        """Main event loop."""
        print("\nControls:")
        print("  Mouse hover: Show dependencies")
        print("  Mouse wheel: Zoom in/out")
        print("  Arrow keys: Pan view")
        print("  R: Reset view")
        print("  Q/ESC: Quit")
        print()

        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        running = False
                    elif event.key == pygame.K_r:
                        # Reset view
                        self.zoom = 1.0
                        self.offset_x = 0
                        self.offset_y = 0
                    elif event.key == pygame.K_LEFT:
                        self.offset_x += 50
                    elif event.key == pygame.K_RIGHT:
                        self.offset_x -= 50
                    elif event.key == pygame.K_UP:
                        self.offset_y += 50
                    elif event.key == pygame.K_DOWN:
                        self.offset_y -= 50

                elif event.type == pygame.MOUSEWHEEL:
                    # Zoom
                    old_zoom = self.zoom
                    if event.y > 0:
                        self.zoom *= 1.1
                    else:
                        self.zoom /= 1.1
                    self.zoom = max(0.1, min(10.0, self.zoom))

                    # Adjust offset to zoom toward mouse position
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    self.offset_x = mouse_x - (mouse_x - self.offset_x) * (self.zoom / old_zoom)
                    self.offset_y = mouse_y - (mouse_y - self.offset_y) * (self.zoom / old_zoom)

                elif event.type == pygame.MOUSEMOTION:
                    # Check for hover
                    mx, my = event.pos
                    gate = self.find_gate_at(mx, my)

                    if gate != self.hovered_gate:
                        self.hovered_gate = gate
                        if gate:
                            self.print_gate_info(gate)

                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

            self.draw()
            self.clock.tick(60)  # 60 FPS

        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Interactive circuit visualizer")
    parser.add_argument("--nands", "-n", default="ga-nands.txt",
                        help="NAND circuit file")
    parser.add_argument("--constants", "-c", default="constants-bits.txt",
                        help="Constants file")
    args = parser.parse_args()

    viz = CircuitVisualizer(args.nands, args.constants)
    viz.load_layer0()
    viz.load_circuit()
    viz.compute_layout()
    viz.init_display()
    viz.run()

    return 0


if __name__ == "__main__":
    exit(main())
