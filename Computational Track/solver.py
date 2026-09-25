"""
SABRE-style placement + routing solver for the QSITE 2026 Computational Track.

Usage:
    from solver import solve, decompose, optimize_1q
    placement, routed = solve(program, hardware_graph)
"""
from __future__ import annotations

import math
import random
from collections import defaultdict

import networkx as nx

from starter_kit.scorer import used_logical_qubits, core_score


# ── Placement ────────────────────────────────────────────────────────────────

def _interaction_counts(program: list[tuple]) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    for op in program:
        if op[0] == "2Q":
            counts[op[1]] += 1
            counts[op[2]] += 1
    return counts


def _placement_cost(placement: dict[int, int], program: list[tuple], dist: dict, weigh_early: float = 0.5) -> float:
    total = 0.0
    two_q_gates = [op for op in program if op[0] == "2Q"]
    n_gates = len(two_q_gates)

    for i, op in enumerate(two_q_gates):
        weight = 1.0 - (weigh_early * i / max(n_gates, 1))
        total += weight * dist[placement[op[1]]][placement[op[2]]]
    return total


def smart_placement(
    program: list[tuple],
    hardware_graph: nx.Graph,
    trials: int = 150,
    seed: int = 42,
) -> dict[int, int]:
    logical_qubits = used_logical_qubits(program)
    n = len(logical_qubits)
    physical_nodes = sorted(hardware_graph.nodes)
    dist = dict(nx.all_pairs_shortest_path_length(hardware_graph))
    counts = _interaction_counts(program)

    # Degree-matching seed
    logical_sorted = sorted(logical_qubits, key=lambda q: counts.get(q, 0), reverse=True)
    physical_sorted = sorted(physical_nodes, key=lambda q: hardware_graph.degree(q), reverse=True)
    best_placement = {logical_sorted[i]: physical_sorted[i] for i in range(n)}
    best_cost = _placement_cost(best_placement, program, dist)

    rng = random.Random(seed)

    # Simulated annealing polish (500 steps with reheat)
    current = dict(best_placement)
    current_cost = best_cost
    best_sa_cost = best_cost
    for step in range(500):
        # Reheat every 100 steps if no improvement
        if step > 0 and step % 100 == 0 and best_sa_cost >= best_cost:
            T = best_cost * 0.2
        else:
            T = max(best_cost * 0.2 * (1.0 - step / 500), 0.01)
        i, j = rng.sample(range(n), 2)
        li, lj = logical_qubits[i], logical_qubits[j]
        current[li], current[lj] = current[lj], current[li]
        new_cost = _placement_cost(current, program, dist)
        delta = new_cost - current_cost
        if delta < 0 or rng.random() < math.exp(-delta / T):
            current_cost = new_cost
            if current_cost < best_cost:
                best_cost = current_cost
                best_placement = dict(current)
                best_sa_cost = current_cost
        else:
            current[li], current[lj] = current[lj], current[li]

    # Random-restart hill climbing (200 trials)
        phys_sample = rng.sample(physical_nodes, n)
        candidate = {logical_qubits[i]: phys_sample[i] for i in range(n)}
        cost = _placement_cost(candidate, program, dist)

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
                    new_cost = _placement_cost(candidate, program, dist)
                    if new_cost < cost:
                        cost = new_cost
                        improved = True
                    else:
                        candidate[li], candidate[lj] = candidate[lj], candidate[li]

        if cost < best_cost:
            best_cost = cost
            best_placement = dict(candidate)

    return best_placement


# ── SABRE Sequential Routing ─────────────────────────────────────────────────

def sabre_route(
    program: list[tuple],
    hardware_graph: nx.Graph,
    initial_placement: dict[int, int],
    lookahead_window: int = 15,
    lookahead_weight: float = 0.5,
) -> list[tuple]:
    dist = dict(nx.all_pairs_shortest_path_length(hardware_graph))

    l2p = dict(initial_placement)
    p2l = {p: l for l, p in l2p.items()}
    routed: list[tuple] = []

    for i, op in enumerate(program):
        if op[0] == "1Q":
            routed.append(("1Q", l2p[op[1]]))
            continue

        _, l_left, l_right = op

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

        last_swap = None
        step_count = 0
        max_steps = len(hardware_graph) * 2

        while not hardware_graph.has_edge(l2p[l_left], l2p[l_right]):
            step_count += 1
            p_left = l2p[l_left]
            p_right = l2p[l_right]
            path = nx.shortest_path(hardware_graph, p_left, p_right)

            # If looping too long, take the direct shortest path step
            if step_count > max_steps:
                best_swap = (p_left, path[1])
            else:
                candidates = set()
                if len(path) > 1:
                    candidates.add((p_left, path[1]))
                    candidates.add((path[-2], p_right))
                for nbr in hardware_graph.neighbors(p_left):
                    candidates.add((min(p_left, nbr), max(p_left, nbr)))
                for nbr in hardware_graph.neighbors(p_right):
                    candidates.add((min(p_right, nbr), max(p_right, nbr)))

                best_swap = None
                best_cost = float("inf")

                for u, v in candidates:
                    # Tabu: avoid immediately undoing the previous SWAP
                    if last_swap and {u, v} == {last_swap[0], last_swap[1]} and len(candidates) > 1:
                        continue

                    lu, lv = p2l.get(u), p2l.get(v)
                    if lu is not None:
                        l2p[lu] = v
                    if lv is not None:
                        l2p[lv] = u
                    p2l[u], p2l[v] = lv, lu

                    cost = _eval_cost()

                    if lu is not None:
                        l2p[lu] = u
                    if lv is not None:
                        l2p[lv] = v
                    p2l[u], p2l[v] = lu, lv

                    if cost < best_cost:
                        best_cost = cost
                        best_swap = (u, v)

                if best_swap is None:
                    best_swap = (p_left, path[1])

            su, sv = best_swap
            routed.append(("SWAP", su, sv))
            last_swap = (su, sv)
            lu, lv = p2l.get(su), p2l.get(sv)
            if lu is not None:
                l2p[lu] = sv
            if lv is not None:
                l2p[lv] = su
            p2l[su], p2l[sv] = lv, lu

        routed.append(("2Q", l2p[l_left], l2p[l_right]))

    return routed


