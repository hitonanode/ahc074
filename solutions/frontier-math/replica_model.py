#!/usr/bin/env python3
"""Exact toy model, not a full AHC074 solver or a measured contest score."""
from __future__ import annotations

import csv
import math
import sys


def replica_gain(n: int, gap: int, delta: float = 0.0) -> float:
    """Expected saving against the old representation, uniform circular cut."""
    return (gap * max(0.0, n-gap-delta)
            + (n-gap) * max(0.0, -gap-delta)) / n


def enumerate_gain(n: int, gap: int, delta: float = 0.0) -> float:
    return sum(max(0.0, ((-cut) % n) - ((gap-cut) % n) - delta)
               for cut in range(n)) / n


def best_replica(n: int, delta: float = 0.0) -> tuple[float, int]:
    return max((replica_gain(n, gap, delta), gap) for gap in range(1, n))


def independent_gain(n: int, delta: float = 0.0) -> float:
    """Two independent equal-length columns; useful comparison only."""
    return sum(max(0.0, a-b-delta)
               for a in range(n) for b in range(n)) / (n*n)


def stationary_column(n: int, promoted: bool, tail_rate: float) -> float:
    """Small illustrative chain with retrievals and alternating-color repairs.

    The first half of cards encode two targets; the rest encode one. A promoted
    singleton at n-2 also represents one target of the diametrically opposite
    paired card. All pair-specific costs are an assumed 2.6 moves. A retrieval
    rotates to one past the selected card; a color repair rotates to the first
    card of the desired color. This deliberately preserves circular order.
    """
    labels: list[list[tuple[int, float]]] = []
    ntargets = 0
    for card in range(n):
        count = 2 if card < n//2 else 1
        labels.append([(ntargets+j, 2.6 if count == 2 else 0.0)
                       for j in range(count)])
        ntargets += count
    if promoted:
        new_card = n-2
        old_card = (new_card-n//2) % n
        assert new_card % 2 == old_card % 2
        target = labels[old_card][0][0]
        labels[new_card][0] = (labels[new_card][0][0], 2.6)
        labels[new_card].append((target, 2.6))

    trans = [[0.0]*n for _ in range(n)]
    cost = [0.0]*n
    for cut in range(n):
        for target in range(ntargets):
            options = [(((card-cut) % n)+fee, (card+1) % n)
                       for card in range(n)
                       for t, fee in labels[card] if t == target]
            value, nxt = min(options)
            prob = (1-tail_rate)/ntargets
            trans[cut][nxt] += prob
            cost[cut] += prob*value
        for color in range(2):
            distance = next(d for d in range(n)
                            if ((cut+d) % n) % 2 == color)
            trans[cut][(cut+distance) % n] += tail_rate/2
            cost[cut] += tail_rate*distance/2
    pi = [1/n]*n
    for _ in range(10000):
        nxt = [sum(pi[i]*trans[i][j] for i in range(n)) for j in range(n)]
        if max(abs(x-y) for x, y in zip(pi, nxt)) < 1e-14:
            pi = nxt
            break
        pi = nxt
    else:
        raise RuntimeError("stationary iteration failed")
    return sum(p*c for p, c in zip(pi, cost))


def main() -> None:
    # Verify the derivation on all integer cuts, including negative offsets.
    for n in range(2, 33):
        for gap in range(1, n):
            for delta in [-5.5, -1.0, 0.0, 1.3, 2.6, 3.8, 7.0]:
                assert abs(replica_gain(n, gap, delta)
                           - enumerate_gain(n, gap, delta)) < 1e-10

    out = csv.writer(sys.stdout)
    out.writerow(["n", "extra_cost_b", "optimal_gap", "gain_b",
                  "independent_gain_b", "max_cost_a_for_promotion"])
    for n in [6, 8, 10, 12, 14, 16, 20]:
        for delta in [0.0, 1.0, 2.6, 3.8]:
            gain, gap = best_replica(n, delta)
            out.writerow([n, delta, gap, f"{gain:.6f}",
                          f"{independent_gain(n, delta):.6f}", f"{gain:.6f}"])
    print("\n# If delta_a = delta_b = delta >= 0, a continuous necessary condition is")
    print(f"# n > (3+2*sqrt(2))*delta = {3+2*math.sqrt(2):.9f}*delta.")
    print("# If b's old representation was already paired and delta_b ~ 0,")
    print("# the corresponding idealized condition is n > 4*delta_a.")
    print("\n# Synthetic stationary chain, not generated contest instances:")
    out.writerow(["n", "tail_event_probability", "base_cost_per_event",
                  "promoted_cost_per_event", "saving_per_target_event"])
    for n in [8, 12, 16]:
        for tail_rate in [0.0, 0.5, 0.8, 0.95]:
            base = stationary_column(n, False, tail_rate)
            new = stationary_column(n, True, tail_rate)
            out.writerow([n, tail_rate, f"{base:.9f}", f"{new:.9f}",
                          f"{(base-new)/(1-tail_rate):.9f}"])


if __name__ == "__main__":
    main()
