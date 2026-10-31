#!/usr/bin/env python3
"""Slot model with pair diffs: a pair paper in column l pays its diff windows that fall on shallow
handles (0.48 each) and on G windows (cG each); diffs on deeper handles are free (already holes).
Diffs are spread uniformly over the 64 windows (d per pair). G = 64 - H windows."""
import sys
def run(H, ns, npair, d=18.0, hole=0.48, cG=0.2):
    G = 64 - H
    c = [0] * H; T = [0] * H; X = [0.0] * H  # X: extra (diff) cost summed over targets
    def cost(l, cl, Tl, Xl):
        return (Tl * ((cl - 1) / 2 + hole * (H - 1 - l)) + Xl) if cl > 0 else 0.0
    def pair_extra(l):  # per target
        return d / 64 * (hole * l + cG * G)
    for t in [2] * npair + [1] * ns:
        best = None
        for l in range(H):
            x = t * pair_extra(l) if t == 2 else 0.0
            dd = cost(l, c[l] + 1, T[l] + t, X[l] + x) - cost(l, c[l], T[l], X[l])
            if best is None or dd < best[0]: best = (dd, l, x)
        _, l, x = best
        c[l] += 1; T[l] += t; X[l] += x
    ntar = ns + 2 * npair
    tot = sum(cost(l, c[l], T[l], X[l]) for l in range(H)) / ntar
    return tot, sum(X) / ntar
if __name__ == "__main__":
    for H in [20, 24, 28, 32, 36, 40]:
        G = 64 - H
        blocks = max(1, G // 5)
        ns = 192 - (blocks + 1) - 70
        tot, x = run(H, ns, 70)
        print(f"H={H} G={G} dig+holes+diffs={tot:.3f} (pair diff part {x:.3f})")
