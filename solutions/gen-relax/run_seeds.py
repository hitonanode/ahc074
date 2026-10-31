#!/usr/bin/env python3
"""Own check (not an evaluation record): runs the tester on the given seeds (in parallel) and
prints the selected `name = value` stderr lines of each.

    run_seeds.py BINARY SEED [SEED ...] [-s stat ...] [-e KEY=VAL ...]
"""
import argparse
import concurrent.futures as cf
import os
import re
import subprocess

ROOT = "/home/sato/ahc074"
LINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([-+0-9.eE]+)\s*$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("binary")
    ap.add_argument("seeds", type=int, nargs="+")
    ap.add_argument("-s", action="append", default=[])
    ap.add_argument("-e", action="append", default=[])
    ap.add_argument("-j", type=int, default=12)
    a = ap.parse_args()
    env = dict(os.environ)
    for kv in a.e:
        k, v = kv.split("=", 1)
        env[k] = v

    def run(seed):
        with open(f"{ROOT}/tools/in/{seed:04d}.txt") as inp:
            p = subprocess.run([f"{ROOT}/tools/target/release/tester", a.binary], stdin=inp,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=env)
        vals = {}
        for line in p.stderr.splitlines():
            m = LINE.match(line)
            if m:
                vals[m.group(1)] = m.group(2)
        return seed, vals

    with cf.ThreadPoolExecutor(a.j) as ex:
        for seed, vals in ex.map(run, a.seeds):
            print(seed, " ".join(f"{k}={vals.get(k)}" for k in a.s + ["Score"]))


if __name__ == "__main__":
    main()
