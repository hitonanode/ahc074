"""Runs the probe binary on seeds [lo, hi) with several annealing rng seeds (ANNEAL_SEED) and prints
per case: score and model_cost_after per rng seed, then the correlation. usage: rngvar.py <binary> <outdir> lo hi nrng"""
import os, re, subprocess, sys, math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
binary, outdir, lo, hi, nr = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
root = Path("/home/sato/ahc074")
outdir.mkdir(parents=True, exist_ok=True)
def job(a):
    s, rs = a
    env = dict(os.environ, HUB_ANNEAL="9000000", CLIMB_ITERS="60000", ANNEAL_SEED=str(rs))
    with open(root / "tools/in" / f"{s:04d}.txt") as fi:
        r = subprocess.run([str(root / "tools/target/release/tester"), binary], stdin=fi, capture_output=True, text=True, env=env)
    err = r.stderr
    sc = int(re.findall(r"^Score = (\d+)", err, re.M)[-1])
    mc = float(re.findall(r"^model_cost_after = ([-\d.e+]+)", err, re.M)[-1])
    pr = float(re.findall(r"^climb_proxy_after = ([-\d.e+]+)", err, re.M)[-1])
    hf = float(re.findall(r"^climb_hole_fixes = ([-\d.e+]+)", err, re.M)[-1])
    return s, rs, sc, mc, pr, hf
jobs = [(s, rs) for s in range(lo, hi) for rs in range(nr)]
res = {}
with ThreadPoolExecutor(8) as ex:
    for s, rs, sc, mc, pr, hf in ex.map(job, jobs):
        res[(s, rs)] = (sc, mc, pr, hf)
xs, ys = [], []
for s in range(lo, hi):
    row = [res[(s, rs)] for rs in range(nr)]
    scs = [r[0] for r in row]
    m = sum(scs) / nr
    print(s, " ".join(f"{sc} ({mc:.3f},{pr:.2f},{hf:.2f})" for sc, mc, pr, hf in row), f"spread {max(scs) - min(scs)} sd {math.sqrt(sum((x - m) ** 2 for x in scs) / (nr - 1)):.0f}")
    for sc, mc, pr, hf in row:
        xs.append(mc - sum(r[1] for r in row) / nr); ys.append(math.log(sc / m))
n = len(xs); mx, my = sum(xs) / n, sum(ys) / n
sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys)); sxx = sum((x - mx) ** 2 for x in xs); syy = sum((y - my) ** 2 for y in ys)
print(f"corr(model_cost dev, log score dev) = {sxy / math.sqrt(sxx * syy):.3f}, slope {sxy / sxx:.4f} (log score per unit model cost), sd log score within case {math.sqrt(syy / n) * 100:.2f}%")
