"""Fixed-iteration simulations of compute.cpp (as6-cap38p0 without the helper cutoff): the mean moves
per request of SIM_SEQS random request sequences per design, for a scale of the design iterations.

usage: python3 solutions/steady-probe/run_compute.py BINARY SCALE [SEEDS_FROM SEEDS_TO JOBS] > out.tsv
"""
import os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

BASE = dict(MAP_ITERS=380000, GOPT_STEPS=110000, ANNEAL_ITERS=19000000, CLIMB_ITERS=65000)


def run(binary, scale, seed):
    env = dict(os.environ, SIM_SEQS="4", **{k: str(int(v * scale)) for k, v in BASE.items()})
    with open(f"/home/sato/ahc074/tools/in/{seed:04d}.txt") as f:
        p = subprocess.run([binary], stdin=f, capture_output=True, text=True, env=env)
    stats = dict(l.split(" = ") for l in p.stderr.splitlines() if " = " in l)
    return seed, float(stats["sim_moves"]), float(stats.get("model_cost", "nan"))


binary, scale = sys.argv[1], float(sys.argv[2])
lo, hi, jobs = (int(x) for x in (sys.argv[3:6] if len(sys.argv) > 5 else (24, 88, 8)))
with ThreadPoolExecutor(jobs) as ex:
    for seed, moves, model in ex.map(lambda s: run(binary, scale, s), range(lo, hi)):
        print(f"{seed}\t{moves}\t{model}", flush=True)
