"""Compare stored stdout bytes; never execute a solution."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('before')
parser.add_argument('after')
parser.add_argument('--seeds', type=int, default=25)
parser.add_argument('--orders', type=int, default=1)
parser.add_argument('--output', required=True)
args = parser.parse_args()
root = Path('/home/sato/ahc074/runs')
checks = []
for j in range(args.orders):
    suffix = Path('out') if not j else Path('orders') / str(j) / 'out'
    for seed in range(args.seeds):
        a = (root / args.before / suffix / f'{seed:04d}.txt').read_bytes()
        b = (root / args.after / suffix / f'{seed:04d}.txt').read_bytes()
        assert a == b, (args.before, args.after, seed, j)
        checks.append({'seed': seed, 'order': j, 'sha256': hashlib.sha256(a).hexdigest()})
result = {'before': args.before, 'after': args.after, 'seeds': args.seeds,
          'orders': args.orders, 'byte_identical': True, 'checks': checks}
Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
print(f'{len(checks)} stored stdout files are byte-identical.')
