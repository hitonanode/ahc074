"""2 つの設計（同じ seed、同じ解法、設計だけ違う）を、同じ注文列 Q 本で処理した結果から、
設計どうしの手数の差を「設計の良し悪し（どの注文列でも同じ向き）」と「注文列との相性」に分ける。
使い方: python3 decompose.py RUN_A RUN_B   （どちらも --design-from ... --orders Q の run）"""
import sys, json, re, math, collections
from pathlib import Path
ROOT = Path('/home/sato/ahc074/runs')
A, B = sys.argv[1], sys.argv[2]
LAB = ['dig', 'fix', 'gen', 'fret', 'lift', 'ret', 'repair', 'fill', 'relevel', 'fdig', 'reuse', 'help', 'hdig']
MET = ['model_cost', 'model_hole', 'model_col', 'model_gc', 'd2_model_final']
def load(run):
    res = json.load(open(ROOT / run / 'result.json'))
    cases = res['cases'] if isinstance(res, dict) and 'cases' in res else res
    out = {}
    for c in cases:
        s = int(c['seed'])
        sc = c.get('order_scores') or [c['score']]
        if any(x <= 0 for x in sc): continue
        per = []
        for j in range(len(sc)):
            p = ROOT / run / ('err' if j == 0 else f'orders/{j}/err') / f'{s:04d}.txt'
            t = p.read_text()
            cnt = collections.Counter()
            for line in t.splitlines():
                if line.startswith('@ops '):
                    for tok in line.split('=', 1)[1].split():
                        lab, _, n = tok.partition('*'); cnt[lab] += int(n) if n else 1
            d = {'T': sc[j] / 1024.0}
            for l in LAB: d[l] = cnt[l] / 1024.0
            if j == 0:
                for m in MET:
                    mm = re.search(rf'^{m} = ([-0-9.e+]+)', t, re.M); d[m] = float(mm.group(1)) if mm else float('nan')
            per.append(d)
        out[s] = per
    return out
da, db = load(A), load(B)
seeds = sorted(set(da) & set(db))
Q = len(da[seeds[0]])
keys = ['T'] + LAB
# D[s][q][k] = A - B
D = {s: [{k: da[s][q][k] - db[s][q][k] for k in keys} for q in range(Q)] for s in seeds}
mean_shift = sum(sum(x['T'] for x in D[s]) / Q for s in seeds) / len(seeds)
def within(k1, k2):  # mean over seeds of the within-seed covariance across the Q sequences (Q-1 df)
    t = 0.0
    for s in seeds:
        m1 = sum(x[k1] for x in D[s]) / Q; m2 = sum(x[k2] for x in D[s]) / Q
        t += sum((x[k1] - m1) * (x[k2] - m2) for x in D[s]) / (Q - 1)
    return t / len(seeds)
def between(k1, k2):  # covariance over seeds of the per-seed means over the Q sequences
    a = [sum(x[k1] for x in D[s]) / Q for s in seeds]; b = [sum(x[k2] for x in D[s]) / Q for s in seeds]
    ma = sum(a) / len(a); mb = sum(b) / len(b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (len(a) - 1)
w = within('T', 'T'); bt = between('T', 'T')
inter = w / 2                 # Var(design x sequence) per design
design = (bt - w / Q) / 2     # Var(design quality) per design
print(f'{len(seeds)} seeds, {Q} order sequences; mean shift A-B {mean_shift:+.4f} moves/order')
print(f'difference of two designs on one sequence: SD {math.sqrt(2 * (design + inter)):.4f} moves/order')
print(f'per design: design-quality SD {math.sqrt(max(design, 0)):.4f}, design x sequence SD {math.sqrt(inter):.4f} moves/order;'
      f' design-quality share {design / (design + inter):.1%}')
# sequence effect common to both designs (for scale): variance of the A-cost across sequences within seed
wa = sum(sum((x['T'] - sum(y['T'] for y in da[s]) / Q) ** 2 for x in da[s]) / (Q - 1) for s in seeds) / len(seeds)
print(f'for scale: SD of one design\'s moves/order across order sequences {math.sqrt(wa):.4f}')
print('by label: share of the design-quality part, and of the design x sequence part:')
for l in LAB:
    wl = within(l, 'T'); bl = between(l, 'T')
    dl = (bl - wl / Q) / 2; il = wl / 2
    print(f'  {l:8s} design {dl / design:+.3f}   interaction {il / inter:+.3f}')
# does the design objective predict the design-quality part?
for m in MET:
    xs = [da[s][0][m] - db[s][0][m] for s in seeds]; ys = [sum(x['T'] for x in D[s]) / Q for s in seeds]
    if any(math.isnan(x) for x in xs): continue
    mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    cxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys)); vx = sum((x - mx) ** 2 for x in xs); vy = sum((y - my) ** 2 for y in ys)
    r = cxy / math.sqrt(vx * vy)
    # correlation with the true design part = r / sqrt(design part share of the variance of the Q-mean)
    rel = (2 * design) / bt
    print(f'  {m:15s} corr with the {Q}-sequence mean difference {r:+.3f}; implied corr with the design-quality difference {r / math.sqrt(rel):+.3f}')
