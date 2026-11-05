"""Validate the exact one-line change, the four builds and the saved final run."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('run')
a = p.parse_args()
here = Path(__file__).resolve().parent
source = (here / 'main.cpp').read_text()
base = (here.parent / 'argon-des-perf-condbound/main.cpp').read_text()
assert source == base.replace('    perforation.run(0.5);', '    perforation.run(0.7);')
assert source != base
run = Path('/home/sato/ahc074/runs') / a.run
assert source == (run / 'src/main.cpp').read_text()
sha = hashlib.sha256(source.encode()).hexdigest()
build = json.loads((here / 'build-results.json').read_text())
assert build['sha256'] == sha
assert build['temporary_binaries_removed']
assert all(r['exit'] == 0 and r['warnings'] == 0 for r in build['results'])
assert not list(here.glob('check-*'))
cases = json.loads((run / 'metrics.json').read_text())['cases']
assert len(cases) == 2000
assert all(c['score'] > 0 and c['stderr']['self_wrong'] == 0 and c['stderr']['op_label_errors'] == 0
           for c in cases.values())
designs = len(list((run / 'design').iterdir()))
assert designs == 2000
result = dict(run=a.run, sha256=sha, change='perforation.run(0.5) -> perforation.run(0.7)',
              changed_lines=1, cases=len(cases), designs=designs, builds=4, warnings=0,
              wa=0, self_wrong=0, op_label_errors=0, temporary_binaries_removed=True)
(here / 'final-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
