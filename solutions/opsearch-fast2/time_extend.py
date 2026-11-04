"""Use the evaluation script for a one-seed comparison and an immediate binary reuse extension."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
from experiment import summarize
folder = Path(__file__).resolve().parent
root = folder.parents[1]
env = dict(os.environ, F2_MODE='2')
base = [str(root / 'scripts/pahcer_run.py')]
first = base + ['--compare', 'solutions/esw-fixiter', 'solutions/opsearch-fast', 'solutions/opsearch-fast2',
                '--design-from', '20261104-224750_esw-fixiter', '--seeds', '0-1', '--orders', '2',
                '--no-record', '-c', 'upper timing: prepare binaries for immediate extension']
log_path = folder / 'experiments/upper-extended.log'
def execute(command, log):
    lines = []
    proc = subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        lines.append(line)
        log.write(line)
        if 'run-id:' in line or '待っています' in line or '警告:' in line:
            print(line, end='', flush=True)
    assert proc.wait() == 0
    return ''.join(lines)
with log_path.open('w') as log:
    out = execute(first, log)
    ids = re.findall(r'\[pahcer_run\] run-id: (\S+)', out)
    assert len(ids) == 3
    second = base + ['--extend', *ids, '--seeds', '0-100', '--orders', '2', '--no-record',
                     '-c', 'upper timing: extend the same binaries to 100 seeds x 2 orders']
    execute(second, log)
result = summarize(ids)
result.update({'label': 'upper-extended', 'settings': {'F2_MODE': '2'}, 'command': [first, second]})
result['extensions'] = [json.loads((Path('/home/sato/ahc074/runs') / run / 'meta.json').read_text()).get('extensions') for run in ids]
(folder / 'experiments/upper-extended.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ('runs','seeds','orders')}, ensure_ascii=False), flush=True)
for arm in result['arms']:
    print(arm['run'], arm['moves'], arm['req_sec_mean'], arm['time_ratio'], flush=True)
