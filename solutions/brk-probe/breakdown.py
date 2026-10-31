"""Breakdown of the moves per request from the REQ_PROBE=1 output of solutions/brk-probe (stderr files
in <dir>/*.txt, as written by runm.py). usage: breakdown.py <errdir> [lo] [hi]

Per request the probe prints
  REQ r u d l n ops pre holes mism fixed want bt rc0..rc8 ret fret pool depth0 nf0 nf1
(holes / mism / fixed / want: hex masks over the handle indices: handle holes of D, mismatched at the
start, dug by set_handle, color 1 wanted; rc: moves by role 0 return of the previous paper, 1 return
of an old filler, 2 re-level, 3 generic layer, 4 new filler, 5 digs of D's column, 6 lift, 7 handle
fixes, 8 other; depth0: depth of D in its column at the start, -1 lifted, -2 a filler; nf0 / nf1:
fillers out before / after), and once per case CSIZE (column sizes), BIASG (2p-1 per handle), BIASC
(majority color per handle) and PAPERS (paper:column:opaque windows).
"""
import sys
from collections import defaultdict
from pathlib import Path

d = Path(sys.argv[1])
lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0
hi = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9
H = 34
G = 64 - H
rows = []
cases = 0
for f in sorted(d.glob("*.txt")):
    seed = int(f.stem)
    if not (lo <= seed < hi):
        continue
    cases += 1
    csize = biasg = biasc = None
    pair = {}
    for line in f.read_text().splitlines():
        a = line.split()
        if not a:
            continue
        if a[0] == "CSIZE":
            csize = list(map(int, a[1:]))
        elif a[0] == "BIASG":
            biasg = list(map(float, a[1:]))
        elif a[0] == "BIASC":
            biasc = list(map(int, a[1:]))
        elif a[0] == "PAPERS":
            for x in a[1:]:
                k, c, o = map(int, x.split(":"))
                pair[k] = o < G + c + 1
        elif a[0] == "REQ":
            r, u, dd, l, n, ops, pre = map(int, a[1:8])
            holes, mism, fixed, want = (int(x, 16) for x in a[8:12])
            bt = int(a[12])
            rc = list(map(int, a[13:22]))
            ret, fret, pool, depth0, nf0, nf1 = map(int, a[22:28])
            rows.append(dict(seed=seed, r=r, u=u, d=dd, l=l, n=n, ops=ops, pre=pre, holes=holes, mism=mism, fixed=fixed,
                             want=want, bt=bt, rc=rc, ret=ret, fret=fret, pool=pool, depth0=depth0, nf0=nf0, nf1=nf1,
                             csize=csize, biasg=biasg, biasc=biasc, pair=pair.get(dd, False)))
R = len(rows)
print(f"cases {cases} requests {R}")


def bits(m):
    return [i for i in range(H) if m >> i & 1]


def mean(v):
    return sum(v) / max(1, len(v))


names = ["ret_prev", "ret_old", "relevel", "blocks", "newfill", "digD", "lift", "fix", "other"]
rc = [mean([x["rc"][j] for x in rows]) for j in range(9)]
ops = mean([x["ops"] for x in rows])
pre = mean([x["pre"] for x in rows])
print(f"moves/request {ops:.3f} (before the merge {pre:.3f}, merge saves {pre - ops:.3f})")
print("roles: " + "  ".join(f"{nm} {v:.3f}" for nm, v in zip(names, rc)))

# Holes
for x in rows:
    hb = bits(x["holes"])
    x["tri"] = sum(1 for m in hb if m > x["l"])
    x["pairh"] = sum(1 for m in hb if m < x["l"])
    x["nh"] = len(hb)
    x["nmism"] = bin(x["mism"]).count("1")
    x["nfixed"] = bin(x["fixed"]).count("1")
    # mismatched holes not dug: covered by a filler / the previous paper / a return at the top
    x["ncov"] = bin(x["mism"] & ~x["fixed"]).count("1")
    # persistence model: expected fixes = sum over holes of 1 - p_m(color wanted)
    e = 0.0
    for m in hb:
        g = x["biasg"][m]  # 2p-1 with p = freq of the majority color
        p = (1 + g) / 2
        want = x["want"] >> m & 1
        pc = p if want == x["biasc"][m] else 1 - p
        e += 1 - pc
    x["mfix"] = e
nh = mean([x["nh"] for x in rows])
print(f"handle holes/request {nh:.3f} (triangle {mean([x['tri'] for x in rows]):.3f}, pair {mean([x['pairh'] for x in rows]):.3f});"
      f" mismatched at the start {mean([x['nmism'] for x in rows]):.3f} (rate {mean([x['nmism'] for x in rows]) / nh:.3f});"
      f" persistence model {mean([x['mfix'] for x in rows]):.3f}")
print(f"  dug {mean([x['nfixed'] for x in rows]):.3f} handles with {rc[7]:.3f} fix moves ({rc[7] / mean([x['nfixed'] for x in rows]):.3f} per dug handle);"
      f" mismatched and not dug (covered) {mean([x['ncov'] for x in rows]):.3f}")
hole_moves = rc[7] + rc[4] + rc[1] + rc[2]
print(f"  moves for holes = fix {rc[7]:.3f} + new fillers {rc[4]:.3f} + old filler returns {rc[1]:.3f} + re-levels {rc[2]:.3f} = {hole_moves:.3f}"
      f" ({hole_moves / nh:.3f} per hole; 0.5 per hole = {0.5 * nh:.3f}; persistence = {mean([x['mfix'] for x in rows]):.3f})")

