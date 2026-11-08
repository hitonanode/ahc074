#!/usr/bin/env python3
"""How the SOTA's next request treats a paper left above (or inside) the generic layer: at every request
start, the papers above the lowest generic sheet other than the cap and the generic sheets ("extras":
the previous request's paper, old fillers kept on top, helpers), and whether that request moves them
(by label). This is the clearing a repair paper left there would get. From saved outputs only.

usage: extras.py --run RUN --seeds A-B
"""
import argparse
import sys
from collections import Counter

sys.path.insert(0, '/home/sato/ahc074/.claude/worktrees/esw-fixiter-improvement-55c629/scripts')
import replay  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', default='20261108-063038_legal-tie-fix')
    ap.add_argument('--seeds', default='0-50')
    a = ap.parse_args()
    lo, hi = map(int, a.seeds.split('-'))
    run = replay.resolve_run(a.run)
    fate = Counter()
    count = Counter()
    requests = 0
    for seed in range(lo, hi):
        inp = replay.load_input(seed)
        out = replay.parse_output(inp, (run / 'out' / f'{seed:04d}.txt').read_text())
        ann = replay.parse_annotations((run / 'err' / f'{seed:04d}.txt').read_text(), inp.k)
        role = ann.papers['role']
        special = {k for k in range(inp.k) if role[k] in ('cap', 'generic')}
        game = replay.Game(inp, out.designs)
        for r, ops in enumerate(out.queries):
            labels = ann.labels_of(r, len(ops))
            lowest = max(game.order.index(k) for k in special if role[k] == 'generic')
            extras = [k for k in game.order[:lowest] if k not in special]
            count[len(extras)] += 1
            moved = {}
            for (k, d), lab in zip(ops, labels):
                moved.setdefault(k, lab)
            for k in extras:
                fate[moved.get(k, 'kept')] += 1
            requests += 1
            for k, d in ops:
                game.move(k, d)
            game.finish(r)
    tot = sum(fate.values())
    print(f'{requests} requests; extras above the lowest generic sheet at a request start: '
          f'{tot / requests:.3f} per request, distribution {dict(sorted(count.items()))}')
    print('their fate in that request:', {k: f'{v / tot:.3f}' for k, v in fate.most_common()})


if __name__ == '__main__':
    main()
