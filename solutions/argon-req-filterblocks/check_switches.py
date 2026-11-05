"""Exercise experimental paths through pahcer only. Single-solution runs isolate env overrides."""
from pathlib import Path
import json
import os
import re
import subprocess
import sys

here = Path(__file__).resolve().parent
records = []
cases = [
    ('wide-trace', '0-4', '1', {'F3_MODE': '2', 'F3_NS_TRIPLES': '1', 'F3_NS_INTERIOR': '4',
                              'F3_HEAVY_TRACE': '1', 'F3_HEAVY_PREDICT': '1'}),
    ('uncached-mdpoff', '0-8', '2', {'F3_MEMO': '0', 'F3_PREFIX': '0', 'COLMDP': '0'}),
]
for label, seeds, orders, overrides in cases:
    names = []
    for name in ['argon-des-perf-stratacut', 'argon-req-filterblocks']:
        log = here / f'switch-{label}-{name}.log'
        cmd = [sys.executable, 'scripts/pahcer_run.py', 'solutions/' + name,
               '--design-from', '20261106-032942_argon-des-perf-stratacut',
               '--seeds', seeds, '--orders', orders, '-c', 'Exact filter switch equality: ' + label]
        print(label, name, overrides, flush=True)
        with log.open('w') as out:
            subprocess.run(cmd, env={**os.environ, **overrides}, stdout=out, stderr=subprocess.STDOUT, check=True)
        run = re.search(r'run-id: (\S+)', log.read_text())
        assert run, log
        names.append(run[1])
    records.append({'case': label, 'env': overrides, 'runs': names})
    (here / 'switch-runs.json').write_text(json.dumps(records, indent=2) + '\n')
print('All switch evaluations completed through pahcer; compare saved artifacts separately.', flush=True)
