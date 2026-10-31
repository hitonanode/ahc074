"""Runs a solution binary on local inputs without the tester (the requests are read from the end of
the input file) and prints selected `name = value` lines of its stderr, to look at the design stage.

usage: python3 design_stats.py BINARY SEED_FROM SEED_TO NAME [NAME ...]
"""
import re
import subprocess
import sys
from pathlib import Path

binary, s0, s1, names = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4:]
root = Path(__file__).resolve().parents[2]
sums = {n: [] for n in names}
for seed in range(s0, s1):
    inp = (root / "tools" / "in" / f"{seed:04d}.txt").read_text()
    res = subprocess.run([binary], input=inp, capture_output=True, text=True)
    vals = {}
    for line in res.stderr.splitlines():
        m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([-+0-9.eE]+)\s*$", line)
        if m and m.group(1) in sums:
            vals[m.group(1)] = float(m.group(2))
    print(seed, " ".join(f"{n}={vals.get(n)}" for n in names))
    for n in names:
        if n in vals:
            sums[n].append(vals[n])
print("mean", " ".join(f"{n}={sum(v) / len(v):.4f}" for n, v in sums.items() if v))
