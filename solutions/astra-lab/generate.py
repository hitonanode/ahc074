#!/usr/bin/env python3
"""Generate independent cases from the exact specified distribution, not official seed bytes."""
import argparse
import hashlib
import json
import random
from pathlib import Path

def generate(seed):
    rng = random.Random(seed)
    patterns, seen = [], set()
    while len(patterns) < 256:
        ones = set(rng.sample(range(64), 32))
        pattern = ''.join('1' if j in ones else '0' for j in range(64))
        if pattern not in seen:
            seen.add(pattern)
            patterns.append(pattern)
    requests = [rng.randrange(256)]
    for _ in range(1023):
        a = rng.randrange(255)
        requests.append(a + (a >= requests[-1]))
    return '64 192 256 1024\n' + '\n'.join(patterns) + '\n' + '\n'.join(map(str, requests)) + '\n'

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--count', type=int, default=2000)
    ap.add_argument('--seed-offset', type=int, default=74000000)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    records = []
    for i in range(args.count):
        data = generate(args.seed_offset + i).encode()
        path = args.out / f'{i:04d}.txt'
        if path.exists() and path.read_bytes() != data:
            raise SystemExit(f'Refusing to overwrite a different case: {path}')
        path.write_bytes(data)
        records.append({'case': i, 'python_random_seed': args.seed_offset + i,
                        'sha256': hashlib.sha256(data).hexdigest()})
    manifest = {'generator': 'Python random.Random + uniform sample/randrange',
                'official_seed_compatible': False, 'cases': records}
    (args.out / 'astra_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Generated {args.count} cases; seeds {args.seed_offset}..{args.seed_offset + args.count - 1}')

if __name__ == '__main__':
    main()
