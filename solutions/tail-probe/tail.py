"""Tail analysis of the moves per request from the REQ_PROBE=1 output of solutions/brk-probe
(stderr files <dir>/*.txt; line format in solutions/brk-probe/breakdown.py).
usage: tail.py <errdir>"""
import sys, math
from collections import defaultdict
from pathlib import Path

H = 34
G = 64 - H
d = Path(sys.argv[1])
rows = []
for f in sorted(d.glob("*.txt")):
    seed = int(f.stem)
    pair = {}
    csize = None
    for line in f.read_text().splitlines():
        a = line.split()
        if not a:
            continue
        if a[0] == "CSIZE":
            csize = list(map(int, a[1:]))
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
            rows.append(dict(seed=seed, r=r, u=u, d=dd, l=l, n=n, ops=ops, holes=holes, mism=mism, fixed=fixed, bt=bt, rc=rc,
                             depth0=depth0, nf0=nf0, nf1=nf1, pair=pair.get(dd, False), ret=ret, fret=fret))
R = len(rows)
pc = lambda m: bin(m).count("1")
for x in rows:
    x["nh"] = pc(x["holes"]); x["nm"] = pc(x["mism"]); x["nfix"] = pc(x["fixed"])
mean = lambda v: sum(v) / max(1, len(v))
ops = sorted(x["ops"] for x in rows)
print(f"requests {R}, mean {mean(ops):.3f}, p50 {ops[R//2]} p90 {ops[int(R*.9)]} p95 {ops[int(R*.95)]} p99 {ops[int(R*.99)]} max {ops[-1]}")
hist = defaultdict(int)
for o in ops:
    hist[o] += 1
print("hist: " + " ".join(f"{k}:{v}" for k, v in sorted(hist.items())))
thr = ops[int(R * .95)]
names = ["ret_prev", "ret_old", "relevel", "blocks", "newfill", "digD", "lift", "fix", "other"]


def summ(v, tag):
    print(f"{tag:10s} n={len(v):6d} ({len(v)/R:.3f}) ops {mean([x['ops'] for x in v]):6.2f} pair {mean([x['pair'] for x in v]):.2f} l {mean([x['l'] for x in v]):5.1f}"
          f" n {mean([x['n'] for x in v]):4.1f} depth0 {mean([x['depth0'] for x in v if x['depth0']>=0]):4.1f} lifted {mean([x['depth0']==-1 for x in v]):.2f} filler {mean([x['depth0']==-2 for x in v]):.2f}"
          f" holes {mean([x['nh'] for x in v]):5.1f} mism {mean([x['nm'] for x in v]):5.1f} dug {mean([x['nfix'] for x in v]):4.1f} bt {mean([x['bt'] for x in v]):.2f} nf0 {mean([x['nf0'] for x in v]):.2f}")
    print("           roles " + " ".join(f"{nm} {mean([x['rc'][j] for x in v]):.2f}" for j, nm in enumerate(names)))


summ(rows, "all")
summ([x for x in rows if x["ops"] >= thr], f"ops>={thr}")
summ([x for x in rows if x["ops"] >= 20], "ops>=20")
summ([x for x in rows if x["ops"] <= 6], "ops<=6")
tail = [x for x in rows if x["ops"] >= thr]
print("excess of the tail by role: " + " ".join(f"{nm} {mean([x['rc'][j] for x in tail]) - mean([x['rc'][j] for x in rows]):+.2f}" for j, nm in enumerate(names)))
# Per-target means within a case: between-target variance vs noise
for kind in (None, False, True):
    sub = defaultdict(list)
    for x in rows:
        if kind is None or x["pair"] == kind:
            sub[(x["seed"], x["u"])].append(x["ops"])
    ms = [mean(v) for v in sub.values()]
    am = mean(ms)
    wv = []
    for o in sub.values():
        if len(o) >= 2:
            m = mean(o)
            wv.append(sum((a - m) ** 2 for a in o) / (len(o) - 1))
    w2 = mean(wv)
    vm = mean([(m - am) ** 2 for m in ms])
    en = mean([w2 / len(v) for v in sub.values()])
    tag = "all" if kind is None else ("pair" if kind else "single")
    print(f"  {tag}: targets {len(sub)} mean {am:.2f} within-target var {w2:.2f} var of means {vm:.2f} noise {en:.2f} -> between-target var {vm-en:.2f} (sd {math.sqrt(max(0, vm-en)):.2f})")
