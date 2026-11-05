"""Check the final source, build matrix, preserved sections and saved designs."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('run')
a = p.parse_args()
here = Path(__file__).resolve().parent
source = (here / 'main.cpp').read_text()
base = (here.parent / 'argon-req-completefast-v3/main.cpp').read_text()
run = Path('/home/sato/ahc074/runs') / a.run
assert source == (run / 'src/main.cpp').read_text()
sha = hashlib.sha256(source.encode()).hexdigest()
builds = json.loads((here / 'build-results.json').read_text())
assert sha == builds['sha256'] and builds['temporary_binaries_removed']
assert all(r['exit'] == 0 and r['warnings'] == 0 for r in builds['results'])
assert not list(here.glob('check-*'))
def outside_changed_parts(s):
    for first, last in [
        ('// ==== Handle perforation ====', '// ==== Design state:'),
        ('    // ==== design_papers: handle perforation ====', '#ifdef LOCAL_BENCH\n// ==== Saving and loading'),
    ]:
        start = s.index(first)
        end = s.index(last, start)
        s = s[:start] + s[end:]
    return s
assert outside_changed_parts(source) == outside_changed_parts(base)
assert [s.strip() for s in source.splitlines() if s.strip().startswith('// ====')] == [
    s.strip() for s in base.splitlines() if s.strip().startswith('// ====')]
assert source[:source.index('// ==== Common:')] == base[:base.index('// ==== Common:')]
cases = json.loads((run / 'metrics.json').read_text())['cases']
assert len(cases) == 2000
assert all(c['score'] > 0 and c['stderr']['self_wrong'] == 0 and c['stderr']['op_label_errors'] == 0
           for c in cases.values())
designs = len(list((run / 'design').iterdir()))
assert designs == 2000
result = dict(run=a.run, sha256=sha, cases=len(cases), designs=designs, builds=4, warnings=0,
              wa=0, self_wrong=0, op_label_errors=0, temporary_binaries_removed=True,
              other_sections_identical=True, markers_and_contents_identical=True)
(here / 'final-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
