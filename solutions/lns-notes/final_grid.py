"""Frozen phase-1 budget comparisons; all solver executions use pahcer_run.py.

Each source must implement LNS_MULTIPLIER. The manifest is written before the
first held-out case and checked before and after every run. No parameters are
chosen from these results.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, os, re, subprocess, sys

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
R = Path('/home/sato/ahc074/runs')
p = argparse.ArgumentParser()
p.add_argument('tag')
p.add_argument('--solvers', nargs='+', required=True)
p.add_argument('--budgets', nargs='+', type=int, default=[2, 4, 8])
p.add_argument('--seeds', default='500-1000')
p.add_argument('--baseline', required=True)
p.add_argument('--control', required=True)
p.add_argument('--reason', required=True)
a = p.parse_args()
assert a.control in a.solvers
assert all(n.startswith('lns-') for n in a.solvers)
for n in a.solvers:
    assert 'LNS_MULTIPLIER' in (ROOT/'solutions'/n/'main.cpp').read_text()

def hashes():
    return {n: hashlib.sha256((ROOT/'solutions'/n/'main.cpp').read_bytes()).hexdigest()
            for n in ['deval-helper-wide', *a.solvers]}

manifest = dict(vars(a), sha256=hashes(),
                frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                parameters={n:json.loads((ROOT/'solutions'/n/'config.json').read_text()) for n in a.solvers})
mp = H/(a.tag+'-frozen.json')
assert not mp.exists(), 'Use a new tag; never overwrite a frozen experiment.'
mp.write_text(json.dumps(manifest, indent=2)+'\n')

def invoke(cmd, log, env=None):
    with (H/log).open('w') as f:
        subprocess.run(cmd, cwd=ROOT, env=env, stdout=f,
                       stderr=subprocess.STDOUT, check=True)

records = []
for budget in a.budgets:
    assert hashes() == manifest['sha256']
    tag = f'{a.tag}-b{budget}'
    env = os.environ.copy()
    env['LNS_MULTIPLIER'] = str(budget-1)
    env.pop('LNS_STEPS', None)
    cmd = [sys.executable, str(H/'run.py'), '--compare',
           'solutions/deval-helper-wide', *['solutions/'+n for n in a.solvers],
           '--seeds', a.seeds, '--save-design', '--no-record', '-c',
           f'Task7 phase1 frozen {tag}; fixed iterations; research only; '+a.reason]
    invoke(cmd, tag+'-normal.log', env)
    ids = re.findall(r'run-id: (\S+)', (H/(tag+'-normal.log')).read_text())
    assert len(ids) == len(a.solvers)+1, ids
    for run in ids:
        assert json.loads((R/run/'meta.json').read_text())['status'] == 'ok'
    assert hashes() == manifest['sha256']
    invoke([sys.executable, str(H/'replay_batch.py'), tag+'-replay', *ids[1:],
            '--seeds', a.seeds], tag+'-replays.log', env)
    rows = json.loads((H/(tag+'-replay.json')).read_text())
    replays = [x['replay'] for x in rows]
    record = dict(budget=budget, normal=ids, replays=replays, solvers=a.solvers,
                  baseline=a.baseline, seeds=a.seeds, sha256=manifest['sha256'])
    records.append(record)
    (H/(a.tag+'-runs.json')).write_text(json.dumps(records, indent=2)+'\n')
    control = replays[a.solvers.index(a.control)]
    env_analysis = os.environ.copy()
    env_analysis['OPENBLAS_NUM_THREADS'] = '1'
    for key, reference, targets in [('normal', ids[0], ids[1:]),
                                   ('baseline', a.baseline, replays),
                                   ('paired', control, [x for x in replays if x != control])]:
        invoke(['flock', '-x', '/home/sato/ahc074/runs/.lock', 'nice', '-n', '10',
                sys.executable, str(H/'analyze.py'), reference, *targets,
                '--output', str(H/(tag+'-'+key+'-metrics.json'))],
               tag+'-'+key+'-metrics.log', env_analysis)
    print(json.dumps(record), flush=True)

