#!/usr/bin/env python3
"""Parameter sweep helper (own measurement, not an evaluation record).

Runs the official tester on seeds [START, END) for a compiled binary with environment variables,
in parallel, and prints the mean score and the mean of selected `name = value` stderr lines.

    sweep.py BINARY START END [-j 8] [-e KEY=VAL ...] [-s stat_name ...]
"""
import argparse
import concurrent.futures as cf
import os
import re
import subprocess
import sys

ROOT = "/home/sato/ahc074"
LINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([-+0-9.eE]+)\s*$")


def run(binary, seed, env):
    inp = open(f"{ROOT}/tools/in/{seed:04d}.txt")
    p = subprocess.run([f"{ROOT}/tools/target/release/tester", binary], stdin=inp,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=env)
    vals = {}
    for line in p.stderr.splitlines():
        m = LINE.match(line)
        if m:
            vals[m.group(1)] = float(m.group(2))
    return seed, vals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("binary")
    ap.add_argument("start", type=int)
    ap.add_argument("end", type=int)
    ap.add_argument("-j", type=int, default=8)
    ap.add_argument("-e", action="append", default=[])
    ap.add_argument("-s", action="append", default=[])
    a = ap.parse_args()
    env = dict(os.environ)
    for kv in a.e:
        k, v = kv.split("=", 1)
        env[k] = v
    res = {}
    with cf.ThreadPoolExecutor(a.j) as ex:
        for seed, vals in ex.map(lambda s: run(a.binary, s, env), range(a.start, a.end)):
            res[seed] = vals
    scores = [res[s].get("Score", 0) for s in sorted(res)]
    n = len(scores)
    print(f"{' '.join(a.e) or '(default)'}: n={n} mean_score={sum(scores)/n:.1f} zero={sum(1 for x in scores if x == 0)}", end="")
    for name in a.s:
        xs = [res[s][name] for s in res if name in res[s]]
        if xs:
            print(f" {name}={sum(xs)/len(xs):.4g}", end="")
    print()
    if os.environ.get("SWEEP_PER_SEED"):
        for s in sorted(res):
            print(s, res[s].get("Score"))


if __name__ == "__main__":
    sys.exit(main())
