#!/usr/bin/env python3
"""Whether two runs printed the same outputs (all seeds, and all order lists of --orders runs), and
their paired request time (req_sec of the err files).

usage: same_outputs.py RUN_A RUN_B   (run-ids under /home/sato/ahc074/runs or paths)
"""
import glob
import os
import re
import sys

ROOT = '/home/sato/ahc074/runs'
REQ = re.compile(r'^req_sec = ([0-9.eE+-]+)$', re.M)


def outs(run):
    d = run if os.path.isdir(run) else os.path.join(ROOT, run)
    files = {('0', os.path.basename(f)): f for f in glob.glob(os.path.join(d, 'out', '*.txt'))}
    for f in glob.glob(os.path.join(d, 'orders', '*', 'out', '*.txt')):
        files[(f.split(os.sep)[-3], os.path.basename(f))] = f
    return d, files


def req(path):
    m = REQ.findall(open(path).read())
    return float(m[-1]) if m else None


def main():
    da, fa = outs(sys.argv[1])
    db, fb = outs(sys.argv[2])
    keys = sorted(set(fa) & set(fb))
    diff = [k for k in keys if open(fa[k], 'rb').read() != open(fb[k], 'rb').read()]
    print(f'common outputs {len(keys)} (only A {len(set(fa) - set(fb))}, only B {len(set(fb) - set(fa))}); '
          f'different {len(diff)}')
    for k in diff[:10]:
        print('  different:', k)
    d = []
    for j, name in keys:
        sub = '' if j == '0' else os.path.join('orders', j)
        ea, eb = os.path.join(da, sub, 'err', name), os.path.join(db, sub, 'err', name)
        if os.path.exists(ea) and os.path.exists(eb):
            a, b = req(ea), req(eb)
            if a is not None and b is not None:
                d.append((a, b))
    if d:
        n = len(d)
        ma = sum(a for a, _ in d) / n
        mb = sum(b for _, b in d) / n
        diffs = [1000 * (b - a) for a, b in d]
        md = sum(diffs) / n
        sd = (sum((x - md) ** 2 for x in diffs) / (n - 1)) ** .5 if n > 1 else 0
        print(f'req_sec (err files {n}): A {1000 * ma:.2f} ms, B {1000 * mb:.2f} ms, B - A {md:+.2f} +- {sd / n ** .5:.2f} ms '
              f'({100 * md / (1000 * ma):+.2f}%)')


if __name__ == '__main__':
    main()
