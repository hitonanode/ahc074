"""Column sizes and handle colors of a hub-type design (left-tools).

usage: python3 columns.py RUN [SEEDS]
For each seed: columns from the shallowest, as size:(papers black at the handle).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402


def columns(run_dir, seed):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, replay.out_path(run_dir, seed).read_text())
    pap = out.designs
    flips = [p for p in pap if 0 < bin(p.opaque).count("1") <= 8]
    gmask = 0
    for p in flips:
        gmask |= p.opaque
    # depth order of the handles from the single papers (opaque on every generic window): a
    # single of column l is opaque exactly on h_0..h_l
    singles = [p for p in pap if p.opaque & gmask == gmask and p.opaque & ~gmask]
    holes = [sum(1 for p in singles if not (p.opaque >> w & 1)) for w in range(inp.n)]
    handles = sorted([w for w in range(inp.n) if not (gmask >> w & 1)], key=lambda w: holes[w])
    cols = [[0, 0] for _ in handles]
    for p in pap:
        if p.opaque & ~gmask == 0:
            continue
        # column = deepest handle where the paper is opaque
        l = max(m for m, w in enumerate(handles) if p.opaque >> w & 1)
        cols[l][p.black >> handles[l] & 1] += 1
    return cols


run = replay.resolve_run(sys.argv[1])
n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
odd = tot = 0
for s in range(n):
    cols = columns(run, s)
    odd += sum((a + b) % 2 for a, b in cols)
    tot += len(cols)
    if s < 5:
        print(s, " ".join(f"{a + b}:{b}" for a, b in cols))
print(f"odd columns {odd}/{tot}")
