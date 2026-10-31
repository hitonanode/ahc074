"""Own measurement runner (not an evaluation record): runs a binary built from ceil-probe with
SIM_ONLY=1 on tools/in/<seed>.txt for every (config, seed), holding runs/.lock, and appends one JSON
line per job (config, seed, env, sim_moves, sim_per, anneal/climb iters) to <out>.
usage: simrun.py <out.jsonl> <binary> <lo> <hi> <name>:K=V,K=V ...   (JOBS env, default 22)
The environment common to all configs is taken from os.environ."""
import os, re, subprocess, sys, json, fcntl, datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

out, binary = sys.argv[1], sys.argv[2]
lo, hi = int(sys.argv[3]), int(sys.argv[4])
configs = []
for spec in sys.argv[5:]:
    name, _, kvs = spec.partition(":")
    env = dict(os.environ, SIM_ONLY="1")
    for kv in filter(None, kvs.split(",")):
        k, v = kv.split("=", 1)
        env[k] = v
    configs.append((name, env))
root = Path("/home/sato/ahc074")
LINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$")


def job(arg):
    ci, s = arg
    name, env = configs[ci]
    with open(root / "tools/in" / f"{s:04d}.txt") as fi:
        p = subprocess.run([binary], stdin=fi, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=env)
    vals = {}
    for line in p.stderr.splitlines():
        m = LINE.match(line)
        if m:
            vals[m.group(1)] = m.group(2)
    rec = {"config": name, "seed": s, "env": {k: v for k, v in env.items() if k not in os.environ or k == "SIM_ONLY"}}
    rec.update(vals)
    return rec


lock_fd = os.open(root / "runs" / ".lock", os.O_RDWR | os.O_CREAT, 0o644)
fcntl.flock(lock_fd, fcntl.LOCK_EX)
os.ftruncate(lock_fd, 0)
os.write(lock_fd, f"ceil-probe simrun.py (pid {os.getpid()}, {datetime.datetime.now().isoformat()} から)\n".encode())
print("lock acquired", datetime.datetime.now().isoformat(), flush=True)
jobs = [(ci, s) for ci in range(len(configs)) for s in range(lo, hi)]
# longest first
with ThreadPoolExecutor(int(os.environ.get("JOBS", "22"))) as ex, open(out, "a") as fo:
    for rec in ex.map(job, jobs):
        fo.write(json.dumps(rec) + "\n")
        fo.flush()
print("done", datetime.datetime.now().isoformat(), flush=True)
