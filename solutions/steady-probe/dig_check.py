"""For each request: the papers above the requested paper D that block it at its handle (opaque
there; the generic sheets, the cap and the previous paper excluded), and the moves of papers of D's
column before D is lifted. By column depth, steady state (r >= 50).

usage: python3 solutions/steady-probe/dig_check.py RUN [NSEEDS]
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
    acc = defaultdict(lambda: defaultdict(float))
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
        size = defaultdict(int)
        for k in ded: size[col[k]] += 1
        paper_of = {}
        for k in ded:
            for u in range(256):
                if ((A[u] ^ P[k].black) & P[k].opaque & M63) == 0: paper_of[u] = k
        g = replay.Game(inp, P)
        prevD = None
        for r, ops in enumerate(out.queries):
            D = paper_of[inp.requests[r]]; c = col[D]
            if r >= 50 and D != prevD:
                h = hs[c]
                i = g.order.index(D)
                above = [k for k in g.order[:i] if k not in gen and k != cap and k != prevD]
                block_h = sum(1 for k in above if P[k].opaque >> h & 1)
                same_col = sum(1 for k in above if col[k] == c)
                # the fewest blockers over D's opaque windows (D is visible once one window is free)
                least = min(sum(1 for k in g.order[:i] if k != prevD and P[k].opaque >> w & 1)
                            for w in range(64) if P[D].opaque >> w & 1)
                lifted = False; dig = 0
                for k, d in ops:
                    if k == D: lifted = True
                    elif not lifted and k != prevD and k not in gen and k != cap: dig += 1
                a = acc[c]
                a["n"] += 1; a["block_h"] += block_h; a["same_col"] += same_col; a["least"] += least
                a["moved_before_lift"] += dig; a["size"] += size[c]
            for k, d in ops: g.move(k, d)
            g.finish(r)
            prevD = D
    print("depth  size  blockers@h  same-col-above  least-blockers  moved-before-lift")
    for c in sorted(acc):
        a = acc[c]; n = a["n"]
        print(f"{c:4d} {a['size']/n:5.1f} {a['block_h']/n:10.2f} {a['same_col']/n:14.2f} {a['least']/n:14.2f} {a['moved_before_lift']/n:16.2f}")
    n = sum(a["n"] for a in acc.values())
    print("all", *(f"{k} {sum(a[k] for a in acc.values())/n:.2f}" for k in ["block_h", "same_col", "least", "moved_before_lift"]))


if __name__ == "__main__":
    main()
