# Computational Track: Compiling for Quantum Computers

## Hacker Handout

---

# Overview

> **You are given a set of quantum programs and a hardware connectivity graph. Your core job: find a qubit placement and SWAP routing strategy that executes all required interactions using the fewest SWAP operations and parallel time steps.**
>
> **For extra points**, optimize the gate decomposition and single-qubit gate layers - we provide intentionally bad baselines for both that are easy to beat.

### The Compilation Pipeline

```
Abstract Circuit
      ↓
  [Placement]        assign logical qubits to physical qubits       ⬅ CORE CHALLENGE
      ↓
  [Routing]          insert SWAPs so all 2Q gates are on neighbors   ⬅ CORE CHALLENGE
      ↓
  [Scheduling]       pack gates into parallel time steps              ⬅ CORE CHALLENGE
      ↓
  [Decomposition]    rewrite gates into hardware-native gate set     ⬅ STRETCH GOAL A
      ↓
  [1Q Optimization]  fuse/cancel redundant single-qubit gates        ⬅ STRETCH GOAL B
      ↓
Executable Circuit
```

### What You Receive

| Item | Description |
|---|---|
| **Hardware graph** | A 20-qubit connectivity graph (which physical qubits are wired together) |
| **Benchmark programs** | 5–8 quantum programs of increasing difficulty, as lists of two-qubit interactions |
| **Bad baselines** | Three intentionally terrible solutions you can immediately beat |
| **Scorer** | An autograder that checks correctness and computes your score |
| **Starter notebook** | Setup, examples, walkthrough, and submission template |

### What You Submit

1. A `solve(program, hardware_graph)` function that returns a placement and routed program
2. (Optional) `decompose()` and `optimize_1q()` functions for stretch goals
3. A 1–2 page writeup explaining your approach
4. A 3–5 minute demo/presentation

### How You're Scored

```
total_score = core_score - stretch_A_bonus - stretch_B_bonus      (lower is better)
```

**Core score** (required):
```
core_score = Σ_benchmarks [ swap_count + 0.5 × depth ]
```

**Stretch bonuses** (optional, subtracted as rewards):
- Stretch A: `0.1 × (gates saved vs. bad decomposer)`
- Stretch B: `0.05 × (1Q gates saved vs. bad 1Q optimizer)`

### Essential Resources

