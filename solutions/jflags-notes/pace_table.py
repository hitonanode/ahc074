#!/usr/bin/env python3
"""Pacer stretch tests: per run, the loss against a base run of the same compare, the end times and the
efforts used (solutions/jflags-pace-*, stderr lines pace_effort0..4, pace_light, pace_max_cycle_ms,
end_sec, req_sec, pace_sim_start_sec).

usage: pace_table.py BASE_RUN RUN [RUN ...]   (run-ids under /home/sato/ahc074/runs; every order list
       of a --orders run is read: err/ and orders/<j>/err/)

Columns: loss (mean over seeds of the per-seed mean over the lists of log(score / base score), %, with
its standard error), the predicted loss from the efforts used (sum over efforts of the share of the
requests at that effort x the loss of every request at it, LEVEL_LOSS below, measured with forced
efforts), end_sec (mean, max, and the number of runs past 1.88 / 1.90 / 1.93 s), the mean number of
requests at each effort, and the longest cycle of a request (ms, max over the runs).
"""
import glob
import json
import math
import os
import re
import sys

ROOT = '/home/sato/ahc074/runs'
LINE = re.compile(rb'^([A-Za-z_][A-Za-z0-9_]*) = ([0-9.eE+-]+)$', re.M)
# loss (%) of every request at effort e against effort 0 (fixed designs 20261108-155517_combo-m1-nine,
# 500 seeds x 2 lists: runs 20261108-232031_jflags-pace-dual30[-2], 20261108-232630_jflags-pace-dual30-2/-3
# and 20261108-232031_jflags-pace-dual30-5)
LEVEL_LOSS = [0.0, 0.0137, 0.1105, 0.1818, 0.6752, 4.8715]


def scores(run):
    r = json.load(open(os.path.join(ROOT, run, 'result.json')))
    return {c['seed']: (c.get('order_scores') or [c['score']]) for c in r['cases']}


def stats(run):
    d = os.path.join(ROOT, run)
    out = {}
    for f in glob.glob(os.path.join(d, 'err', '*.txt')) + glob.glob(os.path.join(d, 'orders', '*', 'err', '*.txt')):
        parts = f.split(os.sep)
        j = parts[-3] if parts[-4] == 'orders' else '0'
        seed = int(parts[-1][:-4])
        vals = {}
        for k, v in LINE.findall(open(f, 'rb').read()):
            vals[k.decode()] = float(v)
        out[(seed, j)] = vals
    return out


def mean_se(xs):
    n = len(xs)
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / (n - 1) if n > 1 else 0
    return m, math.sqrt(v / n)


def main():
    base, runs = sys.argv[1], sys.argv[2:]
    bs = scores(base)
    print('run                                          loss %     se  pred %   end mean    max  >1.88 >1.90 >1.93'
          '   e0     e1     e2     e3     e4  light  cyc ms  start')
    for run in [base] + runs:
        rs = scores(run)
        diffs = []
        for seed, s in rs.items():
            b = bs.get(seed)
            if not b or len(b) != len(s) or 0 in s or 0 in b:
                continue
            diffs.append(100 * sum(math.log(x / y) for x, y in zip(s, b)) / len(s))
        m, se = mean_se(diffs)
        st = stats(run)
        ends = [v['end_sec'] for v in st.values() if 'end_sec' in v]
        eff = [[v.get('pace_effort%d' % e, 0) for e in range(5)] + [v.get('pace_light', 0)] for v in st.values()]
        n = len(eff)
        effm = [sum(x[e] for x in eff) / n for e in range(6)]
        pred = sum(effm[e] / 1024 * LEVEL_LOSS[e] for e in range(6))
        cyc = max(v.get('pace_max_cycle_ms', 0) for v in st.values())
        starts = [v['pace_sim_start_sec'] for v in st.values() if 'pace_sim_start_sec' in v]
        start = sum(starts) / len(starts) if starts else float('nan')
        print('%-42s %+7.4f %6.4f %+7.4f  %7.4f %7.4f %5d %5d %5d ' % (
            run, m, se, pred, sum(ends) / len(ends), max(ends), sum(e > 1.88 for e in ends),
            sum(e > 1.90 for e in ends), sum(e > 1.93 for e in ends))
            + ' '.join('%6.1f' % x for x in effm) + ' %7.2f %6.3f' % (cyc, start))


if __name__ == '__main__':
    main()
