"""Compares runm.py outputs: per-seed log ratio of T (and of the score when both have E = 0),
mean +- SE, W/D/L, and the means of selected stats.
usage: cmpm.py base.txt cand.txt [stat ...]"""
import math, sys


def load(p):
    d = {}
    for line in open(p):
        a = line.split()
        if len(a) < 5:
            continue
        s = int(a[0])
        st = {"score": int(a[1]), "T": int(a[2]), "E": int(a[3]), "sec": float(a[4])}
        for kv in a[5:]:
            k, _, v = kv.partition("=")
            try:
                st[k] = float(v)
            except ValueError:
                pass
        d[s] = st
    return d


b, c = load(sys.argv[1]), load(sys.argv[2])
stats = sys.argv[3:]
seeds = sorted(set(b) & set(c))
for key in ("T", "score"):
    xs = [math.log(c[s][key] / b[s][key]) * 100 for s in seeds if b[s][key] > 0 and c[s][key] > 0]
    n = len(xs)
    if n == 0:
        continue
    m = sum(xs) / n
    se = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1) / n) if n > 1 else 0
    w = sum(x < 0 for x in xs)
    l = sum(x > 0 for x in xs)
    print(f"{key}: n={n} diff={m:+.3f}% se={se:.3f}% W/D/L={w}/{n-w-l}/{l} "
          f"base={sum(b[s][key] for s in seeds)/len(seeds):.1f} cand={sum(c[s][key] for s in seeds)/len(seeds):.1f}")
print(f"E>0 cases: base {sum(b[s]['E'] > 0 for s in seeds)} cand {sum(c[s]['E'] > 0 for s in seeds)}; "
      f"max sec base {max(b[s]['sec'] for s in seeds):.3f} cand {max(c[s]['sec'] for s in seeds):.3f}")
for k in stats:
    vb = [b[s][k] for s in seeds if k in b[s]]
    vc = [c[s][k] for s in seeds if k in c[s]]
    print(f"  {k}: base {sum(vb)/max(1,len(vb)):.4f} cand {sum(vc)/max(1,len(vc)):.4f}")
