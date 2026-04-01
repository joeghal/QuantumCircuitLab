
import math
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import cudaq

# Using both tkinter and ttk is standard. 'tk' is for core widgets and geometry,
# while 'ttk' provides themed widgets for a modern look and feel.

class CircuitLabGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CircuitLab")
        self.geometry("980x760")
        self.configure(bg="#f0f0f0")

        self.num_qubits = 3
        self.qubit_start_y = 50
        self.qubit_spacing = 100

        # Main container frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left frame for gate palette
        self.palette_frame = ttk.LabelFrame(main_frame, text="Gate Palette", padding="10")
        self.palette_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self._create_palette()


        # Right frame for circuit and results
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Circuit frame
        circuit_frame = ttk.LabelFrame(right_frame, text="Quantum Circuit", padding="10")
        circuit_frame.pack(fill=tk.BOTH, expand=True)

        # Button Frame
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(pady=5, fill=tk.X)

        self.shots_var = tk.StringVar(value="1024")
        self.angle_prompt_default = "pi/4"

        run_button = ttk.Button(button_frame, text="Run Simulation", command=self._run_simulation)
        run_button.pack(side=tk.LEFT, padx=5)

        save_qasm_button = ttk.Button(button_frame, text="Save QASM", command=self._save_to_qasm)
        save_qasm_button.pack(side=tk.LEFT, padx=5)

        load_qasm_button = ttk.Button(button_frame, text="Load QASM", command=self._load_from_qasm)
        load_qasm_button.pack(side=tk.LEFT, padx=5)

        export_png_button = ttk.Button(button_frame, text="Export PNG", command=self._export_screenshot)
        export_png_button.pack(side=tk.LEFT, padx=5)

        clear_button = ttk.Button(button_frame, text="Clear Circuit", command=self._clear_circuit)
        clear_button.pack(side=tk.LEFT, padx=5)

        shots_label = ttk.Label(button_frame, text="Shots:")
        shots_label.pack(side=tk.LEFT, padx=(20, 4))

        shots_entry = ttk.Entry(button_frame, textvariable=self.shots_var, width=8)
        shots_entry.pack(side=tk.LEFT)

        helper_label = ttk.Label(
            right_frame,
            text="Tip: right-click a placed gate to delete it. Double-click an `RX`, `RY`, or `RZ` gate to edit its angle. Drop `CCX` on the target wire; the other two wires become controls. For controlled gates (CNOT, CZ, CRX, CRY, CRZ), drop on target and select control. For SWAP, drop on one wire and select partner. Each Run Simulation click re-initializes |000> and reruns the circuit from scratch.",
            foreground="#555555",
            wraplength=680,
            justify=tk.LEFT,
        )
        helper_label.pack(fill=tk.X, padx=5)

        # Results frame
        results_frame = ttk.LabelFrame(right_frame, text="Simulation Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))


        circuit_canvas_frame = ttk.Frame(circuit_frame)
        circuit_canvas_frame.pack(fill=tk.BOTH, expand=True)
        circuit_canvas_frame.columnconfigure(0, weight=1)
        circuit_canvas_frame.rowconfigure(0, weight=1)

        self.circuit_canvas = tk.Canvas(
            circuit_canvas_frame,
            bg="white",
            highlightthickness=1,
            highlightbackground="#d0d0d0",
        )
        circuit_y_scrollbar = ttk.Scrollbar(circuit_canvas_frame, orient=tk.VERTICAL, command=self.circuit_canvas.yview)
        circuit_x_scrollbar = ttk.Scrollbar(circuit_canvas_frame, orient=tk.HORIZONTAL, command=self.circuit_canvas.xview)

        self.circuit_canvas.configure(
            yscrollcommand=circuit_y_scrollbar.set,
            xscrollcommand=circuit_x_scrollbar.set,
        )
        self.circuit_canvas.grid(row=0, column=0, sticky="nsew")
        circuit_y_scrollbar.grid(row=0, column=1, sticky="ns")
        circuit_x_scrollbar.grid(row=1, column=0, sticky="ew")

        self.circuit_canvas.bind("<Button-3>", self._delete_gate_at_position)
        self.circuit_canvas.bind("<Double-Button-1>", self._edit_rotation_gate_at_position)
        self.circuit_canvas.bind("<MouseWheel>", self._on_circuit_mousewheel)
        self.circuit_canvas.bind("<Shift-MouseWheel>", self._on_circuit_mousewheel)
        self.circuit_canvas.bind("<Button-4>", self._on_circuit_mousewheel)
        self.circuit_canvas.bind("<Button-5>", self._on_circuit_mousewheel)

        self.results_label = ttk.Label(
            results_frame,
            text="Final state vector or full 3-qubit measurement distribution will appear here",
            font=("Courier", 9),
            justify=tk.LEFT,
        )
        self.results_label.pack(anchor="w", fill=tk.X)

        histogram_frame = ttk.Frame(results_frame)
        histogram_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        histogram_frame.columnconfigure(0, weight=1)
        histogram_frame.rowconfigure(0, weight=1)

        self.histogram_canvas = tk.Canvas(
            histogram_frame,
            bg="white",
            height=160,
            highlightthickness=1,
            highlightbackground="#d0d0d0",
        )
        histogram_y_scrollbar = ttk.Scrollbar(histogram_frame, orient=tk.VERTICAL, command=self.histogram_canvas.yview)
        histogram_x_scrollbar = ttk.Scrollbar(histogram_frame, orient=tk.HORIZONTAL, command=self.histogram_canvas.xview)

        self.histogram_canvas.configure(
            yscrollcommand=histogram_y_scrollbar.set,
            xscrollcommand=histogram_x_scrollbar.set,
        )
        self.histogram_canvas.grid(row=0, column=0, sticky="nsew")
        histogram_y_scrollbar.grid(row=0, column=1, sticky="ns")
        histogram_x_scrollbar.grid(row=1, column=0, sticky="ew")

        self.histogram_canvas.bind("<MouseWheel>", self._on_histogram_mousewheel)
        self.histogram_canvas.bind("<Button-4>", self._on_histogram_mousewheel)
        self.histogram_canvas.bind("<Button-5>", self._on_histogram_mousewheel)

        self.circuit = []
        self._draw_circuit_lines()



    def _create_palette(self):
        self.gates = {
            "H": {"color": "#a1e6a3", "qubits": 1},
            "X": {"color": "#f09a9a", "qubits": 1},
            "Y": {"color": "#f0f09a", "qubits": 1},
            "Z": {"color": "#9ab6f0", "qubits": 1},
            "S": {"color": "#b7f0d3", "qubits": 1},
            "T": {"color": "#f5c28b", "qubits": 1},
            "RX": {"color": "#c8f2ff", "qubits": 1},
            "RY": {"color": "#ffe3a3", "qubits": 1},
            "RZ": {"color": "#d6c6ff", "qubits": 1},
            "CRX": {"color": "#89f5e4", "qubits": 2},
            "CRY": {"color": "#f7e589", "qubits": 2},
            "CRZ": {"color": "#d8b7ff", "qubits": 2},
            "CNOT": {"color": "#e6a1e6", "qubits": 2},
            "CZ": {"color": "#c8a1f0", "qubits": 2},
            "SWAP": {"color": "#a1d9f0", "qubits": 2},
            "CCX": {"color": "#ffb3c7", "qubits": 3},
            "M": {"color": "#d9d9d9", "qubits": 1},
            "MA": {"color": "#bbbbbb", "qubits": 0},
        }

        self.palette_canvas = tk.Canvas(self.palette_frame, bg="#f0f0f0", width=130, highlightthickness=0)
        palette_scrollbar = ttk.Scrollbar(self.palette_frame, orient=tk.VERTICAL, command=self.palette_canvas.yview)
        self.palette_inner_frame = ttk.Frame(self.palette_canvas)

        self.palette_inner_frame.bind(
            "<Configure>",
            lambda event: self.palette_canvas.configure(scrollregion=self.palette_canvas.bbox("all")),
        )

        self.palette_canvas.create_window((0, 0), window=self.palette_inner_frame, anchor="nw")
        self.palette_canvas.configure(yscrollcommand=palette_scrollbar.set)
        self.palette_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        palette_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.palette_canvas.bind("<MouseWheel>", self._on_palette_mousewheel)
        self.palette_canvas.bind("<Button-4>", self._on_palette_mousewheel)
        self.palette_canvas.bind("<Button-5>", self._on_palette_mousewheel)
        self.palette_inner_frame.bind("<MouseWheel>", self._on_palette_mousewheel)
        self.palette_inner_frame.bind("<Button-4>", self._on_palette_mousewheel)
        self.palette_inner_frame.bind("<Button-5>", self._on_palette_mousewheel)

        for gate_name, properties in self.gates.items():
            gate_label = tk.Label(
                self.palette_inner_frame,
                text=gate_name,
                bg=properties["color"],
                fg="black",
                width=6,
                height=2,
                relief="raised",
                borderwidth=2,
                font=("Helvetica", 10, "bold"),
            )
            gate_label.pack(pady=5, padx=(0, 6))
            gate_label.bind("<MouseWheel>", self._on_palette_mousewheel)
            gate_label.bind("<Button-4>", self._on_palette_mousewheel)
            gate_label.bind("<Button-5>", self._on_palette_mousewheel)
            DraggableGate(gate_label, self)

    def _on_palette_mousewheel(self, event):
        if not hasattr(self, "palette_canvas"):
            return

        if getattr(event, "delta", 0):
            self.palette_canvas.yview_scroll(int(-event.delta / 120), "units")
        elif getattr(event, "num", None) == 4:
            self.palette_canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            self.palette_canvas.yview_scroll(1, "units")

    def _on_histogram_mousewheel(self, event):
        if not hasattr(self, "histogram_canvas"):
            return

        if getattr(event, "delta", 0):
            self.histogram_canvas.yview_scroll(int(-event.delta / 120), "units")
        elif getattr(event, "num", None) == 4:
            self.histogram_canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            self.histogram_canvas.yview_scroll(1, "units")

    def _on_circuit_mousewheel(self, event):
        if not hasattr(self, "circuit_canvas"):
            return

        if getattr(event, "delta", 0):
            amount = int(-event.delta / 120)
        elif getattr(event, "num", None) == 4:
            amount = -1
        elif getattr(event, "num", None) == 5:
            amount = 1
        else:
            return

        if event.state & 0x0001:
            self.circuit_canvas.xview_scroll(amount, "units")
        else:
            self.circuit_canvas.yview_scroll(amount, "units")

    def _get_qubit_y(self, qubit_index):
        return self.qubit_start_y + qubit_index * self.qubit_spacing

    def _get_nearest_qubit(self, y_position):
        return min(range(self.num_qubits), key=lambda index: abs(y_position - self._get_qubit_y(index)))

    def _choose_partner_qubit(self, qubit_index):
        if self.num_qubits < 2:
            raise ValueError("At least two qubits are required for a controlled gate.")
        return qubit_index + 1 if qubit_index < self.num_qubits - 1 else qubit_index - 1

    def _prompt_for_control_qubit(self, target_qubit, gate_name):
        import tkinter.simpledialog as sd
        import tkinter.messagebox as mb

        available_controls = [i for i in range(self.num_qubits) if i != target_qubit]
        if not available_controls:
            mb.showerror("Error", f"No available control qubits for {gate_name} on target q{target_qubit}")
            return None

        control_str = sd.askstring(
            title=f"Select control for {gate_name}",
            prompt=f"Target is q{target_qubit}. Enter control qubit (0-{self.num_qubits-1}, not {target_qubit}):",
            parent=self,
        )
        if control_str is None:
            return None
        try:
            control = int(control_str.strip())
            if control not in available_controls:
                mb.showerror("Error", f"Invalid control qubit: {control}. Must be one of {available_controls}")
                return None
            return control
        except ValueError:
            mb.showerror("Error", "Control qubit must be an integer.")
            return None

    def _prompt_for_partner_qubit(self, first_qubit, gate_name):
        import tkinter.simpledialog as sd
        import tkinter.messagebox as mb

        available_partners = [i for i in range(self.num_qubits) if i != first_qubit]
        if not available_partners:
            mb.showerror("Error", f"No available partner qubits for {gate_name} on q{first_qubit}")
            return None

        partner_str = sd.askstring(
            title=f"Select partner for {gate_name}",
            prompt=f"First qubit is q{first_qubit}. Enter partner qubit (0-{self.num_qubits-1}, not {first_qubit}):",
            parent=self,
        )
        if partner_str is None:
            return None
        try:
            partner = int(partner_str.strip())
            if partner not in available_partners:
                mb.showerror("Error", f"Invalid partner qubit: {partner}. Must be one of {available_partners}")
                return None
            return partner
        except ValueError:
            mb.showerror("Error", "Partner qubit must be an integer.")
            return None

    def _add_gate_to_circuit(self, gate_name, x, y):
        qubit = self._get_nearest_qubit(y)
        gate_record = {"name": gate_name, "x": x}

        if gate_name in {"CNOT", "CZ", "CRX", "CRY", "CRZ"}:
            target = qubit
            control = self._prompt_for_control_qubit(target, gate_name)
            if control is None:
                return
            gate_record["control"] = control
            gate_record["target"] = target
            if gate_name in {"CRX", "CRY", "CRZ"}:
                angle_result = self._prompt_for_rotation_angle(gate_name)
                if angle_result is None:
                    return
                gate_record["theta"], gate_record["theta_text"] = angle_result
        elif gate_name == "SWAP":
            first = qubit
            partner = self._prompt_for_partner_qubit(first, gate_name)
            if partner is None:
                return
            gate_record["control"] = first
            gate_record["target"] = partner
        elif gate_name == "CCX":
            gate_record["target"] = qubit
            gate_record["controls"] = [index for index in range(self.num_qubits) if index != qubit]
        elif gate_name == "MA":
            gate_record = {"name": "MA", "x": x}
        else:
            gate_record["qubit"] = qubit
            if gate_name in {"RX", "RY", "RZ"}:
                angle_result = self._prompt_for_rotation_angle(gate_name)
                if angle_result is None:
                    return
                gate_record["theta"], gate_record["theta_text"] = angle_result

        self.circuit.append(gate_record)
        self._redraw_circuit()

    def _redraw_circuit(self):
        self.circuit_canvas.delete("all")
        self._draw_circuit_lines()
        for gate in sorted(self.circuit, key=lambda item: item["x"]):
            self._draw_gate_visual(gate)

    def _draw_gate_visual(self, gate):
        gate_name = gate["name"]
        x_pos = gate["x"]

        if gate_name in {"CNOT", "CZ", "SWAP", "CRX", "CRY", "CRZ"}:
            control_y = self._get_qubit_y(gate["control"])
            target_y = self._get_qubit_y(gate["target"])
            self.circuit_canvas.create_line(x_pos, control_y, x_pos, target_y, width=2, tags=("gate", gate_name))

            if gate_name == "CNOT":
                self.circuit_canvas.create_oval(x_pos - 5, control_y - 5, x_pos + 5, control_y + 5, fill="black", tags=("gate", gate_name))
                self.circuit_canvas.create_oval(x_pos - 15, target_y - 15, x_pos + 15, target_y + 15, outline="black", width=2, tags=("gate", gate_name))
                self.circuit_canvas.create_line(x_pos, target_y - 15, x_pos, target_y + 15, width=2, tags=("gate", gate_name))
                self.circuit_canvas.create_line(x_pos - 15, target_y, x_pos + 15, target_y, width=2, tags=("gate", gate_name))
            elif gate_name == "CZ":
                self.circuit_canvas.create_oval(x_pos - 6, control_y - 6, x_pos + 6, control_y + 6, fill="black", tags=("gate", gate_name))
                self.circuit_canvas.create_oval(x_pos - 6, target_y - 6, x_pos + 6, target_y + 6, fill="black", tags=("gate", gate_name))
            elif gate_name == "SWAP":
                for y_pos in (control_y, target_y):
                    self.circuit_canvas.create_line(x_pos - 10, y_pos - 10, x_pos + 10, y_pos + 10, width=2, tags=("gate", gate_name))
                    self.circuit_canvas.create_line(x_pos - 10, y_pos + 10, x_pos + 10, y_pos - 10, width=2, tags=("gate", gate_name))
            else:
                # CRX/CRY/CRZ controls
                self.circuit_canvas.create_oval(x_pos - 5, control_y - 5, x_pos + 5, control_y + 5, fill="black", tags=("gate", gate_name))
                self.circuit_canvas.create_rectangle(
                    x_pos - 15,
                    target_y - 15,
                    x_pos + 15,
                    target_y + 15,
                    fill=self.gates[gate_name]["color"],
                    tags=("gate", gate_name),
                )
                self.circuit_canvas.create_text(x_pos, target_y, text=f"{gate_name}\nθ={gate.get('theta_text', '')}", font=("Helvetica", 8, "bold"), tags=("gate", gate_name))
            return

        if gate_name == "MA":
            y_pos = self._get_qubit_y(self.num_qubits // 2)
            self.circuit_canvas.create_rectangle(
                x_pos - 24,
                y_pos - 16,
                x_pos + 24,
                y_pos + 16,
                fill=self.gates[gate_name]["color"],
                tags=("gate", gate_name),
            )
            self.circuit_canvas.create_text(x_pos, y_pos, text="MEASURE ALL", font=("Helvetica", 8, "bold"), tags=("gate", gate_name))
            return

        if gate_name == "CCX":
            controls = gate["controls"]
            target = gate["target"]
            control_y_positions = [self._get_qubit_y(index) for index in controls]
            target_y = self._get_qubit_y(target)
            self.circuit_canvas.create_line(
                x_pos,
                min(control_y_positions + [target_y]),
                x_pos,
                max(control_y_positions + [target_y]),
                width=2,
                tags=("gate", gate_name),
            )
            for control_y in control_y_positions:
                self.circuit_canvas.create_oval(x_pos - 5, control_y - 5, x_pos + 5, control_y + 5, fill="black", tags=("gate", gate_name))
            self.circuit_canvas.create_oval(x_pos - 15, target_y - 15, x_pos + 15, target_y + 15, outline="black", width=2, tags=("gate", gate_name))
            self.circuit_canvas.create_line(x_pos, target_y - 15, x_pos, target_y + 15, width=2, tags=("gate", gate_name))
            self.circuit_canvas.create_line(x_pos - 15, target_y, x_pos + 15, target_y, width=2, tags=("gate", gate_name))
            return

        gate_width = 48
        gate_height = 46
        y_pos = self._get_qubit_y(gate["qubit"])
        display_text = gate_name

        if gate_name in {"RX", "RY", "RZ"}:
            theta_text = gate.get("theta_text", self._format_theta_for_display(gate["theta"], gate["theta"]))
            display_text = f"{gate_name}\nθ={theta_text}"
            gate_height = 54

        self.circuit_canvas.create_rectangle(
            x_pos - gate_width / 2,
            y_pos - gate_height / 2,
            x_pos + gate_width / 2,
            y_pos + gate_height / 2,
            fill=self.gates[gate_name]["color"],
            tags=("gate", gate_name),
        )
        self.circuit_canvas.create_text(x_pos, y_pos, text=display_text, font=("Helvetica", 9, "bold"), tags=("gate", gate_name))

    def _find_gate_index_at_position(self, x_pos, y_pos):
        if not self.circuit:
            return None

        def gate_qubits(gate):
            if gate["name"] in {"CNOT", "CZ", "SWAP", "CRX", "CRY", "CRZ"}:
                return [gate["control"], gate["target"]]
            if gate["name"] == "CCX":
                return [*gate["controls"], gate["target"]]
            if gate["name"] == "MA":
                return list(range(self.num_qubits))
            return [gate.get("qubit", 0)]

        best_index = None
        best_score = None

        for index, gate in enumerate(self.circuit):
            y_distance = min(abs(self._get_qubit_y(qubit) - y_pos) for qubit in gate_qubits(gate))
            x_distance = abs(gate["x"] - x_pos)

            if x_distance > 50 or y_distance > 60:
                continue

            score = x_distance + (1.5 * y_distance)
            if best_score is None or score < best_score:
                best_score = score
                best_index = index

        return best_index

    def _delete_gate_at_position(self, event):
        canvas_x = self.circuit_canvas.canvasx(event.x)
        canvas_y = self.circuit_canvas.canvasy(event.y)
        gate_index = self._find_gate_index_at_position(canvas_x, canvas_y)
        if gate_index is None:
            return

        removed_gate = self.circuit.pop(gate_index)
        self._redraw_circuit()
        self._clear_histogram()
        self.results_label.config(
            text=f"Deleted {self._describe_gate(removed_gate)}.\nTip: right-click another placed gate to remove it."
        )

    def _edit_rotation_gate_at_position(self, event):
        canvas_x = self.circuit_canvas.canvasx(event.x)
        canvas_y = self.circuit_canvas.canvasy(event.y)
        gate_index = self._find_gate_index_at_position(canvas_x, canvas_y)
        if gate_index is None:
            return

        gate = self.circuit[gate_index]
        if gate["name"] not in {"RX", "RY", "RZ"}:
            return

        angle_result = self._prompt_for_rotation_angle(
            gate["name"],
            initial_value=gate.get("theta_text", f"{gate['theta']:.3f}"),
        )
        if angle_result is None:
            return

        gate["theta"], gate["theta_text"] = angle_result
        self._redraw_circuit()
        self.results_label.config(
            text=f"Updated {self._describe_gate(gate)}.\nDouble-click another rotation gate to edit its angle."
        )


    def _run_simulation(self):
        if not self.circuit:
            self.results_label.config(text="Circuit is empty.")
            self._clear_histogram()
            return

        sorted_circuit = sorted(self.circuit, key=lambda gate: gate["x"])

        try:
            kernel = cudaq.make_kernel()
            qubits = kernel.qalloc(self.num_qubits)
            measured_qubits = []
            measurement_seen = False

            for gate_info in sorted_circuit:
                gate_name = gate_info["name"]

                if gate_name == "M":
                    measurement_seen = True
                    qubit_index = gate_info["qubit"]
                    if qubit_index not in measured_qubits:
                        measured_qubits.append(qubit_index)
                    continue

                if gate_name == "MA":
                    measurement_seen = True
                    measured_qubits = list(range(self.num_qubits))
                    continue

                if measurement_seen:
                    raise ValueError("Measurement gates must be placed at the end of the circuit.")

                if gate_name == "H":
                    kernel.h(qubits[gate_info["qubit"]])
                elif gate_name == "X":
                    kernel.x(qubits[gate_info["qubit"]])
                elif gate_name == "Y":
                    kernel.y(qubits[gate_info["qubit"]])
                elif gate_name == "Z":
                    kernel.z(qubits[gate_info["qubit"]])
                elif gate_name == "S":
                    kernel.s(qubits[gate_info["qubit"]])
                elif gate_name == "T":
                    kernel.t(qubits[gate_info["qubit"]])
                elif gate_name == "RX":
                    kernel.rx(gate_info["theta"], qubits[gate_info["qubit"]])
                elif gate_name == "RY":
                    kernel.ry(gate_info["theta"], qubits[gate_info["qubit"]])
                elif gate_name == "RZ":
                    kernel.rz(gate_info["theta"], qubits[gate_info["qubit"]])
                elif gate_name == "CRX":
                    kernel.crx(gate_info["theta"], qubits[gate_info["control"]], qubits[gate_info["target"]])
                elif gate_name == "CRY":
                    kernel.cry(gate_info["theta"], qubits[gate_info["control"]], qubits[gate_info["target"]])
                elif gate_name == "CRZ":
                    kernel.crz(gate_info["theta"], qubits[gate_info["control"]], qubits[gate_info["target"]])
                elif gate_name == "CNOT":
                    kernel.cx(qubits[gate_info["control"]], qubits[gate_info["target"]])
                elif gate_name == "CZ":
                    kernel.cz(qubits[gate_info["control"]], qubits[gate_info["target"]])
                elif gate_name == "SWAP":
                    kernel.swap(qubits[gate_info["control"]], qubits[gate_info["target"]])
                elif gate_name == "CCX":
                    self._apply_toffoli(kernel, qubits, gate_info["controls"], gate_info["target"])
                else:
                    raise ValueError(f"Unsupported gate: {gate_name}")

            measured_qubits.sort()
            if measured_qubits:
                shots = self._get_shots()
                kernel.mz(qubits)
                sample_result = cudaq.sample(kernel, shots_count=shots)
                result_text = self._format_measurement_results(sample_result, measured_qubits, shots)
            else:
                state = cudaq.get_state(kernel)
                result_text = self._format_state_results(state)

            self.results_label.config(text=result_text)

        except Exception as e:
            self._clear_histogram()
            gate_order = ", ".join(self._describe_gate(gate) for gate in sorted_circuit)
            self.results_label.config(
                text=f"Simulation error:\n{e}\n\nGate order: {gate_order or 'empty'}"
            )

    def _get_shots(self):
        try:
            shots = int(self.shots_var.get().strip())
        except ValueError as exc:
            raise ValueError("Shots must be a positive integer.") from exc

        if shots <= 0:
            raise ValueError("Shots must be a positive integer.")

        return shots

    def _parse_angle_value(self, raw_value):
        raw_value = str(raw_value).strip()
        if not raw_value:
            raise ValueError("Angle θ must be a valid number, e.g. 0.5 or pi/4.")

        try:
            angle = float(eval(raw_value, {"__builtins__": {}}, {"pi": math.pi, "tau": math.tau, "e": math.e}))
        except Exception as exc:
            raise ValueError("Angle θ must be a valid number, e.g. 0.5 or pi/4.") from exc

        return angle

    def _format_theta_for_display(self, raw_value, theta_value=None):
        compact_text = str(raw_value).strip().replace(" ", "")
        if compact_text and len(compact_text) <= 7:
            return compact_text

        if theta_value is None:
            theta_value = self._parse_angle_value(raw_value)

        return f"{theta_value:.2f}"

    def _prompt_for_rotation_angle(self, gate_name, initial_value=None):
        prompt_value = initial_value or self.angle_prompt_default

        while True:
            raw_value = simpledialog.askstring(
                title=f"Set angle for {gate_name}",
                prompt=f"Enter θ for {gate_name}. Examples: pi/4, pi/2, 1.5708",
                initialvalue=prompt_value,
                parent=self,
            )

            if raw_value is None:
                return None

            raw_value = raw_value.strip()
            try:
                theta_value = self._parse_angle_value(raw_value)
            except ValueError as exc:
                self.results_label.config(text=str(exc))
                prompt_value = raw_value or prompt_value
                continue

            self.angle_prompt_default = raw_value
            return theta_value, self._format_theta_for_display(raw_value, theta_value)

    def _apply_toffoli(self, kernel, qubits, controls, target):
        control_a, control_b = controls

        kernel.h(qubits[target])
        kernel.cx(qubits[control_b], qubits[target])
        kernel.tdg(qubits[target])
        kernel.cx(qubits[control_a], qubits[target])
        kernel.t(qubits[target])
        kernel.cx(qubits[control_b], qubits[target])
        kernel.tdg(qubits[target])
        kernel.cx(qubits[control_a], qubits[target])
        kernel.t(qubits[control_b])
        kernel.t(qubits[target])
        kernel.h(qubits[target])
        kernel.cx(qubits[control_a], qubits[control_b])

    def _generate_qasm(self):
        lines = [
            "OPENQASM 2.0;",
            'include "qelib1.inc";',
            f"qreg q[{self.num_qubits}];",
            f"creg c[{self.num_qubits}];",
        ]

        for gate in sorted(self.circuit, key=lambda g: g["x"]):
            name = gate["name"]
            lines.append(self._gate_to_qasm(name, gate))

        return "\n".join([l for l in lines if l])

    def _gate_to_qasm(self, name, gate):
        if name in {"H", "X", "Y", "Z", "S", "T"}:
            return f"{name.lower()} q[{gate['qubit']}] ;"
        if name in {"RX", "RY", "RZ"}:
            return f"{name.lower()}({gate['theta']}) q[{gate['qubit']}] ;"
        if name in {"CNOT", "CZ", "SWAP"}:
            op = "cx" if name == "CNOT" else "cz" if name == "CZ" else "swap"
            return f"{op} q[{gate['control']}],q[{gate['target']}] ;"
        if name in {"CRX", "CRY", "CRZ"}:
            op = name.lower()
            return f"{op}({gate['theta']}) q[{gate['control']}],q[{gate['target']}] ;"
        if name == "CCX":
            return f"ccx q[{gate['controls'][0]}],q[{gate['controls'][1]}],q[{gate['target']}] ;"
        if name == "M":
            return f"measure q[{gate['qubit']} ] -> c[{gate['qubit']}] ;"
        if name == "MA":
            return "\n".join([f"measure q[{i}] -> c[{i}] ;" for i in range(self.num_qubits)])
        return ""

    def _save_to_qasm(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".qasm",
            filetypes=[("OpenQASM", "*.qasm"), ("All Files", "*.*")],
            title="Save circuit as QASM",
            parent=self,
        )
        if not filename:
            return
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self._generate_qasm())
            messagebox.showinfo("Saved", f"Circuit saved to {filename}", parent=self)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to save QASM: {exc}", parent=self)

    def _load_from_qasm(self):
        filename = filedialog.askopenfilename(
            defaultextension=".qasm",
            filetypes=[("OpenQASM", "*.qasm"), ("All Files", "*.*")],
            title="Load circuit from QASM",
            parent=self,
        )
        if not filename:
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                qasm_text = f.read()
            self.circuit = self._parse_qasm(qasm_text)
            self._redraw_circuit()
            self._clear_histogram()
            self.results_label.config(text=f"Loaded circuit from {filename}")
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load QASM: {exc}", parent=self)

    def _export_screenshot(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")],
            title="Export circuit screenshot",
            parent=self,
        )
        if not filename:
            return

        try:
            ps_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ps")
            self.circuit_canvas.update_idletasks()
            self.circuit_canvas.postscript(file=ps_file.name, colormode="color")
            ps_file.close()
            try:
                from PIL import Image
            except ImportError:
                raise RuntimeError("Pillow is required for PNG export (pip install pillow)")

            image = Image.open(ps_file.name)
            image.save(filename, "PNG")
            messagebox.showinfo("Saved", f"Screenshot saved to {filename}", parent=self)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to export screenshot: {exc}", parent=self)

    def _parse_qasm(self, qasm_text):
        lines = [ln.split("//")[0].strip() for ln in qasm_text.splitlines()]
        lines = [ln for ln in lines if ln and not ln.startswith("//")]

        num_qubits = self.num_qubits
        circuit = []

        for ln in lines:
            if ln.startswith("OPENQASM") or ln.startswith("include"):
                continue
            if ln.startswith("qreg"):
                try:
                    num_qubits = int(ln.split("[")[1].split("]")[0])
                except Exception:
                    raise ValueError("Invalid qreg format in QASM file")
                continue
            if ln.startswith("creg"):
                continue

            if ln.startswith("measure"):
                parts = ln.replace(";", "").split()
                if len(parts) >= 2 and parts[1].startswith("q["):
                    idx = int(parts[1].split("[")[1].split("]")[0])
                    circuit.append({"name": "M", "x": 0, "qubit": idx})
                continue

            tokens = ln.replace(";", "").split()
            if not tokens:
                continue
            op = tokens[0]
            op_name = op
            theta = 0.0
            if "(" in op and ")" in op:
                op_name = op.split("(")[0]
                theta = float(op.split("(")[1].split(")")[0])

            if op_name in {"h", "x", "y", "z", "s", "t"}:
                idx = int(tokens[1].split("[")[1].split("]")[0])
                gate_name = op_name.upper()
                circuit.append({"name": gate_name, "x": 0, "qubit": idx})
                continue

            if op_name in {"rx", "ry", "rz", "crx", "cry", "crz"}:
                rest = ln.split(")")[1].strip() if ")" in ln else (tokens[1] if len(tokens) > 1 else "")
                targets = [x.strip() for x in rest.replace(";", "").split(",") if x.strip()]
                if len(targets) == 1:
                    idx = int(targets[0].split("[")[1].split("]")[0])
                    gate_name = op_name.upper()
                    circuit.append({"name": gate_name, "x": 0, "qubit": idx, "theta": theta, "theta_text": self._format_theta_for_display(str(theta), theta)})
                elif len(targets) == 2:
                    control_idx = int(targets[0].split("[")[1].split("]")[0])
                    target_idx = int(targets[1].split("[")[1].split("]")[0])
                    gate_name = op_name.upper()
                    circuit.append({"name": gate_name, "x": 0, "control": control_idx, "target": target_idx, "theta": theta, "theta_text": self._format_theta_for_display(str(theta), theta)})
                continue

            if op == "cx" or op == "cz" or op == "swap":
                parts = ln.replace(";", "").split()
                indices = [int(p.split("[")[1].split("]")[0]) for p in parts[1].split(",")]
                gate_name = "CNOT" if op == "cx" else "CZ" if op == "cz" else "SWAP"
                circuit.append({"name": gate_name, "x": 0, "control": indices[0], "target": indices[1]})
                continue

            if op == "ccx":
                parts = ln.replace(";", "").split()
                indices = [int(p.split("[")[1].split("]")[0]) for p in parts[1].split(",")]
                circuit.append({"name": "CCX", "x": 0, "controls": indices[:2], "target": indices[2]})
                continue

        if num_qubits != self.num_qubits:
            raise ValueError(f"Loaded QASM has {num_qubits} qubits, expected {self.num_qubits}")

        # assign x positions spaced evenly
        spacing = 100
        for idx, gate in enumerate(circuit):
            gate["x"] = 80 + idx * spacing

        return circuit

    def _describe_gate(self, gate):
        gate_name = gate["name"]
        if gate_name in {"CNOT", "CZ"}:
            return f"{gate_name}(q{gate['control']}→q{gate['target']})"
        if gate_name == "SWAP":
            return f"SWAP(q{gate['control']}↔q{gate['target']})"
        if gate_name == "CCX":
            controls = ", ".join(f"q{qubit}" for qubit in gate["controls"])
            return f"CCX({controls}→q{gate['target']})"
        if gate_name in {"RX", "RY", "RZ"}:
            theta_text = gate.get("theta_text", f"{gate['theta']:.3f}")
            return f"{gate_name}(q{gate['qubit']}, θ={theta_text})"
        if gate_name in {"CRX", "CRY", "CRZ"}:
            theta_text = gate.get("theta_text", f"{gate['theta']:.3f}")
            return f"{gate_name}(q{gate['control']}→q{gate['target']}, θ={theta_text})"
        if gate_name == "MA":
            return "MEASURE_ALL"
        return f"{gate_name}(q{gate.get('qubit', '?')})"

    def _format_state_results(self, state):
        self._clear_histogram()
        result_lines = [f"Final State Vector ({self.num_qubits} qubits):"]
        basis_states = [format(index, f"0{self.num_qubits}b") for index in range(2 ** self.num_qubits)]

        for basis_state in basis_states:
            amp = state.amplitude(basis_state)
            result_lines.append(f"|{basis_state}>: {amp.real:.4f} + {amp.imag:.4f}i")

        return "\n".join(result_lines)

    def _format_measurement_results(self, sample_result, measured_qubits, shots):
        counts = {str(bitstring): count for bitstring, count in sample_result.items()}
        total_shots = sum(counts.values()) or shots
        expected_states = [format(i, f"0{self.num_qubits}b") for i in range(2 ** self.num_qubits)]
        marker_labels = ", ".join(f"q{qubit}" for qubit in measured_qubits)
        full_register = ", ".join(f"q{index}" for index in range(self.num_qubits))

        self._draw_histogram(counts, expected_states, total_shots)

        result_lines = [
            f"Measurement Results ({total_shots} shots)",
            f"Measurement markers placed on: {marker_labels}",
            f"Reported register: {full_register}",
        ]

        for bitstring in expected_states:
            count = counts.get(bitstring, 0)
            probability = 100.0 * count / total_shots
            result_lines.append(f"{bitstring}: {count:>4} ({probability:5.1f}%)")

        result_lines.extend([
            "",
            "Note: each Run Simulation click re-initializes |000> and reruns the whole circuit from scratch.",
            "Within a single shot, the first measurement collapses the state to a classical 3-bit result.",
        ])

        return "\n".join(result_lines)
    def _clear_histogram(self):
        if hasattr(self, "histogram_canvas"):
            self.histogram_canvas.delete("all")
            self.histogram_canvas.configure(scrollregion=(0, 0, 0, 0))
            self.histogram_canvas.xview_moveto(0)
            self.histogram_canvas.yview_moveto(0)

    def _draw_histogram(self, counts, expected_states, total_shots):
        if not hasattr(self, "histogram_canvas"):
            return

        canvas = self.histogram_canvas
        canvas.delete("all")
        canvas.update_idletasks()

        visible_width = max(canvas.winfo_width(), 420)
        left_margin = 60
        right_margin = 70
        top = 28
        spacing = 26
        content_height = max(150, top + len(expected_states) * spacing + 20)
        content_width = max(visible_width, 520)
        bar_area = max(content_width - left_margin - right_margin, 120)

        max_count = max((counts.get(state, 0) for state in expected_states), default=1) or 1
        canvas.create_text(content_width / 2, 12, text="Measurement Histogram", font=("Helvetica", 10, "bold"))

        for index, state in enumerate(expected_states):
            y = top + index * spacing
            count = counts.get(state, 0)
            probability = count / total_shots if total_shots else 0.0
            bar_length = 0 if max_count == 0 else int((count / max_count) * bar_area)

            canvas.create_text(10, y, text=state, anchor="w", font=("Courier", 10, "bold"))
            canvas.create_rectangle(left_margin, y - 8, left_margin + bar_length, y + 8, fill="#6c8ef5", outline="#4f6bc9")
            canvas.create_text(content_width - 10, y, text=f"{probability * 100:4.1f}%", anchor="e", font=("Courier", 10))

        canvas.configure(scrollregion=(0, 0, content_width, content_height))
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)
    def _clear_circuit(self):
        self.circuit = []
        self._redraw_circuit()
        self.circuit_canvas.xview_moveto(0)
        self.circuit_canvas.yview_moveto(0)
        self.results_label.config(text="Final state vector or full 3-qubit measurement distribution will appear here")
        self._clear_histogram()

    def _get_circuit_dimensions(self):
        circuit_gates = getattr(self, "circuit", [])
        max_gate_x = max((gate["x"] for gate in circuit_gates), default=700)
        content_width = max(900, int(max_gate_x + 140))
        content_height = max(260, self._get_qubit_y(self.num_qubits - 1) + 80)
        return content_width, content_height

    def _draw_circuit_lines(self):
        content_width, content_height = self._get_circuit_dimensions()
        right_edge = content_width - 50
        self.circuit_canvas.config(scrollregion=(0, 0, content_width, content_height))
        for qubit_index in range(self.num_qubits):
            y_pos = self._get_qubit_y(qubit_index)
            self.circuit_canvas.create_line(50, y_pos, right_edge, y_pos, width=2)
            self.circuit_canvas.create_text(20, y_pos, text=f"q{qubit_index}", font=("Helvetica", 12))

