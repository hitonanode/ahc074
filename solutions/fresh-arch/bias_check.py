import sys
sys.path.insert(0, "/home/sato/ahc074/.claude/worktrees/clean-base-optimization-1b199f/scripts")
import replay
run = replay.resolve_run("20261102-175341_as6-cap38p0")
M63 = (1 << 63) - 1
per = {}; T = {"tri": 0, "pdtri": 0, "pdshallow": 0}; ntgt = 0
for s in range(40):
    inp = replay.load_input(s); A = inp.target
    P = replay.parse_output(inp, (run / "out" / f"{s:04d}.txt").read_text()).designs
    gm = 0
    for k in range(1, 7): gm |= P[k].opaque
    hm = M63 & ~gm
    hs = [w for w in range(64) if hm >> w & 1]
    # handle order: shallow handles are opaque in more papers
    hs.sort(key=lambda h: -sum(P[k].opaque >> h & 1 for k in range(7, 192)))
    pos = {h: i for i, h in enumerate(hs)}
    allc = {h: [0, 0] for h in hs}; agree = {h: [0, 0] for h in hs}; pdn = {h: 0 for h in hs}
    for k in range(7, 192):
        us = [u for u in range(256) if ((A[u] ^ P[k].black) & P[k].opaque & M63) == 0]
        diff = (A[us[0]] ^ A[us[1]]) if len(us) == 2 else 0
        col = max([pos[h] for h in hs if P[k].opaque >> h & 1], default=-1)
        for u in us:
            ntgt += 1
            for h in hs:
                if P[k].opaque >> h & 1: continue
                c = A[u] >> h & 1
                allc[h][c] += 1
                if diff >> h & 1:
                    pdn[h] += 1
                    T["pdtri" if pos[h] > col else "pdshallow"] += 1
                else:
                    agree[h][c] += 1; T["tri"] += 1
    for h in hs:
        per.setdefault(pos[h], []).append((sum(allc[h]), min(allc[h]), sum(agree[h]), min(agree[h]), pdn[h]))
print("per target:", {k: round(v / ntgt, 2) for k, v in T.items()})
print("depth  n_all  minority_all  n_agree  minority_agree  n_pairdiff")
tw = tn = 0
for i in sorted(per):
    v = per[i]; f = lambda j: sum(x[j] for x in v)
    tw += f(1); tn += f(0)
    print(f"{i:4d} {f(0)/40:7.1f} {f(1)/max(f(0),1):9.3f} {f(2)/40:8.1f} {f(3)/max(f(2),1):9.3f} {f(4)/40:8.1f}")
print(f"hole-weighted minority (all holes) {tw/tn:.3f}")
