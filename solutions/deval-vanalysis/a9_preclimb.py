"""仕上げ前の V3 の climb の効果: 候補 1 つの設計で、climb あり（pre1）となし（base1）の本当の手数を注文列 8 本で比べる。
使い方: a9_preclimb.py <base1 の replay> <pre1 の design run> <pre1 の replay>"""
import json, re, sys, math
from pathlib import Path
import numpy as np
R = Path('/home/sato/ahc074/runs')
def scores(run):
    return {int(c['seed']): np.array(c['order_scores'], float) / 1024 for c in json.load(open(R / run / 'result.json'))['cases'] if c.get('order_scores') and min(c['order_scores']) > 0}
def vals(run, keys):
    out = {}
    for f in (R / run / 'err').glob('*.txt'):
        t = f.read_text(errors='ignore')
        try: out[int(f.stem)] = [float(re.findall(rf'^{k} = (\S+)$', t, re.M)[-1]) for k in keys]
        except IndexError: pass
    return out
b, d, r = sys.argv[1:4]
base, new = scores(b), scores(r)
v = vals(d, ['dv_preclimb_tried', 'dv_preclimb_accepted', 'dv_preclimb_before', 'dv_preclimb_after', 'dv_preclimb_sec'])
seeds = sorted(set(base) & set(new) & set(v))
dv = np.array([v[s][3] - v[s][2] for s in seeds])
for name, sl in [('lists 1-7', slice(1, 8)), ('all 8', slice(0, 8)), ('real', slice(0, 1))]:
    pct = np.array([math.log(new[s][sl].mean() / base[s][sl].mean()) * 100 for s in seeds])
    dy = np.array([new[s][sl].mean() - base[s][sl].mean() for s in seeds])
    print(f'{name:9s}: true change {pct.mean():+.3f} ± {pct.std(ddof=1)/math.sqrt(len(pct)):.3f}%  ({dy.mean():+.5f} moves/order)  slope on dV3 {np.polyfit(dv, dy, 1)[0]:+.2f}')
a = np.array([v[s] for s in seeds])
print(f'n={len(seeds)} tried {a[:,0].mean():.0f} accepted {a[:,1].mean():.1f}/case  dV3 {dv.mean():+.5f} moves/order ({100*dv.mean()/10.08:+.3f}%)  sec {a[:,4].mean():.2f}')
