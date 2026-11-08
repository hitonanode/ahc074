"""Valid inputs near the minimum number of variable handle windows."""
from pathlib import Path
import random

dest = Path(__file__).resolve().parent / "inputs_variable"
dest.mkdir(exist_ok=True)
notes = []
for seed in range(120):
    rng = random.Random(741000 + seed)
    varying = 24 + seed % 40
    placement = seed // 40
    windows = list(range(64))
    if placement == 1:
        windows.reverse()
    elif placement == 2:
        rng.shuffle(windows)
    variable, constant = windows[:varying], windows[varying:]
    n_black = varying // 2
    fixed = sum(1 << j for j in constant[:32 - n_black])
    patterns, seen = [], set()
    while len(patterns) < 256:
        mask = fixed | sum(1 << j for j in rng.sample(variable, n_black))
        if mask in seen:
            continue
        assert mask.bit_count() == 32
        seen.add(mask)
        patterns.append(mask)
    orders = [rng.randrange(256)]
    for _ in range(1023):
        u = rng.randrange(255)
        orders.append(u + (u >= orders[-1]))
    rows = ["64 192 256 1024"]
    rows += ["".join(str(x >> j & 1) for j in range(64)) for x in patterns]
    rows += list(map(str, orders))
    (dest / f"{seed:04d}.txt").write_text("\n".join(rows) + "\n")
    notes.append(f"{seed}: varying={varying}, placement={placement}, variable={variable}")
(dest / "cases.txt").write_text("\n".join(notes) + "\n")
