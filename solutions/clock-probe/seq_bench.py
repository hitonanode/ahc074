#!/usr/bin/env python3
"""Runs a solution on seeds sequentially (one case at a time, on a quiet machine) and prints the
wall time of each case and its *_sec lines. Holds runs/.lock (the lock of scripts/pahcer_run.py) so
no evaluation shares the CPU. Not a record: nothing is written to runs/ or pahcer/.

    solutions/clock-probe/seq_bench.py solutions/clock-probe/main.cpp 0-50 [out.json]
"""
import fcntl, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

root = Path(subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True,
                           check=True).stdout.strip()).resolve().parent
src, rng = sys.argv[1], sys.argv[2]
lo, hi = map(int, rng.split("-"))
exe = Path(tempfile.mkdtemp()) / "a.out"
subprocess.run(["g++", "-std=c++23", "-O2", "-o", str(exe), src], check=True)
fd = os.open(root / "runs" / ".lock", os.O_RDWR | os.O_CREAT, 0o644)
fcntl.flock(fd, fcntl.LOCK_EX)
os.ftruncate(fd, 0); os.write(fd, f"clock-probe seq_bench (pid {os.getpid()})".encode())
tester = root / "tools" / "target" / "release" / "tester"
res = []
for s in range(lo, hi):
    with open(root / "tools" / "in" / f"{s:04d}.txt") as fin:
        t0 = time.perf_counter()
        p = subprocess.run([str(tester), str(exe)], stdin=fin, capture_output=True, text=True)
        wall = time.perf_counter() - t0
    d = {k: float(v) for k, v in re.findall(r"^(\w+_sec) = ([\d.e-]+)", p.stderr, re.M)}
    d.update(seed=s, wall=wall)
    res.append(d)
    print(json.dumps(d), flush=True)
os.ftruncate(fd, 0)
if len(sys.argv) > 3: json.dump(res, open(sys.argv[3], "w"))