# Residual per target after the model's features: holes at the fitted flat cost per hole (0.40),
# the digs at (n-1)/2, the generic layer moves as measured (its model is per want code). A between-
# target variance of the residual near 0 means the model's features explain the per-target costs.
print("residual = ops - 0.40*holes - (n-1)/2 - blocks(actual) - 1 (lift)")
for kind in (None, False, True):
    sub = defaultdict(list)
    for x in rows:
        if kind is None or x["pair"] == kind:
            sub[(x["seed"], x["u"])].append(x["ops"] - 0.40 * x["nh"] - (x["n"] - 1) / 2 - x["rc"][3] - 1)
    ms = [mean(v) for v in sub.values()]
    am = mean(ms)
    wv = []
    for o in sub.values():
        if len(o) >= 2:
            m = mean(o)
            wv.append(sum((a - m) ** 2 for a in o) / (len(o) - 1))
    w2 = mean(wv)
    vm = mean([(m - am) ** 2 for m in ms])
    en = mean([w2 / len(v) for v in sub.values()])
    tag = "all" if kind is None else ("pair" if kind else "single")
    print(f"  {tag}: mean residual {am:.2f} within var {w2:.2f} between-target var {vm-en:.3f} (sd {math.sqrt(max(0, vm-en)):.2f})")
# Residual by column and kind
byl = defaultdict(list)
for x in rows:
    byl[(x["l"], x["pair"])].append(x["ops"] - 0.40 * x["nh"] - (x["n"] - 1) / 2 - x["rc"][3] - 1)
print("residual by column (single | pair): " + " ".join(f"{l}:{mean(byl.get((l,False),[0])):.2f}|{mean(byl.get((l,True),[0])):.2f}" for l in range(H)))
# The heaviest requests: what fraction of the moves is above the per-column mean?
print("tail list (ops >= 24): seed r u l n depth0 holes mism dug bt roles")
for x in rows:
    if x["ops"] >= 24:
        print(f"  {x['seed']} {x['r']} {x['u']} l={x['l']} n={x['n']} d0={x['depth0']} h={x['nh']} mism={x['nm']} dug={x['nfix']} bt={x['bt']} rc={x['rc'][:8]}")
# Residual after the fitted per-type hole model (fitpair.py on brk-probe probe0: pairs 2.134 +
# 0.345 tri + 0.343 pair holes, singles 0.765 + 0.380 tri), digs (n-1)/2, blocks (actual), lift.
def fitres(x):
    tri = sum(1 for m in range(H) if x["holes"] >> m & 1 and m > x["l"])
    ph = x["nh"] - tri
    hm = 2.134 + 0.345 * tri + 0.343 * ph if x["pair"] else 0.765 + 0.380 * tri
    return x["ops"] - hm - (x["n"] - 1) / 2 - x["rc"][3] - 1
print("residual after the fitted per-type hole model")
for kind in (None, False, True):
    sub = defaultdict(list)
    for x in rows:
        if kind is None or x["pair"] == kind:
            sub[(x["seed"], x["u"])].append(fitres(x))
    ms = [mean(v) for v in sub.values()]
    am = mean(ms)
    wv = []
    for o in sub.values():
        if len(o) >= 2:
            m = mean(o)
            wv.append(sum((a - m) ** 2 for a in o) / (len(o) - 1))
    w2 = mean(wv)
    vm = mean([(m - am) ** 2 for m in ms])
    en = mean([w2 / len(v) for v in sub.values()])
    tag = "all" if kind is None else ("pair" if kind else "single")
    print(f"  {tag}: mean residual {am:.2f} within var {w2:.2f} between-target var {vm-en:.3f} (sd {math.sqrt(max(0, vm-en)):.2f})")
byl = defaultdict(list)
for x in rows:
    byl[(x["l"], x["pair"])].append(fitres(x))
print("fitted residual by column (single | pair): " + " ".join(f"{l}:{mean(byl.get((l,False),[0])):.2f}|{mean(byl.get((l,True),[0])):.2f}" for l in range(H)))
print("pair fitted residual by touched blocks bt: " + " ".join(
    f"{b}:{mean([fitres(x) for x in rows if x['pair'] and x['bt']==b]):.2f}({sum(1 for x in rows if x['pair'] and x['bt']==b)})" for b in range(6)))
print("pair roles by bt (ret_prev ret_old relevel newfill fix): ")
for b in range(6):
    v = [x for x in rows if x['pair'] and x['bt'] == b]
    if v:
        print(f"  bt={b} n={len(v)} " + " ".join(f"{mean([x['rc'][j] for x in v]):.2f}" for j in (0, 1, 2, 4, 7)) + f" holes {mean([x['nh'] for x in v]):.1f} blocks {mean([x['rc'][3] for x in v]):.2f}")
