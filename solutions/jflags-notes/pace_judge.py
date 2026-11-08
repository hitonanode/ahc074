#!/usr/bin/env python3
"""Normal runs of the pacer against its base (judge-like builds): times, shedding, scores, identity.

usage: pace_judge.py BASE_RUN RUN [RUN ...]   (run-ids under /home/sato/ahc074/runs, same seeds)

Per run: the mean helper_end_sec / req_sec (ms, as the solution prints them, CLOCK_SCALE included),
end_sec mean / p99 / max and the cases past 1.85 / 1.88 / 1.90 / 1.93 s, the tester's execution time
(ms, real time; and its max), the requests below effort 0 (the cases with any, the mean per case, and
the mean requests per case at each effort), and against BASE_RUN: the paired
differences (run - base) of end_sec, req_sec and the execution time with their standard errors, the
mean log score ratio (%) with its standard error, and the seeds whose stdout is the same as the
base's (all of them, and among the cases without shedding).
"""
import glob
import json
import math
import os
import re
import sys

ROOT = '/home/sato/ahc074/runs'
LINE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*) = ([0-9.eE+-]+)$', re.M)


def load(run):
    d = os.path.join(ROOT, run)
    res = json.load(open(os.path.join(d, 'result.json')))
    cases = {}
    for c in res['cases']:
        seed = c['seed']
        f = os.path.join(d, 'err', '%04d.txt' % seed)
        v = dict((k, float(x)) for k, x in LINE.findall(open(f, errors='replace').read())) if os.path.exists(f) else {}
        v['score'] = c['score']
        v['exec'] = c['execution_time']
        v['out'] = open(os.path.join(d, 'out', '%04d.txt' % seed), 'rb').read()
        v['shed'] = sum(v.get('pace_effort%d' % e, 0) for e in range(1, 5)) + v.get('pace_light', 0)
        cases[seed] = v
    return cases


def mean_se(xs):
    n = len(xs)
    if n == 0:
        return float('nan'), float('nan')
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / (n - 1) if n > 1 else 0
    return m, math.sqrt(v / n)


def main():
    base_run, runs = sys.argv[1], sys.argv[2:]
    base = load(base_run)
    for run in [base_run] + runs:
        c = load(run)
        seeds = sorted(set(c) & set(base))
        g = lambda k: [c[s].get(k, float('nan')) * 1000 for s in seeds]
        ends = [c[s]['end_sec'] for s in seeds]
        shed = [c[s]['shed'] for s in seeds]
        se_ = sorted(ends)
        p99 = se_[min(len(se_) - 1, int(0.99 * len(se_)))]
        print('%s  (%d seeds)' % (run, len(seeds)))
        print('  helper_end %.1f  req %.1f ms  end mean %.4f p99 %.4f max %.4f s (>1.85 %d, >1.88 %d, >1.90 %d, >1.93 %d)'
              '  exec %.1f ms (max %.3f s)' % (
            mean_se(g('helper_end_sec'))[0], mean_se(g('req_sec'))[0], sum(ends) / len(ends), p99, max(ends),
            sum(e > 1.85 for e in ends), sum(e > 1.88 for e in ends), sum(e > 1.90 for e in ends),
            sum(e > 1.93 for e in ends), mean_se(g('exec'))[0], max(c[s]['exec'] for s in seeds)))
        if any('pace_effort0' in c[s] for s in seeds):
            lv = [sum(c[s].get(k, 0) for s in seeds) / len(seeds) for k in
                  ('pace_effort0', 'pace_effort1', 'pace_effort2', 'pace_effort3', 'pace_effort4', 'pace_light')]
            print('  shedding: %d/%d cases, %.2f requests per case (efforts 0-4, light per case: %s)' % (
                sum(x > 0 for x in shed), len(seeds), sum(shed) / len(shed), ' '.join('%.2f' % x for x in lv)))
        if run == base_run:
            continue
        for k, name in (('end_sec', 'end'), ('req_sec', 'req'), ('exec', 'exec')):
            m, se = mean_se([(c[s][k] - base[s][k]) * 1000 for s in seeds if k in c[s] and k in base[s]])
            print('  d%s %+.2f +- %.2f ms' % (name, m, se), end='')
        lr = [100 * math.log(c[s]['score'] / base[s]['score']) for s in seeds if c[s]['score'] and base[s]['score']]
        m, se = mean_se(lr)
        same = [s for s in seeds if c[s]['out'] == base[s]['out']]
        noshed = [s for s in seeds if c[s]['shed'] == 0]
        print('  score %+.4f +- %.4f%%  same stdout %d/%d (no shedding: %d/%d)' % (
            m, se, len(same), len(seeds), sum(c[s]['out'] == base[s]['out'] for s in noshed), len(noshed)))


if __name__ == '__main__':
    main()
