"""Own measurement runner for parameter sweeps (not an evaluation record). Holds runs/.lock once
and runs every (config, seed) job through the tester, writing <outdir>/<name>.txt in the format of
solutions/brk-probe/runm.py (`seed score T E sec stat=...`), so that cmpm.py compares them.
usage: sweep.py <outdir> <lo> <hi> <name>=[<binary>][:K=V,K=V...] ...   (JOBS env, default 8;
an empty binary means the BIN env)
The environment common to all configs (e.g. HUB_ANNEAL, CLIMB_ITERS) is taken from os.environ."""
import os, re, subprocess, sys, time, fcntl, datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

outdir = Path(sys.argv[1])
lo, hi = int(sys.argv[2]), int(sys.argv[3])
outdir.mkdir(parents=True, exist_ok=True)
configs = []
for spec in sys.argv[4:]:
    name, _, rest = spec.partition("=")
    binary, _, kvs = rest.partition(":")
    binary = binary or os.environ["BIN"]  # empty binary: the BIN env
    env = dict(os.environ)
    for kv in filter(None, kvs.split(",")):
        k, v = kv.split("=", 1)
        env[k] = v
    configs.append((name, binary, env))
root = Path("/home/sato/ahc074")
LINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([-+0-9.eE]+)\s*$")


def job(arg):
    ci, s = arg
    name, binary, env = configs[ci]
    t0 = time.perf_counter()
    with open(root / "tools/in" / f"{s:04d}.txt") as fi:
        p = subprocess.run([str(root / "tools/target/release/tester"), binary], stdin=fi,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=env)
    el = time.perf_counter() - t0
    vals = {}
    for line in p.stderr.splitlines():
        m = LINE.match(line)
        if m:
            vals[m.group(1)] = m.group(2)
    return ci, s, vals, el


lock_fd = os.open(root / "runs" / ".lock", os.O_RDWR | os.O_CREAT, 0o644)
fcntl.flock(lock_fd, fcntl.LOCK_EX)
os.ftruncate(lock_fd, 0)
os.write(lock_fd, f"retune sweep.py (pid {os.getpid()}, {datetime.datetime.now().isoformat()} から)\n".encode())
print("lock acquired", datetime.datetime.now().isoformat(), flush=True)
jobs = [(ci, s) for s in range(lo, hi) for ci in range(len(configs))]
res = {ci: [] for ci in range(len(configs))}
with ThreadPoolExecutor(int(os.environ.get("JOBS", "8"))) as ex:
    for ci, s, vals, el in ex.map(job, jobs):
        res[ci].append((s, vals, el))
for ci, (name, _, _) in enumerate(configs):
    with open(outdir / f"{name}.txt", "w") as fo:
        for s, vals, el in sorted(res[ci], key=lambda r: r[0]):
            score = int(vals.get("Score", 0))
            T = int(vals.get("total_moves", 0))
            E = (score - T) // 384 if score else -1
            extra = " ".join(f"{k}={v}" for k, v in vals.items() if k not in ("Score", "total_moves"))
            fo.write(f"{s} {score} {T} {E} {el:.3f} {extra}\n")
print("done", datetime.datetime.now().isoformat(), flush=True)
