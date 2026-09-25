"""
SABRE-style placement + routing solver for the QSITE 2026 Computational Track.

Usage:
    from solver import solve
    placement, routed = solve(program, hardware_graph)
"""
from __future__ import annotations

import random
from collections import defaultdict

import networkx as nx

from starter_kit.scorer import used_logical_qubits, core_score


# ── Placement ────────────────────────────────────────────────────────────────

def _interaction_counts(program: list[tuple]) -> dict[int, int]:
    """Count how many 2Q gates each logical qubit participates in."""
    counts: dict[int, int] = defaultdict(int)
    for op in program:
        if op[0] == "2Q":
            counts[op[1]] += 1
            counts[op[2]] += 1
    return counts


def _placement_cost(placement: dict[int, int], program: list[tuple], dist: dict, weigh_early: float = 0.5) -> float:
    """
    Sum of hardware distances for every 2Q gate under a given placement.
    Weights gates exponentially to favor placing early interactions optimally.
    """
    total = 0.0
    two_q_gates = [op for op in program if op[0] == "2Q"]
    n_gates = len(two_q_gates)

    for i, op in enumerate(two_q_gates):
        # Weight scales from 1.0 (early) down to (1-weigh_early) (late)
        weight = 1.0 - (weigh_early * i / n_gates)
        total += weight * dist[placement[op[1]]][placement[op[2]]]
    return total


def smart_placement(
    program: list[tuple],
    hardware_graph: nx.Graph,
    trials: int = 200,
    seed: int = 42,
) -> dict[int, int]:
    """
    Two-phase placement:
    1. Degree-matching heuristic as a warm start.
    2. Random-restart hill climbing: swap two logical->physical assignments
       if it reduces total gate distance.
    """
    logical_qubits = used_logical_qubits(program)
    n = len(logical_qubits)
    physical_nodes = sorted(hardware_graph.nodes)
    dist = dict(nx.all_pairs_shortest_path_length(hardware_graph))
    counts = _interaction_counts(program)

    # Phase 1: busiest logical qubits → highest-degree physical qubits
    logical_sorted = sorted(logical_qubits, key=lambda q: counts.get(q, 0), reverse=True)
    physical_sorted = sorted(physical_nodes, key=lambda q: hardware_graph.degree(q), reverse=True)
    best_placement = {logical_sorted[i]: physical_sorted[i] for i in range(n)}
    best_cost = _placement_cost(best_placement, program, dist, weigh_early=0.5)

    # Phase 2: random-restart local search
    rng = random.Random(seed)
    for _ in range(trials):
        phys_sample = rng.sample(physical_nodes, n)
        candidate = {logical_qubits[i]: phys_sample[i] for i in range(n)}
        cost = _placement_cost(candidate, program, dist, weigh_early=0.5)

        # hill-climb via pairwise swaps
        improved = True
        while improved:
            improved = False
            indices = list(range(n))
            rng.shuffle(indices)
            for i in indices:
                for j in indices:
                    if i >= j:
                        continue
                    li, lj = logical_qubits[i], logical_qubits[j]
                    candidate[li], candidate[lj] = candidate[lj], candidate[li]
                    new_cost = _placement_cost(candidate, program, dist, weigh_early=0.5)
                    if new_cost < cost:
                        cost = new_cost
                        improved = True
                    else:
                        candidate[li], candidate[lj] = candidate[lj], candidate[li]

        if cost < best_cost:
            best_cost = cost
            best_placement = dict(candidate)

    return best_placement


# ── SABRE-style Sequential Routing with Lookahead ────────────────────────────

