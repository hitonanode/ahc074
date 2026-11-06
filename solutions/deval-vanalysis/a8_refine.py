"""局所改善の因果性: V3 / V16 で選んだ設計を局所改善したとき、V の下がり幅と本当の手数（注文列 8 本）の下がり幅を比べる。
使い方: a8_refine.py <refine の design run> <その replay run>（基準は deval-vbranch-o3 の設計の replay 20261107-062543）。"""
import json, re, sys, math
from pathlib import Path
import numpy as np
R = Path('/home/sato/ahc074/runs')
def scores(run):
    return {int(c['seed']): np.array(c['order_scores'], float) / 1024 for c in json.load(open(R / run / 'result.json'))['cases'] if c.get('order_scores') and min(c['order_scores']) > 0}
def stderr_vals(run, keys):
    out = {}
    for f in (R / run / 'err').glob('*.txt'):
        t = f.read_text(errors='ignore')
        try: out[int(f.stem)] = [float(re.findall(rf'^{k} = (\S+)$', t, re.M)[-1]) for k in keys]
        except IndexError: pass
    return out
design, replay = sys.argv[1], sys.argv[2]
base = scores('20261107-062543_deval-vbranch-o3'); new = scores(replay)
keys = ['dv_refine_accepted', 'dv_refine_v3_before', 'dv_refine_v3_after', 'dv_refine_v16_before', 'dv_refine_v16_after', 'dv_refine_sec']
vals = stderr_vals(design, keys)
cand = stderr_vals('20261107-062104_deval-vbranch-o3', ['dv_candidates'])
seeds = sorted(s for s in set(base) & set(new) & set(vals) if cand.get(s, [4])[0] == 4)
acc = np.array([vals[s][0] for s in seeds]); d3 = np.array([vals[s][2] - vals[s][1] for s in seeds]); d16 = np.array([vals[s][4] - vals[s][3] for s in seeds])
for name, sl in [('lists 1-7', slice(1, 8)), ('all 8', slice(0, 8)), ('real', slice(0, 1))]:
    dy = np.array([new[s][sl].mean() - base[s][sl].mean() for s in seeds])
    pct = np.array([math.log(new[s][sl].mean() / base[s][sl].mean()) * 100 for s in seeds])
    b3 = np.polyfit(d3, dy, 1)[0] if d3.std() > 0 else float('nan')
    b16 = np.polyfit(d16, dy, 1)[0] if d16.std() > 0 else float('nan')
    print(f'{name:9s}: true change {pct.mean():+.3f} ± {pct.std(ddof=1)/math.sqrt(len(pct)):.3f}%  ({dy.mean():+.5f} moves/order)   slope on dV3 {b3:+.2f}, on dV16 {b16:+.2f}')
print(f'n={len(seeds)}  accepted swaps {acc.mean():.1f}/case  dV3 {d3.mean():+.5f}  dV16 {d16.mean():+.5f} moves/order  refine sec {np.mean([vals[s][5] for s in seeds]):.3f}')