class DraggableGate:
    def __init__(self, label, app):
        self.label = label
        self.app = app
        self.drag_window = None
        self.label.bind("<Button-1>", self.on_drag_start)
        self.label.bind("<B1-Motion>", self.on_drag_motion)
        self.label.bind("<ButtonRelease-1>", self.on_drag_release)

    def on_drag_start(self, event):
        if not self.drag_window:
            self.drag_window = tk.Toplevel(self.app)
            self.drag_window.overrideredirect(True)
            self.drag_window.geometry(f"+{event.x_root}+{event.y_root}")
            
            dragged_label = tk.Label(
                self.drag_window,
                text=self.label.cget("text"),
                bg=self.label.cget("bg"),
                fg="black",
                relief="raised",
                borderwidth=2,
                font=("Helvetica", 10, "bold"),
            )
            dragged_label.pack()

    def on_drag_motion(self, event):
        if self.drag_window:
            self.drag_window.geometry(f"+{event.x_root}+{event.y_root}")

    def on_drag_release(self, event):
        if self.drag_window:
            self.drag_window.destroy()
            self.drag_window = None

            x_root, y_root = event.x_root, event.y_root
            canvas = self.app.circuit_canvas
            
            if (canvas.winfo_rootx() < x_root < canvas.winfo_rootx() + canvas.winfo_width() and
                canvas.winfo_rooty() < y_root < canvas.winfo_rooty() + canvas.winfo_height()):
                
                canvas_x = canvas.canvasx(x_root - canvas.winfo_rootx())
                canvas_y = canvas.canvasy(y_root - canvas.winfo_rooty())

                self.app._add_gate_to_circuit(self.label.cget("text"), canvas_x, canvas_y)


