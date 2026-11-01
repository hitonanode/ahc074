"""Necessary top-paper coverage and trace-specific lower bound; read-only inputs.

PYTHONDONTWRITEBYTECODE=1 python3 solutions/astra-probe/top_cover.py 0 8
The returned lower bound permits arbitrary final states and representations,
but fixes the printed design and the starting state in the recorded trace.
"""
import json
import sys
from analyze import load, shown, mean_se


def run(lo, hi):
    result = []
    for seed in range(lo, hi):
        inp, out, gm, hs, cols, serves = load(seed)
        ps = out.designs
        assert all(p.opaque for p in ps)
        compatible = [[k for k,p in enumerate(ps) if a & p.opaque == p.black]
                      for a in inp.target]
        assert all(compatible)
        order = list(range(192))
        lower = 0
        example = None
        for r, ops in enumerate(out.queries):
            target = inp.target[inp.requests[r]]
            costs = []
            for k in compatible[inp.requests[r]]:
                pos = order.index(k)
                blockers = min(sum(ps[x].opaque >> j & 1 for x in order[:pos])
                               for j in range(64) if ps[k].opaque >> j & 1)
                # Either k is never moved and all predecessors must leave,
                # or a first move of k requires exposing it plus that move.
                costs.append(min(pos, 1 + blockers))
            lower += min(costs)
            previous = order[0]
            final = list(order)
            for k,d in ops:
                final.remove(k)
                final.insert(d,k)
            top = final[0]
            above = {k for k in order[:order.index(top)] if cols[k] == cols[top]}
            old, _ = shown(ps,order)
            for step,(k,d) in enumerate(ops):
                pos = order.index(k)
                order.remove(k)
                order.insert(d,k)
                new, _ = shown(ps,order)
                good = (old ^ target) & ~(new ^ target)
                bad = (new ^ target) & ~(old ^ target)
                if example is None and k >= 6 and k not in above and k not in (top, previous) and good.bit_count() >= 4:
                    example = dict(seed=seed, request=r, step=step, paper=k,
                                   source_position=pos, destination=d,
                                   newly_correct=[j for j in range(64) if good >> j & 1],
                                   newly_wrong=[j for j in range(64) if bad >> j & 1])
                old = new
        result.append(dict(seed=seed,
                           targets_with_generic_top=[(u,[k for k in ks if k < 6])
                                                     for u,ks in enumerate(compatible)
                                                     if any(k < 6 for k in ks)],
                           unique_top_count=sum(len(ks)==1 for ks in compatible),
                           fixed_design_query_lower=lower/inp.r,
                           multiple_window_repair_example=example))
    return result


if __name__ == '__main__':
    lo, hi = map(int, sys.argv[1:3])
    rows = run(lo,hi)
    print(json.dumps(rows,ensure_ascii=False,indent=2))
    print('Mean, SE:', mean_se([r['fixed_design_query_lower'] for r in rows]),file=sys.stderr)