# Digs of D's column
inc = [x for x in rows if x["depth0"] >= 0]
print(f"digs of D's column {rc[5]:.3f}; model (n-1)/2 {mean([(x['n'] - 1) / 2 for x in rows]):.3f}; requests with D in its column {len(inc) / R:.3f},"
      f" their depth {mean([x['depth0'] for x in inc]):.3f} vs (n-1)/2 {mean([(x['n'] - 1) / 2 for x in inc]):.3f};"
      f" D lifted (kept) {sum(x['depth0'] == -1 for x in rows) / R:.3f}, D a filler {sum(x['depth0'] == -2 for x in rows) / R:.3f}")
# depth distribution relative to n
dist = defaultdict(lambda: [0, 0])
for x in inc:
    dist[x["n"]][0] += 1
for x in inc:
    pass
print("  depth of D at the start by column size n: n: count, mean depth, P(depth=0), P(depth=n-1)")
by_n = defaultdict(list)
for x in inc:
    by_n[x["n"]].append(x["depth0"])
for n in sorted(by_n):
    v = by_n[n]
    print(f"    n={n:2d}: {len(v):5d} {mean(v):.3f} {sum(1 for t in v if t == 0) / len(v):.3f} {sum(1 for t in v if t == n - 1) / len(v):.3f}")

# Returns of the previous paper
print(f"return of the previous paper: moves {rc[0]:.3f}; ret_mode chosen: " +
      " ".join(f"{m}:{sum(x['ret'] == m for x in rows) / R:.3f}" for m in range(5)) +
      f"; fret_mode: " + " ".join(f"{m}:{sum(x['fret'] == m for x in rows) / R:.3f}" for m in range(6)) +
      f"; pool lift {mean([x['pool'] for x in rows]):.3f}")
print(f"fillers out: before {mean([x['nf0'] for x in rows]):.3f}, after {mean([x['nf1'] for x in rows]):.3f}")
print(f"generic layer: moves {rc[3]:.3f}; touched blocks {mean([x['bt'] for x in rows]):.3f}; pair requests {mean([x['pair'] for x in rows]):.3f}")
bt_moves = defaultdict(list)
for x in rows:
    bt_moves[x["bt"]].append(x["rc"][3])
print("  by touched blocks: " + " ".join(f"{b}:{mean(v):.2f}({len(v) / R:.2f})" for b, v in sorted(bt_moves.items())))

# Per column of the target: requests, moves, digs, holes, hole moves
print("\nper column l: share  ops  digD  (n-1)/2  n  holes(tri,pair)  mism  fixmv  newfill  retold  relevel  ret_prev  blocks  pair%")
byl = defaultdict(list)
for x in rows:
    byl[x["l"]].append(x)
for l in sorted(byl):
    v = byl[l]
    print(f"  l={l:2d} {len(v) / R:.3f} {mean([x['ops'] for x in v]):6.2f} {mean([x['rc'][5] for x in v]):5.2f} {mean([(x['n'] - 1) / 2 for x in v]):5.2f}"
          f" {mean([x['n'] for x in v]):4.1f} {mean([x['nh'] for x in v]):5.1f}({mean([x['tri'] for x in v]):4.1f},{mean([x['pairh'] for x in v]):4.1f})"
          f" {mean([x['nmism'] for x in v]):5.2f} {mean([x['rc'][7] for x in v]):5.2f} {mean([x['rc'][4] for x in v]):5.2f} {mean([x['rc'][1] for x in v]):5.2f}"
          f" {mean([x['rc'][2] for x in v]):5.2f} {mean([x['rc'][0] for x in v]):5.2f} {mean([x['rc'][3] for x in v]):5.2f} {mean([x['pair'] for x in v]):.2f}")

# Single vs pair
for kind in (False, True):
    v = [x for x in rows if x["pair"] == kind]
    if not v:
        continue
    print(f"\n{'pair' if kind else 'single'} requests {len(v) / R:.3f}: ops {mean([x['ops'] for x in v]):.3f}, holes {mean([x['nh'] for x in v]):.2f}"
          f" (tri {mean([x['tri'] for x in v]):.2f}, pair {mean([x['pairh'] for x in v]):.2f}), mism {mean([x['nmism'] for x in v]):.2f},"
          f" roles " + " ".join(f"{nm} {mean([x['rc'][j] for x in v]):.2f}" for j, nm in enumerate(names)))

# Per handle m: hole share, mismatch rate, dig rate, covered rate
print("\nper handle m: holes/req  mism_rate  dug/mism  covered/mism  model(1-p)  colsize")
agg = defaultdict(lambda: [0, 0, 0, 0, 0.0])
for x in rows:
    for m in bits(x["holes"]):
        a = agg[m]
        a[0] += 1
        a[1] += x["mism"] >> m & 1
        a[2] += x["fixed"] >> m & 1
        a[3] += (x["mism"] >> m & 1) and not (x["fixed"] >> m & 1)
        g = x["biasg"][m]
        p = (1 + g) / 2
        pc = p if (x["want"] >> m & 1) == x["biasc"][m] else 1 - p
        a[4] += 1 - pc
cs = rows[0]["csize"]
for m in range(H):
    a = agg[m]
    if a[0] == 0:
        continue
    print(f"  m={m:2d} {a[0] / R:6.3f} {a[1] / a[0]:8.3f} {a[2] / max(1, a[1]):8.3f} {a[3] / max(1, a[1]):8.3f} {a[4] / a[0]:8.3f}")
