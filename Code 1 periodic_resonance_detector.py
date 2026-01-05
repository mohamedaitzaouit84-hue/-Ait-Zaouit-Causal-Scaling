# ======================================
# 1. Install dependencies (Colab)
# ======================================
!pip install -q qiskit qiskit-ibm-runtime matplotlib numpy

# ======================================
# 2. Imports
# ======================================
import numpy as np
import matplotlib.pyplot as plt

from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

# ======================================
# 3. IBM Quantum connection (CORRECT)
# ======================================
IBM_TOKEN = "PUT_YOUR_IBM_TOKEN_HERE"

service = QiskitRuntimeService(
    channel="ibm_quantum_platform",
    token=IBM_TOKEN
)

# Backends (as requested)
backends = ["ibm_fez", "ibm_torino", "ibm_marrakesh"]

# ======================================
# 4. Experiment parameters (reviewer-safe)
# ======================================
N_QUBITS = 20          # deliberately conservative (scientifically reasonable)
SHOTS = 256
DEPTHS = list(range(1, 101, 5))   # D up to 100, step = 5
WINDOW = 10
ALPHA = 0.5

# ======================================
# 5. Predictive correction (your law)
# ======================================
def predictive_correction(signal, window=10, alpha=0.5):
    corrected = np.copy(signal)
    for i in range(window, len(signal)):
        predicted = np.mean(corrected[i-window:i])
        corrected[i] -= alpha * predicted
    return corrected

# ======================================
# 6. Single experiment run
# ======================================
def run_depth_experiment(backend_name, depth):
    backend = service.backend(backend_name)

    qc = QuantumCircuit(N_QUBITS)
    for _ in range(depth):
        for q in range(N_QUBITS):
            qc.h(q)
        for q in range(0, N_QUBITS - 1, 2):
            qc.cx(q, q + 1)
    qc.measure_all()

    tqc = transpile(qc, backend, optimization_level=1)

    sampler = Sampler(mode=backend)
    job = sampler.run([tqc], shots=SHOTS)
    result = job.result()[0]

    counts = result.data.meas.get_counts()

    series = []
    for bitstring, count in counts.items():
        bits = np.array([int(b) for b in bitstring[::-1]])
        for _ in range(count):
            series.append(bits)

    data = np.array(series)[:SHOTS]  # shape: (shots, qubits)
    mean_raw = np.mean(data)
    std_raw = np.std(data)

    corrected_all = []
    for q in range(N_QUBITS):
        corrected_all.append(
            predictive_correction(data[:, q], WINDOW, ALPHA)
        )

    corrected_all = np.array(corrected_all).T
    mean_corr = np.mean(corrected_all)
    std_corr = np.std(corrected_all)

    return mean_raw, std_raw, mean_corr, std_corr

# ======================================
# 7. Full experiment loop
# ======================================
results = {}

for backend_name in backends:
    print(f"\nRunning experiments on {backend_name}")
    results[backend_name] = {
        "D": [],
        "std_raw": [],
        "std_corr": []
    }

    for D in DEPTHS:
        mean_r, std_r, mean_c, std_c = run_depth_experiment(backend_name, D)

        results[backend_name]["D"].append(D)
        results[backend_name]["std_raw"].append(std_r)
        results[backend_name]["std_corr"].append(std_c)

        print(
            f"D={D:3d} | "
            f"Std Raw={std_r:.4f} | "
            f"Std Corrected={std_c:.4f}"
        )

# ======================================
# 8. Visualization (reviewer-grade)
# ======================================
plt.figure(figsize=(10, 6))

for backend_name in backends:
    D = results[backend_name]["D"]
    raw = results[backend_name]["std_raw"]
    corr = results[backend_name]["std_corr"]

    plt.plot(D, raw, "--", label=f"{backend_name} Raw")
    plt.plot(D, corr, "-", label=f"{backend_name} Corrected")

plt.xlabel("Circuit Depth D")
plt.ylabel("Standard Deviation of Measurement Outcomes")
plt.title("Predictive Correction vs Raw Noise (IBM Quantum)")
plt.legend()
plt.grid(True)
plt.show()