def qasm_from_circuit(circuit, num_qubits=3):
    lines = [
        "OPENQASM 2.0;",
        'include "qelib1.inc";',
        f"qreg q[{num_qubits}];",
        f"creg c[{num_qubits}];",
    ]

    def gate_to_qasm(name, gate):
        if name in {"H", "X", "Y", "Z", "S", "T"}:
            return f"{name.lower()} q[{gate['qubit']}] ;"
        if name in {"RX", "RY", "RZ"}:
            return f"{name.lower()}({gate['theta']}) q[{gate['qubit']}] ;"
        if name in {"CNOT", "CZ", "SWAP"}:
            op = "cx" if name == "CNOT" else "cz" if name == "CZ" else "swap"
            return f"{op} q[{gate['control']}],q[{gate['target']}] ;"
        if name in {"CRX", "CRY", "CRZ"}:
            return f"{name.lower()}({gate['theta']}) q[{gate['control']}],q[{gate['target']}] ;"
        if name == "CCX":
            return f"ccx q[{gate['controls'][0]}],q[{gate['controls'][1]}],q[{gate['target']}] ;"
        if name == "M":
            return f"measure q[{gate['qubit']}] -> c[{gate['qubit']}] ;"
        if name == "MA":
            return "\n".join([f"measure q[{i}] -> c[{i}] ;" for i in range(num_qubits)])
        return ""

    for gate in sorted(circuit, key=lambda g: g.get("x", 0)):
        qasm = gate_to_qasm(gate["name"], gate)
        if qasm:
            lines.append(qasm)

    return "\n".join(lines)


