from __future__ import annotations

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.animation import FuncAnimation

from .hardware import HARDWARE_POSITIONS, build_hardware_graph


def draw_hardware(
    graph: nx.Graph | None = None,
    placement: dict[int, int] | None = None,
    highlight_edges: list[tuple[int, int]] | None = None,
    ax=None,
    title: str | None = None,
):
    graph = graph or build_hardware_graph()
    ax = ax or plt.gca()
    highlight_edges = highlight_edges or []

    nx.draw_networkx_edges(graph, HARDWARE_POSITIONS, ax=ax, edge_color="#94a3b8", width=1.8)
    if highlight_edges:
        nx.draw_networkx_edges(
            graph,
            HARDWARE_POSITIONS,
            ax=ax,
            edgelist=highlight_edges,
            edge_color="#dc2626",
            width=3.5,
        )
    nx.draw_networkx_nodes(graph, HARDWARE_POSITIONS, ax=ax, node_color="#e2e8f0", node_size=820)
    nx.draw_networkx_labels(graph, HARDWARE_POSITIONS, ax=ax, labels={node: str(node) for node in graph.nodes}, font_size=9)

    if placement:
        for logical, physical in placement.items():
            x, y = HARDWARE_POSITIONS[physical]
            ax.text(x, y + 0.22, f"L{logical}", ha="center", va="center", fontsize=11, color="#b91c1c", fontweight="bold")

    ax.set_axis_off()
    if title:
        ax.set_title(title)
    return ax


def animate_placements(
    frames: list[dict[int, int]],
    highlight_edges: list[tuple[int, int]] | None = None,
    title_prefix: str = "Routing frame",
    interval: int = 700,
):
    graph = build_hardware_graph()
    fig, ax = plt.subplots(figsize=(5.5, 5.5))

    def _update(index: int):
        ax.clear()
        draw_hardware(
            graph=graph,
            placement=frames[index],
            highlight_edges=highlight_edges,
            ax=ax,
            title=f"{title_prefix} {index}",
        )
        return ax.collections + ax.lines + ax.texts

    return FuncAnimation(fig, _update, frames=len(frames), interval=interval, blit=False)


def animate_layers(layers: list[list[tuple]], interval: int = 900):
    graph = build_hardware_graph()
    fig, ax = plt.subplots(figsize=(5.5, 5.5))

    def _update(index: int):
        ax.clear()
        highlight_edges = [tuple(op[1:]) for op in layers[index]]
        draw_hardware(graph=graph, highlight_edges=highlight_edges, ax=ax, title=f"Layer {index + 1}")
        return ax.collections + ax.lines + ax.texts

    return FuncAnimation(fig, _update, frames=len(layers), interval=interval, blit=False)
