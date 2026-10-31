# Toy model (variant of solutions/pool-value/fillsim.py) of the hole fixing of one request with
# "signature columns": every paper of column c has the SAME colors on handles c-k..c-1 (k = signature
# length), so a filler from column c covers [c-k, c] whenever the target matches the signature, whatever
# the rotation state. T triangle holes at handles 1..T (target's column is 0); column c has papers at
# depth 0..3 (depth p costs p extra digs), alternating at h_c. A filler covering [lvl, c] is taken if it
# saves >= thr + its cost, minus `charge` for its later return (weighted interval scheduling).
# Prints moves per hole for k = 0 (no signature; = fillsim "depth 0..3") .. T.
# Usage: python3 sigsim.py [T]
import random, sys


def sim(T, k, ncand=4, trials=4000, thr=1, charge=0.8, seed=1, select=1):
    rnd = random.Random(seed)
    tot = 0.0
    nfill = 0
    for _ in range(trials):
        # `select` independent targets; keep the cheapest (crude model of choosing the column per target).
        best_cost = None
        best_cnt = 0
        sigs = [[rnd.getrandbits(1) for _ in range(c + 1)] for c in range(T + 1)]
        X = []
        for c in range(T + 1):
            col = []
            for p in range(ncand):
                x = [rnd.getrandbits(1) for _ in range(c + 1)]
                for j in range(max(1, c - k), c):
                    x[j] = sigs[c][j]
                col.append(x)
            col[1][c] = 1 - col[0][c]; col[2][c] = col[0][c]; col[3][c] = col[1][c]
            X.append(col)
        for _s in range(select):
            A = [rnd.getrandbits(1) for _ in range(T + 1)]
            fix = [0] * (T + 1)
            for j in range(1, T + 1):
                fix[j] = 1 if X[j][0][j] != A[j] else 0
            cands = [[] for _ in range(T + 1)]
            for c in range(1, T + 1):
                for p in range(ncand):
                    x = X[c][p]
                    if x[c] != A[c]:
                        continue
                    lvl = 1
                    for j in range(c, 0, -1):
                        if x[j] != A[j]:
                            lvl = j + 1
                            break
                    save = sum(fix[j] for j in range(lvl, c + 1) if (j != c or p > 0))
                    cost = 1 + p
                    if save - cost >= thr:
                        cands[c].append((lvl, save - cost - charge))
            best = [0.0] * (T + 2)
            cnt = [0] * (T + 2)
            for c in range(1, T + 1):
                best[c + 1] = best[c]
                cnt[c + 1] = cnt[c]
                for (lvl, g) in cands[c]:
                    if best[lvl] + g > best[c + 1]:
                        best[c + 1] = best[lvl] + g
                        cnt[c + 1] = cnt[lvl] + 1
            cost_here = sum(fix[1:]) - best[T + 1]
            if best_cost is None or cost_here < best_cost:
                best_cost = cost_here
                best_cnt = cnt[T + 1]
        tot += best_cost
        nfill += best_cnt
    return round(tot / trials / T, 4), round(nfill / trials, 3)


T = int(sys.argv[1]) if len(sys.argv) > 1 else 16
print('T', T, '(moves per hole, fillers per request)')
for k in [0, 1, 2, 3, 4, 6, 8, T]:
    print(f'signature k={k:<2}            ', sim(T, k))
for k in [0, 4, 8]:
    print(f'signature k={k:<2}, best of 8 ', sim(T, k, select=8))
