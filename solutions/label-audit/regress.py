"""Per-seed regression of the actual moves (and of each label group) on the model terms printed by
the design (model_col, model_hole, model_gc): does the actual cost follow the model's weights?

Usage: python3 regress.py RUN
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402

run_dir = replay.resolve_run(sys.argv[1])
rows = []
groups = {"dig": ["dig"], "hole": ["fix", "fdig", "fill", "fret", "relevel", "reuse"], "gen": ["gen", "help", "hdig"],
          "fix": ["fix"], "fillers": ["fdig", "fill", "fret", "relevel", "reuse"], "ret": ["ret"], "lift": ["lift"],
          "repair": ["repair"]}
for seed in replay.all_seeds():
    err = replay.err_path(run_dir, seed).read_text()
    st = replay.stderr_stats(err)
    labs = {}
    for line in err.splitlines():
        if line.startswith("@ops "):
            for t in line.split("=", 1)[1].split():
                name, star, cnt = t.rpartition("*")
                if star:
                    labs[name] = labs.get(name, 0) + int(cnt)
                else:
                    labs[t] = labs.get(t, 0) + 1
    R = 1024
    row = [st["model_col"], st["model_hole"], st["model_gc"], st["total_moves"] / R]
    row += [sum(labs.get(l, 0) for l in g) / R for g in groups.values()]
    rows.append(row)
X = np.array(rows)
print(f"{len(X)} seeds; means: col {X[:,0].mean():.3f} hole {X[:,1].mean():.3f} gc {X[:,2].mean():.3f} actual {X[:,3].mean():.3f}")
print(f"sd: col {X[:,0].std():.4f} hole {X[:,1].std():.4f} gc {X[:,2].std():.4f} actual {X[:,3].std():.4f}")
D = np.column_stack([np.ones(len(X)), X[:, 0], X[:, 1], X[:, 2]])
names = ["total"] + list(groups)
for i, name in enumerate(names):
    y = X[:, 3 + i]
    coef, res, *_ = np.linalg.lstsq(D, y, rcond=None)
    pred = D @ coef
    resid = y - pred
    sigma2 = resid @ resid / (len(y) - 4)
    cov = sigma2 * np.linalg.inv(D.T @ D)
    se = np.sqrt(np.diag(cov))
    r2 = 1 - resid.var() / y.var()
    print(f"{name:8s} mean {y.mean():6.3f}  = {coef[0]:6.3f} + col {coef[1]:6.3f}±{se[1]:.3f} + hole {coef[2]:6.3f}±{se[2]:.3f}"
          f" + gc {coef[3]:6.3f}±{se[3]:.3f}   R2 {r2:.3f}")
