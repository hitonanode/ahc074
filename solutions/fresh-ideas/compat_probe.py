# Toy check of two "new" pair mechanisms against the 2-sheet comparator (random labels, no
# window-assignment optimization, so absolute rates are lower than the real 7.5%; ratios matter).
#   base   : D on top, pair (u,v) usable iff u's relations on Delta_G form a DAG.
#   cap1   : one of the G windows is replaced by a "cap" window (a permanent 1-window sheet on top of
#            the stack; D inserted at depth 0 or 1). Diffs there are free, so that window is simply
#            dropped from the relation set. Compared with the same 36 windows minus that one.
#   best1  : upper bound: drop the best single window per pair (what "1 breaker" would give).
#   depth1 : B-side shown with D at depth 1 under generic sheet s (s on top of the generic order):
#            B must equal s's color on all windows touching s; A acyclic on Delta_G minus those.
# Usage: python3 compat_probe.py [seeds]
import random, sys, itertools

M, G = 6, 36


def read(seed):
    with open(f"tools/in/{seed:04d}.txt") as f:
        f.readline()
        return [f.readline().strip() for _ in range(256)]


def acyclic(rel):
    # rel: list of (a, b) meaning a above b
    succ = {i: set() for i in range(M)}
    for a, b in rel:
        if a in succ[b]:
            return False
        succ[a].add(b)
    indeg = [0] * M
    for a in range(M):
        for b in succ[a]:
            indeg[b] += 1
    st = [i for i in range(M) if indeg[i] == 0]
    seen = 0
    while st:
        x = st.pop()
        seen += 1
        for y in succ[x]:
            indeg[y] -= 1
            if indeg[y] == 0:
                st.append(y)
    return seen == M


def run(seed, rng):
    A = read(seed)
    wins = list(range(64))
    rng.shuffle(wins)
    gw = wins[:G]
    pairs = list(itertools.combinations(range(M), 2))
    rng.shuffle(pairs)
    lab = {}
    for j, w in enumerate(gw):
        a, b = pairs[j % len(pairs)]
        pol = rng.getrandbits(1)  # color of a at w
        lab[w] = (a, b, pol)
    cap = gw[0]
    cnt = dict(base=0, cap1=0, best1=0, depth1=0, n=0)
    for u in range(256):
        for v in range(u + 1, 256):
            d = [w for w in range(64) if A[u][w] != A[v][w]]
            if len(d) > 26:
                continue
            cnt['n'] += 1
            dg = [w for w in d if w in lab]

            def rels(ws, t):
                out = []
                for w in ws:
                    a, b, pol = lab[w]
                    bit = int(A[t][w])
                    out.append((a, b) if bit == pol else (b, a))
                return out
            ok = acyclic(rels(dg, u))
            cnt['base'] += ok
            cnt['cap1'] += acyclic(rels([w for w in dg if w != cap], u))
            cnt['best1'] += ok or any(acyclic(rels([w for w in dg if w != x], u)) for x in dg)
            good = False
            for s in range(M):
                touched = [w for w in gw if s in lab[w][:2]]
                rest = [w for w in dg if w not in touched]
                if not acyclic(rels(rest, u)):
                    continue
                for B in (u, v):
                    match = True
                    for w in touched:
                        a, b, pol = lab[w]
                        col_s = pol if s == a else 1 - pol
                        if int(A[B][w]) != col_s:
                            match = False
                            break
                    if match:
                        good = True
                        break
                if good:
                    break
            cnt['depth1'] += good or ok
    return cnt


if __name__ == '__main__':
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    rng = random.Random(1)
    tot = {}
    for s in range(seeds):
        c = run(s, rng)
        for k, x in c.items():
            tot[k] = tot.get(k, 0) + x
        print(s, c, flush=True)
    n = tot['n']
    for k in ('base', 'cap1', 'best1', 'depth1'):
        print(f"{k:7s} {tot[k] / n * 100:.2f}% of {n} close pairs")
