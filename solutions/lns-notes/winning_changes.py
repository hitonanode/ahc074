"""Join paired fresh-list cost to physical design changes (descriptive, not causal).

Run under the common flock with nice. No solver is executed.
"""
from pathlib import Path
import argparse, json, math, statistics, collections, re

R = Path('/home/sato/ahc074/runs')
ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('base_replay'); p.add_argument('candidate_replay')
p.add_argument('--base-design', required=True); p.add_argument('--candidate-design', required=True)
p.add_argument('--output', required=True)
a = p.parse_args()

def read(run):
    d = R / run
    assert json.loads((d / 'meta.json').read_text())['status'] == 'ok'
    return {c['seed']: c for c in json.loads((d / 'result.json').read_text())['cases']}

bc, cc = read(a.base_replay), read(a.candidate_replay)

def design_path(run, seed):
    tokens = (ROOT / 'tools/in' / f'{seed:04d}.txt').read_text().split()
    h = 0xcbf29ce484222325
    for barcode in tokens[4:260]:
        assert len(barcode) == 64
        v = int(barcode[::-1], 2)
        for byte in v.to_bytes(8, 'little'):
            h = ((h ^ byte) * 0x100000001b3) & ((1 << 64) - 1)
    return R / run / 'design' / f'{h:016x}.txt'

def parse(path):
    out = {}
    for line in path.read_text().split('\nstderr ')[0].splitlines():
        t = line.split()
        if t[0] in ['permutation', 'edge', 'polarity', 'ded', 'columns', 'handle', 'A', 'papers']:
            out[t[0]] = list(map(int, t[2:]))
        elif t[0] in ['M', 'G', 'H']:
            out[t[0]] = int(t[1])
    return out

def feature(d):
    windows = [None] * 64
    for i in range(d['G']):
        windows[d['permutation'][i]] = (tuple(d['edge'][2*i:2*i+2]), d['polarity'][i])
    members = collections.defaultdict(list)
    for t, k in enumerate(d['ded']): members[k].append(t)
    pairs = {tuple(v) for v in members.values() if len(v) == 2}
    extra, distance = 0, 0
    for k, ts in members.items():
        col = d['columns'][k]
        natural = sum(1 << d['handle'][j] for j in range(col + 1))
        if len(ts) == 2:
            diff = d['A'][ts[0]] ^ d['A'][ts[1]]
            natural &= ~diff
            distance += diff.bit_count()
        extra += (natural & ~d['papers'][2*k]).bit_count()
    depths = [d['columns'][d['ded'][t]] for t in range(256)]
    return windows, pairs, extra, distance / 71, statistics.mean(depths)

def stat(v):
    return {'n': len(v), 'mean': statistics.mean(v),
            'se': statistics.stdev(v)/math.sqrt(len(v)) if len(v)>1 else 0}

rows = []
for seed in sorted(set(bc) & set(cc)):
    b, c = feature(parse(design_path(a.base_design, seed))), feature(parse(design_path(a.candidate_design, seed)))
    before, after = (statistics.mean(d[seed]['order_scores'][1:8])/1024 for d in [bc, cc])
    row = {'seed': seed, 'moves': after-before, 'pct': 100*math.log(after/before),
           'windows_changed': sum(x != y for x, y in zip(b[0], c[0])),
           'new_pairs': len(c[1]-b[1]), 'extra_holes_delta': c[2]-b[2],
           'pair_hamming_delta': c[3]-b[3], 'target_column_delta': c[4]-b[4]}
    vals = []
    for run in [a.base_design, a.candidate_design]:
        t = (R/run/'err'/f'{seed:04d}.txt').read_text()
        vals.append({k: float(v) for k, v in re.findall(r'^([a-zA-Z][a-zA-Z0-9_]*) = ([-+0-9.eE]+)$', t, re.M)})
    for key in ['model_cost', 'model_col', 'model_hole', 'model_gc', 'd2_model_final', 'dv_best']:
        if all(key in v for v in vals): row[key+'_delta'] = vals[1][key]-vals[0][key]
    rows.append(row)

out = {'n': len(rows), 'groups': {}, 'best_cases': sorted(rows, key=lambda r:r['moves'])[:12],
       'worst_cases': sorted(rows, key=lambda r:r['moves'])[-12:],
       'note': 'Conditioning on observed wins is descriptive; labels and correlated changes are not causal attribution.'}
groups = {'all': rows, 'changed_windows': [r for r in rows if r['windows_changed']],
          'same_windows': [r for r in rows if not r['windows_changed']],
          'changed_and_better': [r for r in rows if r['windows_changed'] and r['moves'] < 0]}
for name, rr in groups.items():
    out['groups'][name] = {k: stat([r[k] for r in rr]) for k in rows[0] if k != 'seed'} if rr else {'n': 0}
Path(a.output).write_text(json.dumps(out, indent=2)+'\n')
print(json.dumps(out, indent=2))
