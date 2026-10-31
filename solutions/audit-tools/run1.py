"""Runs a solution binary on local seeds through the tester (outputs in a scratch directory).
usage: run1.py <binary> <outdir> <first seed> <end seed> [ENV=VAL ...]
Prints `seed score` lines and the mean; stdout/stderr go to <outdir>/out|err/<seed>.txt."""
import os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
binary, outdir = sys.argv[1], Path(sys.argv[2])
lo, hi = int(sys.argv[3]), int(sys.argv[4])
env = dict(os.environ)
for kv in sys.argv[5:]:
    k, v = kv.split("=", 1)
    env[k] = v
root = Path("/home/sato/ahc074")
(outdir / "out").mkdir(parents=True, exist_ok=True)
(outdir / "err").mkdir(parents=True, exist_ok=True)
def job(s):
    f = f"{s:04d}.txt"
    with open(root / "tools/in" / f) as fi, open(outdir / "out" / f, "w") as fo, open(outdir / "err" / f, "w") as fe:
        t0 = time.perf_counter()
        subprocess.run([str(root / "tools/target/release/tester"), binary], stdin=fi, stdout=fo, stderr=fe, env=env)
        el = time.perf_counter() - t0
    m = re.findall(r"^Score = (\d+)", (outdir / "err" / f).read_text(), re.M)
    return s, (int(m[-1]) if m else 0), el
# Hold the evaluation lock (runs/.lock) so that timed evaluations of other agents do not share the CPU.
import fcntl, datetime
lock_fd = os.open(root / "runs" / ".lock", os.O_RDWR | os.O_CREAT, 0o644)
fcntl.flock(lock_fd, fcntl.LOCK_EX)
os.ftruncate(lock_fd, 0)
os.write(lock_fd, f"audit run1.py {binary} (pid {os.getpid()}, {datetime.datetime.now().isoformat()} から)\n".encode())
res = []
with ThreadPoolExecutor(int(env.get("JOBS", "12"))) as ex:
    for s, sc, el in ex.map(job, range(lo, hi)):
        res.append(sc)
        print(s, sc, f"{el:.3f}", flush=True)
print("mean", sum(res) / len(res))