- [PostQuantum: Routing Quantum Information](https://postquantum.com/quantum-computing/routing-quantum-information/) - visual intro to SWAP routing
- [IBM SABRE Tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/transpilation-optimizations-with-sabre) - the industry-standard routing algorithm explained
- [Python `networkx` docs](https://networkx.org/documentation/stable/) - graph algorithms you'll use heavily
- [PennyLane: Compilation of Quantum Circuits](https://pennylane.ai/qml/demos/tutorial_circuit_compilation) - useful for stretch goals

---

# The Problem - No Quantum Required

## Think of It Like a Delivery Routing Problem

Imagine you're a logistics planner. You have:

- A **street map** where buildings (qubits) are connected by roads (wires). Not every building connects to every other - most connect to only 2 or 3 neighbors.
- A **delivery list**: pairs of buildings that need to exchange packages. The exchanges must happen in a specific order.
- A **constraint**: you can only hand off a package between buildings that share a road.

If two buildings that need to exchange packages don't share a road, you have to **relay** the package through intermediate buildings - each relay is expensive and slow.

Your job: decide where to place your people (placement), how to relay packages when needed (routing), and which exchanges to run simultaneously (scheduling).

**That's the entire problem.** Replace "buildings" with "qubits," "roads" with "physical connections," "package exchange" with "two-qubit gate," and "relay" with "SWAP" - and you have quantum circuit compilation.

## The Hardware Graph

Your "street map" is a **20-qubit heavy-hex-style teaching graph**. It looks like this:

```
    0 - 1 - 2 - 3
    |       |       
    4 - 5 - 6 - 7
        |       |   
    8 - 9 -10 -11
    |       |       
   12 -13 -14 -15
        |       |
   16 -17 -18 -19
```

Key properties:
- Each qubit connects to **1–3 neighbors** (nodes 3 and 16 are dead ends with a single connection; all other nodes have 2 or 3)
- There is **no direct connection** between most qubit pairs (e.g., qubit 0 and qubit 19 are 7 hops apart)
- A two-qubit gate can **only** execute between qubits that share an edge

In the starter notebook, this graph is built directly in code as a `networkx.Graph`. You can visualize it, query shortest paths, check adjacency, and test heuristics with standard NetworkX functions.

## What Is a SWAP?

A SWAP exchanges the quantum states of two adjacent qubits. After a SWAP between qubits A and B, the state that was in A is now in B, and vice versa.

**Why you need SWAPs**: if your program says "qubit 0 must interact with qubit 7" but they aren't neighbors, you need to move one of them closer by doing a chain of SWAPs along a path in the hardware graph.

### Walkthrough: Routing a Single Interaction

Suppose your program needs a two-qubit gate between logical qubits 0 and 3, and you've placed them on physical qubits 0 and 11:

```
Step 0 (initial):
    [L0] - 1  - 2  - 3
     |         |       
     4  - 5  - 6  - 7
          |         |   
     8  - 9  -10  -[L3]
```

Physical qubits 0 and 11 aren't adjacent. Shortest path: 0 → 1 → 2 → 6 → 7 → 11 (length 5).

We can SWAP L0 toward L3:

```
Step 1: SWAP(0, 1) - L0 moves from physical qubit 0 to physical qubit 1
     0  -[L0]- 2  - 3
     |         |       
     4  - 5  - 6  - 7
          |         |   
     8  - 9  -10  -[L3]

Step 2: SWAP(1, 2) - L0 moves to physical qubit 2
     0  - 1  -[L0]- 3
     |         |       
     4  - 5  - 6  - 7
          |         |   
     8  - 9  -10  -[L3]

Step 3: SWAP(2, 6) - L0 moves to physical qubit 6
     0  - 1  - 2  - 3
     |        |       
     4  - 5  -[L0]- 7
          |         |   
     8  - 9  -10  -[L3]

Step 4: SWAP(6, 7) - L0 moves to physical qubit 7
     0  - 1  - 2  - 3
     |         |       
     4  - 5  - 6  -[L0]
          |         |   
     8  - 9  -10  -[L3]

Step 5: Now L0 (physical 7) and L3 (physical 11) ARE adjacent!
        → Execute the two-qubit gate. Done.
```

That took **4 SWAPs**. A better initial placement (e.g., putting L0 and L3 on adjacent physical qubits) could have taken **0 SWAPs**. That's why placement matters.

## The Three Sub-Problems

### 1. Placement

**Question**: which logical qubit goes on which physical qubit?

**Why it matters**: a good placement puts frequently-interacting logical qubits on nearby physical qubits, reducing the number of SWAPs needed. A bad placement puts them far apart.

**CS framing**: this is a **graph assignment** problem. You're mapping the nodes of one graph (your program's interaction pattern) onto the nodes of another graph (the hardware), trying to minimize some distance metric.

**Approaches**: random assignment (bad), degree-matching heuristics (decent), simulated annealing (good), exhaustive search on small instances (optimal but slow).

### 2. Routing

**Question**: when two qubits need to interact but aren't adjacent, which SWAPs do you insert?

**Why it matters**: every SWAP adds cost. Greedy routing (always SWAP along the shortest path to the current gate) ignores the rest of the program - a SWAP that helps gate #5 might make gate #6 much harder.

**CS framing**: this is a **path planning** problem with a twist - every SWAP changes the state of the graph (qubit positions move), so future routing depends on past decisions.

**Approaches**: greedy shortest-path (baseline), look-ahead heuristics that consider upcoming gates (better), SABRE-style bidirectional search (state of the art). See the [IBM SABRE tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/transpilation-optimizations-with-sabre) for a detailed walkthrough of the best known heuristic.

### 3. Scheduling

**Question**: which two-qubit operations can run at the same time?

**Why it matters**: running gates in parallel reduces the total circuit depth (execution time). Two 2Q gates can run simultaneously if they act on completely different qubits.

**CS framing**: this is **DAG scheduling** / **bin packing**. Build a dependency graph of operations that respects both the original gate order and qubit conflicts, then assign operations to time slots such that no two operations in the same slot share a qubit.

**Approaches**: sequential execution (no parallelism - baseline), greedy layer packing (decent), DAG-based topological scheduling (good).

---

# Scheduling - Parallelism Matters

## The "1Q Free, 2Q Exclusive" Execution Model

For scoring purposes, the hardware works like this:

- **Single-qubit gates take zero time.** They're instant. Don't worry about them for scheduling.
- **Two-qubit gates** (including SWAPs) execute in **layers**. Each layer is one time step.
- Within a layer, you can run **any number of 2Q gates** - as long as they all act on **non-overlapping qubits** (no qubit appears in two gates in the same layer) and you do not violate the original program order.

### Example: Sequential vs. Parallel

Consider this routed program (all gates on adjacent qubits):

```
CNOT(0,1), CNOT(4,5), CNOT(1,2), CNOT(5,6), CNOT(2,6)
```

**Sequential scheduling** (no parallelism):
```
Layer 1: CNOT(0,1)
Layer 2: CNOT(4,5)
Layer 3: CNOT(1,2)
Layer 4: CNOT(5,6)
Layer 5: CNOT(2,6)
→ Depth = 5
```

**Parallel scheduling** (pack non-overlapping gates together):
```
Layer 1: CNOT(0,1) + CNOT(4,5)    ← qubits {0,1} and {4,5} don't overlap → OK
Layer 2: CNOT(1,2) + CNOT(5,6)    ← qubits {1,2} and {5,6} don't overlap → OK
Layer 3: CNOT(2,6)                  ← both qubits were used in layer 2 → new layer
→ Depth = 3
```

Same gates, same SWAPs, but **depth drops from 5 to 3** - a 40% improvement just from better scheduling.

---

# Scoring & Submission

## Scoring Formula - Worked Example

Suppose on one benchmark:
- Your routing inserts **8 SWAPs**
- Your scheduling achieves a **depth of 12** (2Q layers)

```
benchmark_score = 8 × 1.0 + 12 × 0.5 = 8 + 6 = 14
```

Your total core score is the sum across all benchmarks.

If you also attempted Stretch Goal A and saved 40 gates vs. the bad decomposer:
```
stretch_A_bonus = 40 × 0.1 = 4.0
```

```
total_score = core_score - 4.0
```

## What "Correct" Means

A routed program is **correct** if:

1. Every two-qubit gate in the output acts on **adjacent physical qubits** (qubits that share an edge in the hardware graph)
2. If you strip out all the inserted SWAPs, the remaining operations match the **original program in order** (you haven't reordered, dropped, or added any program gates)
3. The qubit placement and SWAP tracking are **consistent** (after all SWAPs, every logical qubit's physical position is well-defined)

If any of these fail, that benchmark gets a score of **∞** (disqualified).

## Submission Format

Your core submission is a Python function:

```python
def solve(program, hardware_graph):
    """
    Args:
        program: list of tuples
            ("2Q", i, j) = two-qubit gate between logical qubits i and j
            ("1Q", i)    = single-qubit gate on logical qubit i
        hardware_graph: networkx.Graph
            Nodes are physical qubit indices, edges are connections

    Returns:
        initial_placement: dict
            Maps logical qubit index → physical qubit index
            e.g. {0: 5, 1: 6, 2: 9, 3: 10}
        routed_program: list of tuples
            Same format as input, but on PHYSICAL qubits,
            with ("SWAP", p, q) operations inserted as needed.
            Every ("2Q", p, q) must have (p,q) as an edge in hardware_graph.
    """
```

---

# Stretch Goals - For Extra Points

## Stretch Goal A: Gate Decomposition

### What It Is

Real quantum hardware can only execute a small set of **native gates** - think of them like the assembly instructions of a CPU. For this challenge, the native set is `{RZ, SX, CNOT}`:

- `RZ(θ)` - a single-qubit rotation (one parameter)
- `SX` - a fixed single-qubit gate (no parameters)
- `CNOT` - a two-qubit gate (the only native two-qubit operation)

Every other gate (Hadamard, SWAP, Toffoli, etc.) must be **decomposed** into sequences of these three gates.

### Why the Bad Baseline Is Bad

The provided `baseline_decompose.py` wraps every operation with pointless `RZ(0.0)` identity rotations (a zero-angle rotation does nothing):

```
SWAP gate:
  Good decomposition:  CNOT(a,b) → CNOT(b,a) → CNOT(a,b)                                       [3 gates]
  Bad baseline:        RZ(0) → CNOT(a,b) → RZ(0) → CNOT(b,a) → RZ(0) → CNOT(a,b) → RZ(0)     [7 gates]

2Q gate (treated as CNOT):
  Good decomposition:  CNOT(a,b)                                                                 [1 gate]
  Bad baseline:        RZ(0) → CNOT(a,b) → RZ(0)                                                [3 gates]

1Q gate:
  Good decomposition:  remove entirely (if identity) or fuse with neighbors                      [≤1 gate]
  Bad baseline:        RZ(0) → SX → RZ(0)                                                       [3 gates]
```

Every `RZ(0.0)` is a no-op and can be eliminated. On circuits with many gates, these add up quickly.

### How to Beat It

**Easy (use existing tools)**: PennyLane's `qml.transforms.decompose(gate_set={"RZ", "SX", "CNOT"})` or `qml.compile(basis_set=["CNOT", "RX", "RY", "RZ"])` will massively improve over the bad baseline with minimal code.

See the [PennyLane Circuit Compilation demo](https://pennylane.ai/qml/demos/tutorial_circuit_compilation) for a full walkthrough.

**Harder (custom optimization)**: choose decompositions that create opportunities for cancellation with neighboring gates. This is context-aware instruction selection - a real compiler optimization problem.

## Stretch Goal B: Single-Qubit Optimization

### What It Is

After decomposition, the circuit often has long chains of single-qubit gates on the same qubit that could be simplified:

```
Before optimization:  RZ(0.3) → RZ(0.5) → RZ(0.2) → SX → SX → RZ(0.0)
After optimization:   RZ(1.0) → X                                        
```

### The Patterns to Look For

| Pattern | Rule | Example |
|---|---|---|
| **Same-axis merge** | `RZ(a) · RZ(b) = RZ(a+b)` | `RZ(0.3) · RZ(0.5)` → `RZ(0.8)` |
| **Self-inverse cancel** | `H · H = I`, `X · X = I`, `SX · SX = X` | Two adjacent Hadamards → remove both |
| **Zero rotation eliminate** | `RZ(0) = I` | `RZ(0.0)` → remove entirely |
| **Full rotation eliminate** | `RZ(2π) = I` (up to global phase) | `RZ(6.283...)` → remove |

For teams who know some linear algebra: **any sequence of single-qubit gates on the same qubit can be fused into at most 3 rotations** using the ZYZ decomposition. PennyLane provides `qml.transforms.single_qubit_fusion` for this.

### How to Beat It

The bad baseline literally does nothing (`return circuit`). **Any** simplification gets you bonus points:

- **Easy**: merge adjacent same-axis rotations, eliminate zero/full rotations
- **Medium**: use PennyLane's `qml.transforms.merge_rotations` and `qml.transforms.cancel_inverses`
- **Hard**: implement full single-qubit fusion (ZYZ decomposition) from scratch or via `qml.transforms.single_qubit_fusion`

---

# Strategy Guide & Resources

## Suggested Timeline

| Phase | Hours | Focus |
|---|---|---|
| **Understand** | 0–6 | Read this handout, explore the starter notebook, run the baseline, understand the scorer. Try manual placement on `ghz_star`. |
| **Core iteration** | 6–18 | Build and iterate your placement + routing algorithms. Start with small benchmarks, scale up. Try different placement strategies. |
| **Optimize & extend** | 18–30 | Add scheduling for depth reduction. Attempt stretch goals if core is solid. Try your solution on all benchmarks. |
| **Polish** | 30–36 | Final benchmarking runs, writeup, prepare demo. |

## Approach Cheat Sheet

| Approach | Difficulty | Expected Quality | Good First Step? |
|---|---|---|---|
| Random placement + greedy routing | Easy | Poor (but it works!) | ✅ Start here |
| Degree-matching placement | Easy | Decent | ✅ Quick improvement |
| Simulated annealing placement | Medium | Good | After greedy works |
| Look-ahead routing (consider next K gates) | Medium | Good | After placement works |
| SABRE-style bidirectional routing | Hard | Very good | If you want top scores |
| DAG-based parallel scheduling | Medium | Good depth reduction | After routing works |
| Stretch Goal A via `qml.compile` | Easy | Easy bonus points | When core is solid |
| Stretch Goal B via rotation merging | Easy-Medium | Easy bonus points | When core is solid |

## If You're Stuck

- **"My routing produces invalid output"** → print your routed program and check each 2Q gate: is it on an edge? Use `hardware_graph.has_edge(p, q)` to verify.
- **"My SWAP tracking is wrong"** → maintain a `placement` dict that you update after every SWAP. Print it frequently.
- **"I can't beat the baseline on the dense benchmarks"** → that's expected - dense programs need many SWAPs no matter what. Focus on placement optimization; even small improvements compound across many gates.
- **"I don't know where to start"** → implement the greedy baseline yourself (don't just use ours). Understanding *why* it's bad will give you ideas for improvement.

## Key Resources

### For the Core Challenge
- 📖 [PostQuantum: Routing Quantum Information](https://postquantum.com/quantum-computing/routing-quantum-information/) - start here for the big picture
- 📖 [IBM SABRE Tutorial](https://quantum.cloud.ibm.com/docs/en/tutorials/transpilation-optimizations-with-sabre) - detailed walkthrough of the best known routing heuristic
- 🔧 [networkx: Shortest Paths](https://networkx.org/documentation/stable/reference/algorithms/shortest_paths.html) - `nx.shortest_path()` is your best friend
- 🔧 [networkx: Graph Generators](https://networkx.org/documentation/stable/reference/generators.html) - if you want to test on other topologies

### For Stretch Goals
- 📖 [PennyLane: Compilation of Quantum Circuits](https://pennylane.ai/qml/demos/tutorial_circuit_compilation) - full walkthrough of gate cancellation, rotation merging, and decomposition
- 🔧 [PennyLane `qml.compile` docs](https://docs.pennylane.ai/en/stable/code/api/pennylane.compile.html) - one-liner compilation with configurable pipeline
- 🔧 [PennyLane `qml.transforms` reference](https://docs.pennylane.ai/en/stable/code/qml_transforms.html) - `cancel_inverses`, `merge_rotations`, `single_qubit_fusion`, `decompose`

### For Going Deep
- 📄 Li et al., "Tackling the Qubit Mapping Problem for NISQ-Era Quantum Devices" (ASPLOS 2019) - the original SABRE paper
- 📄 [RL-based transpilation (arXiv:2405.13196)](https://arxiv.org/abs/2405.13196) - reinforcement learning for SWAP selection
- 📄 [NASSC: Not All SWAPs Have the Same Cost (HPCA 2022)](https://hzhou.wordpress.ncsu.edu/files/2022/12/HPCA22_NASSC.pdf) - choosing SWAPs that enable downstream gate cancellation
