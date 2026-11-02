"""Characterizes the stack at the start of each request (as6-cap38p0 outputs): papers out of their
columns, column tops, and the moves by role, for the first requests and for the steady state.

usage: python3 solutions/steady-probe/state_stats.py RUN [SEEDS]
"""
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay

M63 = (1 << 63) - 1


def analyse_case(run, s):
    inp = replay.load_input(s); A = inp.target
    out = replay.parse_output(inp, (run / "out" / f"{s:04d}.txt").read_text())
    P = out.designs
    # the cap is opaque on window 63 only; the generic sheets are the papers with a hole on window 63
    # (every dedicated paper is opaque there)
    cap = next(k for k in range(192) if P[k].opaque == 1 << 63)
    gen = [k for k in range(192) if k != cap and P[k].opaque >> 63 & 1 == 0]
    gm = 0
    for k in gen: gm |= P[k].opaque
    hm = M63 & ~gm
    hs = [w for w in range(64) if hm >> w & 1]
    ded = [k for k in range(192) if k != cap and k not in gen]
    hs.sort(key=lambda h: -sum(P[k].opaque >> h & 1 for k in ded))
    H = len(hs)
    # column of a paper: its deepest opaque handle (a pair paper also has holes at its differences)
    col = {k: max(c for c, h in enumerate(hs) if P[k].opaque >> h & 1) for k in ded}
    paper_of, users = {}, defaultdict(list)
    for k in ded:
        for u in range(256):
            if ((A[u] ^ P[k].black) & P[k].opaque & M63) == 0: paper_of[u] = k; users[k].append(u)
    # share of the targets with a hole of each color at h_c (the demand at the handle)
    demand = [[0, 0] for _ in range(H)]
    for u in range(256):
        k = paper_of[u]
        for c, h in enumerate(hs):
            if not (P[k].opaque >> h & 1): demand[c][A[u] >> h & 1] += 1
    g = replay.Game(inp, P)
    rows = []
    prevD = None
    for r, ops in enumerate(out.queries):
        order = g.order
        # papers out of their column: scanning from the bottom, a dedicated paper is in place when its
        # column is <= the least column seen below it
        least = H; out_papers = []
        for k in reversed(order):
            if k not in col: continue
            if col[k] <= least: least = col[k]
            elif k != prevD: out_papers.append(k)
        # column tops (in place papers only) and whether they show the majority hole color
        top_of = {}
        outset = set(out_papers) | ({prevD} if prevD is not None else set())
        for k in order:
            if k in col and k not in outset and col[k] not in top_of: top_of[col[k]] = k
        maj_ok = 0; maj_n = 0
        for c in range(H):
            if c in top_of and sum(demand[c]):
                maj = int(demand[c][1] > demand[c][0])
                maj_n += 1; maj_ok += (P[top_of[c]].black >> hs[c] & 1) == maj
        # where the out papers are: depth below the generic layer bottom
        gbottom = max(order.index(k) for k in gen)
        just_below = sum(1 for k in out_papers if order.index(k) > gbottom and order.index(k) <= gbottom + 4)
        D = paper_of[inp.requests[r]]
        roles = defaultdict(int); lifted = False
        for k, d in ops:
            if k == D: roles["lift"] += 1; lifted = True
            elif k in gen: roles["generic"] += 1
            elif k == cap: roles["cap"] += 1
            elif k == prevD: roles["prevD"] += 1
            elif not lifted and col.get(k) == col[D] and k not in outset: roles["dig"] += 1
            elif k in outset: roles["out_paper"] += 1
            else: roles["other_col"] += 1
        rows.append(dict(r=r, n_out=len(out_papers), just_below=just_below, maj=maj_ok / max(maj_n, 1),
                         d_out=D in outset, moves=len(ops), **roles))
        for k, d in ops: g.move(k, d)
        g.finish(r)
        prevD = D
    return rows


def main():
    run = replay.resolve_run(sys.argv[1])
    seeds = range(int(sys.argv[2])) if len(sys.argv) > 2 else range(40)
    allrows = [analyse_case(run, s) for s in seeds]
    keys = ["moves", "lift", "dig", "generic", "prevD", "out_paper", "other_col", "cap"]
    print("range       n_out  justbelow  top=maj  D_out  " + " ".join(f"{k:>9s}" for k in keys))
    for a, b in [(0, 1), (1, 2), (2, 5), (5, 12), (12, 25), (25, 50), (200, 1024)]:
        sel = [row for rows in allrows for row in rows[a:b]]
        n = len(sel)
        f = lambda key: sum(row.get(key, 0) for row in sel) / n
        print(f"{a:4d}-{b:4d}  {f('n_out'):6.2f} {f('just_below'):9.2f} {f('maj'):8.3f} {f('d_out'):6.3f}  "
              + " ".join(f"{f(k):9.3f}" for k in keys))


if __name__ == "__main__":
    main()
