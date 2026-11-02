"""Fixed-iteration simulations (SIM_SEQS=4 random sequences per design) of a -DSIM_HARNESS binary
with extra environment settings, at the base iteration counts (as Astra's measurements).

usage: python3 solutions/steady-probe/run_knobs.py BINARY FROM TO JOBS [NAME=VALUE ...] > out.tsv
(prints: seed, mean moves per request of the simulations, model_cost)
"""
import os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

BASE = dict(MAP_ITERS="380000", GOPT_STEPS="110000", ANNEAL_ITERS="19000000", CLIMB_ITERS="65000", SIM_SEQS="4")


def run(binary, extra, seed):
    env = dict(os.environ, **BASE, **extra)
    with open(f"/home/sato/ahc074/tools/in/{seed:04d}.txt") as f:
        p = subprocess.run([binary], stdin=f, capture_output=True, text=True, env=env)
    stats = dict(l.split(" = ") for l in p.stderr.splitlines() if " = " in l)
    return seed, float(stats["sim_moves"]), float(stats.get("model_cost", "nan")), float(stats.get("sim_wrong", "nan"))


binary, lo, hi, jobs = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
extra = dict(a.split("=", 1) for a in sys.argv[5:])
with ThreadPoolExecutor(jobs) as ex:
    for seed, moves, model, wrong in ex.map(lambda s: run(binary, extra, s), range(lo, hi)):
        print(f"{seed}\t{moves}\t{model}\t{wrong}", flush=True)
