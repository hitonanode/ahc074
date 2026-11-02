"""Moves per request by role, for pair targets and single targets, by depth group of D's column
(steady state r >= 50). Roles: lift (D), dig (papers of D's column in place moved before D is lifted),
generic, cap, prevD (the previous request's paper), out (papers out of their column at the start:
fillers), other (papers of other columns in place: handle fixes and new fillers).

usage: python3 solutions/steady-probe/pair_roles.py RUN [NSEEDS]
"""
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay

M63 = (1 << 63) - 1
ROLES = ["lift", "dig", "generic", "prevD", "out", "other"]


def main():
    run = replay.resolve_run(sys.argv[1])
    ns = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    acc = defaultdict(lambda: defaultdict(float)); n = defaultdict(int)
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
        g = replay.Game(inp, P)
        prevD = None
        for r, ops in enumerate(out.queries):
            u = inp.requests[r]; D = paper_of[u]; c = col[D]
            if r >= 50 and D != prevD:
                least = H; inplace = set()
                for k in reversed(g.order):
                    if k in col and k != prevD and col[k] <= least: least = col[k]; inplace.add(k)
                key = ("pair" if len(users[D]) == 2 else "single", c // 9)
                n[key] += 1
                lifted = False
                for k, d in ops:
                    if k == D: role = "lift"; lifted = True
                    elif k in gen or k == cap: role = "generic"
                    elif k == prevD: role = "prevD"
                    elif k not in inplace: role = "out"
                    elif not lifted and col[k] == c: role = "dig"
                    else: role = "other"
                    acc[key][role] += 1
            for k, d in ops: g.move(k, d)
            g.finish(r)
            prevD = D
    print("kind    depth  share   " + " ".join(f"{x:>7s}" for x in ROLES) + "   total")
    for key in sorted(n):
        m = n[key]
        print(f"{key[0]:6s} {key[1] * 9:2d}-{key[1] * 9 + 8:2d} {m / sum(n.values()):6.3f}  " + " ".join(f"{acc[key][x] / m:7.2f}" for x in ROLES) + f"  {sum(acc[key].values()) / m:6.2f}")


if __name__ == "__main__":
    main()
