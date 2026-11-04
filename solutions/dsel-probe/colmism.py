#!/usr/bin/env python3
"""Column-level handle mismatches before each request (dsel-probe).

Usage: colmism.py LIST CASE SALT [SALT...] [--orders N]
Tracks which papers are out of their columns (last move labeled lift / fill / reuse / relevel / help /
repair) or in place (ret / fret / dig / fix / fdig / hdig / gen). Before request r (target t, paper D),
for each handle hole h_c of D, the color of the first in-place paper of column c in the stack is
compared with A_t. Prints per salt: hole-requests, column-level mismatches and fixes per request, and
the mismatch rate by depth band of the handle.
"""
import sys
from collections import Counter
from pathlib import Path
import numpy as np
sys.path.insert(0, "/home/sato/ahc074/scripts")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay
from colfix import barcode_hash_of_input, load_design, parse_err
RUNS = Path("/home/sato/ahc074/runs")
OUT = {"lift", "fill", "reuse", "relevel", "help", "repair"}


def analyse(design_file, inp_path, out_path, err_path):
    d = load_design(design_file)
    H = int(d["H"]); perm = d["permutation"]
    hw = [perm[w] for w in d["handle"]]
    inp = replay.parse_input(Path(inp_path).read_text())
    out = replay.parse_output(inp, Path(out_path).read_text())
    text = Path(err_path).read_text()
    col, labels = parse_err(Path(err_path))
    tl = next(l for l in text.splitlines() if l.startswith("@paper targets = "))[len("@paper targets = "):].split()
    ded = {}
    for k, v in enumerate(tl):
        if v != "-":
            for t in v.split(","):
                ded[int(t)] = k
    papers = out.designs
    game = replay.Game(inp, papers)
    out_set = set()
    acc = np.zeros((3, H))  # hole requests, mismatches, fixes per handle
    for r, ops in enumerate(out.queries):
        t = inp.requests[r]; D = ded[t]
        top = {}
        for k in game.order:
            c = col[k]
            if c >= 0 and k not in out_set and c not in top and k != D:
                top[c] = k
        for c in range(H):
            bit = 1 << hw[c]
            if papers[D].opaque & bit:
                continue
            acc[0, c] += 1
            k = top.get(c)
            if k is not None and ((papers[k].black >> hw[c] & 1) != (inp.target[t] >> hw[c] & 1)):
                acc[1, c] += 1
        lab = labels.get(r, [])
        for (k, dd), l in zip(ops, lab):
            if l == "fix" and col[k] >= 0:
                acc[2, col[k]] += 1
            if l in OUT:
                out_set.add(k)
            else:
                out_set.discard(k)
        for k, dd in ops:
            game.move(k, dd)
        game.finish(r)
    return acc / len(out.queries)


def main():
    lst = Path(sys.argv[1]); case = int(sys.argv[2]); args = sys.argv[3:]
    n_orders = 2
    if "--orders" in args:
        n_orders = int(args[args.index("--orders") + 1]); args = args[:args.index("--orders")]
    info = {r[0]: (r[1], r[2]) for r in (l.split() for l in open(lst)) if r}
    for s in args:
        drun, orun = info[s]; run = RUNS / orun
        acc = 0
        for j in range(n_orders):
            base = run if j == 0 else run / "orders" / str(j)
            inp = Path(f"/home/sato/ahc074/tools/in/{case:04d}.txt") if j == 0 else sorted(Path("/home/sato/ahc074/runs/.orders").glob(f"*/{j}/{case:04d}.txt"))[0]
            acc = acc + analyse(RUNS / drun / "design" / f"{barcode_hash_of_input(case)}.txt", inp, base / "out" / f"{case:04d}.txt", base / "err" / f"{case:04d}.txt")
        acc = acc / n_orders
        bands = [(0, 8), (8, 16), (16, 21), (21, 25)]
        line = ' '.join(f"h{a}-{b}: rate {acc[1, a:b].sum() / acc[0, a:b].sum():.3f} fix/mism {acc[2, a:b].sum() / max(acc[1, a:b].sum(), 1e-9):.3f}" for a, b in bands)
        print(f"case {case} salt {s}: holes {acc[0].sum():.2f} col-mism {acc[1].sum():.3f} fix {acc[2].sum():.3f} | {line}")


if __name__ == "__main__":
    main()
