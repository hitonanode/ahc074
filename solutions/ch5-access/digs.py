#!/usr/bin/env python3
"""Dig moves per request by the role of the requested paper (pair / single), from saved outputs and
@ops labels: what a product already pays for the papers above its own paper.

usage: digs.py --run RUN --seeds A-B
"""
import argparse
import sys
from collections import defaultdict

sys.path.insert(0, '/home/sato/ahc074/.claude/worktrees/esw-fixiter-improvement-55c629/scripts')
import replay  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', default='20261108-063038_legal-tie-fix')
    ap.add_argument('--seeds', default='0-50')
    a = ap.parse_args()
    lo, hi = map(int, a.seeds.split('-'))
    run = replay.resolve_run(a.run)
    acc = defaultdict(lambda: [0, 0, 0, 0])  # role -> requests, digs, requests with >= 1 dig, >= 2 digs
    for seed in range(lo, hi):
        inp = replay.load_input(seed)
        out = replay.parse_output(inp, (run / 'out' / f'{seed:04d}.txt').read_text())
        ann = replay.parse_annotations((run / 'err' / f'{seed:04d}.txt').read_text(), inp.k)
        role, targets = ann.papers['role'], ann.papers['targets']
        paper_of = {}
        for k in range(inp.k):
            if targets[k] != '-':
                for t in targets[k].split(','):
                    paper_of[int(t)] = k
        for r, ops in enumerate(out.queries):
            labels = ann.labels_of(r, len(ops))
            x = inp.requests[r]
            k = paper_of.get(x, -1)
            ro = role[k] if k >= 0 else 'none'
            d = sum(1 for l in labels if l == 'dig')
            s = acc[ro]
            s[0] += 1
            s[1] += d
            s[2] += d >= 1
            s[3] += d >= 2
    for ro, (n, d, d1, d2) in sorted(acc.items()):
        print(f'{ro:7s} requests {n:6d}: digs {d / n:.3f} per request, >= 1 dig {d1 / n:.3f}, >= 2 digs {d2 / n:.3f}')


if __name__ == '__main__':
    main()