def circuit_from_qasm(qasm_text, num_qubits=3):
    lines = [ln.split("//")[0].strip() for ln in qasm_text.splitlines()]
    lines = [ln for ln in lines if ln and not ln.startswith("//")]

    circuit = []

    for ln in lines:
        if ln.startswith("OPENQASM") or ln.startswith("include"):
            continue
        if ln.startswith("qreg"):
            continue
        if ln.startswith("creg"):
            continue

        if ln.startswith("measure"):
            parts = ln.replace(";", "").split()
            if len(parts) >= 2 and parts[1].startswith("q["):
                idx = int(parts[1].split("[")[1].split("]")[0])
                circuit.append({"name": "M", "x": 0, "qubit": idx})
            continue

        tokens = ln.replace(";", "").split()
        if not tokens:
            continue
        op = tokens[0]
        op_name = op
        theta = 0.0
        if "(" in op and ")" in op:
            op_name = op.split("(")[0]
            theta = float(op.split("(")[1].split(")")[0])

        if op_name in {"h", "x", "y", "z", "s", "t"}:
            idx = int(tokens[1].split("[")[1].split("]")[0])
            circuit.append({"name": op_name.upper(), "x": 0, "qubit": idx})
            continue

        if op_name in {"rx", "ry", "rz", "crx", "cry", "crz"}:
            rest = ln.split(")")[1].strip() if ")" in ln else (tokens[1] if len(tokens) > 1 else "")
            targets = [x.strip() for x in rest.replace(";", "").split(",") if x.strip()]
            if len(targets) == 1:
                idx = int(targets[0].split("[")[1].split("]")[0])
                circuit.append({"name": op_name.upper(), "x": 0, "qubit": idx, "theta": theta, "theta_text": f"{theta:.2f}"})
            elif len(targets) == 2:
                control_idx = int(targets[0].split("[")[1].split("]")[0])
                target_idx = int(targets[1].split("[")[1].split("]")[0])
                circuit.append({"name": op_name.upper(), "x": 0, "control": control_idx, "target": target_idx, "theta": theta, "theta_text": f"{theta:.2f}"})
            continue

        if op in {"cx", "cz", "swap"}:
            args = ln.replace(";", "").split()[1].split(",")
            cidx = int(args[0].split("[")[1].split("]")[0])
            tidx = int(args[1].split("[")[1].split("]")[0])
            gate_name = "CNOT" if op == "cx" else "CZ" if op == "cz" else "SWAP"
            circuit.append({"name": gate_name, "x": 0, "control": cidx, "target": tidx})
            continue

        if op == "ccx":
            args = ln.replace(";", "").split()[1].split(",")
            c0 = int(args[0].split("[")[1].split("]")[0])
            c1 = int(args[1].split("[")[1].split("]")[0])
            t = int(args[2].split("[")[1].split("]")[0])
            circuit.append({"name": "CCX", "x": 0, "controls": [c0, c1], "target": t})
            continue

    spacing = 100
    for idx, gate in enumerate(circuit):
        gate["x"] = 80 + idx * spacing

    return circuit


if __name__ == "__main__":
    app = CircuitLabGUI()
    app.mainloop()
