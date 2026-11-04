"""Moves per request by the request's index r (buckets), per label: how much the first requests cost
(the initial stack) compared to the steady state.

Usage: python3 by_time.py RUN [--seeds A-B]
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("run")
ap.add_argument("--seeds", default="0-2000")
args = ap.parse_args()
run_dir = replay.resolve_run(args.run)
a, b = map(int, args.seeds.split("-"))
edges = [0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
tot = defaultdict(lambda: defaultdict(float))
cnt = defaultdict(int)
for seed in range(a, b):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, replay.out_path(run_dir, seed).read_text())
    ann = replay.parse_annotations(replay.err_path(run_dir, seed).read_text(), inp.k)
    for r, ops in enumerate(out.queries):
        bk = max(i for i in range(len(edges) - 1) if edges[i] <= r)
        cnt[bk] += 1
        tot[bk]["all"] += len(ops)
        for lab in ann.labels_of(r, len(ops)):
            tot[bk][lab] += 1
labels = ["all", "dig", "fix", "gen", "lift", "fret", "ret", "fill", "fdig", "relevel", "help", "reuse"]
print("requests   " + " ".join(f"{x:>7s}" for x in labels))
for bk in sorted(cnt):
    print(f"{edges[bk]:4d}-{edges[bk + 1] - 1:4d}  " + " ".join(f"{tot[bk][x] / cnt[bk]:7.3f}" for x in labels))
