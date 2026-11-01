#!/usr/bin/env python3
"""Generate fresh AHC074 inputs from the official distribution, with a separate RNG namespace."""
import argparse
import csv
import hashlib
from pathlib import Path
import random

BASE_SEED = 0x4153545241303734

def case_text(seed: int) -> str:
    rng = random.Random(seed)
    seen = set()
    patterns = []
    while len(patterns) < 256:
        black = set(rng.sample(range(64), 32))
        s = ''.join('1' if j in black else '0' for j in range(64))
        if s not in seen:
            seen.add(s)
            patterns.append(s)
    requests = [rng.randrange(256)]
    for _ in range(1023):
        x = rng.randrange(255)
        requests.append(x + (x >= requests[-1]))
    return '64 192 256 1024\n' + '\n'.join(patterns) + '\n' + '\n'.join(map(str, requests)) + '\n'

def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=2000)
    parser.add_argument('--dir', type=Path, default=root/'tools/in')
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('generated_manifest.csv'))
    args = parser.parse_args()
    args.dir.mkdir(parents=True, exist_ok=True)
    # Never silently replace existing official generator cases.
    for i in range(args.count):
        path = args.dir/f'{i:04d}.txt'
        if path.exists():
            raise SystemExit(f'{path} already exists; choose an empty --dir')
    with args.manifest.open('w', newline='') as fp:
        writer = csv.writer(fp)
        writer.writerow(['case_id', 'python_random_seed', 'sha256'])
        for i in range(args.count):
            data = case_text(BASE_SEED+i).encode()
            (args.dir/f'{i:04d}.txt').write_bytes(data)
            writer.writerow([i, BASE_SEED+i, hashlib.sha256(data).hexdigest()])
    print(f'Generated {args.count} cases; namespace=astra-generated-v1, base={BASE_SEED}; manifest={args.manifest}')

if __name__ == '__main__':
    main()
