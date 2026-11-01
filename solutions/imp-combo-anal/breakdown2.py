"""Finer breakdown of the moves of a run by role.

usage: python3 breakdown2.py RUN [SEED_FROM SEED_TO]
Paper roles: generic = the 6 top papers at the start; handle windows = windows where every generic
sheet is a hole; the column of a dedicated paper = (number of opaque handle windows) - 1.
Within a request, D = the last dedicated paper moved to the top (d = 0). Deep moves (d > 6) are
split into: digs of D's column before D moves, the previous request's top paper put back, and the
rest (other columns: digging for the handle holes of D, or later clean-up).
"""
import sys
from collections import Counter
sys.path.insert(0, "/home/sato/ahc074/scripts")
import replay

run = replay.resolve_run(sys.argv[1])
lo, hi = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 100)
tot = Counter(); reqs = 0
for seed in range(lo, hi):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, replay.out_path(run, seed).read_text())
    game = replay.Game(inp, out.designs)
    generic = set(game.order[:6])
    gmask = 0
    for k in generic: gmask |= out.designs[k].opaque
    hmask = inp.full & ~gmask if hasattr(inp, "full") else ((1 << 64) - 1) & ~gmask
    col = {k: bin(p.opaque & hmask).count("1") - 1 for k, p in enumerate(out.designs) if k not in generic}
    prev_top = None
    for r, ops in enumerate(out.queries):
        reqs += 1
        D = None
        for k, d in ops:
            if k not in generic and d == 0: D = k
        tot["no_target_move"] += D is None
        if D is not None:
            H = bin(hmask).count("1")
            tot["D_handle_holes"] += H - 1 - col[D]
            tot["D_column_size_x"] += sum(1 for k in col if col[k] == col[D])
        seen_D = False
        for k, d in ops:
            if k in generic: tot["generic"] += 1
            elif d <= 6:
                tot["to_top" if d == 0 else "below_generic"] += 1
                if k == D: seen_D = True
            elif k == prev_top: tot["deep:prev_top_back"] += 1
            elif D is not None and not seen_D and col[k] == col[D]: tot["deep:dig_D_column"] += 1
            elif not seen_D: tot["deep:other_before_D"] += 1
            else: tot["deep:after_D"] += 1
            game.move(k, d, check=False)
        game.finish(r)
        tot["ops"] += len(ops)
        top_ded = next(k for k in game.order if k not in generic)
        prev_top = top_ded
print(f"run {run.name}, seeds {lo}-{hi}")
for key in sorted(tot): print(f"  {key:22s} {tot[key] / reqs:7.3f} per request")
