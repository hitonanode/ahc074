# Toy model of the hole fixing of one request (trial_log "pool-"): T triangle holes at handles 1..T (the
# target's column is 0). Column c has papers X_{c,0..n-1} accessible (depth p costs depth_cost(p) extra
# moves); colors random. A filler X_{c,p} covers [lvl, c] (lvl = just past its deepest mismatch) and is
# taken if it saves at least 2 + p digs, minus 0.8 for its later return (weighted interval scheduling).
# Prints the moves per hole: how the cost falls with more candidates (= more chance matches), and
# (mode 1, 2) whether ordering the papers of a column (alternating at h_c; papers at distance 2 also
# differing at h_{c-1}) helps.
# Usage: python3 fillsim.py [T]
import random, sys


def sim(T, depth_cost, ncand, trials=3000, thr=1, charge=0.8, seed=1, mode=0):
    rnd = random.Random(seed)
    tot = 0.0
    nfill = 0
    for _ in range(trials):
        A = [rnd.getrandbits(1) for _ in range(T + 1)]
        X = [[[rnd.getrandbits(1) for _ in range(c + 1)] for p in range(ncand)] for c in range(T + 1)]
        if mode >= 1 and ncand == 4:
            for c in range(T + 1):
                col = X[c]
                col[1][c] = 1 - col[0][c]; col[2][c] = col[0][c]; col[3][c] = col[1][c]
                if mode >= 2 and c >= 1:
                    col[2][c - 1] = 1 - col[0][c - 1]; col[3][c - 1] = 1 - col[1][c - 1]
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
                cost = 1 + depth_cost(p)
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
        tot += sum(fix[1:]) - best[T + 1]
        nfill += cnt[T + 1]
    return round(tot / trials / T, 4), round(nfill / trials, 3)


T = int(sys.argv[1]) if len(sys.argv) > 1 else 24
print('T', T)
print('no fillers           ', sim(T, lambda p: p, 1, thr=10**9))
print('depth 0..3 (cost p)  ', sim(T, lambda p: p, 4))
print('2 free candidates    ', sim(T, lambda p: 0, 2))
print('4 free candidates    ', sim(T, lambda p: 0, 4))
print('8 free candidates    ', sim(T, lambda p: 0, 8))
print('16 free candidates   ', sim(T, lambda p: 0, 16))
print('depth 0..3, alternating at h_c         ', sim(T, lambda p: p, 4, mode=1))
print('  + distance 2 differing at h_{c-1}    ', sim(T, lambda p: p, 4, mode=2))
