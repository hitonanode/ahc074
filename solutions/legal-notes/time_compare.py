#!/usr/bin/env python3
"""Judge-model times of runs of one normal compare, against a reference run (paired by seed).

usage: time_compare.py REF_RUN RUN [RUN ...]   (run-ids under /home/sato/ahc074/runs)
The judge model (trial_log 2026-11-05): 1.04 x helper_end_sec + 1.35 x req_sec + (end_sec - both).
Prints for each run: the mean of the model (and its ratio to the first run given, usually argon), its 99%
point, the 99% point difference to REF with a paired bootstrap 90% interval over seeds, the mean
req_sec and its paired difference to REF (ms), and end_sec over 1.8 s.
"""
import glob
import os
import re
import sys

import numpy as np

ROOT = '/home/sato/ahc074/runs'
KEYS = ('helper_end_sec', 'req_sec', 'end_sec')


def load(run):
    out = {}
    for f in glob.glob(os.path.join(ROOT, run, 'err', '*.txt')):
        text = open(f, errors='replace').read()
        v = {}
        for k in KEYS:
            m = re.findall(r'^' + k + r' = ([0-9.eE+-]+)$', text, re.M)
            if m:
                v[k] = float(m[-1])
        if len(v) == 3:
            h, q, e = v['helper_end_sec'], v['req_sec'], v['end_sec']
            out[int(os.path.basename(f)[:-4])] = (1.04 * h + 1.35 * q + (e - h - q), q, e)
    return out


def main():
    ref, runs = sys.argv[1], sys.argv[2:]
    data = {r: load(r) for r in [ref] + runs}
    first = runs[0] if runs else ref
    first_mean = np.mean([v[0] for v in data[first].values()])
    rng = np.random.default_rng(1)
    rd = data[ref]
    for run in [ref] + runs:
        d = data[run]
        seeds = sorted(set(d) & set(rd))
        m = np.array([d[s][0] for s in seeds])
        mr = np.array([rd[s][0] for s in seeds])
        q = np.array([d[s][1] for s in seeds])
        qr = np.array([rd[s][1] for s in seeds])
        e = np.array([d[s][2] for s in seeds])
        boots = []
        for _ in range(2000):
            idx = rng.integers(0, len(seeds), len(seeds))
            boots.append(np.quantile(m[idx], .99) - np.quantile(mr[idx], .99))
        lo, hi = np.quantile(boots, [.05, .95])
        dq = 1000 * (q - qr)
        print(f'{run}: seeds {len(seeds)}, model mean {m.mean():.4f} s ({m.mean() / first_mean:.3f} x {first}), '
              f'p99 {np.quantile(m, .99):.4f} s, p99 - ref {1000 * (np.quantile(m, .99) - np.quantile(mr, .99)):+.1f} ms '
              f'[90%: {1000 * lo:+.1f}, {1000 * hi:+.1f}], req {1000 * q.mean():.1f} ms '
              f'(- ref {dq.mean():+.1f} +- {dq.std(ddof=1) / len(dq) ** .5:.1f}), end_sec > 1.8: {(e > 1.8).sum()}')


if __name__ == '__main__':
    main()
