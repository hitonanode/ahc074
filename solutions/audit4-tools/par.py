"""Runs an analysis binary (mk_probe4.py) on seeds lo..hi-1 in parallel, stderr to <outdir>/<seed>.err.

usage: par.py <binary> <lo> <hi> <outdir> [ENV=VAL ...]   (JOBS, default 6)
HUB_ANNEAL=9000000 CLIMB_ITERS=60000 unless set. No lock (the analysis is not timed).
e.g. INS=16 INS_OFF=2 par.py probe 0 24 ins1   (64 requests per seed, about 3 minutes per seed)."""
import os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

b, lo, hi, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
os.makedirs(out, exist_ok=True)
env = dict(os.environ)
env.setdefault("HUB_ANNEAL", "9000000")
env.setdefault("CLIMB_ITERS", "60000")
for kv in sys.argv[5:]:
    k, v = kv.split("=", 1)
    env[k] = v


def job(s):
    t = time.time()
    with open(f"/home/sato/ahc074/tools/in/{s:04d}.txt") as fi, open(f"{out}/{s}.err", "w") as fe:
        subprocess.run([b], stdin=fi, stdout=subprocess.DEVNULL, stderr=fe, env=env)
    return s, time.time() - t


with ThreadPoolExecutor(int(os.environ.get("JOBS", "6"))) as ex:
    for s, dt in ex.map(job, range(lo, hi)):
        print(s, f"{dt:.1f}s", flush=True)
