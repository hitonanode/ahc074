"""Fixed iteration counts of esw-fixiter from the local esw-pace runs and the judge's code test.

Usage: python3 calibrate.py SCALE RUN-ID ...
Model: in a local run (CLOCK_SCALE 1.1) a stage of D scaled seconds ran n_s iterations on seed s;
the judge (Clang, AtCoder code test, seed 0) ran r times the local count of seed 0 in D real seconds.
A fixed count C then takes C * D / (r * n_s) judge seconds on seed s. C = SCALE * r * HM(n_s) keeps
the mean time of the stage at SCALE * D. Prints the counts and the predicted judge design end.
"""
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from iter_stats import load  # noqa: E402

scale = float(sys.argv[1])
runs = [load(r) for r in sys.argv[2:]]
# stage: (key, D = scaled seconds of the stage in esw-pace, judge Clang count on seed 0 or None)
judge = {"map_iters": 355e3, "anneal_iters": 16.1e6, "climb_iters": 34.6e3 * 1.13}  # climb: GCC x 1.13
stages = {
    "map_iters": 0.45 - 0.005,     # kMapEnd minus the input
    "gopt_steps": 0.549 - 0.45,    # kGoptEnd - kMapEnd
    "anneal_iters": 1.0845 - 0.5554,
    "climb_iters": 1.134 - 1.0845,
}
per_seed = {}
for data in runs:
    for s, d in data.items():
        for k in stages:
            if k in d:
                per_seed.setdefault(k, {}).setdefault(s, []).append(d[k])
n = {k: {s: sum(v) / len(v) for s, v in m.items()} for k, m in per_seed.items()}
r = {k: judge[k] / n[k][0] for k in judge}
r["gopt_steps"] = r["map_iters"]  # same matching evaluation as the window annealing
seeds = sorted(n["map_iters"])
C = {}
for k, D in stages.items():
    hm = len(seeds) / sum(1 / n[k][s] for s in seeds)
    C[k] = scale * r[k] * hm
    print(f"{k:14s} r={r[k]:.3f} hm={hm:10.0f} C={C[k]:10.0f}")
# the rest of the design: input 0.005, 4 reassignments 0.080, perforation 0.029, helpers 0.030
rest = 0.005 + 0.0646 / 3.23 * 4 + 0.029 + 0.030
t = sorted(rest + sum(C[k] * D / (r[k] * n[k][s]) for k, D in stages.items()) for s in seeds)
mean = sum(t) / len(t)
print(f"design end (judge, Clang): mean {mean:.3f}  50% {t[len(t)//2]:.3f}  99% {t[int(len(t)*0.99)]:.3f}"
      f"  99.9% {t[int(len(t)*0.999)]:.3f}  max {t[-1]:.3f}  min {t[0]:.3f}")
