"""How the handle holes of the target paper D are shown at the end of each request: by the top of
their own column (a paper of column j on h_j) or by a filler (a paper of a deeper column covering
an interval of handles).

usage: python3 fillers.py RUN [SEED_FROM SEED_TO]
"""
import sys
from collections import Counter
sys.path.insert(0, "/home/sato/ahc074/scripts")
import replay

run = replay.resolve_run(sys.argv[1])
lo, hi = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 20)
tot = Counter(); reqs = 0; flen = Counter()
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
    def shown(D, w):
        return next((k for k in game.order if k != D and k not in generic and P[k].opaque >> w & 1), None)
    for r, ops in enumerate(out.queries):
        for k, d in ops: game.move(k, d, check=False)
        game.finish(r)
        D = next(k for k in game.order if k not in generic)
        holes = hmask & ~P[D].opaque
        reqs += 1
        papers = Counter()
        h = holes
        while h:
            w = (h & -h).bit_length() - 1; h &= h - 1
            x = shown(D, w)
            tot["holes"] += 1
            if x is None: tot["shown_none"] += 1
            elif col[x] == rank[w]: tot["shown_by_own_column_top"] += 1
            else:
                tot["shown_by_filler"] += 1; papers[x] += 1
        tot["filler_papers_showing"] += len(papers)
        for x, n in papers.items(): flen[n] += 1
print(f"run {run.name}, seeds {lo}-{hi}")
for key in sorted(tot): print(f"  {key:26s} {tot[key] / reqs:7.3f} per request")
print("  holes covered per filler paper:", dict(sorted(flen.items())))
