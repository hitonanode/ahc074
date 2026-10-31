"""One line per config of a sweep.py output directory: per-seed log ratio of the score against
base.txt (mean +- SE, W/D/L), E>0 cases and the max seconds.
usage: cmpall.py <dir> [base_name]"""
import math, sys
from pathlib import Path


def load(p):
    d = {}
    for line in open(p):
        a = line.split()
        if len(a) >= 5:
            d[int(a[0])] = (int(a[1]), int(a[3]), float(a[4]))
    return d


dr = Path(sys.argv[1])
bname = sys.argv[2] if len(sys.argv) > 2 else "base"
b = load(dr / f"{bname}.txt")
for p in sorted(dr.glob("*.txt")):
    if p.stem == bname:
        continue
    c = load(p)
    seeds = [s for s in sorted(set(b) & set(c)) if b[s][0] > 0 and c[s][0] > 0]
    xs = [math.log(c[s][0] / b[s][0]) * 100 for s in seeds]
    n = len(xs)
    if n < 2:
        continue
    m = sum(xs) / n
    se = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1) / n)
    w, l = sum(x < 0 for x in xs), sum(x > 0 for x in xs)
    wa = sum(1 for s in c if c[s][0] == 0)
    e = sum(1 for s in c if c[s][1] > 0)
    print(f"{p.stem:10s} n={n} {m:+.3f} ± {se:.3f}%  {w}/{n-w-l}/{l}  mean={sum(c[s][0] for s in seeds)/n:.1f}"
          f" (base {sum(b[s][0] for s in seeds)/n:.1f})  WA={wa} E>0={e} max_sec={max(v[2] for v in c.values()):.2f}")
