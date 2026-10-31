"""Moves of the requests of u0 and of the request right after them, against a reference run.

usage: python3 u0_after.py RUN_U0 RUN_REF [SEED_END]
RUN_U0 prints `u0 = <target>` on stderr (paper-u0). For every seed, the requests r with a_r = u0 and
r + 1 are compared with the same requests of RUN_REF, and the other requests too.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402

run_u, run_r = replay.resolve_run(sys.argv[1]), replay.resolve_run(sys.argv[2])
end = int(sys.argv[3]) if len(sys.argv) > 3 else 96
tot = {"u0": [0, 0, 0], "next": [0, 0, 0], "other": [0, 0, 0]}  # moves u0-run, moves ref, count
for seed in range(end):
    errp = run_u / "err" / f"{seed:04d}.txt"
    if not errp.exists():
        continue
    m = re.search(r"^u0 = (\d+)$", errp.read_text(), re.M)
    if not m:
        continue
    u0 = int(m.group(1))
    inp = replay.load_input(seed)
    ou = replay.parse_output(inp, (run_u / "out" / f"{seed:04d}.txt").read_text())
    orf = replay.parse_output(inp, (run_r / "out" / f"{seed:04d}.txt").read_text())
    reqs = inp.requests
    kind = ["other"] * len(reqs)
    for r, a in enumerate(reqs):
        if a == u0:
            kind[r] = "u0"
            if r + 1 < len(reqs) and reqs[r + 1] != u0:
                kind[r + 1] = "next"
    for r in range(len(reqs)):
        t = tot[kind[r]]
        t[0] += len(ou.queries[r])
        t[1] += len(orf.queries[r])
        t[2] += 1
for k, (a, b, n) in tot.items():
    if n:
        print(f"{k:6s} n={n:6d}  u0-run {a / n:7.3f}  ref {b / n:7.3f}  diff {(a - b) / n:+7.3f}")
