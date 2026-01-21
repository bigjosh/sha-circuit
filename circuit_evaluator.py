"""
Circuit Evaluator for SHA-256

Reads the three circuit files and evaluates the circuit to produce the hash output.
This verifies that the circuit representation is correct.
"""

import hashlib


def load_input(filename):
    """Load input words from input.txt."""
    nodes = {}
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            label, value = line.split(',')
            nodes[label] = int(value, 16)
    return nodes


def load_constants(filename):
    """Load constants from constants.txt."""
    nodes = {}
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            label, value = line.split(',')
            nodes[label] = int(value, 16)
    return nodes


def load_functions(filename):
    """Load function definitions from functions.txt."""
    functions = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            label = parts[0]
            func = parts[1]
            inputs = parts[2:] if len(parts) > 2 else []
            functions.append((label, func, inputs))
    return functions


def rotr(x, n):
    """Right rotate 32-bit value by n bits."""
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF


def shr(x, n):
    """Right shift 32-bit value by n bits."""
    return x >> n


def evaluate(nodes, func, inputs):
    """Evaluate a function with given inputs."""
    values = [nodes[inp] for inp in inputs]

    if func == "XOR":
        return values[0] ^ values[1]
    elif func == "AND":
        return values[0] & values[1]
    elif func == "OR":
        return values[0] | values[1]
    elif func == "NOT":
        return (~values[0]) & 0xFFFFFFFF
    elif func == "ADD":
        return (values[0] + values[1]) & 0xFFFFFFFF
    elif func == "COPY":
        return values[0]
    elif func.startswith("ROTR"):
        n = int(func[4:])
        return rotr(values[0], n)
    elif func.startswith("SHR"):
        n = int(func[3:])
        return shr(values[0], n)
    else:
        raise ValueError(f"Unknown function: {func}")


def run_circuit(input_file, constants_file, functions_file):
    """Run the circuit and return the output hash."""
    # Load all nodes
    nodes = {}
    nodes.update(load_input(input_file))
    nodes.update(load_constants(constants_file))

    # Load and evaluate functions
    functions = load_functions(functions_file)

    for label, func, inputs in functions:
        result = evaluate(nodes, func, inputs)
        nodes[label] = result

    # Collect output
    output = []
    for i in range(8):
        label = f"OUTPUT-W{i}"
        if label in nodes:
            output.append(nodes[label])

    return output


def format_hash(words):
    """Format 8 words as a hex hash string."""
    return ''.join(f'{w:08x}' for w in words)


def compute_reference_hash(message):
    """Compute SHA-256 using Python's hashlib for reference."""
    return hashlib.sha256(message).hexdigest()


if __name__ == "__main__":
    import sys

    input_file = "input.txt"
    constants_file = "constants.txt"
    functions_file = "functions.txt"

    # Run the circuit
    output = run_circuit(input_file, constants_file, functions_file)
    circuit_hash = format_hash(output)

    print(f"Circuit output: {circuit_hash}")

    # Compare with reference
    # The input message is "josh" based on the generator
    message = b"josh" if len(sys.argv) < 2 else sys.argv[1].encode()
    reference_hash = compute_reference_hash(message)
    print(f"Reference hash: {reference_hash}")

    if circuit_hash == reference_hash:
        print("SUCCESS: Circuit output matches reference!")
    else:
        print("MISMATCH: Circuit output differs from reference")
