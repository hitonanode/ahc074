#!/usr/bin/env python3
"""Per-case comparison of two safe_run.py results: mean log score ratio (B vs A), SE, win/tie/loss.

usage: safe_compare.py RESULT_DIR_A RESULT_DIR_B
"""
import json, math, statistics, sys

a = {r["seed"]: r for r in json.load(open(f"{sys.argv[1]}/result.json"))}
b = {r["seed"]: r for r in json.load(open(f"{sys.argv[2]}/result.json"))}
seeds = sorted(s for s in a if s in b and a[s]["score"] and b[s]["score"])
lr = [math.log(b[s]["score"] / a[s]["score"]) for s in seeds]
m = statistics.mean(lr)
se = statistics.stdev(lr) / math.sqrt(len(lr))
w = sum(x < 0 for x in lr)
t = sum(x == 0 for x in lr)
print(f"cases {len(seeds)}  mean log ratio {100*m:+.3f}% +- {100*se:.3f}%  better/equal/worse {w}/{t}/{len(lr)-w-t}")
print(f"mean A {statistics.mean(a[s]['score'] for s in seeds):.1f}  mean B {statistics.mean(b[s]['score'] for s in seeds):.1f}")
