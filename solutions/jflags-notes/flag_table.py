#!/usr/bin/env python3
"""Times of the flag arms of one run.py compare, and whether paired arms printed the same outputs.

usage: flag_table.py GROUP SOLVER [SOLVER ...] [--pairs a:b,c:d]
  GROUP: the run-id stamp (e.g. 20261108-220309); each solver has arms GROUP_<solver>, GROUP_<solver>-2,
  -3, -4 ... (in the order run.py gave them). --pairs lists the arm pairs (1-based) to difference, e.g.
  1:2,3:4 = (clang native, + zero) and (gcc native, + zero).
Per arm: the mean helper_end_sec / req_sec / end_sec (ms, CLOCK_SCALE included as the solution prints
them) and the judge-model time (1.04 helper_end + 1.35 req + the rest). Per pair: the paired per-seed
difference (second - first) with its standard error, and the number of seeds whose stdout differs.
"""
import glob
import json
import os
import re
import sys

import numpy as np

ROOT = '/home/sato/ahc074/runs'
KEYS = ('map_end_sec', 'climb_end_sec', 'anneal_end_sec', 'helper_end_sec', 'req_sec', 'end_sec')


def load(run):
    out = {}
    for f in glob.glob(os.path.join(ROOT, run, 'err', '*.txt')):
        text = open(f, errors='replace').read()
        v = {}
        for k in KEYS:
            m = re.findall(r'^' + k + r' = ([0-9.eE+-]+)$', text, re.M)
            if m:
                v[k] = float(m[-1])
        if {'helper_end_sec', 'req_sec', 'end_sec'} <= v.keys():
            h, q, e = v['helper_end_sec'], v['req_sec'], v['end_sec']
            v['judge'] = 1.04 * h + 1.35 * q + (e - h - q)
        out[int(os.path.basename(f)[:-4])] = v  # a stage line can be missing (climb_end_sec in some designs)
    return out


def outputs(run):
    return {os.path.basename(f): open(f, 'rb').read() for f in glob.glob(os.path.join(ROOT, run, 'out', '*.txt'))}


def label(run):
    m = json.load(open(os.path.join(ROOT, run, 'meta.json')))
    j = m.get('jflags', {})
    return f'{j.get("compiler", "?")} {j.get("flags", "?")}'


def main():
    args = sys.argv[1:]
    pairs = [(1, 2), (3, 4)]
    if '--pairs' in args:
        i = args.index('--pairs')
        pairs = [tuple(map(int, p.split(':'))) for p in args[i + 1].split(',')]
        args = args[:i] + args[i + 2:]
    group, solvers = args[0], args[1:]
    for s in solvers:
        runs = []
        for i in range(1, 20):
            r = f'{group}_{s}' if i == 1 else f'{group}_{s}-{i}'
            if not os.path.isdir(os.path.join(ROOT, r)):
                break
            runs.append(r)
        data = [load(r) for r in runs]
        print(f'== {s}')
        for i, (r, d) in enumerate(zip(runs, data), 1):
            vals = {k: (1000 * np.mean([v[k] for v in d.values() if k in v]), sum(1 for v in d.values() if k in v))
                    for k in KEYS + ('judge',)}
            print(f'  arm {i} ({label(r)}): seeds {len(d)}, ' + ', '.join(
                f'{k.replace("_sec", "")} {vals[k][0]:.1f}' + (f' (n {vals[k][1]})' if vals[k][1] != len(d) else '')
                for k in KEYS + ('judge',)) + ' ms')
        for a, b in pairs:
            da, db = data[a - 1], data[b - 1]
            seeds = sorted(set(da) & set(db))
            line = []
            for k in KEYS + ('judge',):
                x = np.array([1000 * (db[t][k] - da[t][k]) for t in seeds if k in da[t] and k in db[t]])
                line.append(f'{k.replace("_sec", "")} {x.mean():+.1f} ± {x.std(ddof=1) / len(x) ** .5:.1f}')
            oa, ob = outputs(runs[a - 1]), outputs(runs[b - 1])
            common = set(oa) & set(ob)
            diff = sum(1 for f in common if oa[f] != ob[f])
            print(f'  arm {b} - arm {a}: ' + ', '.join(line) + f' ms; stdout different in {diff} of {len(common)} seeds')


if __name__ == '__main__':
    main()
