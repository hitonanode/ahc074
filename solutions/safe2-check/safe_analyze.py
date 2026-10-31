#!/usr/bin/env python3
"""Summarizes a safe_run.py result of solutions/safe2-check (safe-check ported to audit4-flip): correctness counters and phase times.

usage: safe_analyze.py RESULT_DIR [--scale 1.5]

The judge estimate assumes a machine `scale` times slower: the time-bounded part (annealing and
climb) ends at the same cut-off (climb_end_real of this run, unless the pre-processing x scale
passes the annealing end), and everything after it takes `scale` times longer. For a run made
with SAFE_TIME_SCALE=s, use end_real x s instead (the slow machine is already simulated).
"""
import json, sys, statistics

d = sys.argv[1]
scale = float(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[2] == "--scale" else 1.5
res = json.load(open(f"{d}/result.json"))


def g(r, k):
    return r["kv"].get(k, float("nan"))


def top(f, n=5):
    rs = sorted(res, key=lambda r: -f(r))[:n]
    return ", ".join(f"{r['seed']}:{f(r):.4f}" for r in rs)


def stat(name, f):
    v = [f(r) for r in res]
    v = [x for x in v if x == x]
    print(f"{name:34s} mean {statistics.mean(v):.4f}  p99 {sorted(v)[int(len(v)*0.99)]:.4f}  max {max(v):.4f}   top: {top(f)}")


print("cases", len(res))
zero = [r for r in res if not r["score"]]
print("score 0 / missing:", len(zero), [(r["seed"], r["tail"]) for r in zero[:10]])
print("rc != 0:", [(r["seed"], r["rc"]) for r in res if r["rc"] != 0][:10])
for k in ["self_wrong", "uncovered", "inconsistent_pairs", "split_fallback", "safe_split_aug", "split_failed",
          "repaired_pairs", "safe_plain_requests", "safe_plain_invisible", "safe_plain_wrong", "blk_fallback",
          "canon_fail"]:
    nz = [(r["seed"], g(r, k)) for r in res if g(r, k) != 0 and g(r, k) == g(r, k)]
    print(f"{k:24s} nonzero cases {len(nz)}: {nz[:15]}")
print("E>0 (score - total_moves)/384:", [(r["seed"], (r["score"] - g(r, "total_moves")) / 384) for r in res
                                      if r["score"] and r["score"] != g(r, "total_moves")][:10])
stat("safe_max_ops", lambda r: g(r, "safe_max_ops"))
sc = [r["score"] for r in res if r["score"]]
print(f"mean score {statistics.mean(sc):.1f}")
print("--- time (real seconds of this machine) ---")
stat("wall (tester)", lambda r: r["time"])
stat("pre (until anneal start)", lambda r: g(r, "safe_pre_real"))
stat("anneal_end_real", lambda r: g(r, "safe_anneal_end_real"))
stat("climb_end_real", lambda r: g(r, "safe_climb_end_real"))
stat("split+generic (climb->split end)", lambda r: g(r, "safe_split_end_real") - g(r, "safe_climb_end_real"))
stat("design out (climb end->out)", lambda r: g(r, "safe_design_out_real") - g(r, "safe_climb_end_real"))
stat("query compute", lambda r: g(r, "safe_query_compute"))
stat("query compute max ms", lambda r: g(r, "safe_query_compute_max_ms"))
stat("query wait", lambda r: g(r, "safe_query_wait"))
stat("end_real (in-process)", lambda r: g(r, "safe_end_real"))
stat("post climb (end - climb end)", lambda r: g(r, "safe_end_real") - g(r, "safe_climb_end_real"))
stat("pre cpu", lambda r: g(r, "safe_pre_cpu"))
stat("post climb cpu (process CPU)", lambda r: g(r, "safe_end_cpu") - g(r, "safe_climb_end_cpu"))
stat("post climb real - cpu (preempted+waits)", lambda r: g(r, "safe_end_real") - g(r, "safe_climb_end_real") - (g(r, "safe_end_cpu") - g(r, "safe_climb_end_cpu")))
stat("post compute (no waits)", lambda r: g(r, "safe_design_out_real") - g(r, "safe_climb_end_real") + g(r, "safe_query_compute"))


def est(r, s, with_wait=True):
    pre = g(r, "safe_pre_real") * s
    cut = g(r, "safe_climb_end_real")
    post = (g(r, "safe_end_real") - cut) if with_wait else \
        (g(r, "safe_design_out_real") - cut + g(r, "safe_query_compute"))
    return max(cut, pre + 0.06) + post * s


stat(f"judge est x{scale} (with waits)", lambda r: est(r, scale))
stat(f"judge est x{scale} (no waits)", lambda r: est(r, scale, False))
# safe2-check: the post-climb part by process CPU time (the solver's own work, not inflated by
# preemption on a loaded machine) plus the waits for the tester's replies, both x scale.
stat(f"judge est x{scale} (post cpu + waits)", lambda r: g(r, "safe_climb_end_real")
     + (g(r, "safe_end_cpu") - g(r, "safe_climb_end_cpu") + g(r, "safe_query_wait")) * scale)
