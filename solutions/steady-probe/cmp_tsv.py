"""Paired comparison of run_knobs.py / run_compute.py outputs: mean log ratio of the simulated moves
per design (percent) +- standard error, and the model cost difference.

usage: python3 solutions/steady-probe/cmp_tsv.py BASE.tsv CAND.tsv [...]
"""
import math, statistics, sys


def load(p):
    return {int(l.split()[0]): [float(x) for x in l.split()[1:]] for l in open(p) if l.strip()}


base = load(sys.argv[1])
for path in sys.argv[2:]:
    c = load(path)
    ks = sorted(set(base) & set(c))
    d = [100 * math.log(c[k][0] / base[k][0]) for k in ks]
    dm = [c[k][1] - base[k][1] for k in ks]
    wrong = sum(c[k][2] for k in ks if len(c[k]) > 2)
    se = statistics.stdev(d) / len(d) ** 0.5
    print(f"{path.split('/')[-1]}: n={len(ks)} sim {statistics.mean(d):+.3f} ± {se:.3f}%  "
          f"model {statistics.mean(dm):+.4f} moves  win {sum(x < 0 for x in d)}/{sum(x == 0 for x in d)}/{sum(x > 0 for x in d)}  wrong {wrong}")
