from __future__ import annotations


def decompose(routed_circuit: list[tuple]) -> list[tuple]:
    """Deliberately wasteful native-gate baseline for stretch goal A.

    This assumes abstract `2Q` interactions are represented with a single `CNOT`
    placeholder in the teaching starter kit. `SWAP` is expanded into three CNOTs
    with redundant `RZ(0.0)` identities left in place.
    """
    decomposed: list[tuple] = []

    for op in routed_circuit:
        kind = op[0]
        if kind == "SWAP":
            _, left, right = op
            decomposed.extend(
                [
                    ("RZ", left, 0.0),
                    ("CNOT", left, right),
                    ("RZ", right, 0.0),
                    ("CNOT", right, left),
                    ("RZ", left, 0.0),
                    ("CNOT", left, right),
                    ("RZ", right, 0.0),
                ]
            )
        elif kind == "2Q":
            _, left, right = op
            decomposed.extend([("RZ", left, 0.0), ("CNOT", left, right), ("RZ", right, 0.0)])
        elif kind == "1Q":
            _, qubit = op
            decomposed.extend([("RZ", qubit, 0.0), ("SX", qubit), ("RZ", qubit, 0.0)])
        else:
            raise ValueError(f"Unknown operation kind: {kind}")

    return decomposed
