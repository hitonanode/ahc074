"""Compares two run1.py result files (`seed score` lines): mean log ratio (%), stderr, W/D/L.
usage: cmp.py <base.txt> <cand.txt>"""
import math, sys
def load(p):
    d = {}
    for line in open(p):
        a = line.split()
        if len(a) >= 2 and a[0].isdigit(): d[int(a[0])] = int(a[1])
    return d
b, c = load(sys.argv[1]), load(sys.argv[2])
xs = [math.log(c[s] / b[s]) * 100 for s in b if s in c and b[s] > 0 and c[s] > 0]
n = len(xs); m = sum(xs) / n
se = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1) / n) if n > 1 else 0
w = sum(x < 0 for x in xs); l = sum(x > 0 for x in xs)
print(f"n={n} diff={m:+.3f}% se={se:.3f}% W/D/L={w}/{n-w-l}/{l} base={sum(b[s] for s in b)/len(b):.1f} cand={sum(c[s] for s in c)/len(c):.1f}")
