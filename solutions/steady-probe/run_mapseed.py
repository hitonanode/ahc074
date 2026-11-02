"""Within-input variation of the window assignment: for each input, several MAP_SEED values (fixed
iteration counts), and the resulting gobj_after, model_cost and simulated moves (SIM_SEQS=2).

usage: python3 solutions/steady-probe/run_mapseed.py BINARY FROM TO NSEEDS JOBS [NAME=VALUE ...] > out.tsv
"""
import os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

BASE = dict(MAP_ITERS="380000", GOPT_STEPS="110000", ANNEAL_ITERS="19000000", CLIMB_ITERS="65000", SIM_SEQS="2")


def run(binary, extra, seed, ms):
    env = dict(os.environ, **BASE, **extra, MAP_SEED=str(ms))
    with open(f"/home/sato/ahc074/tools/in/{seed:04d}.txt") as f:
        p = subprocess.run([binary], stdin=f, capture_output=True, text=True, env=env)
    st = dict(l.split(" = ") for l in p.stderr.splitlines() if " = " in l)
    return seed, ms, st.get("gobj_after"), st.get("model_cost"), st.get("sim_moves")


binary, lo, hi, nseeds, jobs = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
extra = dict(a.split("=", 1) for a in sys.argv[6:])
tasks = [(s, m) for s in range(lo, hi) for m in range(nseeds)]
with ThreadPoolExecutor(jobs) as ex:
    for r in ex.map(lambda t: run(binary, extra, *t), tasks):
        print("\t".join(str(x) for x in r), flush=True)
