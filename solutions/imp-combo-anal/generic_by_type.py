"""Moves of the generic sheets per request, split by the kind of the target paper D (pair: D has
generic holes; single) and by the kind of the previous request.

usage: python3 generic_by_type.py RUN [SEED_FROM SEED_TO]
"""
import sys
from collections import Counter
sys.path.insert(0, "/home/sato/ahc074/scripts")
import replay

run = replay.resolve_run(sys.argv[1])
lo, hi = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 20)
n = Counter(); g = Counter(); ops_t = Counter()
for seed in range(lo, hi):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, replay.out_path(run, seed).read_text())
    P = out.designs
    game = replay.Game(inp, P)
    generic = set(game.order[:6])
    gmask = 0
    for k in generic: gmask |= P[k].opaque
    paper_of = {}
    for k in range(len(P)):
        if k in generic: continue
        for v, t in enumerate(inp.target):
            pass
    prev_kind = "none"
    for r, ops in enumerate(out.queries):
        D = None
        for k, d in ops:
            if k not in generic and d == 0: D = k
        for k, d in ops: game.move(k, d, check=False)
        game.finish(r)
        if D is None: D = next(k for k in game.order if k not in generic)
        kind = "pair" if gmask & ~P[D].opaque else "single"
        key = (prev_kind, kind)
        n[key] += 1; g[key] += sum(1 for k, d in ops if k in generic); ops_t[key] += len(ops)
        prev_kind = kind
print(f"run {run.name}, seeds {lo}-{hi}")
for key in sorted(n): print(f"  prev {key[0]:6s} -> {key[1]:6s}: n {n[key]:6d}  generic {g[key]/n[key]:.3f}  ops {ops_t[key]/n[key]:.2f}")
