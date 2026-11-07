"""variants.tsv / runs.tsv の replay run を base と比べる（seed ごとに注文列の平均の log 比、全 8 本・元の列・別の 7 本）。
使い方: python3 cmp_variant.py BASE_REPLAY_RUN RUN ..."""
import json, sys, math
import numpy as np
R = '/home/sato/ahc074/runs/'
def load(run):
    d = json.load(open(R + run + '/result.json'))
    return {int(c['seed']): np.array(c['order_scores'], float) for c in d['cases'] if min(c['order_scores']) > 0}
base = load(sys.argv[1])
for run in sys.argv[2:]:
    v = load(run); seeds = sorted(set(base) & set(v))
    out = []
    for name, sl in [('all 8', slice(0, 8)), ('real list', slice(0, 1)), ('lists 1-7', slice(1, 8))]:
        x = np.array([math.log(v[s][sl].mean() / base[s][sl].mean()) * 100 for s in seeds])
        out.append(f'{name} {x.mean():+.3f} ± {x.std(ddof=1) / math.sqrt(len(x)):.3f}%')
    print(f'{run}: n={len(seeds)}  ' + '   '.join(out))
