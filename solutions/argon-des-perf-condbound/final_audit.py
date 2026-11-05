"""Read-only checks of the final source and saved run; launch through whenidle.sh."""
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
run = Path('/home/sato/ahc074/runs/20261106-005414_argon-des-perf-condbound')
source = (here / 'main.cpp').read_text()
saved = (run / 'src/main.cpp').read_text()
assert len(source.splitlines()) == len(saved.splitlines())
assert all(a.lstrip() == b.lstrip() for a, b in zip(source.splitlines(), saved.splitlines()))
builds = json.loads((here / 'build-results.json').read_text())
sha = hashlib.sha256(source.encode()).hexdigest()
assert sha == builds['sha256']
assert all(r['exit'] == 0 and r['warnings'] == 0 for r in builds['results'])

base = (here.parent / 'argon-req-filldp-positive/main.cpp').read_text()
def outside_changed_parts(s):
    for first, last in [
        ('// ==== Handle perforation ====', '// ==== Design state:'),
        ('    // ==== design_papers: handle perforation ====', '#ifdef LOCAL_BENCH\n// ==== Saving and loading'),
    ]:
        a = s.index(first)
        b = s.index(last, a)
        s = s[:a] + s[b:]
    return s
assert outside_changed_parts(base) == outside_changed_parts(source)
assert [s.strip() for s in base.splitlines() if s.strip().startswith('// ====')] == [
    s.strip() for s in source.splitlines() if s.strip().startswith('// ====')]
assert base[:base.index('// ==== Common:')] == source[:source.index('// ==== Common:')]

cases = json.loads((run / 'metrics.json').read_text())['cases']
assert len(cases) == 2000
assert all(c['score'] > 0 and c['stderr']['self_wrong'] == 0 and c['stderr']['op_label_errors'] == 0
           for c in cases.values())
designs = list((run / 'design').iterdir())
assert len(designs) == 2000
result = dict(sha256=sha, run=run.name, cases=len(cases), saved_designs=len(designs),
              run_source_diff='indentation only', builds=4, warnings=0,
              changed_sections=['Handle perforation', 'design_papers: handle perforation'],
              outside_sections_identical=True, markers_and_contents_identical=True)
(here / 'final-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
