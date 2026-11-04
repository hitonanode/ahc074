#!/usr/bin/env python3
"""Per-request start mismatches vs fixes and fillers, by column band of the target (dsel-probe).

Usage: reqmism.py LIST CASE SALT [SALT...] [--orders N]
Before each request (target t, paper D, column l): holes of D at the handles; for each, the color
shown by the first paper (other than D) opaque there; mismatches. Then the request's fix moves and
filler moves (fill, reuse). Mean per band of l.
"""
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0, "/home/sato/ahc074/scripts")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay
from colfix import barcode_hash_of_input, load_design, parse_err
RUNS = Path("/home/sato/ahc074/runs")


def run_one(design_file, inp_path, out_path, err_path):
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
    acc = defaultdict(lambda: np.zeros(5))  # band -> [requests, holes, mism, fix, fillers]
    for r, ops in enumerate(out.queries):
        t = inp.requests[r]; D = ded[t]; band = min(col[D] // 5, 4)
        holes = mism = 0
        for c in range(H):
            bit = 1 << hw[c]
            if papers[D].opaque & bit:
                continue
            holes += 1
            want = inp.target[t] >> hw[c] & 1
            for k in game.order:
                if k != D and papers[k].opaque & bit:
                    mism += (papers[k].black >> hw[c] & 1) != want
                    break
        lab = labels.get(r, [])
        acc[band] += [1, holes, mism, sum(1 for l in lab if l == "fix"), sum(1 for l in lab if l in ("fill", "reuse"))]
        for k, dd in ops:
            game.move(k, dd)
        game.finish(r)
    return acc


def main():
    lst = Path(sys.argv[1]); case = int(sys.argv[2])
    args = sys.argv[3:]
    n_orders = 2
    if "--orders" in args:
        n_orders = int(args[args.index("--orders") + 1]); args = args[:args.index("--orders")]
    info = {r[0]: (r[1], r[2]) for r in (l.split() for l in open(lst)) if r}
    for s in args:
        drun, orun = info[s]; run = RUNS / orun
        tot = defaultdict(lambda: np.zeros(5))
        for j in range(n_orders):
            base = run if j == 0 else run / "orders" / str(j)
            inp = Path(f"/home/sato/ahc074/tools/in/{case:04d}.txt") if j == 0 else sorted(Path("/home/sato/ahc074/runs/.orders").glob(f"*/{j}/{case:04d}.txt"))[0]
            a = run_one(RUNS / drun / "design" / f"{barcode_hash_of_input(case)}.txt", inp, base / "out" / f"{case:04d}.txt", base / "err" / f"{case:04d}.txt")
            for b, v in a.items():
                tot[b] += v
        line = []
        for b in range(5):
            n, h, m, fx, fl = tot[b]
            line.append(f"band{b}: holes {h/n:5.2f} mism {m/n:5.2f} fix {fx/n:4.2f} fill {fl/n:4.2f}")
        allv = sum(tot.values())
        print(f"case {case} salt {s}: " + " | ".join(line) + f" || all: mism {allv[2]/allv[0]:.3f} fix {allv[3]/allv[0]:.3f}")


if __name__ == "__main__":
    main()
