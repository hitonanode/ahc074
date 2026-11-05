"""保存済みの計測値だけを集計する。whenidle.sh + flockから実行する。"""
import argparse
import json
import statistics
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('run')
p.add_argument('--output', default='stages.json')
a = p.parse_args()
root = Path('/home/sato/ahc074/runs') / a.run
cases = json.loads((root / 'metrics.json').read_text())['cases']
rows = [c['stderr'] for c in cases.values()]
def stats(v):
    v = sorted(v)
    return dict(mean=statistics.mean(v), min=min(v), max=max(v),
                p99=v[min(len(v)-1, int(.99*len(v)))])
result = dict(run=a.run, n=len(rows), stages={}, metrics={})
previous = None
for end in ['map_end_sec', 'anneal_end_sec', 'climb_end_sec', 'match_end_sec',
            'perforation_end_sec', 'helper_end_sec']:
    result['stages'][end] = stats([r[end] - (r[previous] if previous else 0) for r in rows])
    previous = end
keys = set.intersection(*(set(r) for r in rows))
for name in sorted(keys):
    if name.startswith('af_') or name in ['perforation_sec', 'colmdp_sec', 'req_sec', 'end_sec']:
        result['metrics'][name] = stats([r[name] for r in rows])
print(json.dumps(result, indent=2))
(Path(__file__).resolve().parent / a.output).write_text(json.dumps(result, indent=2)+'\n')
