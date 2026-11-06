"""同じケースで設計だけが違う run（キャップの窓を入れ替えた版）を並べ、
ケース内で手数がどの操作で違うか、設計の評価値がその違いを予測するかを調べる。
使い方: python3 design_var.py RUN1 RUN2 ...（同じ seed の集合）"""
import sys, json, re, math, collections
from pathlib import Path
ROOT = Path('/home/sato/ahc074/runs')
runs = sys.argv[1:]
MET = ['model_cost', 'model_col', 'model_hole', 'model_gc', 'd2_model_final', 'd2_filler_final', 'gobj_after', 'perforation_holes']
LAB = ['dig', 'fix', 'gen', 'fret', 'lift', 'ret', 'repair', 'fill', 'relevel', 'fdig', 'reuse', 'help', 'hdig']
data = {}  # (run, seed) -> dict
for r in runs:
    res = json.load(open(ROOT / r / 'result.json'))
    cases = res['cases'] if isinstance(res, dict) and 'cases' in res else res
    for c in cases:
        s = int(c['seed'])
        if c['score'] <= 0: continue
        t = (ROOT / r / 'err' / f'{s:04d}.txt').read_text()
        d = {'T': c['score'] / 1024.0}
        for m in MET:
            mm = re.search(rf'^{m} = ([-0-9.e+]+)', t, re.M)
            d[m] = float(mm.group(1)) if mm else float('nan')
        cnt = collections.Counter()
        for line in t.splitlines():
            if line.startswith('@ops '):
                for tok in line.split('=', 1)[1].split():
                    lab, _, n = tok.partition('*')
                    cnt[lab] += int(n) if n else 1
        for l in LAB: d[l] = cnt[l] / 1024.0
        data[(r, s)] = d
seeds = sorted({s for (_, s) in data if all((r, s) in data for r in runs)})
keys = ['T'] + LAB + MET
# remove each run's global mean (systematic effects such as the biased cap), then within-seed deviations
gm = {r: {k: sum(data[(r, s)][k] for s in seeds) / len(seeds) for k in keys} for r in runs}
dev = {k: [] for k in keys}
for s in seeds:
    vals = {k: [data[(r, s)][k] - gm[r][k] for r in runs] for k in keys}
    for k in keys:
        m = sum(vals[k]) / len(runs)
        dev[k].append([v - m for v in vals[k]])
def cov(a, b):
    n = 0; t = 0.0
    for xa, xb in zip(a, b):
        for u, v in zip(xa, xb): t += u * v
        n += len(xa) - 1
    return t / n
vT = cov(dev['T'], dev['T'])
print(f'{len(runs)} designs per seed, {len(seeds)} seeds; mean moves/order {sum(data[(runs[0], s)]["T"] for s in seeds)/len(seeds):.3f}')
print(f'within-seed SD of moves/order between designs: {math.sqrt(vT):.4f} ({math.sqrt(vT)/10.08*100:.2f}% of the score)')
print('share of the within-seed variance by label (cov(label, total)/var(total)), and the label\'s own within-seed SD:')
for l in LAB:
    print(f'  {l:8s} share {cov(dev[l], dev["T"]) / vT:+.3f}   SD {math.sqrt(cov(dev[l], dev[l])):.4f}')
print('design metrics: within-seed correlation with moves/order, and slope (moves/order per unit):')
for m in MET:
    vm = cov(dev[m], dev[m])
    if vm <= 0 or math.isnan(vm): continue
    c = cov(dev[m], dev['T'])
    print(f'  {m:18s} corr {c / math.sqrt(vm * vT):+.3f}  slope {c / vm:+.3f}  SD {math.sqrt(vm):.4f}')
