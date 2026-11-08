"""Verify load-warned fixed diagnostic replays without changing a solver."""
from pathlib import Path
import json, re, subprocess, sys

h = Path(__file__).resolve().parent
root = h.parents[1]
r = Path('/home/sato/ahc074/runs')

def read(path):
    return json.loads(path.read_text())

def warned(meta):
    x = meta.get('outside_load') or {}
    return x.get('mean_cores', 0) > .5 or x.get('max_cores', 0) > 3

rows = read(h/'diagnostic-joint-fixed.json') + read(h/'diagnostic-star-fixed-new.json')
assert len(rows) == 16
out = {'done': False, 'checked_replays': len(rows), 'checks': {}}
dest = h/'clean-candidate-checks.json'
if dest.exists():
    out = read(dest)
for row in rows:
    original = row['replay']
    meta = read(r/original/'meta.json')
    assert meta['status'] == 'ok'
    if not warned(meta) or original in out['checks']:
        continue
    attempts = []
    for attempt in range(1, 4):
        tag = f'clean-candidate-{original}-{attempt}'
        log = h/(tag+'.log')
        with log.open('w') as f:
            subprocess.run([sys.executable, str(h/'run.py'), 'solutions/deval-helper-wide',
                            '--design-from', row['source'], '--orders', str(row['orders']),
                            '--seeds', row['seeds'], '-c',
                            f'Task7 diagnostic replay load check: {original}; attempt {attempt}'],
                           cwd=root, stdout=f, stderr=subprocess.STDOUT, check=True)
        ids = re.findall(r'run-id: (\S+)', log.read_text())
        assert len(ids) == 1
        repeated = ids[0]
        mm = read(r/repeated/'meta.json')
        assert mm['status'] == 'ok'
        identity_path = h/(tag+'-identity.json')
        with (h/(tag+'-identity.log')).open('w') as f:
            subprocess.run(['flock', '-x', str(r/'.lock'), 'nice', '-n', '10',
                            sys.executable, str(h/'identity_orders.py'), original, repeated,
                            '--output', str(identity_path)],
                           cwd=root, stdout=f, stderr=subprocess.STDOUT, check=True)
        identity = read(identity_path)
        assert identity['identical'] == identity['n_outputs'] == 800
        attempts.append({'replay': repeated, 'load': mm.get('outside_load'), 'identity': identity})
        if not warned(mm):
            break
    assert not warned(mm), ('No clean repetition', original, attempts)
    out['checks'][original] = {'original_load': meta.get('outside_load'),
                               'clean_replay': repeated, 'attempts': attempts}
    dest.write_text(json.dumps(out, indent=2)+'\n')
    print('Verified', original, repeated, flush=True)
out['done'] = True
dest.write_text(json.dumps(out, indent=2)+'\n')
print('All fixed candidate replay load checks complete.', flush=True)
