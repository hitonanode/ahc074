"""For each request, how many handle holes of the target paper D would show a wrong color if D were
put on top of the state before the request (the column tops showing through), versus the moves on
other columns that the solution then spends.

usage: python3 holes.py RUN [SEED_FROM SEED_TO]
"""
import sys
from collections import Counter
sys.path.insert(0, "/home/sato/ahc074/scripts")
import replay

run = replay.resolve_run(sys.argv[1])
lo, hi = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 20)
tot = Counter(); reqs = 0
for seed in range(lo, hi):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, replay.out_path(run, seed).read_text())
    P = out.designs
    game = replay.Game(inp, P)
    generic = set(game.order[:6])
    gmask = 0
    for k in generic: gmask |= P[k].opaque
    hmask = inp.full & ~gmask
    for r, ops in enumerate(out.queries):
        D = None
        for k, d in ops:
            if k not in generic and d == 0: D = k
        if D is None:
            D = next(k for k in game.order if k not in generic)  # already on top
        want = inp.target[inp.requests[r]]
        holes = hmask & ~P[D].opaque
        wrong = 0; h = holes
        while h:
            w = (h & -h).bit_length() - 1; h &= h - 1
            top = next((k for k in game.order if k != D and k not in generic and P[k].opaque >> w & 1), None)
            if top is None or (P[top].black >> w & 1) != (want >> w & 1): wrong += 1
        reqs += 1
        tot["holes"] += bin(holes).count("1"); tot["wrong_holes_before"] += wrong
        for k, d in ops: game.move(k, d, check=False)
        game.finish(r)
print(f"run {run.name}, seeds {lo}-{hi}")
for key in sorted(tot): print(f"  {key:22s} {tot[key] / reqs:7.3f} per request")
