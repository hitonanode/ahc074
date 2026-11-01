"""Shared helpers for lat-probe scripts: load a run's case, column of each paper, replay."""
import sys
sys.path.insert(0, __file__.rsplit("/solutions/", 1)[0] + "/scripts")
import replay

RUN = "20261101-183237_imp-all"


def load(seed, run=RUN):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, (replay.resolve_run(run) / "out" / f"{seed:04d}.txt").read_text())
    d = out.designs
    gen = 0
    for k in range(6):
        gen |= d[k].opaque
    hw = [j for j in range(64) if not (gen >> j) & 1]
    cnt = {j: sum((d[k].opaque >> j) & 1 for k in range(6, 192)) for j in hw}
    chain = sorted(hw, key=lambda j: -cnt[j])  # h_0 .. h_{H-1}
    pos = {j: i for i, j in enumerate(chain)}
    col = {}
    for k in range(6, 192):
        op = [pos[j] for j in hw if (d[k].opaque >> j) & 1]
        col[k] = max(op) if op else -1
    gmask = gen
    # targets served by each paper: those barcodes equal to the paper on its opaque cells
    serves = {}
    for k in range(6, 192):
        o, b = d[k].opaque, d[k].black
        serves[k] = [v for v, a in enumerate(inp.target) if (a & o) == b]
    return inp, out, d, gmask, chain, col, serves
