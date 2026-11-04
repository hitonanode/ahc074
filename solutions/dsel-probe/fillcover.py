#!/usr/bin/env python3
"""How many handle holes the fillers cover, good vs bad design of one case (dsel-probe).

Usage: fillcover.py LIST CASE SALT [SALT...] [--orders N]
Replays each request; after its moves, for every paper moved with the label fill / reuse / relevel,
counts the handle windows where it is the first opaque paper and the requested paper is a hole there
(the holes it covers), and the source column of the paper. Prints per salt: fills per request, mean
holes covered per fill, the distribution, and the mean source column.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0, "/home/sato/ahc074/scripts")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay
from colfix import barcode_hash_of_input, load_design, parse_err
RUNS = Path("/home/sato/ahc074/runs")


def analyse(design_file, inp_path, out_path, err_path):
    d = load_design(design_file)
    H = int(d["H"]); perm = d["permutation"]
    hmask = 0
    for w in d["handle"]:
        hmask |= 1 << perm[w]
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
    stats = Counter(); dist = Counter(); src = []
    for r, ops in enumerate(out.queries):
        t = inp.requests[r]; D = ded[t]
        lab = labels.get(r, [])
        for k, dd in ops:
            game.move(k, dd)
        game.finish(r)
        holes = hmask & ~papers[D].opaque
        fills = {k for (k, dd), l in zip(ops, lab) if l in ("fill", "reuse", "relevel", "repair")}
        if not fills:
            continue
        covered = 0
        first = {}
        for k in game.order:
            new = papers[k].opaque & ~covered
            if new & holes and k in fills:
                first[k] = bin(new & holes).count("1")
            covered |= papers[k].opaque
        for k in fills:
            c = first.get(k, 0)
            stats["fills"] += 1; stats["covered"] += c; dist[min(c, 6)] += 1; src.append(col[k])
    stats["requests"] = len(out.queries)
    return stats, dist, src


def main():
    lst = Path(sys.argv[1]); case = int(sys.argv[2]); args = sys.argv[3:]
    n_orders = 2
    if "--orders" in args:
        n_orders = int(args[args.index("--orders") + 1]); args = args[:args.index("--orders")]
    info = {r[0]: (r[1], r[2]) for r in (l.split() for l in open(lst)) if r}
    for s in args:
        drun, orun = info[s]; run = RUNS / orun
        S = Counter(); Dd = Counter(); src = []
        for j in range(n_orders):
            base = run if j == 0 else run / "orders" / str(j)
            inp = Path(f"/home/sato/ahc074/tools/in/{case:04d}.txt") if j == 0 else sorted(Path("/home/sato/ahc074/runs/.orders").glob(f"*/{j}/{case:04d}.txt"))[0]
            a, b, c = analyse(RUNS / drun / "design" / f"{barcode_hash_of_input(case)}.txt", inp, base / "out" / f"{case:04d}.txt", base / "err" / f"{case:04d}.txt")
            S.update(a); Dd.update(b); src += c
        n = S["fills"]
        print(f"case {case} salt {s}: fills/req {n / S['requests']:.3f} holes covered/fill {S['covered'] / max(n, 1):.3f} "
              f"dist {[round(Dd[i] / max(n, 1), 3) for i in range(7)]} mean src col {np.mean(src):.1f}")


if __name__ == "__main__":
    main()
