from circuitlab import qasm_from_circuit, circuit_from_qasm


def test_qasm_roundtrip():
    circuit = [
        {"name": "H", "x": 100, "qubit": 0},
        {"name": "CNOT", "x": 200, "control": 0, "target": 1},
        {"name": "RX", "x": 300, "qubit": 2, "theta": 1.5708, "theta_text": "pi/2"},
        {"name": "CRZ", "x": 400, "control": 0, "target": 2, "theta": 3.1416, "theta_text": "pi"},
        {"name": "MA", "x": 500},
    ]
    qasm = qasm_from_circuit(circuit, num_qubits=3)
    loaded = circuit_from_qasm(qasm, num_qubits=3)

    assert len(loaded) == 7  # H, CNOT, RX, CRZ, measure 0,1,2
    assert loaded[0]["name"] == "H"
    assert loaded[1]["name"] == "CNOT"
    assert loaded[4]["name"] == "M"
    assert loaded[5]["name"] == "M"


def test_parse_export_h_simple():
    circuit = [{"name": "H", "x": 50, "qubit": 1}]
    qasm = qasm_from_circuit(circuit, num_qubits=3)
    assert "h q[1] ;" in qasm
    loaded = circuit_from_qasm(qasm, num_qubits=3)
    assert loaded[0]["name"] == "H"
    assert loaded[0]["qubit"] == 1
