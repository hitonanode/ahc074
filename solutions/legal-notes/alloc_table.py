#!/usr/bin/env python3
"""Value per ms of request-side variants against a base run of the same compare (fixed designs).

usage: alloc_table.py BASE_RUN RUN [RUN ...]   (run-ids under /home/sato/ahc074/runs; a run may also be
       given as the suffix of a group: alloc_table.py --group 20261108-090642 lists every run of it)

For each run: the mean over seeds of the per-seed mean (over the order lists) of log(score / base score)
in % (negative: better) with its standard error, wins/ties/losses of the seeds, the paired request time
(req_sec of the err files of every list, ms per case) with its standard error, and the value per 100 ms:
-(difference %) / (time difference ms) * 100, i.e. % gained per 100 ms spent (for a reduction: % lost per
100 ms freed).
"""
import glob
import json
import math
import os
import re
import sys

ROOT = '/home/sato/ahc074/runs'
REQ = re.compile(rb'^req_sec = ([0-9.eE+-]+)$', re.M)


def scores(run):
    r = json.load(open(os.path.join(ROOT, run, 'result.json')))
    out = {}
    for c in r['cases']:
        s = c.get('order_scores') or [c['score']]
        out[c['seed']] = s
    return out


def reqs(run):
    d = os.path.join(ROOT, run)
    out = {}
    for f in glob.glob(os.path.join(d, 'err', '*.txt')) + glob.glob(os.path.join(d, 'orders', '*', 'err', '*.txt')):
        parts = f.split(os.sep)
        j = parts[-3] if parts[-4] == 'orders' else '0'
        seed = int(parts[-1][:-4])
        m = REQ.findall(open(f, 'rb').read())
        if m:
            out[(seed, j)] = float(m[-1])
    return out


def mean_se(xs):
    n = len(xs)
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / (n - 1) if n > 1 else 0
    return m, math.sqrt(v / n)


def main():
    args = sys.argv[1:]
    if args and args[0] == '--group':
        runs = sorted(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, args[1] + '_*')))
        base = args[2] if len(args) > 2 else next(r for r in runs if r.endswith('legal-tie-fast'))
        runs = [r for r in runs if r != base]
    else:
        base, runs = args[0], args[1:]
    bs, br = scores(base), reqs(base)
    print(f'base {base}: seeds {len(bs)}, req {1000 * sum(br.values()) / len(br):.1f} ms per case')
    print(f'{"run":44s} {"diff %":>8s} {"se":>7s} {"W/T/L":>14s} {"req ms":>8s} {"se":>5s} {"%/100ms":>8s}')
    rows = []
    for run in runs:
        s, rq = scores(run), reqs(run)
        ds, w, t, l = [], 0, 0, 0
        for seed, v in s.items():
            b = bs.get(seed)
            if not b or len(b) != len(v) or 0 in v or 0 in b:
                continue
            x = sum(math.log(a / c) for a, c in zip(v, b)) / len(v) * 100
            ds.append(x)
            w += x < -1e-12
            l += x > 1e-12
            t += abs(x) <= 1e-12
        dm, dse = mean_se(ds)
        dt = [1000 * (rq[k] - br[k]) for k in rq if k in br]
        tm, tse = mean_se(dt) if len(dt) > 1 else (float('nan'), 0)
        value = -dm / tm * 100 if abs(tm) > 0.5 else float('nan')
        rows.append((run, dm, dse, w, t, l, tm, tse, value))
    for run, dm, dse, w, t, l, tm, tse, value in rows:
        print(f'{run:44s} {dm:+8.4f} {dse:7.4f} {w:5d}/{t:3d}/{l:4d} {tm:+8.1f} {tse:5.1f} {value:+8.3f}')


if __name__ == '__main__':
    main()
