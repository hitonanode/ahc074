"""Validate heavy traces against stored outputs and default-mode outputs."""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path('scripts').resolve()))
import replay

here = Path(__file__).resolve().parent
root = Path('/home/sato/ahc074/runs')
name = re.search(r'run-id: (\S+)', (here/'trace.log').read_text())[1]
plain = re.findall(r'run-id: (\S+)', (here/'fixed-screen.log').read_text())[1]
r = root/name
n = plans = predictions = cases = 0
for f in sorted((r/'out').glob('*.txt')):
    cases += 1
    assert f.read_bytes() == (root/plain/'out'/f.name).read_bytes(), f.name
    seed = int(f.stem)
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, f.read_text())
    err = (r/'err'/f.name).read_text()
    ann = replay.parse_annotations(err, inp.k)
    for line in err.splitlines():
        predictions += line.startswith('#heavycand ')
        if not line.startswith('#heavy '):
            continue
        fields = line.split()
        q, last = int(fields[1]), fields[-1]
        ops, labels = [], []
        if last != '-':
            for item in last.split(','):
                k, d, label = item.split(':')
                ops.append((int(k), int(d)))
                labels.append(label)
        assert ops == out.queries[q], (seed, q)
        assert labels == ann.labels_of(q, len(ops)), (seed, q)
        n += 1
        plans += fields[3].startswith('plans.')
    assert 'self_wrong = 0' in err and 'op_label_errors = 0' in err
assert cases == 8 and n > 0 and plans > 0 and predictions > 0
print('Trace run:', name)
print('Default stdout identical on', cases, 'seeds.')
print('Heavy records:', n, '; plans records:', plans, '; predictions:', predictions)
print('All heavy final paths and labels match stdout and @ops; errors = 0.')
