"""Separates design quality from design-sequence noise: for seeds [lo, hi), nrng annealing seeds and
nseq request sequences (0 = the original, others re-drawn with the generator's rule), runs the probe
binary and prints the correlation between sequences of the design's score deviation within a case.
usage: seqvar.py <binary> <outdir> lo hi nrng nseq"""
import os, random, re, subprocess, sys, math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
binary, outdir, lo, hi, nr, ns = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
root = Path("/home/sato/ahc074")
(outdir / "in").mkdir(parents=True, exist_ok=True)
def input_path(s, q):
    if q == 0:
        return root / "tools/in" / f"{s:04d}.txt"
    p = outdir / "in" / f"{s:04d}_{q}.txt"
    if not p.exists():
        lines = (root / "tools/in" / f"{s:04d}.txt").read_text().split("\n")
        rng = random.Random(1000 * s + q)
        req = [rng.randrange(256)]
        for r in range(1, 1024):
            x = rng.randrange(255)
            req.append(x + (x >= req[-1]))
        p.write_text("\n".join(lines[:257] + [str(x) for x in req]) + "\n")
    return p
def job(a):
    s, rs, q = a
    env = dict(os.environ, HUB_ANNEAL="9000000", CLIMB_ITERS="60000", ANNEAL_SEED=str(rs))
    with open(input_path(s, q)) as fi:
        r = subprocess.run([str(root / "tools/target/release/tester"), binary], stdin=fi, capture_output=True, text=True, env=env)
    sc = int(re.findall(r"^Score = (\d+)", r.stderr, re.M)[-1])
    return s, rs, q, sc
jobs = [(s, rs, q) for s in range(lo, hi) for rs in range(nr) for q in range(ns)]
res = {}
with ThreadPoolExecutor(8) as ex:
    for s, rs, q, sc in ex.map(job, jobs):
        res[(s, rs, q)] = sc
# deviation of log score from the case-sequence mean
dev = {}
for s in range(lo, hi):
    for q in range(ns):
        m = sum(math.log(res[(s, rs, q)]) for rs in range(nr)) / nr
        for rs in range(nr):
            dev[(s, rs, q)] = math.log(res[(s, rs, q)]) - m
    print(s, " | ".join(" ".join(str(res[(s, rs, q)]) for rs in range(nr)) for q in range(ns)))
def corr(q1, q2):
    xs = [dev[(s, rs, q1)] for s in range(lo, hi) for rs in range(nr)]
    ys = [dev[(s, rs, q2)] for s in range(lo, hi) for rs in range(nr)]
    n = len(xs); mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys)); sxx = sum((x - mx) ** 2 for x in xs); syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy)
for q1 in range(ns):
    for q2 in range(q1 + 1, ns):
        print(f"corr of design deviations between sequences {q1} and {q2}: {corr(q1, q2):.3f}")
sd = math.sqrt(sum(v * v for v in dev.values()) / len(dev))
print(f"sd of log score within (case, sequence) across designs: {sd * 100:.2f}%")
