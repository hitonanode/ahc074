"""Compare saved outputs and all non-timing stderr lines; never execute a solver."""
from pathlib import Path
import json
import re
import sys

root = Path('/home/sato/ahc074/runs')
timing = re.compile(r'^\w*_sec = ')


def normal_lines(file):
    lines = []
    for s in file.read_text().splitlines():
        if timing.match(s) or re.match(r'^cfprof_.*_(inc|exc) = ', s):
            continue
        if s.startswith(('#f3post ', '#f3op ')):
            s = s.rsplit(' ', 1)[0]  # last field is the measured time
        lines.append(s)
    return lines


base = root / sys.argv[1]
for name in sys.argv[2:]:
    candidate = root / name
    count = 0
    failures = []
    for f in sorted(base.glob('out/*.txt')) + sorted(base.glob('orders/*/out/*.txt')):
        relative = f.relative_to(base)
        other = candidate / relative
        if not other.exists():
            continue
        count += 1
        if f.read_bytes() != other.read_bytes():
            failures.append(('stdout', str(relative)))
        err = relative.parent.parent / 'err' / relative.name
        left, right = normal_lines(base / err), normal_lines(candidate / err)
        if left != right:
            first = next(((a, b) for a, b in zip(left, right) if a != b), ('line count', f'{len(left)} != {len(right)}'))
            failures.append(('stderr', str(err), first))
        for metric in ('self_wrong', 'op_label_errors'):
            assert f'{metric} = 0' in right, (name, relative, metric)
    result = json.loads((candidate / 'result.json').read_text())
    assert all(c['score'] > 0 for c in result['cases']), name
    assert count and not failures, (name, count, failures[:8])
    print(name, count, 'stdout and every non-timing stderr line identical; WA/self_wrong/op_label_errors = 0', flush=True)
