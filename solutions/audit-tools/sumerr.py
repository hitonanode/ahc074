"""Means of the `name = value` lines over the err files of a directory (last value per file).
usage: sumerr.py <dir with err/> [prefix]"""
import re, sys
from pathlib import Path
d = Path(sys.argv[1]) / "err"
pre = sys.argv[2] if len(sys.argv) > 2 else ""
tot, n = {}, 0
for f in sorted(d.glob("*.txt")):
    vals = {}
    for line in f.read_text().splitlines():
        m = re.match(r"^(\w+) = ([-\d.e+]+)$", line)
        if m and m[1].startswith(pre): vals[m[1]] = float(m[2])
    n += 1
    for k, v in vals.items(): tot[k] = tot.get(k, 0) + v
for k in sorted(tot): print(f"{k} = {tot[k] / n:.4f}")
print("files", n)
