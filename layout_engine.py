"""
Layout Engine for NAND Circuit Visualization
Computes topological layers and assigns gate positions.
"""

from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional
import sys


class LayoutEngine:
    """Computes topological layers and X/Y positions for circuit elements."""

    # Layout constants
    GATE_WIDTH = 40
    GATE_HEIGHT = 50
    GATE_SPACING_X = 60  # Horizontal spacing between gates
    GATE_SPACING_Y = 80  # Vertical spacing between layers (includes routing channel)
    ROUTING_CHANNEL_HEIGHT = 40  # Space for wire routing between layers
    INPUT_ROW_HEIGHT = 30
    OUTPUT_ROW_HEIGHT = 30

    def __init__(self):
        self.inputs: Dict[str, int] = {}  # label -> value (all input values including constants)
        self.constants: Dict[str, int] = {}  # Alias for backwards compatibility
        self.nands: Dict[str, Tuple[str, str]] = {}  # label -> (input_a, input_b)
        self.outputs: Set[str] = set()

        # Computed layout data
        self.node_layer: Dict[str, int] = {}  # label -> layer number
        self.layer_nodes: Dict[int, List[str]] = defaultdict(list)  # layer -> [labels]
        self.node_position: Dict[str, Tuple[int, int]] = {}  # label -> (x, y)
        self.node_type: Dict[str, str] = {}  # label -> 'input'/'constant'/'nand'/'output'

        # Graph structure for wire routing
        self.fanout: Dict[str, List[str]] = defaultdict(list)  # source -> [destinations]
        self.fanin: Dict[str, List[str]] = defaultdict(list)  # dest -> [sources]

    def load_inputs(self, filepath: str):
        """Load input bits from file.

        File format: label,value (where value is 0 or 1)
        Can be called multiple times to load from multiple files.
        """
        count_before = len(self.inputs)
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) >= 2:
                    label = parts[0]
                    value = int(parts[1])
                    self.inputs[label] = value
                    # Determine type based on label prefix
                    if label.startswith('INPUT-'):
                        self.node_type[label] = 'input'
                    else:
                        self.node_type[label] = 'constant'
        count_loaded = len(self.inputs) - count_before
        print(f"Loaded {count_loaded} inputs from {filepath}")
        # Keep constants alias in sync
        self.constants = self.inputs

    def load_constants(self, filepath: str):
        """Load constant bits from file.

        Deprecated: Use load_inputs() instead. This method is kept for backwards compatibility.
        """
        self.load_inputs(filepath)

    def load_nands(self, filepath: str):
        """Load NAND gates from file."""
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) >= 3:
                    label = parts[0]
                    input_a = parts[1]
                    input_b = parts[2]
                    self.nands[label] = (input_a, input_b)
                    self.node_type[label] = 'nand'

                    # Build fanout/fanin graph
                    self.fanout[input_a].append(label)
                    self.fanout[input_b].append(label)
                    self.fanin[label] = [input_a, input_b]

                    # Track outputs
                    if label.startswith('OUTPUT-'):
                        self.outputs.add(label)

        print(f"Loaded {len(self.nands)} NAND gates")
        print(f"Found {len(self.outputs)} outputs")

    def compute_layers(self):
        """Compute topological layers using BFS from inputs."""
        print("Computing topological layers...")

        # Initialize: inputs and constants are layer 0
        for label in self.inputs:
            self.node_layer[label] = 0
            self.layer_nodes[0].append(label)

        for label in self.constants:
            self.node_layer[label] = 0
            self.layer_nodes[0].append(label)

        # Process NAND gates in topological order
        # A gate's layer = max(layer of inputs) + 1
        remaining = set(self.nands.keys())
        max_iterations = len(remaining) + 1
        iteration = 0

        while remaining and iteration < max_iterations:
            iteration += 1
            processed_this_round = []

            for label in remaining:
                input_a, input_b = self.nands[label]

                # Check if both inputs have been placed
                if input_a in self.node_layer and input_b in self.node_layer:
                    layer = max(self.node_layer[input_a], self.node_layer[input_b]) + 1
                    self.node_layer[label] = layer
                    self.layer_nodes[layer].append(label)
                    processed_this_round.append(label)

            for label in processed_this_round:
                remaining.remove(label)

            if not processed_this_round and remaining:
                print(f"Warning: Could not place {len(remaining)} gates - possible cycle or missing inputs")
                # Print some problematic gates
                for i, label in enumerate(list(remaining)[:5]):
                    input_a, input_b = self.nands[label]
                    print(f"  {label}: inputs {input_a} (placed: {input_a in self.node_layer}), {input_b} (placed: {input_b in self.node_layer})")
                break

        num_layers = max(self.layer_nodes.keys()) + 1 if self.layer_nodes else 0
        print(f"Computed {num_layers} layers")

        # Print layer statistics
        layer_sizes = [(layer, len(nodes)) for layer, nodes in sorted(self.layer_nodes.items())]
        max_layer_size = max(size for _, size in layer_sizes) if layer_sizes else 0
        print(f"Max layer size: {max_layer_size} gates")

        return num_layers

    def assign_positions(self):
        """Assign X/Y positions to all nodes."""
        print("Assigning positions...")

        # Sort layers
        sorted_layers = sorted(self.layer_nodes.keys())

        # Separate inputs and constants in layer 0
        inputs_layer0 = [n for n in self.layer_nodes[0] if n in self.inputs]
        constants_layer0 = [n for n in self.layer_nodes[0] if n in self.constants]

        # Sort for consistent ordering
        inputs_layer0.sort()
        constants_layer0.sort()

        # Position inputs at the top
        y = self.INPUT_ROW_HEIGHT
        for i, label in enumerate(inputs_layer0):
            x = i * self.GATE_SPACING_X + self.GATE_WIDTH // 2
            self.node_position[label] = (x, y)

        input_row_width = len(inputs_layer0) * self.GATE_SPACING_X

        # Constants will be positioned inline with their first consumer
        # For now, mark them for later placement
        constant_consumers: Dict[str, str] = {}
        for label in constants_layer0:
            if self.fanout[label]:
                # Find first consumer
                first_consumer = min(self.fanout[label], key=lambda g: self.node_layer.get(g, 999999))
                constant_consumers[label] = first_consumer

        # Process NAND layers
        current_y = self.INPUT_ROW_HEIGHT + self.ROUTING_CHANNEL_HEIGHT + self.GATE_HEIGHT

        # Track which constants we've placed
        placed_constants = set()

        for layer in sorted_layers:
            if layer == 0:
                continue  # Skip input layer, already handled

            nodes = [n for n in self.layer_nodes[layer] if n in self.nands]

            # Sort nodes for better wire locality
            # Group by common prefix to keep related gates together
            nodes = self._sort_layer_nodes(nodes)

            # Position gates in this layer
            for i, label in enumerate(nodes):
                x = i * self.GATE_SPACING_X + self.GATE_WIDTH // 2
                self.node_position[label] = (x, current_y)

            # Place any constants that feed into this layer
            for const_label, consumer in constant_consumers.items():
                if const_label not in placed_constants:
                    consumer_layer = self.node_layer.get(consumer)
                    if consumer_layer == layer and consumer in self.node_position:
                        # Place constant above its consumer
                        cx, cy = self.node_position[consumer]
                        self.node_position[const_label] = (cx - 10, cy - self.GATE_HEIGHT // 2 - 15)
                        placed_constants.add(const_label)

            current_y += self.GATE_HEIGHT + self.ROUTING_CHANNEL_HEIGHT

        # Place any remaining constants
        remaining_constants = [c for c in constants_layer0 if c not in placed_constants]
        for i, label in enumerate(remaining_constants):
            # Place at top near inputs
            x = (len(inputs_layer0) + i) * self.GATE_SPACING_X + self.GATE_WIDTH // 2
            self.node_position[label] = (x, self.INPUT_ROW_HEIGHT)

        # Compute dimensions
        all_x = [pos[0] for pos in self.node_position.values()]
        all_y = [pos[1] for pos in self.node_position.values()]

        self.width = max(all_x) + self.GATE_SPACING_X if all_x else 0
        self.height = max(all_y) + self.GATE_HEIGHT + self.OUTPUT_ROW_HEIGHT if all_y else 0

        print(f"Layout dimensions: {self.width} x {self.height}")
        print(f"Positioned {len(self.node_position)} nodes")

    def _sort_layer_nodes(self, nodes: List[str]) -> List[str]:
        """Sort nodes in a layer for better wire locality."""
        # Group by prefix (e.g., W16-s1-XOR1-B0, W16-s1-XOR1-B1 should be adjacent)
        def get_sort_key(label):
            # Extract prefix (everything before last dash-separated number)
            parts = label.rsplit('-', 2)
            if len(parts) >= 2:
                return (parts[0], label)
            return (label, label)

        return sorted(nodes, key=get_sort_key)

    def get_gate_input_positions(self, label: str) -> List[Tuple[int, int]]:
        """Get the positions of a gate's input pins."""
        if label not in self.node_position:
            return []

        x, y = self.node_position[label]
        # Two inputs at top of gate
        return [(x - 8, y - self.GATE_HEIGHT // 2), (x + 8, y - self.GATE_HEIGHT // 2)]

    def get_gate_output_position(self, label: str) -> Optional[Tuple[int, int]]:
        """Get the position of a gate's output pin."""
        if label not in self.node_position:
            return None

        x, y = self.node_position[label]
        # Output at bottom of gate (below inversion bubble)
        return (x, y + self.GATE_HEIGHT // 2 + 5)

    def get_input_output_position(self, label: str) -> Optional[Tuple[int, int]]:
        """Get the output position for an input/constant node."""
        if label not in self.node_position:
            return None

        x, y = self.node_position[label]
        return (x, y + 10)  # Just below the input marker

    def get_layout_data(self) -> dict:
        """Return layout data for serialization."""
        return {
            'width': self.width,
            'height': self.height,
            'num_layers': max(self.layer_nodes.keys()) + 1 if self.layer_nodes else 0,
            'num_inputs': len(self.inputs),
            'num_constants': len(self.constants),
            'num_nands': len(self.nands),
            'num_outputs': len(self.outputs),
            'gate_width': self.GATE_WIDTH,
            'gate_height': self.GATE_HEIGHT,
            'positions': {label: {'x': x, 'y': y, 'type': self.node_type.get(label, 'unknown'),
                                  'layer': self.node_layer.get(label, -1)}
                         for label, (x, y) in self.node_position.items()},
            'nands': {label: {'a': a, 'b': b} for label, (a, b) in self.nands.items()},
            'fanout': {k: v for k, v in self.fanout.items() if v},
        }


def main():
    """Test the layout engine."""
    engine = LayoutEngine()
    engine.load_inputs('input-bits.txt')
    engine.load_constants('constants-bits.txt')
    engine.load_nands('nands-optimized-final.txt')
    engine.compute_layers()
    engine.assign_positions()

    # Print some stats
    data = engine.get_layout_data()
    print(f"\nLayout Summary:")
    print(f"  Dimensions: {data['width']} x {data['height']}")
    print(f"  Layers: {data['num_layers']}")
    print(f"  Inputs: {data['num_inputs']}")
    print(f"  Constants: {data['num_constants']}")
    print(f"  NAND gates: {data['num_nands']}")
    print(f"  Outputs: {data['num_outputs']}")


if __name__ == '__main__':
    main()
