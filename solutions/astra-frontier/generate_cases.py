#!/usr/bin/env python3
"""Generate independent AHC074 cases with the distribution in tools/src/lib.rs."""
import argparse
import hashlib
import json
import pathlib
import random

def generate(seed: int) -> str:
    rng = random.Random(seed ^ 0xA07420261102)
    patterns, seen = [], set()
    while len(patterns) < 256:
        ones = set(rng.sample(range(64), 32))
        s = ''.join('1' if j in ones else '0' for j in range(64))
        if s not in seen:
            seen.add(s)
            patterns.append(s)
    requests = [rng.randrange(256)]
    for _ in range(1023):
        x = rng.randrange(255)
        requests.append(x + (x >= requests[-1]))
    return '64 192 256 1024\n' + '\n'.join(patterns) + '\n' + '\n'.join(map(str, requests)) + '\n'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=pathlib.Path, required=True)
    p.add_argument('--start', type=int, default=0)
    p.add_argument('--end', type=int, default=2000)
    p.add_argument('--manifest', type=pathlib.Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    records = []
    for seed in range(a.start, a.end):
        data = generate(seed).encode()
        path = a.out / f'{seed:04d}.txt'
        if path.exists() and path.read_bytes() != data:
            raise SystemExit(f'refusing to overwrite a different case: {path}')
        path.write_bytes(data)
        records.append({'seed': seed, 'sha256': hashlib.sha256(data).hexdigest()})
    a.manifest.write_text(json.dumps({'generator':'Python random.Random, seed xor 0xA07420261102',
        'official_seed_compatible':False,'cases':records}, indent=2)+'\n')
    print(f'generated {len(records)} independent cases')

if __name__ == '__main__':
    main()
