"""Runs an analysis binary over the outputs of a run and sums its `name = value` lines.
usage: runall.py <binary> <run-id or dir> <first seed> <end seed> [--each]"""
import subprocess, sys, re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
binary, run = sys.argv[1], sys.argv[2]
lo, hi = int(sys.argv[3]), int(sys.argv[4])
each = "--each" in sys.argv
root = Path("/home/sato/ahc074")
rd = Path(run) if Path(run).is_dir() else root / "runs" / run
def job(s):
    f = f"{s:04d}.txt"
    out = subprocess.run([binary, str(root / "tools/in" / f), str(rd / "out" / f)], capture_output=True, text=True).stdout
    vals = {}
    for line in out.splitlines():
        m = re.match(r"^(\w+) = ([-\d.e+]+)$", line)
        if m: vals[m[1]] = float(m[2])
    return s, vals
tot, n = {}, 0
with ThreadPoolExecutor(16) as ex:
    for s, vals in ex.map(job, range(lo, hi)):
        n += 1
        if each: print(s, " ".join(f"{k}={v:g}" for k, v in vals.items()))
        for k, v in vals.items(): tot[k] = tot.get(k, 0) + v
for k, v in tot.items(): print(f"{k} = {v / n:.4f}  (mean over {n} seeds)")
