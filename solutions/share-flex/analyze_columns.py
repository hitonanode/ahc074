#!/usr/bin/env python3
"""Per-column cost breakdown of a hub-type run (hub8 and descendants).

Infers from the design: generic papers (few opaque cells), handle windows (not covered by any
generic paper), the handle order (shallow handles are opaque in more dedicated papers), and for
each dedicated paper its column (deepest opaque handle) and the targets it serves (exact match on
its opaque cells). Then averages the moves of each request by column and by unit type.

usage: analyze_columns.py RUN [SEED_FROM SEED_TO]
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402

run = replay.resolve_run(sys.argv[1])
s0, s1 = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 48)
by_col = defaultdict(lambda: [0, 0, 0, 0])  # moves, requests, pair requests, deep handles
by_type = defaultdict(lambda: [0, 0])
col_sizes = defaultdict(list)
for seed in range(s0, s1):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, replay.out_path(run, seed).read_text())
    gen = [p for p in out.designs if bin(p.opaque).count("1") <= 6]
    gcover = 0
    for p in gen:
        gcover |= p.opaque
    handles = [j for j in range(64) if not gcover >> j & 1]
    ded = [k for k, p in enumerate(out.designs) if bin(p.opaque).count("1") > 6]
    cnt = {j: sum(out.designs[k].opaque >> j & 1 for k in ded) for j in handles}
    order = sorted(handles, key=lambda j: -cnt[j])
    H = len(order)
    col = {}
    serve = defaultdict(list)
    for k in ded:
        p = out.designs[k]
        col[k] = max(i for i, j in enumerate(order) if p.opaque >> j & 1)
    t2paper = {}
    for t, a in enumerate(inp.target):
        for k in ded:
            p = out.designs[k]
            if (a ^ p.black) & p.opaque == 0:
                t2paper[t] = k
                serve[k].append(t)
                break
    sizes = defaultdict(int)
    for k in ded:
        sizes[col[k]] += 1
    for l in range(H):
        col_sizes[l].append(sizes[l])
    for r, ops in enumerate(out.queries):
        t = inp.requests[r]
        if t not in t2paper:
            by_type["none"][0] += len(ops)
            by_type["none"][1] += 1
            continue
        k = t2paper[t]
        l = col[k]
        typ = "pair" if len(serve[k]) >= 2 else "single"
        by_type[typ][0] += len(ops)
        by_type[typ][1] += 1
        e = by_col[l]
        e[0] += len(ops)
        e[1] += 1
        e[2] += typ == "pair"
        e[3] += H - 1 - l
tot = sum(v[1] for v in by_type.values())
print(f"{run.name} seeds {s0}-{s1 - 1}")
for typ, (m, n) in by_type.items():
    print(f"  {typ:6s}: requests {n / tot * 100:5.1f}%  moves/request {m / max(n, 1):6.2f}")
print("  col  size  req%  pair%  deep_handles  moves/request  share_of_total_moves")
allm = sum(v[0] for v in by_col.values())
for l in sorted(by_col):
    m, n, pr, dh = by_col[l]
    sz = sum(col_sizes[l]) / len(col_sizes[l])
    print(f"  {l:3d}  {sz:4.1f}  {n / tot * 100:4.1f}  {pr / n * 100:5.1f}  {dh / n:12.1f}"
          f"  {m / n:13.2f}  {m / allm * 100:6.1f}%")
