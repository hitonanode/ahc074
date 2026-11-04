#!/usr/bin/env python3
"""Handle mismatches at the start of each request, per column (dsel-probe).

Usage: mismatch.py LIST --seeds A-B [--orders N]   (LIST as for variance.py)

Replays the saved outputs. Before each request r (target t, paper D in column l), for every handle
h_c where D is a hole (c > l, or a pair difference), the color shown at h_c by the stack without D
and without the papers out of the columns (the top paper of column c that is in place, i.e. the
first paper of a column >= c in the stack order... approximated by the first paper opaque at h_c
below the generic layer, skipping D) is compared with A_t. Counts per column: hole-requests,
mismatches, and the realized fix moves (label fix). Writes LIST.mismatch.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/sato/ahc074/scripts")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay  # noqa: E402
from colfix import barcode_hash_of_input, load_design, parse_err  # noqa: E402

RUNS = Path("/home/sato/ahc074/runs")


def analyse(design_file, inp_path, out_path, err_path):
    d = load_design(design_file)
    H = int(d["H"])
    perm = d["permutation"]
    handle_win = [perm[w] for w in d["handle"]]  # output window of h_c
    inp = replay.parse_input(Path(inp_path).read_text())
    out = replay.parse_output(inp, Path(out_path).read_text())
    col, labels = parse_err(Path(err_path))
    # the paper (output numbering) of each target: from @paper targets
    targets_line = None
    for line in Path(err_path).read_text().splitlines():
        if line.startswith("@paper targets = "):
            targets_line = line[len("@paper targets = "):].split()
            break
    ded = {}
    for k, v in enumerate(targets_line):
        if v != "-":
            for t in v.split(","):
                ded[int(t)] = k
    papers = out.designs
    game = replay.Game(inp, papers)
    hole_req = np.zeros(H)
    mism = np.zeros(H)
    fixes = np.zeros(H)
    for r, ops in enumerate(out.queries):
        t = inp.requests[r]
        D = ded[t]
        lab = labels.get(r, [])
        # colors at the handles before the request, skipping D (it will be on top, transparent there)
        for c in range(H):
            w = handle_win[c]
            bit = 1 << w
            if papers[D].opaque & bit:
                continue  # not a hole of D
            hole_req[c] += 1
            want = inp.target[t] >> w & 1
            shown = 0
            for k in game.order:
                if k == D:
                    continue
                if papers[k].opaque & bit:
                    shown = papers[k].black >> w & 1
                    break
            if shown != want:
                mism[c] += 1
        for (k, dd), l in zip(ops, lab):
            if l == "fix" and col[k] >= 0:
                fixes[col[k]] += 1
        for k, dd in ops:
            game.move(k, dd)
        game.finish(r)
    n = len(out.queries)
    return hole_req / n, mism / n, fixes / n


def main():
    lst = Path(sys.argv[1])
    lo, hi = map(int, sys.argv[sys.argv.index("--seeds") + 1].split("-"))
    n_orders = int(sys.argv[sys.argv.index("--orders") + 1]) if "--orders" in sys.argv else 1
    rows = [line.split() for line in lst.read_text().splitlines() if line.strip()]
    res = {}
    for salt, design_run, orders_run in rows:
        run = RUNS / orders_run
        for seed in range(lo, hi):
            dfile = RUNS / design_run / "design" / f"{barcode_hash_of_input(seed)}.txt"
            acc = None
            for j in range(n_orders):
                base = run if j == 0 else run / "orders" / str(j)
                inp_path = Path(f"/home/sato/ahc074/tools/in/{seed:04d}.txt") if j == 0 else \
                    sorted(Path("/home/sato/ahc074/runs/.orders").glob(f"*/{j}/{seed:04d}.txt"))[0]
                a = analyse(dfile, inp_path, base / "out" / f"{seed:04d}.txt", base / "err" / f"{seed:04d}.txt")
                acc = a if acc is None else tuple(x + y for x, y in zip(acc, a))
            res[f"{salt}:{seed}"] = [list(x / n_orders) for x in acc]
    lst.with_suffix(".mismatch.json").write_text(json.dumps(res))
    salts = sorted({k.split(":")[0] for k in res}, key=int)
    seeds = sorted({int(k.split(":")[1]) for k in res})
    Hq = np.array([[res[f"{s}:{c}"][0] for s in salts] for c in seeds])
    Mm = np.array([[res[f"{s}:{c}"][1] for s in salts] for c in seeds])
    Fx = np.array([[res[f"{s}:{c}"][2] for s in salts] for c in seeds])
    print(f"{len(seeds)} cases x {len(salts)} designs")
    print(f"{'col':>4s} {'holes/req':>9s} {'mism/req':>9s} {'fix/req':>8s} {'fix/mism':>9s} {'r(mism,fix)':>12s} {'sd mism':>8s} {'sd fix':>7s}")
    for c in range(Hq.shape[2]):
        md = Mm[:, :, c] - Mm[:, :, c].mean(axis=1, keepdims=True)
        fd = Fx[:, :, c] - Fx[:, :, c].mean(axis=1, keepdims=True)
        r = np.corrcoef(md.ravel(), fd.ravel())[0, 1] if md.std() > 0 and fd.std() > 0 else float("nan")
        print(f"{c:4d} {Hq[:, :, c].mean():9.4f} {Mm[:, :, c].mean():9.4f} {Fx[:, :, c].mean():8.4f} "
              f"{Fx[:, :, c].mean() / max(Mm[:, :, c].mean(), 1e-9):9.3f} {r:12.3f} {md.std():8.4f} {fd.std():7.4f}")


if __name__ == "__main__":
    main()
