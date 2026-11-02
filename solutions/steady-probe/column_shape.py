"""The inside of the columns at the start of each request, versus the design model's assumptions
(the top two papers have both handle colors; the pairs, asked twice as often, on top): for the
designed order (r = 0) and the steady state (r >= 200).

usage: python3 solutions/steady-probe/column_shape.py RUN [NSEEDS]
"""
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay

M63 = (1 << 63) - 1


def main():
    run = replay.resolve_run(sys.argv[1])
    ns = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    acc = {name: defaultdict(float) for name in ("r=0", "r>=200")}
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
        H = len(hs)
        col = {k: max(c for c, h in enumerate(hs) if P[k].opaque >> h & 1) for k in ded}
        npair = {k: sum(1 for u in range(256) if ((A[u] ^ P[k].black) & P[k].opaque & M63) == 0) == 2 for k in ded}
        demand = [[0, 0] for _ in range(H)]
        for k in ded:
            for c in range(col[k] + 1, H):
                for u in range(256):
                    if ((A[u] ^ P[k].black) & P[k].opaque & M63) == 0: demand[c][A[u] >> hs[c] & 1] += 1
        g = replay.Game(inp, P)
        prevD = None
        for r, ops in enumerate(out.queries):
            key = "r=0" if r == 0 else "r>=200" if r >= 200 else None
            if key:
                a = acc[key]
                # in place papers per column, top to bottom (scan from the bottom: column <= least)
                least = H; inplace = []
                for k in reversed(g.order):
                    if k in col and k != prevD and col[k] <= least: least = col[k]; inplace.append(k)
                inplace.reverse()
                bycol = defaultdict(list)
                for k in inplace: bycol[col[k]].append(k)
                a["n_out"] += len(ded) - len(inplace) - (prevD is not None)
                for c, ks in bycol.items():
                    if len(ks) < 2: continue
                    colors = [P[k].black >> hs[c] & 1 for k in ks]
                    maj = int(demand[c][1] > demand[c][0])
                    a["cols"] += 1
                    a["top2_both"] += colors[0] != colors[1]
                    a["top_maj"] += colors[0] == maj
                    own_maj = int(sum(colors) * 2 > len(colors))
                    a["top_own_major"] += colors[0] == own_maj
                    # pairs: share among the top half vs the bottom half
                    half = len(ks) // 2
                    a["pairs_top"] += sum(npair[k] for k in ks[:half]) / max(half, 1)
                    a["pairs_bottom"] += sum(npair[k] for k in ks[half:]) / max(len(ks) - half, 1)
                a["states"] += 1
            for k, d in ops: g.move(k, d)
            g.finish(r)
            prevD = inp.requests[r]
            prevD = next(k for k in ded if ((A[prevD] ^ P[k].black) & P[k].opaque & M63) == 0)
    for name, a in acc.items():
        n = a["cols"]
        print(f"{name:7s} papers out {a['n_out'] / a['states']:.2f}; per column: top two of both colors {a['top2_both'] / n:.3f}, "
              f"top = demand majority {a['top_maj'] / n:.3f}, top = column's own majority {a['top_own_major'] / n:.3f}, "
              f"pair share top half {a['pairs_top'] / n:.3f} / bottom half {a['pairs_bottom'] / n:.3f}")


if __name__ == "__main__":
    main()
