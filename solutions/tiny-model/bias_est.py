#!/usr/bin/env python3
"""How much could a biased assignment lower the hole cost of the hub? (rough estimate)

U units (pairs of two targets that agree on a fraction `agree` of the handles, and singles) with
random colors on H handles; column l (0 = shallowest) has s_l units (proportional to l + 1), a
unit of column l has holes at the handles m > l, and a pair also at the handles m <= l where its
two targets differ. If the requests needing handle m want color 1 with frequency p_m (over the
targets with a hole there), and the column top keeps the last color set, a hole costs
2 p_m (1 - p_m) instead of 1/2. Simulated annealing over the assignment (swaps of units between
columns) minimizes the total; prints the cost relative to p = 1/2 (fixes per request).

Usage: bias_est.py [singles=112] [pairs=72] [H=34] [iters=200000] [agree=0.67]
"""
import math
import random
import sys

args = dict(a.split("=") for a in sys.argv[1:])
NS = int(args.get("singles", 112))
NP = int(args.get("pairs", 72))
H = int(args.get("H", 34))
iters = int(args.get("iters", 200000))
agree = float(args.get("agree", 0.67))
rnd = random.Random(1)
U = NS + NP
# targets of each unit: list of color vectors
units = []
for i in range(U):
    a = [rnd.randint(0, 1) for _ in range(H)]
    if i < NP:
        b = [x if rnd.random() < agree else 1 - x for x in a]
        units.append((a, b))
    else:
        units.append((a,))
P = NS + 2 * NP
w = [l + 1 for l in range(H)]
s = [max(1, round(U * x / sum(w))) for x in w]
while sum(s) > U:
    s[s.index(max(s))] -= 1
while sum(s) < U:
    s[-1] += 1
col = []
for l in range(H):
    col += [l] * s[l]
rnd.shuffle(col)
n = [0] * H
n1 = [0] * H


def apply(x, l, sign):
    tg = units[x]
    for m in range(H):
        hole = m > l or (len(tg) == 2 and tg[0][m] != tg[1][m])
        if not hole:
            continue
        for t in tg:
            n[m] += sign
            n1[m] += sign * t[m]


for x in range(U):
    apply(x, col[x], 1)

# alt=1: like the hub, a pair must agree at the handle of its column and every column must keep
# both colors at its handle balanced (|#0 - #1| <= 1)
ALT = int(args.get("alt", 0))


def own(x, l):  # color of unit x at the handle of column l, -1 if a pair differs there
    tg = units[x]
    if len(tg) == 2 and tg[0][l] != tg[1][l]:
        return -1
    return tg[0][l]


def balanced(l):
    c = [own(x, l) for x in range(U) if col[x] == l]
    return -1 not in c and abs(c.count(0) - c.count(1)) <= 1


if ALT:  # repair the random start: greedy swaps until every column is balanced
    for it in range(200000):
        bad = [l for l in range(H) if not balanced(l)]
        if not bad:
            break
        a = rnd.choice([x for x in range(U) if col[x] in bad])
        b = rnd.randrange(U)
        la, lb = col[a], col[b]
        before = (not balanced(la)) + (not balanced(lb))
        col[a], col[b] = lb, la
        after = (not balanced(la)) + (not balanced(lb))
        if after > before:
            col[a], col[b] = la, lb
    n[:] = [0] * H
    n1[:] = [0] * H
    for x in range(U):
        apply(x, col[x], 1)
    print("unbalanced columns after repair:", sum(not balanced(l) for l in range(H)))


DIG = int(args.get("dig", 0))  # dig=1: add the digs sum_l targets_l (s_l - 1) / 2


def digs():
    tg = [0] * H
    for x in range(U):
        tg[col[x]] += len(units[x])
    return sum(tg[l] * (s[l] - 1) / 2 for l in range(H)) / P


def cost():
    c = sum(2 * n1[m] * (n[m] - n1[m]) / n[m] for m in range(H) if n[m]) / P
    return c + (digs() if DIG else 0)


base = sum(n) / P * 0.5
c = cost()
print(f"holes per request {sum(n)/P:.2f}, fixes at p=1/2 {base:.3f}, random assignment {c:.3f}"
      + (f" (digs {digs():.3f})" if DIG else ""))
T0 = 0.01
for it in range(iters):
    a, b = rnd.randrange(U), rnd.randrange(U)
    if col[a] == col[b]:
        continue
    la, lb = col[a], col[b]
    if ALT:
        ok_before = balanced(la) and balanced(lb)
        col[a], col[b] = lb, la
        ok = balanced(la) and balanced(lb)
        col[a], col[b] = la, lb
        if ok_before and not ok:
            continue
    apply(a, la, -1)
    apply(b, lb, -1)
    apply(a, lb, 1)
    apply(b, la, 1)
    nc = cost()
    temp = T0 * (1 - it / iters) + 1e-7
    if nc <= c or rnd.random() < math.exp((c - nc) / temp):
        c = nc
        col[a], col[b] = lb, la
    else:
        apply(a, lb, -1)
        apply(b, la, -1)
        apply(a, la, 1)
        apply(b, lb, 1)
if DIG:
    d = digs()
    print(f"optimized: fixes {c - d:.3f} ({(c - d) / base * 100 - 100:+.1f}%), digs {d:.3f}")
else:
    print(f"optimized assignment {c:.3f} ({(c / base - 1) * 100:+.1f}% of the fixes)")
print("majority share by depth:", " ".join(f"{100 * max(n1[m], n[m] - n1[m]) // max(1, n[m])}" for m in range(H)))
