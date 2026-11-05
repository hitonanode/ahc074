"""Check saved evaluation artifacts; run through whenidle.sh and the shared lock."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import statistics as st
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('log')
p.add_argument('--label', required=True)
p.add_argument('--seeds', type=int, required=True)
p.add_argument('--orders', type=int, default=1)
a = p.parse_args()
here = Path(__file__).resolve().parent
root = Path('/home/sato/ahc074/runs')
names = list(dict.fromkeys(re.findall(r'run-id: (\S+)', Path(a.log).read_text())))
assert len(names) == 2, names
subprocess.run([sys.executable, 'solutions/argon-req-completeold/analyze.py', *names,
                '--end', str(a.seeds), '--json', str(here / (a.label + '-results.json'))], check=True)
metric = re.compile(r'^(\w+) = ([-+\d.eE]+)$', re.M)
rows = [[], []]
identical = 0
score_savings = []
source = (here / 'main.cpp').read_bytes()
assert (root / names[1] / 'src/main.cpp').read_bytes() == source
for side, name in enumerate(names):
    cases = json.loads((root / name / 'result.json').read_text())['cases']
    assert sorted(c['seed'] for c in cases) == list(range(a.seeds))
    assert all(len(c.get('order_scores', [c['score']])) == a.orders for c in cases)
    assert all(c['score'] > 0 and all(x > 0 for x in c.get('order_scores', [])) for c in cases)
for seed in range(a.seeds):
    for j in range(a.orders):
        dirs = [root / name if j == 0 else root / name / 'orders' / str(j) for name in names]
        err = [(r / 'err' / f'{seed:04d}.txt').read_text() for r in dirs]
        out = [(r / 'out' / f'{seed:04d}.txt').read_bytes() for r in dirs]
        identical += out[0] == out[1]
        assert out[0].splitlines()[:192] == out[1].splitlines()[:192], ('design', seed, j)
        assert [[s for s in text.splitlines() if s.startswith('@paper ')] for text in err][0] == \
               [[s for s in text.splitlines() if s.startswith('@paper ')] for text in err][1], ('paper', seed, j)
        base_keys = [key for key, _ in metric.findall(err[0])]
        base_names = set(base_keys)
        candidate_keys = [key for key, _ in metric.findall(err[1]) if key in base_names]
        assert candidate_keys == base_keys, ('metric names/order', seed, j)
        for side, text in enumerate(err):
            m = {k: float(v) for k, v in metric.findall(text)}
            assert m['self_wrong'] == m['op_label_errors'] == 0, (side, seed, j)
            assert m['plan_failures'] == m['unsafe_plans'] == 0, (side, seed, j)
            if a.orders == 2:
                assert m['design_loaded'] == 1
            rows[side].append(m)
        score_savings.append(rows[0][-1]['total_moves'] - rows[1][-1]['total_moves'])
paired = {}
for key in ('req_sec', 'helper_end_sec', 'map_end_sec', 'judge'):
    def value(m):
        return m[key] if key != 'judge' else m['end_sec'] + .04*m['helper_end_sec'] + .35*m['req_sec']
    differences = [value(y)-value(x) for x, y in zip(*rows)]
    # Timings are diagnostic; report seed-clustered SE for multiple order sequences.
    clustered = [st.mean(differences[i:i+a.orders]) for i in range(0, len(differences), a.orders)]
    paired[key] = {'mean': st.mean(clustered), 'se': st.stdev(clustered)/math.sqrt(len(clustered))}
local = {key: st.mean(m[key] for m in rows[1]) for key in rows[1][0] if key.startswith('value_seed_')}
local['realized_saved_moves'] = st.mean(score_savings)
local['predicted_realized_ratio'] = local['realized_saved_moves']/local['value_seed_gain']
details = {'runs': names, 'identical_stdout': identical, 'cases': len(rows[0]),
           'paired_times': paired, 'local_gain': local, 'source_sha256': hashlib.sha256(source).hexdigest()}
(here / (a.label+'-details.json')).write_text(json.dumps(details, indent=2)+'\n')
print('All cases have WA/self_wrong/op_label_errors/plan_failures/unsafe_plans = 0; designs and @paper identical.')
print('All existing metric names and their order retained.')
print('Unchanged stdout', identical, '/', len(rows[0]))
print('Paired timing differences', paired)
print('Additional eject yield and realization', local)
print('Archived source matches current source, SHA256', details['source_sha256'])
