"""Per target: the realized moves of its requests (without the generic sheets' moves) against a
reconstruction of the design model's terms: the digs (pairs first in their column, as W) and the
handle holes (0.8 times the share of the other color at each hole, persistence). Prints the mean
residual (realized - model terms) by column depth, by kind (single / pair), and by the mean share
of the other color over the target's holes.

usage: python3 solutions/steady-probe/target_resid.py RUN [NSEEDS]
"""
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay

M63 = (1 << 63) - 1
ROWS = []  # per target and case: realized moves, model digs, model holes, pair, holes, column, requests


def main():
    run = replay.resolve_run(sys.argv[1])
    ns = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    by = {k: defaultdict(lambda: [0.0, 0.0, 0]) for k in ("depth", "kind", "share", "holes")}
    tot = [0.0, 0.0, 0]
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
        users = defaultdict(list)
        for k in ded:
            for u in range(256):
                if ((A[u] ^ P[k].black) & P[k].opaque & M63) == 0: users[k].append(u)
        paper_of = {u: k for k, us in users.items() for u in us}
        demand = [[0, 0] for _ in range(H)]
        for u in range(256):
            for c, h in enumerate(hs):
                if not (P[paper_of[u]].opaque >> h & 1): demand[c][A[u] >> h & 1] += 1
        # model terms per target
        size = defaultdict(int); npairs = defaultdict(int)
        for k in ded:
            size[col[k]] += 1; npairs[col[k]] += len(users[k]) == 2
        model = {}
        for u in range(256):
            k = paper_of[u]; c = col[k]; pair = len(users[k]) == 2
            n, p = size[c], npairs[c]
            dig = (p - 1) / 2 if pair else p + (n - p - 1) / 2
            hole = 0.0; share = 0.0; nh = 0
            for cc, h in enumerate(hs):
                if P[k].opaque >> h & 1: continue
                d = demand[cc]; other = d[1 - (A[u] >> h & 1)] / max(sum(d), 1)
                hole += 0.8 * other; share += other; nh += 1
            model[u] = (dig, hole, c, pair, share / max(nh, 1), nh)
        moves = defaultdict(float); cnt = defaultdict(int)
        for r, ops in enumerate(out.queries):
            if r < 25: continue
            u = inp.requests[r]
            moves[u] += sum(1 for k, d in ops if k not in gen)
            cnt[u] += 1
        for u in range(256):
            if not cnt[u]: continue
            dig, hole, c, pair, share, nh = model[u]
            real = moves[u] / cnt[u]
            pred = dig + hole
            ROWS.append((real, dig, hole, int(pair), nh, c, cnt[u]))
            for key, val in (("depth", c // 5), ("kind", int(pair)), ("share", min(int(share * 10), 6)), ("holes", min(nh // 4, 6))):
                b = by[key][val]; b[0] += (real - pred) * cnt[u]; b[1] += real * cnt[u]; b[2] += cnt[u]
            tot[0] += (real - pred) * cnt[u]; tot[1] += real * cnt[u]; tot[2] += cnt[u]
    print(f"all: realized (without generic) {tot[1] / tot[2]:.3f}, mean residual {tot[0] / tot[2]:+.3f}")
    for key, label in (("depth", "column depth // 5"), ("kind", "pair"), ("share", "other-color share x10"), ("holes", "holes // 4")):
        print(label + ": " + "  ".join(f"{v}: {b[0] / b[2]:+.2f} (n {b[2] / tot[2]:.2f}, real {b[1] / b[2]:.2f})" for v, b in sorted(by[key].items())))


def regress():
    import numpy as np
    r = np.array(ROWS, float)
    w = r[:, 6]
    X = np.column_stack([np.ones(len(r)), r[:, 1], r[:, 2], r[:, 3]])
    W = np.sqrt(w)
    coef, *_ = np.linalg.lstsq(X * W[:, None], r[:, 0] * W, rcond=None)
    print("weighted fit real = a + b dig + c holes + d pair:", ", ".join(f"{n} {v:+.3f}" for n, v in zip(["a", "b", "c", "d"], coef)))
    X = np.column_stack([np.ones(len(r)), r[:, 1], r[:, 2], r[:, 3], r[:, 4]])
    coef, *_ = np.linalg.lstsq(X * W[:, None], r[:, 0] * W, rcond=None)
    print("  + number of holes:", ", ".join(f"{n} {v:+.3f}" for n, v in zip(["a", "dig", "hole", "pair", "nholes"], coef)))


if __name__ == "__main__":
    main()
    try:
        regress()
    except ImportError:
        pass
