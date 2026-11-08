#!/usr/bin/env python3
"""Whether two runs printed the same design (the K paper lines at the start of stdout) for every seed,
and the dv_candidates values of the first run.

usage: same_design.py RUN_A RUN_B [K]   (run-ids under /home/sato/ahc074/runs)
"""
import collections
import glob
import os
import re
import sys

ROOT = '/home/sato/ahc074/runs'


def designs(run, k):
    out = {}
    for f in glob.glob(os.path.join(ROOT, run, 'out', '*.txt')):
        with open(f) as fh:
            out[os.path.basename(f)] = [next(fh) for _ in range(k)]
    return out


def main():
    a, b = sys.argv[1], sys.argv[2]
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 192
    da, db = designs(a, k), designs(b, k)
    common = sorted(set(da) & set(db))
    diff = [s for s in common if da[s] != db[s]]
    print(f'seeds in both {len(common)} (only A {len(set(da) - set(db))}, only B {len(set(db) - set(da))}); '
          f'different designs {len(diff)}', diff[:10])
    cnt = collections.Counter()
    for f in glob.glob(os.path.join(ROOT, a, 'err', '*.txt')):
        m = re.findall(r'^dv_candidates = (\S+)$', open(f, errors='replace').read(), re.M)
        cnt[m[-1] if m else 'none'] += 1
    print('dv_candidates of A:', dict(cnt))


if __name__ == '__main__':
    main()
