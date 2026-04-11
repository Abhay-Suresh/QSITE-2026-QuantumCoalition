# Bitcamp 2026 - Quantum Track

Welcome to the Quantum Track of the UMD Bitcamp Hackathon! Below is an overview of both tracks.

If you have any questions feel free to ping - [UQA leadership](https://discord.gg/U7ESA74D) or track mentors.

Workshop resources and (completely optional) [notebooks](https://docs.google.com/document/d/1rISiL1AhbTGiic1FWpSQoO6fZNbj6XDcAdE3Vvi_jak/edit?tab=t.0) are also available for a crash course on quantum computing

---

## Tracks at a Glance

| | Computational Track | Scientific Track |
|---|---|---|
| **Topic** | Quantum circuit compilation | Quantum phase detection |
| **Core skill** | Graph algorithms, optimization | Quantum simulation, data analysis |
| **Output** | A `solve()` function | Phase diagrams + writeup |
| **Presentation** | 3–5 min demo | 5–7 min presentation |
| **Background needed** | CS (graphs, heuristics) | Physics or ML helpful, not required |

---

## Reading Order

### Computational Track

1. **`Computational Track/README.md`** - the full hacker handout. Read this first. Covers the compilation pipeline, hardware graph, scoring formula, and stretch goals in detail.
2. **`Computational Track/starter.ipynb`** - animated walkthrough. Opens with the hardware graph, then routes a real program step-by-step, explains where the baseline fails, and ends with a submission template.
3. **`Computational Track/starter_kit/`** - the minimum viable solution. All six modules are intentionally weak; your job is to beat them.

### Scientific Track

1. **`Scientific Track/README.md`** - the full hacker handout. Covers the ANNNI Hamiltonian, all four phases, phase detection approaches, the noise model, and the judging rubric.
2. **`Scientific Track/starter.ipynb`** - guided walkthrough. Builds the Hamiltonian, surveys all four phases, plots a clean 20×20 phase diagram with analytical boundaries overlaid, then demonstrates the noise model.
3. **`Scientific Track/starter_kit/`** - utility functions for building Hamiltonians, exact diagonalization, noise circuits, observables, reference boundaries, and plotting.

---

## Setup

Each track has its own virtual environment (Python 3.14, PennyLane 0.44.1). Activate before launching Jupyter:

```bash
# Computational Track
source "Computational Track/venv/bin/activate"
jupyter lab "Computational Track/starter.ipynb"

# Scientific Track
source "Scientific Track/venv/bin/activate"
jupyter lab "Scientific Track/starter.ipynb"
```

---

## Computational Track - Quick Summary

**The problem**: given a set of quantum programs and a 20-qubit hardware connectivity graph, find a qubit placement and SWAP routing strategy that executes all required two-qubit interactions using the fewest operations and parallel time steps.

**Scoring** (lower is better):
```
score = swap_count + 0.5 × depth
```

**What you implement**:
```python
def solve(program, hardware_graph):
    # Returns: (initial_placement: dict, routed_program: list[tuple])
```

**Stretch goals** (optional bonus points):
- **A**: decompose into native gates `{RZ, SX, CNOT}` - beat the wasteful baseline
- **B**: fuse and cancel redundant single-qubit gates - beat the no-op baseline

The starter kit provides a scorer, six benchmark programs, a hardware graph, and three bad baselines to improve on.

---

## Scientific Track - Quick Summary

**The problem**: map the phase diagram of the 1D ANNNI model in the (κ, h) parameter plane using PennyLane. Then study how depolarizing noise distorts the phase boundaries.

**The model**:
```
H = -J₁ΣZᵢZᵢ₊₁ + J₁κΣZᵢZᵢ₊₂ - hΣXᵢ
```
Four phases: ferromagnetic, antiphase, paramagnetic, and floating.

**What you submit**: phase diagrams at p=0, p=0.01, p=0.05 (noise levels), a 2–3 page writeup, and a presentation.

**Phase detection approaches** (pick one or more):
- Order parameters via exact diagonalization or VQE
- Quantum convolutional neural network (QCNN, supervised)
- Quantum autoencoder (unsupervised)
- Fidelity susceptibility
- Trotterized time evolution

The starter kit provides the Hamiltonian builder, exact diagonalization, noisy circuit utilities, observables, analytical reference boundaries, and plotting helpers.

---

## Key External Resources

**Computational Track**
- [PostQuantum: Routing Quantum Information](https://postquantum.com/quantum-computing/routing-quantum-information/) - visual intro to SWAP routing
- [IBM SABRE Tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/transpilation-optimizations-with-sabre) - the industry-standard routing algorithm

**Scientific Track**
- [PennyLane: ANNNI Phase Detection Demo](https://pennylane.ai/qml/demos/tutorial_annni) - primary starting point; covers Hamiltonian, VQE, QCNN, and autoencoder approaches
- [PennyLane: A Noisy Heisenberg Model](https://pennylane.ai/challenges/heisenberg_model) - the noise model this track extends
