"""Model vs. actual moves, by label and by column / handle (label-audit).

Reads the @paper / @ops output of a run of solutions/esw-roles (or a descendant), replays the
requests, and aggregates the actual moves per column c and handle h_c next to the terms of the
design model (main.cpp, "Design: units, columns and the cost model"):

  - col:  W_c = least weighted depth of column c (pairs first, both colors at the top two), the
          model's expected digs summed over the targets of the column;
  - hole: q_j = (n0 n1 + r min(n0, n1) / 2) / (n0 + n1 + r), r = 2 nt_j, the raw handle-hole term
          (the model uses 4 kHoleWeight q_j, kHoleWeight = 0.38), with the holes of the printed rule
          (handles past the column and the pair differences) and with the final papers (perforation);
  - then per target column and kind (single / pair) the hole moves against the model's share of
    them, per number of holes of the target, and per handle the wrong heads against 2 q_j / N_j
    (README.md lists the tables).

Usage: python3 audit.py RUN [--seeds A-B] [--procs N]
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402

LABELS = ["ret", "fret", "reuse", "relevel", "gen", "dig", "lift", "fdig", "fill", "hdig", "help", "fix",
          "repair"]


def least_depths2(nc: int, nt: int, p1: int) -> int:
    np_ = nt - nc
    p0 = np_ - p1
    corr = max(0, np_ - 1) * int(p0 == 0 or p1 == 0)
    return nc * (nc - 1) + np_ * (np_ - 1) + 2 * corr


def analyze(job):
    run_dir, seed = job
    run_dir = Path(run_dir)
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, replay.out_path(run_dir, seed).read_text())
    ann = replay.parse_annotations(replay.err_path(run_dir, seed).read_text(), inp.k)
    if out.error or "role" not in ann.papers:
        return None
    K = inp.k
    role = ann.papers["role"]
    col = [int(v) if v != "-" else -1 for v in ann.papers["col"]]
    hcolor = [int(v) if v != "-" else -1 for v in ann.papers["hcolor"]]
    papers = out.designs
    generic = [k for k in range(K) if role[k] == "generic"]
    H = max(col) + 1
    # handle windows: holes of every generic sheet (except the cap window 63); h_j = the window whose
    # least column among the opaque column papers is j
    gen_opaque = 0
    for k in generic:
        gen_opaque |= papers[k].opaque
    hwin = [-1] * H
    for w in range(63):
        if gen_opaque >> w & 1:
            continue
        cs = [col[k] for k in range(K) if col[k] >= 0 and papers[k].opaque >> w & 1]
        hwin[min(cs)] = w
    assert -1 not in hwin, (seed, hwin)
    ded = [-1] * inp.p
    for k in range(K):
        t = ann.papers["targets"][k]
        if t != "-":
            for x in t.split(","):
                ded[int(x)] = k
    A = inp.target
    is_pair = [role[k] == "pair" for k in range(K)]

    # model terms per column / handle
    nc = [0] * H
    nt = [0] * H
    p1 = [0] * H
    hn_print = [[0, 0] for _ in range(H)]
    hn_final = [[0, 0] for _ in range(H)]
    for k in range(K):
        c = col[k]
        if c < 0:
            continue
        ts = [int(x) for x in ann.papers["targets"][k].split(",")]
        nc[c] += 1
        nt[c] += len(ts)
        if len(ts) == 2:
            p1[c] += hcolor[k]
        diff = 0
        if len(ts) == 2:
            diff = A[ts[0]] ^ A[ts[1]]
        for j in range(H):
            w = hwin[j]
            printed_hole = j > c or (diff >> w & 1)
            final_hole = not (papers[k].opaque >> w & 1)
            for t in ts:
                colr = A[t] >> w & 1
                if printed_hole:
                    hn_print[j][colr] += 1
                if final_hole and j != c:
                    hn_final[j][colr] += 1
    W = [least_depths2(nc[c], nt[c], p1[c]) * 0.5 for c in range(H)]

    def q(x, y, r):
        return (x * y + 0.5 * r * min(x, y)) / max(1.0, x + y + r)

    qp = [q(hn_print[j][0], hn_print[j][1], 2 * nt[j]) for j in range(H)]
    qf = [q(hn_final[j][0], hn_final[j][1], 2 * nt[j]) for j in range(H)]

    # replay
    game = replay.Game(inp, papers)
    R = len(out.queries)
    # per column of the target: requests, label counts; per handle j: fix moves (moved paper of column j),
    # requests with a hole at h_j (final paper), mismatches of the head at h_j before the request
    req_c = [0] * H
    lab_c = [defaultdict(int) for _ in range(H)]
    fix_j = [0] * H
    fdig_j = [0] * H
    fill_j = [0] * H  # fill moves of a paper of column j
    holes_j = [0] * H
    wrong_j = [0] * H  # head (visible paper at h_j right before the request's ops) shows the wrong color
    depth_sum_c = [0] * H  # actual depth of the target paper in its column (column papers above it)
    pair_req = [0, 0]
    pair_lab = [defaultdict(int), defaultdict(int)]
    by_depth = defaultdict(lambda: [0, 0])  # (depth) -> [requests, digs]
    cov_j = [0] * H     # holes of the target at h_j shown by a paper of another column after the request
    head_j = [0] * H    # ... shown by a paper of column j after the request
    fshare_j = [0.0] * H  # filler moves of the request (fdig fill reuse relevel fret) split over cov
    FILL = {"fdig", "fill", "reuse", "relevel", "fret"}
    HOLE = FILL | {"fix"}
    Nf = [hn_final[j][0] + hn_final[j][1] for j in range(H)]
    tot_c = [0] * H      # moves of the requests of column c except ret
    hole_c = [0] * H     # hole-service moves (fix + filler labels) of the requests of column c
    gen_c = [0] * H      # gen + help + hdig of the requests of column c
    ret_by = [0] * H     # ret moves of a paper of column c
    nholes_c = [0] * H   # holes of the targets at the handles (final papers) of the requests of column c
    mhole_c = [0.0] * H  # model hole share 4 kHoleWeight sum_j q_j / N_j of the requests of column c
    # per paper: why it is out of its column (None: in place; ("T", c, pair): lifted as the target of a
    # request of column c; "F": a filler). Moves of a paper out of place are charged to that reason.
    state = [None] * K
    tret = defaultdict(lambda: [0, 0])  # (column, pair) of the lifted target -> [lifts, return moves]
    fcost = [0, 0]                      # filler placements, moves while out as a filler
    role_c = defaultdict(lambda: defaultdict(float))  # (c, pair) -> sums of the request's quantities
    fixev_j = [0] * H  # requests with a fix of column j
    headmis = [[0, 0, 0, 0] for _ in range(H)]  # per handle: majority / minority requests, their head mismatches
    hstat = defaultdict(lambda: [0, 0, 0, 0])  # (pair, holes) -> [requests, holes by head, by cover, hole moves]
    for r in range(R):
        t = inp.requests[r]
        d = ded[t]
        c = col[d]
        labels = ann.labels_of(r, len(out.queries[r]))
        # state before the ops
        order = game.order
        pos_d = order.index(d)
        depth = sum(1 for k in order[:pos_d] if col[k] == c)
        # visible paper at each handle window (before)
        covered = 0
        vis = {}
        for x in order:
            e = papers[x].opaque & ~covered
            if e:
                for j in range(H):
                    if e >> hwin[j] & 1:
                        vis[j] = x
            covered |= papers[x].opaque
        # the in-place head of each column (the first paper of the column in place: state None)
        head = [-1] * H
        for x in order:
            cx = col[x]
            if cx >= 0 and head[cx] < 0 and state[x] is None:
                head[cx] = x
        for j in range(H):
            w = hwin[j]
            if j != c and not (papers[d].opaque >> w & 1):
                holes_j[j] += 1
                x = vis.get(j)
                shown = (papers[x].black >> w & 1) if x is not None else 0
                if shown != (A[t] >> w & 1):
                    wrong_j[j] += 1
                want = A[t] >> w & 1
                maj = int(hn_final[j][1] > hn_final[j][0])
                hm = headmis[j]
                hm[0 if want == maj else 1] += 1          # requests of the majority / minority color
                if head[j] >= 0 and (papers[head[j]].black >> w & 1) != want:
                    hm[2 if want == maj else 3] += 1      # ... whose in-place head shows the other color
        req_c[c] += 1
        depth_sum_c[c] += depth
        pp = int(is_pair[d])
        pair_req[pp] += 1
        ndig = 0
        rq = role_c[(c, pp)]
        fout_r = 0
        fixcols = set()
        rq["req"] += 1
        rq["W"] += W[c] / nt[c]
        for (k, dd), lab in zip(out.queries[r], labels):
            lab_c[c][lab] += 1
            pair_lab[pp][lab] += 1
            if lab == "dig":
                ndig += 1
            if lab in ("fix", "fdig", "fill", "gen", "help", "hdig", "dig", "lift"):
                rq[lab] += 1
            if col[k] >= 0:
                st = state[k]
                if lab == "lift":
                    state[k] = ("T", c, pp)
                    tret[(c, pp)][0] += 1
                elif lab in ("fill", "help"):
                    if st is not None and st != "F":
                        tret[st[1:]][1] += 1  # the lifted paper moved on as a filler: its return move
                    elif st == "F":
                        fcost[1] += 1
                        rq["fout"] += 1
                        fout_r += 1
                    if st is None:
                        fcost[0] += 1
                    state[k] = "F"
                elif lab in ("ret", "fret", "relevel", "reuse", "repair"):
                    if st == "F":
                        fcost[1] += 1
                        rq["fout"] += 1
                        fout_r += 1
                    elif st is not None:
                        tret[st[1:]][1] += 1
                    else:
                        rq["other"] += 1
                    if lab in ("ret", "fret"):
                        state[k] = None
                    elif lab == "reuse" and st is not None and st != "F":
                        state[k] = "F"  # the lifted paper of the last request becomes a filler
                if lab == "fix":
                    fix_j[col[k]] += 1
                    fixcols.add(col[k])
                elif lab == "fdig":
                    fdig_j[col[k]] += 1
                elif lab == "fill":
                    fill_j[col[k]] += 1
            game.move(k, dd, check=False)
        for j in fixcols:
            fixev_j[j] += 1
        # after: who shows each hole of the target
        covered = 0
        vis = {}
        for x in game.order:
            e = papers[x].opaque & ~covered
            if e:
                for j in range(H):
                    if e >> hwin[j] & 1:
                        vis[j] = x
            covered |= papers[x].opaque
        cov = []
        for j in range(H):
            w = hwin[j]
            if j != c and not (papers[d].opaque >> w & 1):
                x = vis.get(j)
                if x is not None and col[x] == j:
                    head_j[j] += 1
                    rq["byhead"] += 1
                else:
                    cov.append(j)
                    cov_j[j] += 1
                    rq["bycover"] += 1
        nfill = sum(1 for lab in labels if lab in FILL)
        for (k, dd), lab in zip(out.queries[r], labels):
            if lab == "ret":
                if col[k] >= 0:
                    ret_by[col[k]] += 1
            else:
                tot_c[c] += 1
            if lab in HOLE:
                hole_c[c] += 1
            if lab in ("gen", "help", "hdig"):
                gen_c[c] += 1
        for j in range(H):
            if j != c and not (papers[d].opaque >> hwin[j] & 1):
                nholes_c[c] += 1
                mhole_c[c] += 4 * 0.38 * qf[j] / max(1, Nf[j])
                rq["nholes"] += 1
                rq["mhole"] += 4 * 0.38 * qf[j] / max(1, Nf[j])
        if cov and nfill:
            for j in cov:
                fshare_j[j] += nfill / len(cov)
        nh = sum(1 for j in range(H) if j != c and not (papers[d].opaque >> hwin[j] & 1))
        hs = hstat[(pp, nh)]
        hs[0] += 1
        hs[1] += nh - len(cov)
        hs[2] += len(cov)
        hs[3] += sum(1 for lab in labels if lab in ("fix", "fdig", "fill")) + fout_r
        by_depth[min(depth, 15)][0] += 1
        by_depth[min(depth, 15)][1] += ndig
    return {
        "seed": seed, "H": H, "R": R, "nc": nc, "nt": nt, "W": W, "qp": qp, "qf": qf,
        "hn_print": hn_print, "hn_final": hn_final,
        "req_c": req_c, "lab_c": [dict(x) for x in lab_c], "fix_j": fix_j, "fdig_j": fdig_j, "fill_j": fill_j,
        "tot_c": tot_c, "hole_c": hole_c, "gen_c": gen_c, "ret_by": ret_by, "nholes_c": nholes_c, "mhole_c": mhole_c,
        "imb": [abs(hn_final[j][0] - hn_final[j][1]) / max(1, Nf[j]) for j in range(H)],
        "holes_j": holes_j, "cov_j": cov_j, "head_j": head_j, "fshare_j": fshare_j, "wrong_j": wrong_j, "depth_sum_c": depth_sum_c,
        "pair_req": pair_req, "pair_lab": [dict(x) for x in pair_lab], "by_depth": dict(by_depth),
        "tret": {f"{a},{b}": v for (a, b), v in tret.items()}, "fcost": fcost,
        "role_c": {f"{a},{b}": dict(v) for (a, b), v in role_c.items()},
        "hstat": {f"{a},{b}": v for (a, b), v in hstat.items()}, "headmis": headmis, "fixev_j": fixev_j,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--seeds", default="0-2000")
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--dump", default="")
    args = ap.parse_args()
    run_dir = replay.resolve_run(args.run)
    a, b = map(int, args.seeds.split("-"))
    with Pool(args.procs) as pool:
        res = [x for x in pool.map(analyze, [(str(run_dir), s) for s in range(a, b)], chunksize=4) if x]
    if args.dump:
        import json
        Path(args.dump).write_text(json.dumps(res))
    n = len(res)
    H = res[0]["H"]
    print(f"run {run_dir.name}: {n} seeds")
    # per column
    print("\nper column c (sums over seeds, per request = / (n R)):")
    print(" c   nc    nt  W/nt  dig/req_c depth/req_c  req%   lab/req(dig,lift)   fix_j/R  qp/256  qf/256  fix/qf   fdig_j  fill_j  holes%  wrong/holes")
    tot = defaultdict(float)
    for c in range(H):
        s = defaultdict(float)
        for x in res:
            s["nc"] += x["nc"][c]
            s["nt"] += x["nt"][c]
            s["W"] += x["W"][c]
            s["req"] += x["req_c"][c]
            s["dig"] += x["lab_c"][c].get("dig", 0)
            s["lift"] += x["lab_c"][c].get("lift", 0)
            s["depth"] += x["depth_sum_c"][c]
            s["fix"] += x["fix_j"][c]
            s["fdig"] += x["fdig_j"][c]
            s["fill"] += x["fill_j"][c]
            s["qp"] += x["qp"][c]
            s["qf"] += x["qf"][c]
            s["holes"] += x["holes_j"][c]
            s["wrong"] += x["wrong_j"][c]
            s["R"] += x["R"]
            s["cov"] += x["cov_j"][c]
            s["fsh"] += x["fshare_j"][c]
        for k, v in s.items():
            tot[k] += v
        R = s["R"]
        print(f"{c:2d} {s['nc']/n:5.2f} {s['nt']/n:5.2f} {s['W']/s['nt']:5.2f} {s['dig']/s['req']:9.3f} "
              f"{s['depth']/s['req']:10.3f} {100*s['req']/R:6.2f} {s['lift']/s['req']:7.3f}"
              f"   {s['fix']/R:8.4f} {s['qp']/n/256:7.4f} {s['qf']/n/256:7.4f} {s['fix']/R/(s['qf']/n/256+1e-9):6.3f}"
              f"  {s['fdig']/R:7.4f} {s['fill']/R:7.4f} {100*s['holes']/R:6.1f} {s['wrong']/max(1,s['holes']):6.3f}"
              f"  cov% {100*s['cov']/max(1,s['holes']):5.1f} fsh/R {s['fsh']/R:.4f} (fix+fsh)/mis {(s['fix']+s['fsh'])/max(1,s['wrong']):.3f}"
              f" (fix+fsh)/(2qf) {(s['fix']+s['fsh'])/R/(2*s['qf']/n/256):.3f}")
    R = tot["R"] / H
    print(f"tot: W/256 {tot['W']/n/256:.3f}  dig/R {tot['dig']/R:.3f}  depth/R {tot['depth']/R:.3f}  "
          f"fix/R {tot['fix']/R:.3f}  qp/256 {tot['qp']/n/256:.3f} qf/256 {tot['qf']/n/256:.3f}  "
          f"model_hole(qf) {4*0.38*tot['qf']/n/256:.3f}")
    print("\nper target column c: actual moves per request (own ret included) vs the model's share (dig W/nt + holes)")
    print(" c  req%  actual   dig  lift  hole  gen  ret  | model: W/nt  hole  sum | holes/req hole/hole mhole/hole"
          "  actual-(model+gen+lift+ret)  imb_h")
    for c in range(H):
        def g(key):
            return sum(x[key][c] for x in res)
        req = g("req_c")
        W = g("W") / max(1, g("nt"))
        dig = sum(x["lab_c"][c].get("dig", 0) for x in res) / req
        lift = sum(x["lab_c"][c].get("lift", 0) for x in res) / req
        act = (g("tot_c") + g("ret_by")) / req
        hole = g("hole_c") / req
        gen = g("gen_c") / req
        ret = g("ret_by") / req
        mh = g("mhole_c") / req
        nh = g("nholes_c") / req
        imb = g("imb") / n
        print(f"{c:2d} {100*req/(n*res[0]['R']):5.2f} {act:7.3f} {dig:5.2f} {lift:5.2f} {hole:5.2f} {gen:4.2f} {ret:4.2f}"
              f" | {W:5.2f} {mh:5.2f} {W+mh:5.2f} | {nh:5.2f} {hole/max(1e-9,nh):6.3f} {mh/max(1e-9,nh):6.3f}"
              f"   {act-(W+mh+gen+lift+ret):+6.3f}  {imb:.3f}")
    print("\nper target column c and kind (s = single, p = pair): per request; ret = the moves to put the lifted"
          " target back (ret/fret/relevel/reuse of it) per lift; hole = fix + fdig + fill + moves of fillers out")
    print(" c k  req%   dig  W/nt   fix  fdig  fill  fout  hole  nholes hole/h mhole/h  gen  tret  rest=hole+tret-mhole")
    fc = [sum(x["fcost"][i] for x in res) for i in range(2)]
    for c in range(H):
        for pp in (0, 1):
            key = f"{c},{pp}"
            s = defaultdict(float)
            for x in res:
                for k2, v in x["role_c"].get(key, {}).items():
                    s[k2] += v
                tr = x["tret"].get(key)
                if tr:
                    s["lifts"] += tr[0]
                    s["tret"] += tr[1]
            q = s["req"]
            if not q:
                continue
            hole = (s["fix"] + s["fdig"] + s["fill"] + s["fout"]) / q
            tr = s["tret"] / max(1, s["lifts"])
            print(f"{c:2d} {'sp'[pp]} {100*q/(n*res[0]['R']):5.2f} {s['dig']/q:5.2f} {s['W']/q:5.2f} {s['fix']/q:5.2f}"
                  f" {s['fdig']/q:5.2f} {s['fill']/q:5.2f} {s['fout']/q:5.2f} {hole:5.2f} {s['nholes']/q:6.2f}"
                  f" {hole/max(1e-9,s['nholes']/q):6.3f} {s['mhole']/max(1e-9,s['nholes']):6.3f} {(s['gen']+s['help']+s['hdig'])/q:5.2f}"
                  f" {tr:5.2f}  {hole+tr-s['mhole']/q:+6.3f}"
                  f"  head-served {s['byhead']/max(1, s['byhead'] + s['bycover']):.3f}")
    print(f"fillers: {fc[0]} placements from in place, {fc[1]} moves while out ({fc[1]/max(1,fc[0]):.2f} per placement)")
    print("\nby the number of holes h of the target's paper at the handles: requests%, share of its holes shown"
          " by a paper of that handle's column after the request, hole moves (fix fdig fill + fillers out) per"
          " request and per hole")
    for pp, name in ((0, "single"), (1, "pair")):
        hsum = defaultdict(lambda: [0, 0, 0, 0])
        for x in res:
            for key, v in x["hstat"].items():
                a, b = map(int, key.split(","))
                if a == pp:
                    for i in range(4):
                        hsum[b][i] += v[i]
        allq = n * res[0]["R"]
        print(f"  {name}:")
        for h in sorted(hsum):
            v = hsum[h]
            if v[0] < 200:
                continue
            print(f"    h {h:2d}: {100*v[0]/allq:5.2f}%  head {v[1]/max(1, v[1]+v[2]):.3f}  moves {v[3]/v[0]:6.3f}"
                  f"  per hole {v[3]/v[0]/max(1, h):.3f}")
    print("\nhead of column j (first paper in place) before the request, for the requests with a hole at h_j:")
    print("  j  minority share  P(head wrong | majority)  P(head wrong | minority)  P(head wrong)"
          "  persistence 2p(1-p)  majority-top min(p,1-p)")
    for j in range(H):
        hm = [sum(x["headmis"][j][i] for x in res) for i in range(4)]
        tot = hm[0] + hm[1]
        p = hm[1] / max(1, tot)
        fm = sum(x["fix_j"][j] for x in res)
        fe = sum(x["fixev_j"][j] for x in res)
        # the model's implied mismatch per hole 2 q_j / N_j (persistence with the reset demand), and the
        # digs into column j per request (lifts of its targets and fixes), the actual resets
        qn = sum(x["qf"][j] for x in res) / max(1, sum(x["hn_final"][j][0] + x["hn_final"][j][1] for x in res))
        digs_j = sum(x["lab_c"][j].get("dig", 0) for x in res) / (n * res[0]["R"])
        print(f"      model 2q/N {2*qn:.3f}  (head wrong − model {((hm[2]+hm[3])/max(1,tot)) - 2*qn:+.3f})"
              f"  target digs in column j per request {digs_j:.3f}  fixes {fm/(n*res[0]['R']):.3f}"
              f"  requests of column j {sum(x['req_c'][j] for x in res)/(n*res[0]['R']):.3f}")
        print(f" {j:2d}  {p:6.3f}  {hm[2]/max(1,hm[0]):6.3f}  {hm[3]/max(1,hm[1]):6.3f}  {(hm[2]+hm[3])/max(1,tot):6.3f}"
              f"  {2*p*(1-p):6.3f}  {p:6.3f}   fix moves per fixing request {fm/max(1,fe):.3f}"
              f"  fixing requests / head-wrong holes {fe/max(1,hm[2]+hm[3]):.3f}")
    print("\ndigs by the actual depth of the target in its column (depth: requests%, digs/request):")
    bd = defaultdict(lambda: [0, 0])
    for x in res:
        for k, v in x["by_depth"].items():
            bd[int(k)][0] += v[0]
            bd[int(k)][1] += v[1]
    allr = sum(v[0] for v in bd.values())
    for k in sorted(bd):
        print(f"  {k:2d}: {100*bd[k][0]/allr:5.2f}%  {bd[k][1]/bd[k][0]:.3f}")
    print("\nlabels per request by the target's paper (single / pair):")
    for pp, name in ((0, "single"), (1, "pair")):
        req = sum(x["pair_req"][pp] for x in res)
        labs = defaultdict(int)
        for x in res:
            for k, v in x["pair_lab"][pp].items():
                labs[k] += v
        print(f"  {name:6s} share {100*req/(n*res[0]['R']):5.1f}%  total {sum(labs.values())/req:6.3f}  " +
              " ".join(f"{k} {labs[k]/req:.3f}" for k in LABELS))


if __name__ == "__main__":
    main()
