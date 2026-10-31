#!/usr/bin/env python3
"""How much could a biased assignment lower the hole cost of the hub? (rough estimate)

U units with random colors on H handles; column l (0 = shallowest) has s_l units, a unit of
column l has holes at the handles m > l. If the requests needing handle m want color 1 with
probability p_m (fraction over the units with a hole there), and the column top keeps the last
color set, a hole costs 2 p_m (1 - p_m) instead of 1/2. Local search over the assignment (swaps of
units between columns) minimizes the total; prints the cost relative to p = 1/2.
"""
import random
import sys

U = int(sys.argv[1]) if len(sys.argv) > 1 else 184
H = int(sys.argv[2]) if len(sys.argv) > 2 else 34
iters = int(sys.argv[3]) if len(sys.argv) > 3 else 200000
rnd = random.Random(1)
# column sizes proportional to l + 1 (deeper columns larger, as hub5 slope = 1)
w = [l + 1 for l in range(H)]
s = [max(1, round(U * x / sum(w))) for x in w]
while sum(s) > U:
    s[s.index(max(s))] -= 1
while sum(s) < U:
    s[-1] += 1
colors = [[rnd.randint(0, 1) for _ in range(H)] for _ in range(U)]
col = []
for l in range(H):
    col += [l] * s[l]
rnd.shuffle(col)
# n1[m], n[m]: units with a hole at m (column < m) and how many of them have color 1
def counts():
    n = [0] * H
    n1 = [0] * H
    for u in range(U):
        for m in range(col[u] + 1, H):
            n[m] += 1
            n1[m] += colors[u][m]
    return n, n1
def cost(n, n1):
    tot = 0.0
    for m in range(H):
        if n[m]:
            p = n1[m] / n[m]
            tot += n[m] * 2 * p * (1 - p)
    return tot / U
n, n1 = counts()
base = sum(n) / U * 0.5
c = cost(n, n1)
print(f"holes per request {sum(n)/U:.2f}, cost at p=1/2 {base:.3f}, random assignment {c:.3f}")
T = 0.02
for it in range(iters):
    a, b = rnd.randrange(U), rnd.randrange(U)
    if col[a] == col[b]:
        continue
    # swap the columns of a and b
    def apply(u, l_old, l_new, sign):
        for m in range(l_old + 1, H):
            n[m] -= sign
            n1[m] -= sign * colors[u][m]
        for m in range(l_new + 1, H):
            n[m] += sign
            n1[m] += sign * colors[u][m]
    la, lb = col[a], col[b]
    apply(a, la, lb, 1)
    apply(b, lb, la, 1)
    nc = cost(n, n1)
    temp = T * (1 - it / iters) + 1e-6
    if nc <= c or rnd.random() < pow(2.718, (c - nc) / temp):
        c = nc
        col[a], col[b] = lb, la
    else:
        apply(a, lb, la, 1)
        apply(b, la, lb, 1)
print(f"optimized assignment {c:.3f} ({(c / base - 1) * 100:+.1f}% of the hole cost)")
ps = [n1[m] / n[m] if n[m] else 0.5 for m in range(H)]
print("p_m:", " ".join(f"{max(p, 1 - p):.2f}" for p in ps))