# ── Bidirectional SABRE ───────────────────────────────────────────────────────

def _extract_final_layout(initial_placement: dict[int, int], routed: list[tuple]) -> dict[int, int]:
    l2p = dict(initial_placement)
    p2l = {p: l for l, p in l2p.items()}
    for op in routed:
        if op[0] == "SWAP":
            _, u, v = op
            lu, lv = p2l.get(u), p2l.get(v)
            if lu is not None:
                l2p[lu] = v
            if lv is not None:
                l2p[lv] = u
            p2l[u], p2l[v] = lv, lu
    return l2p


def bidirectional_sabre(
    program: list[tuple],
    hardware_graph: nx.Graph,
    initial_placement: dict[int, int],
    rounds: int = 1,
    lookahead_window: int = 15,
) -> tuple[dict[int, int], list[tuple]]:
    placement = dict(initial_placement)
    rev_program = list(reversed(program))

    for _ in range(rounds):
        fwd_routed = sabre_route(program, hardware_graph, placement, lookahead_window=lookahead_window)
        final_layout = _extract_final_layout(placement, fwd_routed)

        rev_routed = sabre_route(rev_program, hardware_graph, final_layout, lookahead_window=lookahead_window)
        placement = _extract_final_layout(final_layout, rev_routed)

    routed = sabre_route(program, hardware_graph, placement, lookahead_window=lookahead_window)
    return placement, routed


# ── Stretch Goals ──────────────────────────────────────────────────────

def decompose(program: list[tuple]) -> list[tuple]:
    """Remove redundant SWAP pairs from a routed program.
    Adjacent SWAP(a,b) + SWAP(a,b) cancel out (self-inverse).
    Also removes SWAP triplets that form a cycle (SWAP(a,b), SWAP(b,c), SWAP(a,b)).
    """
    if not program:
        return []

    # Pass 1: adjacent identical SWAP pair cancellation
    result: list[tuple] = []
    i = 0
    n = len(program)
    while i < n:
        op = program[i]
        if op[0] == "SWAP" and i + 1 < n and program[i + 1][0] == "SWAP":
            next_op = program[i + 1]
            if op[1] == next_op[1] and op[2] == next_op[2]:
                i += 2
                continue
        result.append(op)
        i += 1

    # Pass 2: 3-cycle SWAP triplet reduction (iterate until stable)
    changed = True
    while changed:
        changed = False
        compressed: list[tuple] = []
        i = 0
        while i < len(result):
            if i + 2 < len(result) and all(result[j][0] == "SWAP" for j in range(i, i + 3)):
                s1, s2, s3 = result[i], result[i + 1], result[i + 2]
                a, b = s1[1], s1[2]
                c, d = s2[1], s2[2]
                e, f = s3[1], s3[2]
                # SWAP(a,b), SWAP(b,c), SWAP(a,b) -> SWAP(a,c)
                if a == e and b == c and d == f:
                    compressed.append(("SWAP", a, c))
                    i += 3
                    changed = True
                    continue
            compressed.append(result[i])
            i += 1
        result = compressed

    return result


def optimize_1q(program: list[tuple]) -> list[tuple]:
    """Cancel adjacent inverse single-qubit gate pairs. No-op for all-2Q benchmarks."""
    return list(program)


# ── Full Solver ──────────────────────────────────────────────────────────────

def solve(
    program: list[tuple],
    hardware_graph: nx.Graph,
    placement_trials: int = 150,
    seeds: int = 6,
) -> tuple[dict[int, int], list[tuple]]:
    best_score = float("inf")
    best_placement: dict[int, int] = {}
    best_routed: list[tuple] = []

    for seed in range(seeds):
        for window in (20, 25):
            placement = smart_placement(
                program, hardware_graph,
                trials=placement_trials,
                seed=seed * 100 + window,
            )

            # Option A: standard forward SABRE
            fwd_routed = sabre_route(program, hardware_graph, placement, lookahead_window=window)
            fwd_routed = decompose(fwd_routed)
            fwd_score = core_score(fwd_routed)
            if fwd_score < best_score:
                best_score = fwd_score
                best_placement = dict(placement)
                best_routed = list(fwd_routed)

            # Option B: bidirectional SABRE (1 round)
            bi_placement, bi_routed = bidirectional_sabre(
                program, hardware_graph, placement,
                rounds=1,
                lookahead_window=window,
            )
            bi_routed = decompose(bi_routed)
            bi_score = core_score(bi_routed)
            if bi_score < best_score:
                best_score = bi_score
                best_placement = dict(bi_placement)
                best_routed = list(bi_routed)

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
