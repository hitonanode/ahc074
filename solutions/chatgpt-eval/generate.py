#!/usr/bin/env python3
"""Fresh, reproducible inputs with the official distribution, using Python MT19937."""
import argparse
import hashlib
import json
import random
from pathlib import Path


def generate(seed: int) -> str:
    rng = random.Random(seed ^ 0xA074)
    patterns = []
    used = set()
    while len(patterns) < 256:
        bits = sum(1 << j for j in rng.sample(range(64), 32))
        if bits in used:
            continue
        used.add(bits)
        patterns.append(''.join(str((bits >> j) & 1) for j in range(64)))
    requests = [rng.randrange(256)]
    for _ in range(1023):
        x = rng.randrange(255)
        requests.append(x + (x >= requests[-1]))
    return '\n'.join(['64 192 256 1024', *patterns, *map(str, requests)]) + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', type=int, default=10000)
    parser.add_argument('--end', type=int, default=10064)
    args = parser.parse_args()
    if not 0 <= args.start < args.end:
        parser.error('Require 0 <= start < end')
    root = Path(__file__).resolve().parents[2]
    inputs = root / 'tools' / 'in'
    inputs.mkdir(parents=True, exist_ok=True)
    cases = []
    for seed in range(args.start, args.end):
        content = generate(seed).encode()
        path = inputs / f'{seed:04d}.txt'
        if path.exists() and path.read_bytes() != content:
            raise SystemExit(f'Refusing to overwrite different input: {path}')
        path.write_bytes(content)
        cases.append({'seed': seed, 'sha256': hashlib.sha256(content).hexdigest()})
    manifest = {
        'generator': 'Python random.Random MT19937, seed XOR 0xA074; not official ChaCha20 seeds',
        'distribution': '256 distinct uniform 32-of-64 bit patterns; 1024 uniform requests excluding predecessor',
        'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'start': args.start, 'end_exclusive': args.end, 'cases': cases,
    }
    target = Path(__file__).with_name(f'cases-{args.start}-{args.end}.json')
    target.write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Generated {len(cases)} cases and {target.relative_to(root)}')


if __name__ == '__main__':
    main()
