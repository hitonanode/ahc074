#!/usr/bin/env python3
"""Per-seed log score ratio of runs against a reference run of the same compare, over seed ranges.

usage: range_diff.py REF_RUN RUN [RUN ...]
Prints, for all seeds and for seeds 0-999 / 1000-1999: the mean of 100 * log(score / ref score) with its
standard error, and wins/ties/losses against the reference. WA (score 0) seeds are left out and counted.
"""
import json
import math
import os
import sys

ROOT = '/home/sato/ahc074/runs'


def scores(run):
    r = json.load(open(os.path.join(ROOT, run, 'result.json')))
    return {c['seed']: c['score'] for c in r['cases']}


def main():
    ref, runs = sys.argv[1], sys.argv[2:]
    rs = scores(ref)
    for run in runs:
        s = scores(run)
        for name, lo, hi in (('all', 0, 10 ** 9), ('0-999', 0, 1000), ('1000-1999', 1000, 2000)):
            ds, w, t, l, wa = [], 0, 0, 0, 0
            for seed, v in s.items():
                if not lo <= seed < hi or seed not in rs:
                    continue
                if v == 0 or rs[seed] == 0:
                    wa += 1
                    continue
                x = 100 * math.log(v / rs[seed])
                ds.append(x)
                w += x < 0
                t += x == 0
                l += x > 0
            n = len(ds)
            m = sum(ds) / n
            se = (sum((x - m) ** 2 for x in ds) / (n - 1)) ** .5 / n ** .5
            print(f'{run} vs {ref} [{name}]: {m:+.4f} +- {se:.4f} %, {w}/{t}/{l}, n {n}, WA {wa}')


if __name__ == '__main__':
    main()
