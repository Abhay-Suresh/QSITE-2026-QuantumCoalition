"""Starter-kit utilities for the computational track."""

from .baseline_decompose import decompose as baseline_decompose
from .baseline_oneq import optimize_1q as baseline_optimize_1q
from .baseline_routing import solve as baseline_solve
from .benchmarks import BENCHMARKS, benchmark_stats
from .hardware import HARDWARE_EDGES, HARDWARE_POSITIONS, build_hardware_graph
from .scorer import core_score, score_summary, schedule_layers_ordered, validate_routed_program

__all__ = [
    "BENCHMARKS",
    "HARDWARE_EDGES",
    "HARDWARE_POSITIONS",
    "baseline_decompose",
    "baseline_optimize_1q",
    "baseline_solve",
    "benchmark_stats",
    "build_hardware_graph",
    "core_score",
    "schedule_layers_ordered",
    "score_summary",
    "validate_routed_program",
]
