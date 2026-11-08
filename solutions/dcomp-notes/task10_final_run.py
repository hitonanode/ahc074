"""Frozen Task 10 normal comparison and independent fixed-design replay.

All cases still execute through pahcer_run.py via task10_run.py. The normal
comparison is recorded; replay is unrecorded by pahcer's normal rules.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
NOTES = ROOT / 'solutions/dcomp-notes'
PY = '/home/sato/ahc074/.venv/bin/python'
LOCK = ['flock', '-x', '/home/sato/ahc074/runs/.lock', 'nice', '-n', '10']
SOURCE = ROOT / 'solutions/dcomp-combo-alt1/main.cpp'
FROZEN = '8fae7ff4cbfa331797ef8f3f6835cf6ad912f04fa5a94f3fa084e11a563f97c6'


def run(cmd, log):
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == FROZEN
    path = NOTES / log
    assert not path.exists(), f'Already exists: {path}; do not overwrite a run log'
    print('RUN', cmd, flush=True)
    with path.open('w') as f:
        subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, check=True)
    print('DONE', path.name, flush=True)
    return path


def ids(log):
    return re.findall(r'^\[pahcer_run\] run-id: (\S+)$', log.read_text(), re.M)


runner = [sys.executable, str(NOTES / 'task10_run.py')]
normal = run(runner + ['--compare', 'solutions/argon-des-perf-latew105',
                      'solutions/legal-tie-fix', 'solutions/combo-m1-nine',
                      'solutions/dcomp-combo-alt1', '--seeds', '0-2000',
                      '--save-design', '-c', 'Task10 frozen final: compiler-specific exact speedups, ALT gap1 eject2 NW6; fixed budgets'],
             't10-final-normal.log')
runs = ids(normal)
assert len(runs) == 4
run(LOCK + [PY, str(NOTES / 'task10_final_stats.py'), *runs,
            '--output', str(NOTES / 't10-final-normal.json')], 't10-final-normal-stats.log')
identity_path = NOTES / 't10-final-design-identity.json'
run(LOCK + [PY, str(NOTES / 'task10_identity.py'), runs[2], runs[3],
            '--design', '--seeds', '0-2000', '--output', str(identity_path)],
    't10-final-design-identity.log')
identity = json.loads(identity_path.read_text())
assert identity['same'] == identity['n'] == 2000, identity

replay = run(runner + ['--compare', 'solutions/combo-m1-nine',
                      'solutions/dcomp-combo-alt1', '--design-from', runs[2],
                      '--orders', '4', '--seeds', '0-2000', '-c',
                      'Task10 frozen final replay: same nine-candidate designs, untouched new orders 1-3'],
             't10-final-replay.log')
replays = ids(replay)
assert len(replays) == 2
run(LOCK + [PY, str(NOTES / 'task10_replay_stats.py'), *replays,
            '--output', str(NOTES / 't10-final-replay.json')], 't10-final-replay-stats.log')
print('All final checks completed.', runs, replays, flush=True)
