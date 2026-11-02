"""Regresses the moves of each request (steady state r >= 50) on features of the state at its start:
the papers blocking D at its handle, the handle mismatches under D (the color under D at its holes
differs from the request), whether D serves a pair, whether the previous paper is above D's handle
window... Prints the coefficients and the mean residual by column depth.

usage: python3 solutions/steady-probe/regress.py RUN [NSEEDS]
"""
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay

M63 = (1 << 63) - 1


def main():
    run = replay.resolve_run(sys.argv[1])
    ns = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    X, y, depth = [], [], []
    for s in range(ns):
        inp = replay.load_input(s); A = inp.target
        out = replay.parse_output(inp, (run / "out" / f"{s:04d}.txt").read_text())
        P = out.designs
        cap = next(k for k in range(192) if P[k].opaque == 1 << 63)
        gen = set(k for k in range(192) if k != cap and not (P[k].opaque >> 63 & 1))
        gm = 0
        for k in gen: gm |= P[k].opaque
        hm = M63 & ~gm
        hs = [w for w in range(64) if hm >> w & 1]
        ded = [k for k in range(192) if k != cap and k not in gen]
        hs.sort(key=lambda h: -sum(P[k].opaque >> h & 1 for k in ded))
        col = {k: max(c for c, h in enumerate(hs) if P[k].opaque >> h & 1) for k in ded}
        paper_of, users = {}, defaultdict(list)
        for k in ded:
            for u in range(256):
                if ((A[u] ^ P[k].black) & P[k].opaque & M63) == 0: paper_of[u] = k; users[k].append(u)
        g = replay.Game(inp, P)
        prevD = None
        for r, ops in enumerate(out.queries):
            u = inp.requests[r]; D = paper_of[u]; c = col[D]
            if r >= 50:
                i = g.order.index(D)
                above = [k for k in g.order[:i] if k not in gen and k != cap and k != prevD]
                block = sum(1 for k in above if P[k].opaque >> hs[c] & 1)
                mism = 0; holes = 0
                for cc, h in enumerate(hs):
                    if P[D].opaque >> h & 1: continue
                    holes += 1
                    for k in g.order:
                        if k in (prevD, D, cap) or k in gen: continue
                        if P[k].opaque >> h & 1:
                            mism += (P[k].black >> h & 1) != (A[u] >> h & 1); break
                pair = len(users[D]) == 2
                same = D == prevD  # the partner of the previous target
                X.append([1, block, mism, holes, pair, same])
                y.append(len(ops)); depth.append(c)
            for k, d in ops: g.move(k, d)
            g.finish(r)
            prevD = D
    X = np.array(X, float); y = np.array(y, float)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    names = ["const", "blockers", "mismatches", "holes", "pair", "same paper"]
    print("coefficients:", ", ".join(f"{n} {c:+.3f}" for n, c in zip(names, coef)))
    print("means:", ", ".join(f"{n} {m:.3f}" for n, m in zip(names, X.mean(0))), f"moves {y.mean():.3f}")
    res = y - X @ coef
    depth = np.array(depth)
    print("residual by depth:", " ".join(f"{c}:{res[depth == c].mean():+.2f}" for c in range(depth.max() + 1)))
    print(f"R^2 {1 - res.var() / y.var():.3f}")


if __name__ == "__main__":
    main()
