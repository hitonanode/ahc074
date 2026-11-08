"""Valid, deliberately nonuniform AHC074 inputs for robustness checks, not score evaluation."""
from pathlib import Path
import random

root = Path(__file__).resolve().parent
dest = root / 'inputs'
dest.mkdir(exist_ok=True)
full = (1 << 64) - 1
base = (1 << 32) - 1
notes = []
for seed in range(20):
    rng = random.Random(740000 + seed)
    kind = seed // 2
    patterns = []
    seen = set()
    while len(patterns) < 256:
        if kind < 4:
            swaps = (1, 2, 4, 8)[kind]
            mask = base
            for j in rng.sample(range(32), swaps): mask ^= 1 << j
            for j in rng.sample(range(32, 64), swaps): mask ^= 1 << j
            if rng.randrange(2): mask ^= full
        elif kind == 4:
            # Only 24 varying windows: cannot provide both colors to every handle.
            mask = sum(1 << j for j in range(24, 44))
            mask |= sum(1 << j for j in rng.sample(range(24), 12))
        elif kind in (5, 6):
            # Constant cap, with all other windows sampled normally.
            mask = sum(1 << j for j in rng.sample(range(63), 32 - (kind == 6)))
            if kind == 6: mask |= 1 << 63
        elif kind == 7:
            # Pairwise complementary adjacent windows; every window still varies.
            mask = sum(1 << (2*j + rng.randrange(2)) for j in range(32))
        elif kind == 8:
            # One of two colors per group of four, each group contains two ones.
            mask = sum(1 << (4*j + k) for j in range(16) for k in rng.sample(range(4), 2))
        else:
            mask = sum(1 << j for j in rng.sample(range(64), 32))
        if mask in seen: continue
        assert mask.bit_count() == 32
        seen.add(mask)
        patterns.append(mask)
    requests = [rng.randrange(256)]
    if seed % 2:
        requests = [0, 1] * 512
    else:
        for _ in range(1023):
            x = rng.randrange(255)
            requests.append(x + (x >= requests[-1]))
    assert len(requests) == 1024 and all(a != b for a,b in zip(requests, requests[1:]))
    rows = ['64 192 256 1024']
    rows += [''.join(str(mask >> j & 1) for j in range(64)) for mask in patterns]
    rows += list(map(str, requests))
    (dest / f'{seed:04d}.txt').write_text('\n'.join(rows) + '\n')
    notes.append(f'{seed}: kind={kind}, orders={"alternating 0,1" if seed % 2 else "uniform excluding previous"}')
(dest / 'cases.txt').write_text('\n'.join(notes) + '\n')
