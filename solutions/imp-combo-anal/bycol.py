"""Moves per request grouped by the column of the target paper D (pairs and singles apart), with the
digs of D's column, the handle holes of D and the moves on other columns.

usage: python3 bycol.py RUN [SEED_FROM SEED_TO]
"""
import sys
from collections import defaultdict
sys.path.insert(0, "/home/sato/ahc074/scripts")
import replay

run = replay.resolve_run(sys.argv[1])
lo, hi = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 40)
acc = defaultdict(lambda: [0, 0.0, 0.0, 0.0, 0.0, 0.0])  # n, ops, dig, holes, other, depth
size_acc = defaultdict(list)
for seed in range(lo, hi):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, replay.out_path(run, seed).read_text())
    P = out.designs
    game = replay.Game(inp, P)
    generic = set(game.order[:6])
    gmask = 0
    for k in generic: gmask |= P[k].opaque
    hmask = inp.full & ~gmask
    rank = {}
    for k in game.order:
        if k in generic: continue
        m = P[k].opaque & hmask
        while m:
            w = (m & -m).bit_length() - 1; m &= m - 1
            rank.setdefault(w, len(rank))
    col = {}
    for k in range(len(P)):
        if k in generic: continue
        m = P[k].opaque & hmask; ws = []
        while m:
            w = (m & -m).bit_length() - 1; m &= m - 1; ws.append(rank[w])
        col[k] = max(ws)
    owners = defaultdict(int)
    for v, t in enumerate(inp.target):
        pass
    sizes = defaultdict(int)
    for k, c in col.items(): sizes[c] += 1
    for c, s in sizes.items(): size_acc[c].append(s)
    # which papers serve two targets: a paper is a pair paper if it has generic holes
    pair = {k: bool(gmask & ~P[k].opaque) for k in col}
    for r, ops in enumerate(out.queries):
        D = None
        for k, d in ops:
            if k not in generic and d == 0: D = k
        if D is None:
            for k, d in ops: game.move(k, d, check=False)
            game.finish(r); continue
        c = col[D]
        # depth of D in its column before the request (papers of column c above it)
        depth = 0
        for k in game.order:
            if k == D: break
            if k in col and col[k] == c: depth += 1
        dig = other = 0; seen = False
        for k, d in ops:
            if k == D: seen = True
            elif k not in generic and d > 6:
                if not seen and col[k] == c: dig += 1
                else: other += 1
            game.move(k, d, check=False)
        game.finish(r)
        holes = bin(hmask & ~P[D].opaque).count("1")
        a = acc[(c, pair[D])]
        a[0] += 1; a[1] += len(ops); a[2] += dig; a[3] += holes; a[4] += other; a[5] += depth
print(f"run {run.name}, seeds {lo}-{hi}")
print(" col size | pair: n  ops   dig  holes other depth | single: n  ops   dig  holes other depth")
for c in range(28):
    s = sum(size_acc[c]) / len(size_acc[c]) if size_acc[c] else 0
    row = f" {c:3d} {s:4.1f} |"
    for p in (True, False):
        a = acc[(c, p)]
        if a[0]: row += f" {a[0]:5d} {a[1]/a[0]:5.2f} {a[2]/a[0]:5.2f} {a[3]/a[0]:5.2f} {a[4]/a[0]:5.2f} {a[5]/a[0]:5.2f} |"
        else: row += " " * 37 + "|"
    print(row)
