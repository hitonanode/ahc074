"""Frequencies of two situations the solver may handle with stale rules (as6-majtop outputs, r >= 50):
(a) a hole of D at h_c asks for a color that no paper of column c in place has;
(b) a dedicated paper lies between generic sheets at the start of the request (split generic layer),
    split by whether D has a hole on a generic window.

usage: python3 solutions/steady-probe/stale_freq.py RUN [NSEEDS]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay

M63 = (1 << 63) - 1


def main():
    run = replay.resolve_run(sys.argv[1])
    ns = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    n = absent = holes = split = split_ghole = ghole = 0
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
        paper_of = {}
        for k in ded:
            for u in range(256):
                if ((A[u] ^ P[k].black) & P[k].opaque & M63) == 0: paper_of[u] = k
        g = replay.Game(inp, P)
        prevD = None
        for r, ops in enumerate(out.queries):
            u = inp.requests[r]; D = paper_of[u]
            if r >= 50:
                n += 1
                order = g.order
                least = H; inplace = set()
                for k in reversed(order):
                    if k in col and k not in (prevD, D) and col[k] <= least: least = col[k]; inplace.add(k)
                for c, h in enumerate(hs):
                    if P[D].opaque >> h & 1: continue
                    holes += 1
                    need = A[u] >> h & 1
                    if not any(col[k] == c and (P[k].black >> h & 1) == need for k in inplace): absent += 1
                gpos = [order.index(k) for k in gen]
                inside = any(order[i] not in gen and order[i] != cap for i in range(min(gpos), max(gpos)))
                gh = bool(gm & ~P[D].opaque)
                ghole += gh
                if inside: split += 1; split_ghole += gh
            for k, d in ops: g.move(k, d)
            g.finish(r)
            prevD = D
    print(f"requests {n}: holes/request {holes / n:.2f}, holes asking for a color absent from the column {absent / n:.3f}/request")
    print(f"split generic layer at the start: {split / n:.4f} of the requests ({split_ghole / n:.4f} with a generic hole in D; D has generic holes in {ghole / n:.3f})")


if __name__ == "__main__":
    main()
