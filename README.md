# CircuitLab

CircuitLab is an interactive drag-and-drop quantum circuit playground built with **Python**, **Tkinter**, and **NVIDIA CUDA-Q**. It lets you assemble small circuits visually, simulate them, inspect the final state vector, and run shot-based measurements with a histogram.

## Features

- Drag-and-drop **3-qubit** circuit builder
- Scrollable gate palette and scrollable circuit workspace
- All quantum statevector and measurement calculations are executed with CUDA-Q
- Built-in gates:
  - Single-qubit: `H`, `X`, `Y`, `Z`, `S`, `T`, `RX`, `RY`, `RZ`, `M`
  - Two-qubit: `CNOT`, `CZ`, `SWAP`, `CRX`, `CRY`, `CRZ`
  - Three-qubit: `CCX` (Toffoli)
  - Special: `MA` (Measure All)
- Adjustable **shots** for measurement sampling
- **Per-gate editable** angles for `RX`, `RY`, `RZ`, `CRX`, `CRY`, `CRZ`
- Final **state vector** display when no measurements are present
- **Measurement counts + histogram** when `M` or `MA` gates are used
- Right-click a placed gate to delete it
- **Save/Load circuits** in OpenQASM 2.0 format (compatible with Qiskit)
- **Export circuit screenshots** to PNG images
- Automated tests for core functionality

## Measurement behavior

- If the circuit contains **no measurement gates**, CircuitLab shows the final quantum state vector.
- If the circuit contains one or more **`M`** gates, CircuitLab runs a shot-based simulation and shows the full **3-qubit output distribution**.
- If the circuit contains a **`MA`** (Measure All) gate, it measures all qubits at once, equivalent to placing `M` on every qubit.
- Each click of **Run Simulation** re-initializes the quantum state to `|000>` and reruns the circuit from scratch.
- Within a single shot, once measurement occurs, the state collapses to a classical result for that run.

## Requirements

- Python 3.12+
- A working CUDA-Q installation
- Packages listed in `requirements.txt`

## Installation

```bash
# System dependencies (Linux)
sudo apt-get install ghostscript  # Required for PNG export

# Python setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the app

```bash
python circuitlab.py
```

If you already use the local virtual environment in this repository:

```bash
/mnt/c/Users/joegh/Git/CircuitLab/venv/bin/python /mnt/c/Users/joegh/Git/CircuitLab/circuitlab.py
```

## Running tests

```bash
pytest test_circuitlab.py
```

## How to use

1. Start the app.
2. Drag gates from the **Gate Palette** onto the circuit wires.
3. Use the **Shots** box to control sampling depth for measurement runs.
4. When you drop an `RX`, `RY`, or `RZ` gate, enter that gate's `θ` value in the pop-up prompt.
5. Double-click any placed `RX`, `RY`, or `RZ` gate to change its angle later.
6. Add `M` gates at the **end** of the circuit when you want measurement results.
7. Right-click any placed gate to remove it.

### Notes

- Drop `CCX` on the **target** wire; the other two wires become the controls.
- Drop controlled gates (`CNOT`, `CZ`, `CRX`, `CRY`, `CRZ`) on the **target** wire; you will be prompted to select the control qubit.
- Drop `SWAP` on one wire; you will be prompted to select the partner qubit.
- Drop `MA` anywhere on the circuit to measure all qubits.
- Each placed `RX`, `RY`, `RZ`, `CRX`, `CRY`, or `CRZ` gate stores its own angle instead of sharing one global value.
- Measurement gates (`M` or `MA`) must be placed at the **end** of the circuit.
- The histogram panel is scrollable for easier viewing.
- Use **Save QASM** to export the circuit in OpenQASM 2.0 format.
- Use **Load QASM** to import a circuit from an OpenQASM 2.0 file.
- Use **Export PNG** to save a screenshot of the circuit diagram.

## CUDA-Q execution

All quantum calculations in CircuitLab are delegated to **CUDA-Q**:

- `cudaq.make_kernel()` builds the circuit kernel
- `kernel.h/x/y/z/s/t/rx/ry/rz/crx/cry/crz/cx/cz/swap/...` applies the quantum gates
- `cudaq.get_state()` returns the final state vector when no measurements are present
- `cudaq.sample()` produces the shot-based measurement distributions

Only the UI, angle parsing, and histogram drawing are handled by standard Python / Tkinter code.

## Project structure

```text
CircuitLab/
├── circuitlab.py      # Main Tkinter UI and CUDA-Q simulation logic
├── test_circuitlab.py # Automated tests for QASM import/export
├── requirements.txt   # Python dependencies
├── README.md          # Project documentation
└── .gitignore         # Git/GitHub ignore rules
```

## GitHub readiness

This repository is now suitable for publishing as a small demo project:

- `README.md` explains setup and usage
- `.gitignore` excludes the virtual environment and cache files
- Automated tests are included for core functionality
- The current app is still small enough to stay in a single `circuitlab.py` file

If the project grows further, a good next refactor would be:

- `ui.py` for Tkinter layout
- `simulator.py` for CUDA-Q execution
- `widgets.py` or `palette.py` for reusable UI pieces

## Deploying as a Web-Accessible Tool

CircuitLab is currently a local Tkinter desktop app, but you can expose this functionality online using a lightweight web server and a browser-based front end.

Suggested simple path:
1. Convert circuit state and actions to JSON APIs (`/api/load`, `/api/save`, `/api/run`, `/api/add_gate`, `/api/clear`).
2. Use Flask or FastAPI to host a server process on the same machine or cloud instance.
3. Build a minimal web UI (React/Vue/Vanilla JS) that renders the circuit and sends drag-and-drop updates to the backend.
4. For screenshot export, generate PNG from Tkinter canvas (or directly from HTML5 Canvas for a web UI).
5. Containerize with Docker and deploy to a VM, Kubernetes, or cloud service; expose port through nginx or cloud load balancer.

Example quickstart (Flask):

```python
from flask import Flask, request, jsonify
from circuitlab import CircuitLabGUI

app = Flask(__name__)
backend = CircuitLabGUI()

@app.route('/api/qasm/save', methods=['POST'])
def save_qasm():
    qasm = backend._generate_qasm()  # for demo, keep API simple
    return jsonify({'qasm': qasm})

@app.route('/api/qasm/load', methods=['POST'])
def load_qasm():
    data = request.json
    backend.circuit = backend._parse_qasm(data['qasm'])
    backend._redraw_circuit()
    return jsonify({'status': 'ok'})

# Add run and measurement endpoints similarly

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

### Deployment tips

- Use `gunicorn` + `nginx` for production.
- Mount `/tmp` for screenshot exports and use `Pillow` for image conversions.
- Ensure CUDA-Q is available on the GPU node if using backend simulation.

## Contributions

Contributions are welcome! Please open issues or pull requests for:
- UI improvements (drag-and-drop UX, responsive layout)
- Additional gate support (controlled rotations, multi-qubit instructions)
- Persistence (file-based and cloud storage)
- Automated tests and CI integration
- Web-based frontend + backend deployment recipes

We’re happy to review your PRs and collaborate on new features and bug fixes.
