"""Per handle: the minority share m of the hole demand, and the realized rate at which the color
under the lifted paper (the first opaque paper at the handle, without the previous paper and the
requested one) differs from the request, at the start of each request (steady state r >= 50).
Compares with the design model (persistence: 2m(1-m)) and a reset-to-majority policy (m).

usage: python3 solutions/steady-probe/mismatch_rate.py RUN [NSEEDS]
"""
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay

M63 = (1 << 63) - 1


def case(run, s, acc):
    inp = replay.load_input(s); A = inp.target
    out = replay.parse_output(inp, (run / "out" / f"{s:04d}.txt").read_text())
    P = out.designs
    cap = next(k for k in range(192) if P[k].opaque == 1 << 63)
    gen = [k for k in range(192) if k != cap and not (P[k].opaque >> 63 & 1)]
    gm = 0
    for k in gen: gm |= P[k].opaque
    hm = M63 & ~gm
    hs = [w for w in range(64) if hm >> w & 1]
    ded = [k for k in range(192) if k != cap and k not in gen]
    hs.sort(key=lambda h: -sum(P[k].opaque >> h & 1 for k in ded))
    paper_of = {}
    for k in ded:
        for u in range(256):
            if ((A[u] ^ P[k].black) & P[k].opaque & M63) == 0: paper_of[u] = k
    demand = [[0, 0] for _ in hs]
    for u in range(256):
        for c, h in enumerate(hs):
            if not (P[paper_of[u]].opaque >> h & 1): demand[c][A[u] >> h & 1] += 1
    g = replay.Game(inp, P)
    prevD = None
    for r, ops in enumerate(out.queries):
        u = inp.requests[r]; D = paper_of[u]
        if r >= 50:
            for c, h in enumerate(hs):
                if P[D].opaque >> h & 1: continue
                shown = None
                for k in g.order:
                    if k in (prevD, D, cap) or k in gen: continue
                    if P[k].opaque >> h & 1: shown = P[k].black >> h & 1; break
                n = sum(demand[c]); m = min(demand[c]) / n
                a = acc[c]
                a["n"] += 1; a["m"] += m; a["bad"] += shown != (A[u] >> h & 1)
                # also: is the request color the majority?
                a["minreq"] += (A[u] >> h & 1) != int(demand[c][1] > demand[c][0])
        for k, d in ops: g.move(k, d)
        g.finish(r)
        prevD = D


def main():
    run = replay.resolve_run(sys.argv[1])
    ns = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    acc = defaultdict(lambda: defaultdict(float))
    for s in range(ns): case(run, s, acc)
    print("handle  holes/req  m(demand)  P(min req)  realized  2m(1-m)")
    tot = defaultdict(float)
    for c in sorted(acc):
        a = acc[c]; n = a["n"]; m = a["m"] / n
        print(f"{c:4d} {n / (ns * 974):9.3f} {m:9.3f} {a['minreq'] / n:9.3f} {a['bad'] / n:9.3f} {2 * m * (1 - m):9.3f}")
        tot["n"] += n; tot["bad"] += a["bad"]; tot["pers"] += n * 2 * m * (1 - m); tot["m"] += n * m
    N = ns * 974
    print(f"per request: holes {tot['n'] / N:.2f}, realized mismatches {tot['bad'] / N:.2f}, "
          f"persistence model {tot['pers'] / N:.2f}, reset-to-majority {tot['m'] / N:.2f}")


if __name__ == "__main__":
    main()
