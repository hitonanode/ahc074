#!/usr/bin/env python3
"""Per-target realized cost of two designs of one case (dsel-probe).

Usage: pertarget.py LIST CASE SALT_A SALT_B
Prints, per column band of the target in each design, the mean moves and fix moves per request of
its targets, and the targets whose cost changed most with their column, holes and pair status.
"""
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from colfix import parse_err, parse_out, load_design, barcode_hash_of_input
RUNS = Path('/home/sato/ahc074/runs')


def per_target(info, s, case):
    drun, orun = info[s]
    run = RUNS / orun
    meta_orders = 8
    cost = defaultdict(list); fixc = defaultdict(list)
    d = load_design(RUNS / drun / 'design' / f'{barcode_hash_of_input(case)}.txt')
    for j in range(meta_orders):
        base = run if j == 0 else run / 'orders' / str(j)
        if not (base / 'out' / f'{case:04d}.txt').is_file():
            break
        inp = Path(f'/home/sato/ahc074/tools/in/{case:04d}.txt') if j == 0 else sorted(Path('/home/sato/ahc074/runs/.orders').glob(f'*/{j}/{case:04d}.txt'))[0]
        reqs_t = list(map(int, inp.read_text().split()[4 + 256:]))
        col, labels = parse_err(base / 'err' / f'{case:04d}.txt')
        outs = parse_out(base / 'out' / f'{case:04d}.txt')
        for r, papers in enumerate(outs):
            t = reqs_t[r]
            cost[t].append(len(papers)); fixc[t].append(sum(1 for l in labels.get(r, []) if l == 'fix'))
    H = int(d['H'])
    cols = d['columns']; ded = d['ded']; P = d['papers']; handle = d['handle']
    colt = [cols[ded[t]] for t in range(256)]
    pair = [sum(1 for u in range(256) if ded[u] == ded[t]) == 2 for t in range(256)]
    holes = [sum(1 for j in range(H) if not (P[2 * ded[t]] >> handle[j] & 1)) for t in range(256)]
    return {t: (np.mean(cost[t]), np.mean(fixc[t])) for t in cost}, colt, pair, holes


def main():
    lst, case, sa, sb = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    info = {r[0]: (r[1], r[2]) for r in (l.split() for l in open(lst)) if r}
    a, ca, pa, ha = per_target(info, sa, case)
    b, cb, pb, hb = per_target(info, sb, case)
    print(f"case {case}: salt {sa} mean {np.mean([v[0] for v in a.values()]):.3f}, salt {sb} mean {np.mean([v[0] for v in b.values()]):.3f}")
    for lo, hi in [(0, 5), (5, 10), (10, 15), (15, 20), (20, 25)]:
        ta = [t for t in range(256) if lo <= ca[t] < hi]; tb = [t for t in range(256) if lo <= cb[t] < hi]
        print(f" col {lo:2d}-{hi:2d}: {sa}: n {len(ta):3d} holes {np.mean([ha[t] for t in ta]):5.1f} cost {np.mean([a[t][0] for t in ta]):6.2f} fix {np.mean([a[t][1] for t in ta]):5.2f} | "
              f"{sb}: n {len(tb):3d} holes {np.mean([hb[t] for t in tb]):5.1f} cost {np.mean([b[t][0] for t in tb]):6.2f} fix {np.mean([b[t][1] for t in tb]):5.2f}")
    # regression of per-target cost on holes in each design
    for s, x, col, hol in [(sa, a, ca, ha), (sb, b, cb, hb)]:
        h = np.array([hol[t] for t in range(256)]); c = np.array([x[t][0] for t in range(256)]); f = np.array([x[t][1] for t in range(256)])
        A = np.vstack([np.ones(256), h]).T
        co, *_ = np.linalg.lstsq(A, c, rcond=None); cf, *_ = np.linalg.lstsq(A, f, rcond=None)
        print(f" salt {s}: cost ~ {co[0]:.2f} + {co[1]:.3f} holes; fix ~ {cf[0]:.2f} + {cf[1]:.3f} holes; mean holes {h.mean():.2f}")


if __name__ == '__main__':
    main()
