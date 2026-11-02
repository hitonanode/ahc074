# usage: python3 cmp.py base.txt cand.txt ...  -> mean log ratio (cand/base) in %, SE, W/T/L over common seeds
import sys, math
def load(p):
    d = {}
    for line in open(p):
        t = line.split()
        if len(t) >= 4 and t[1] == 'sim_moves':
            d[int(t[0])] = float(t[3])
            if len(t) >= 7 and float(t[6]) != 0: print('WRONG', p, t[0], t[6])
    return d
b = load(sys.argv[1])
print(f"base {sys.argv[1]}: n={len(b)} mean={sum(b.values())/len(b):.4f}")
for p in sys.argv[2:]:
    c = load(p)
    ks = sorted(set(b) & set(c))
    r = [100 * math.log(c[k] / b[k]) for k in ks]
    m = sum(r) / len(r)
    sd = math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1))
    w = sum(x < 0 for x in r); l = sum(x > 0 for x in r)
    print(f"{p}: n={len(ks)} mean={sum(c[k] for k in ks)/len(ks):.4f} logratio={m:+.3f}% +- {sd/math.sqrt(len(r)):.3f}  W/T/L={w}/{len(r)-w-l}/{l}")
