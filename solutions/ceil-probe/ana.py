"""Summarize simrun.py output: per config group (name before the last '_s'), the mean simulated moves
per request, the per-case log ratio against a reference group (mean over the design seeds of each
case), and the gain of picking the best of the design seeds (by the simulated moves themselves).
usage: ana.py <jsonl> [ref_group]"""
import json, sys, math, statistics as st, collections
recs = [json.loads(l) for l in open(sys.argv[1])]
g = collections.defaultdict(lambda: collections.defaultdict(list))  # group -> seed -> [moves]
for r in recs:
    if "sim_moves" not in r:
        continue
    name = r["config"]
    grp = name.rsplit("_s", 1)[0] if "_s" in name else name
    g[grp][r["seed"]].append(float(r["sim_moves"]))
ref = sys.argv[2] if len(sys.argv) > 2 else sorted(g)[0]
for grp in sorted(g):
    seeds = sorted(g[grp])
    m = st.mean(st.mean(g[grp][s]) for s in seeds)
    sd_in = st.mean(st.stdev(g[grp][s]) / st.mean(g[grp][s]) * 100 for s in seeds if len(g[grp][s]) > 1) if all(len(g[grp][s]) > 1 for s in seeds) else float("nan")
    best = st.mean(math.log(min(g[grp][s]) / st.mean(g[grp][s])) * 100 for s in seeds)
    line = f"{grp:12s} n={len(seeds):3d} moves={m:.4f} sd_within={sd_in:.3f}% best_of_{len(g[grp][seeds[0]])}={best:+.3f}%(optimistic)"
    if grp != ref:
        common = [s for s in seeds if s in g[ref]]
        d = [math.log(st.mean(g[grp][s]) / st.mean(g[ref][s])) * 100 for s in common]
        line += f"  vs {ref}: {st.mean(d):+.3f} ± {st.stdev(d) / math.sqrt(len(d)):.3f}% ({sum(x < 0 for x in d)}/{sum(x > 0 for x in d)})"
    print(line)
