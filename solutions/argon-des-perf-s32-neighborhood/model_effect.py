"""Compare the perforation model to realized moves using saved designs only."""
import argparse
import json
import math
import statistics
from pathlib import Path
from exposure import load_design

here = Path(__file__).resolve().parent
runs = Path('/home/sato/ahc074/runs')
p = argparse.ArgumentParser()
p.add_argument('base')
p.add_argument('candidate')
p.add_argument('--end', type=int, default=500)
p.add_argument('--weight', type=float, required=True)
p.add_argument('--output', default='model-effect.json')
a = p.parse_args()
metrics = [json.loads((runs / r / 'metrics.json').read_text())['cases'] for r in [a.base, a.candidate]]

def cost(d):
    h = d['H']
    targets = [sum(((v >> bit) & 1) << j for j, bit in enumerate(d['handle'])) for v in d['A']]
    count = [[0, 0] for _ in range(h)]
    reset = [0] * h
    owners = [[] for _ in range(192)]
    for u, k in enumerate(d['ded']):
        owners[k].append(u)
        reset[d['columns'][k]] += 2
        for j, bit in enumerate(d['handle']):
            if not (d['papers'][2 * k] >> bit & 1):
                count[j][targets[u] >> j & 1] += 1
    value = sum(4 * .38 * (x*y + .5*r*min(x,y)) / max(1, x+y+r)
                for (x,y),r in zip(count,reset)) / 256
    return value

rows = []
for seed in range(a.end):
    values = []
    for arm, run in enumerate([a.base, a.candidate]):
        _, d = load_design(seed, run)
        m = metrics[arm][str(seed)]
        s = m['stderr']
        values.append(dict(hole=cost(d), owner=s['perf_owner_conditioned'],
                           owner_raw=s['perf_owner_raw'], donor=s['perf_donor_gain'],
                           moves=m['score']/1024))
    b, c = values
    delta = {k: c[k]-b[k] for k in b}
    # Compare both designs at the candidate coefficient, avoiding a coefficient
    # change being mistaken for a prediction of the physical move difference.
    delta['predicted'] = delta['hole'] - a.weight * (delta['owner'] + delta['donor'])
    rows.append(dict(seed=seed, base=b, candidate=c, delta=delta))
summary = {}
for k in rows[0]['delta']:
    values = [r['delta'][k] for r in rows]
    summary[k] = dict(mean=statistics.mean(values), se=statistics.stdev(values)/math.sqrt(len(values)))
prediction = [r['delta']['predicted'] for r in rows]
realized = [r['delta']['moves'] for r in rows]
summary['correlation'] = statistics.correlation(prediction, realized)
out = dict(base=a.base, candidate=a.candidate, n=len(rows), coefficient=a.weight, summary=summary, rows=rows)
(here / a.output).write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(summary, indent=2))