def sabre_route(
    program: list[tuple],
    hardware_graph: nx.Graph,
    initial_placement: dict[int, int],
    lookahead_window: int = 15,
    lookahead_weight: float = 0.5,
) -> list[tuple]:
    """
    Routes gates in exact program order (required by scorer validation).
    For each non-adjacent 2Q gate, selects the SWAP that minimizes:
        cost = dist(current_gate) + sum(weight * dist(next_k_gates))
    """
    dist = dict(nx.all_pairs_shortest_path_length(hardware_graph))

    l2p = dict(initial_placement)
    p2l = {p: l for l, p in l2p.items()}
    routed: list[tuple] = []

    for i, op in enumerate(program):
        if op[0] == "1Q":
            routed.append(("1Q", l2p[op[1]]))
            continue

        _, l_left, l_right = op

        # Lookahead slice: next K upcoming 2Q gates
        upcoming_2q = [
            (prog_op[1], prog_op[2])
            for prog_op in program[i + 1 : i + 1 + lookahead_window]
            if prog_op[0] == "2Q"
        ]

        def _eval_cost() -> float:
            c = float(dist[l2p[l_left]][l2p[l_right]])
            for weight_idx, (u, v) in enumerate(upcoming_2q):
                decay = lookahead_weight ** (1 + weight_idx * 0.2)
                c += decay * dist[l2p[u]][l2p[v]]
            return c

        # Insert SWAPs until the two qubits are adjacent
        while not hardware_graph.has_edge(l2p[l_left], l2p[l_right]):
            p_left = l2p[l_left]
            p_right = l2p[l_right]

            # Shortest path from p_left to p_right gives the most direct route
            path = nx.shortest_path(hardware_graph, p_left, p_right)

            # Candidate SWAPs: edges adjacent to p_left or p_right along shortest path or neighbors
            candidates = set()
            # Direct path step
            candidates.add((p_left, path[1]))
            candidates.add((path[-2], p_right))

            # Also consider all neighbors of both interacting qubits
            for nbr in hardware_graph.neighbors(p_left):
                candidates.add((min(p_left, nbr), max(p_left, nbr)))
            for nbr in hardware_graph.neighbors(p_right):
                candidates.add((min(p_right, nbr), max(p_right, nbr)))

            best_swap = None
            best_cost = float("inf")

            for u, v in candidates:
                # Tentatively apply SWAP(u, v)
                lu, lv = p2l.get(u), p2l.get(v)
                if lu is not None:
                    l2p[lu] = v
                if lv is not None:
                    l2p[lv] = u
                p2l[u], p2l[v] = lv, lu

                cost = _eval_cost()

                # Revert
                if lu is not None:
                    l2p[lu] = u
                if lv is not None:
                    l2p[lv] = v
                p2l[u], p2l[v] = lu, lv

                if cost < best_cost:
                    best_cost = cost
                    best_swap = (u, v)

            if best_swap is None:
                # Fallback to shortest path step
                best_swap = (p_left, path[1])

            su, sv = best_swap
            routed.append(("SWAP", su, sv))
            lu, lv = p2l.get(su), p2l.get(sv)
            if lu is not None:
                l2p[lu] = sv
            if lv is not None:
                l2p[lv] = su
            p2l[su], p2l[sv] = lv, lu

        # Now they are adjacent — emit the 2Q gate
        routed.append(("2Q", l2p[l_left], l2p[l_right]))

    return routed


# ── Full Solver ──────────────────────────────────────────────────────────────

def solve(
    program: list[tuple],
    hardware_graph: nx.Graph,
    placement_trials: int = 150,
    seeds: int = 8,
) -> tuple[dict[int, int], list[tuple]]:
    """
    Finds best (placement, routed_program) by evaluating across seeds
    and lookahead window parameters.
    """
    best_score = float("inf")
    best_placement = {}
    best_routed = []

    for seed in range(seeds):
        # Try a couple of lookahead windows: 10, 15, 20
        for window in (10, 15, 20):
            placement = smart_placement(program, hardware_graph, trials=placement_trials, seed=seed * 100 + window)
            routed = sabre_route(program, hardware_graph, placement, lookahead_window=window)
            score = core_score(routed)
            if score < best_score:
                best_score = score
                best_placement = dict(placement)
                best_routed = list(routed)

    return best_placement, best_routed


# ── Self-test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from starter_kit import BENCHMARKS, build_hardware_graph, score_summary
    from starter_kit.baseline_routing import solve as baseline_solve

    graph = build_hardware_graph()

    print(f"{'benchmark':15s}  {'baseline':>8s}  {'ours':>8s}  {'delta':>8s}")
    print("-" * 46)
    total_base = total_ours = 0.0
    for name, prog in BENCHMARKS.items():
        bl_pl, bl_rt = baseline_solve(prog, graph)
        bl = score_summary(prog, graph, bl_pl, bl_rt)

        my_pl, my_rt = solve(prog, graph)
        my = score_summary(prog, graph, my_pl, my_rt)

        delta = my["score"] - bl["score"]
        tag = "OK" if my["valid"] else my['message']
        print(f"{name:15s}  {bl['score']:8.1f}  {my['score']:8.1f}  {delta:+8.1f}  {tag}")
        total_base += bl["score"]
        total_ours += my["score"]

    print("-" * 46)
    print(f"{'TOTAL':15s}  {total_base:8.1f}  {total_ours:8.1f}  {total_ours - total_base:+8.1f}")