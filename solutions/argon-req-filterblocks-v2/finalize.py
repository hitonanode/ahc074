"""Validate saved artifacts and aggregate timings; run through whenidle.sh and the shared lock."""
from pathlib import Path
import hashlib
import json
import math
import re
import statistics as st
import subprocess
import sys

here = Path(__file__).resolve().parent
runs = Path('/home/sato/ahc074/runs')
helpers = Path('solutions/argon-req-exactprofile')


def ids(log):
    result = list(dict.fromkeys(re.findall(r'run-id: (\S+)', Path(log).read_text())))
    assert len(result) == 2, (log, result)
    return result


def run(script, *args):
    subprocess.run([sys.executable, str(script), *map(str, args)], check=True)


normal = ids(here / 'normal-final.log')
fixed = ids(here / 'fixed-final.log')
for label, names in [('normal', normal), ('fixed', fixed)]:
    for name in names:
        cases = json.loads((runs / name / 'result.json').read_text())['cases']
        assert sorted(c['seed'] for c in cases) == list(range(2000)), (name, len(cases))
        assert all(c['score'] > 0 and all(x > 0 for x in c.get('order_scores', [])) for c in cases)
        orders = 2 if label == 'fixed' else 1
        assert all(len(c.get('order_scores', [c['score']])) == orders for c in cases)
        outputs = list((runs / name).glob('out/*.txt')) + list((runs / name).glob('orders/*/out/*.txt'))
        assert len(outputs) == 2000 * orders, (name, len(outputs))
    run('solutions/argon-req-completeold/analyze.py', *names, '--json', here / (label + '-results.json'))
    run(helpers / 'check_exact.py', *names)

source = (here / 'main.cpp').read_bytes()
base = Path('solutions/argon-des-design-packed/main.cpp').read_bytes()
start = b'    // ==== Post-processing: deletions and new anchors of the edits ===='
end = b'    // ==== Post-processing: two deletions and one repair (eject) ===='
assert base[:base.index(start)] == source[:source.index(start)]
assert base[base.index(end):] == source[source.index(end):]
for name in [normal[1], fixed[1]]:
    assert (runs / name / 'src/main.cpp').read_bytes() == source, name
for name in normal:
    design = list((runs / name / 'design').iterdir())
    assert len(design) == 2000, (name, len(design))
assert 'All four builds passed with no warnings.' in (here / 'builds.log').read_text()

results = json.loads((here / 'normal-results.json').read_text())[normal[1]]
assert results['wtl'] == [0, 2000, 0]
assert results['req_ratio'] < 1
assert results['judge_mean_delta'] <= -.005, results['judge_mean_delta']
assert results['judge_p99_delta'] <= .010, results['judge_p99_delta']

metric = re.compile(r'^(\w+) = ([-+\d.eE]+)$', re.M)
diffs = {'req_sec': [], 'judge': []}
for seed in range(2000):
    values = []
    for name in normal:
        m = {k: float(v) for k, v in metric.findall((runs / name / 'err' / f'{seed:04d}.txt').read_text())}
        values.append((m['req_sec'], m['end_sec'] + .04 * m['helper_end_sec'] + .35 * m['req_sec']))
    for i, key in enumerate(diffs):
        diffs[key].append(values[1][i] - values[0][i])
paired = {k: {'mean': st.mean(v), 'se': st.stdev(v) / math.sqrt(len(v))} for k, v in diffs.items()}
(here / 'paired-times.json').write_text(json.dumps(paired, indent=2) + '\n')
print('Paired time differences:', paired, flush=True)
print('Only the post-processing section changed; archived source identical; all 2000 designs saved.', flush=True)
print('sha256:', hashlib.sha256(source).hexdigest(), flush=True)
print('All final adoption checks passed.', flush=True)
