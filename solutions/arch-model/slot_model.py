#!/usr/bin/env python3
"""Slot model of the hub family (column tops visible at single handle windows, triangle holes).

A target whose paper is in column l (0 = shallowest of H) costs per request
    dig  = (c_l - 1) / 2          (rotation of its column, c_l papers)
    tri  = hole * (H - 1 - l)      (one random-color hole per deeper column)
Pairs (2 targets per paper) count twice. For given numbers of single and pair papers, the column
sizes and the split of pairs/singles over columns are optimized greedily (marginal cost).
Prints the optimum per H. Also the 'flat' variant (no return, holes at all H-1 other handles).
"""
import sys

def best_alloc(H, n_single, n_pair, hole=0.5):
    # Greedy: add papers one by one (pairs first, they are the most frequent) to the column with the
    # smallest marginal increase of the total cost sum_l T_l * ((c_l-1)/2 + hole*(H-1-l)).
    c = [0] * H
    T = [0] * H
    total = 0.0
    def colcost(l, cl, Tl):
        return Tl * ((cl - 1) / 2 + hole * (H - 1 - l)) if cl > 0 else 0.0
    for t in [2] * n_pair + [1] * n_single:
        best = None
        for l in range(H):
            d = colcost(l, c[l] + 1, T[l] + t) - colcost(l, c[l], T[l])
            if best is None or d < best[0]:
                best = (d, l)
        d, l = best
        c[l] += 1
        T[l] += t
        total += d
    ntar = 2 * n_pair + n_single
    dig = sum(T[l] * (c[l] - 1) / 2 for l in range(H) if c[l]) / ntar
    tri = sum(T[l] * (H - 1 - l) for l in range(H)) / ntar
    return total / ntar, dig, tri, c

if __name__ == "__main__":
    n_single = int(sys.argv[1]) if len(sys.argv) > 1 else 112
    n_pair = int(sys.argv[2]) if len(sys.argv) > 2 else 72
    hole = float(sys.argv[3]) if len(sys.argv) > 3 else 0.48
    print(f"singles {n_single}, pairs {n_pair}, cost per hole {hole}")
    for H in [8, 12, 16, 20, 24, 28, 32, 36, 40, 48]:
        cost, dig, tri, c = best_alloc(H, n_single, n_pair, hole)
        print(f"H={H:2d}  dig+holes={cost:6.3f}  dig={dig:5.2f}  triangle holes={tri:5.2f}  sizes={c}")
    # Flat: holes at all other handles, no return (saves 1 move per request).
    print("flat (no return, H-1 holes):")
    for H in [8, 10, 12, 14, 16, 20]:
        n = n_single + n_pair
        ntar = n_single + 2 * n_pair
        c = n / H
        cost = (c - 1) / 2 + hole * (H - 1) - 1.0
        print(f"H={H:2d}  dig+holes-1={cost:6.3f}")
