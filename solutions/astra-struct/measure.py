"""Read-only audit of imp-combo saved outputs; writes only the selected JSON.

PYTHONDONTWRITEBYTECODE=1 python3 solutions/astra-struct/measure.py 0 40
Per-seed standard errors, not per-request pseudo-replicates.
"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import json
import math
from collections import Counter
import statistics
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import replay
RUN = Path("/home/sato/ahc074/runs/20261102-073343_imp-combo")


def load(seed):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, (RUN / "out" / f"{seed:04d}.txt").read_text())
    assert out.error is None
    gm = 0
    for p in out.designs[:6]:
        gm |= p.opaque
    hm = inp.full ^ gm
    handles = []
    for p in out.designs[6:]:
        for w in range(64):
            if (hm & p.opaque) >> w & 1 and w not in handles:
                handles.append(w)
    col = [-1] * 6 + [max(c for c, w in enumerate(handles) if p.opaque >> w & 1) for p in out.designs[6:]]
    serves = [[u for u, a in enumerate(inp.target) if (a ^ p.black) & p.opaque == 0] for p in out.designs]
    ded = []
    for u in range(256):
        matches = [k for k in range(6, 192) if u in serves[k]]
        assert len(matches) == 1, (seed, u, matches)
        ded.append(matches[0])
    assert sorted(len(s) for s in serves[6:]) == [1]*116 + [2]*70
    return inp, out, gm, hm, handles, col, serves, ded


def measure(seed):
    inp, out, gm, hm, hs, col, serves, ded = load(seed)
    game = replay.Game(inp, out.designs)
    ps = out.designs
    window_papers = [sum((1 << k) for k,p in enumerate(ps) if p.opaque >> w & 1) for w in range(64)]
    total = Counter()
    bycol = [Counter() for _ in hs]
    examples = []
    prev = None
    for r, ops in enumerate(out.queries):
        u = inp.requests[r]
        a = inp.target[u]
        D = ded[u]
        c = col[D]
        cc = Counter(requests=1, ops=len(ops))
        holes = hm & ~ps[D].opaque
        cc["handle_holes"] = holes.bit_count()
        cc["triangle_holes"] = len(hs) - 1 - c
        cc["pair_holes"] = cc["handle_holes"] - cc["triangle_holes"]
        cc["paired_requests"] = len(serves[D]) == 2
        lasttop = next((k for k, d in reversed(ops) if k >= 6 and d == 0), None)
        cc["last_to_top_not_D"] = lasttop is not None and lasttop != D
        cc["no_target_move"] = lasttop is None
        prefix = game.order[:game.order.index(D)]
        prefix_mask = sum(1 << k for k in prefix)
        blocks = [(prefix_mask & m).bit_count() for m in window_papers]
        own = int(blocks[hs[c]])
        best = min(blocks[w] for w in range(64) if ps[D].opaque >> w & 1)
        cc["own_handle_blockers"] = own
        cc["best_witness_blockers"] = best
        cc["alternate_witness_gain_upper"] = own - best
        cc["top_compatible_papers"] = sum(u in s for s in serves)
        if own > best and len(examples) < 6:
            examples.append({"seed":seed,"request":r,"D":D,"column":c,"own":own,"best":best})
        # State before this order, with D removed. This is a counterfactual display,
        # not a claimed legal free lift.
        cov = black = 0
        for x in game.order:
            if x == D:
                continue
            black |= ps[x].black & ~cov
            cov |= ps[x].opaque
        cc["wrong_holes_before"] = ((black ^ a) & holes).bit_count()
        seen = False
        for k, d in ops:
            if k < 6:
                cc["generic"] += 1
            elif d <= 6:
                cc["to_top" if d == 0 else "below_generic"] += 1
            elif k == prev:
                cc["prev_top_back"] += 1
            elif not seen and col[k] == c:
                cc["dig_D_column"] += 1
            else:
                cc["other_deep"] += 1
            if k == D:
                seen = True
            game.move(k, d, check=True)
        assert game.finish(r), (seed, r, "wrong display")
        top_ded = next(k for k in game.order if k >= 6)
        cc["first_dedicated_not_D"] = top_ded != D
        prev = top_ded
        providers = Counter()
        cov = 0
        for k in game.order:
            vis = ps[k].opaque & ~cov & holes
            cov |= ps[k].opaque
            for i, w in enumerate(hs):
                if vis >> w & 1:
                    if col[k] == i:
                        cc["own_column_holes"] += 1
                    else:
                        cc["filler_holes"] += 1
                        providers[k] += 1
        cc["filler_papers"] = len(providers)
        for k, n in providers.items():
            cc[f"filler_size_{n}"] += 1
        # A future module can lose this cross-module benefit; count it explicitly.
        for start in (16,19,22,25):
            end = start + 3
            need = sum((1 << hs[i]) for i in range(start,end)) & holes
            cc[f"module{start}_holes"] = need.bit_count()
            cc[f"module{start}_internal_request"] = start <= c < end
            cov = 0
            external = Counter()
            for k in game.order:
                vis = ps[k].opaque & ~cov & need
                cov |= ps[k].opaque
                if vis and not start <= col[k] < end:
                    external[k] = vis.bit_count()
            cc[f"module{start}_external_filler_holes"] = sum(external.values())
        total.update(cc)
        bycol[c].update(cc)
    return {"seed":seed,"total":dict(total),"columns":list(map(dict,bycol)),"examples":examples}


def summarize(records):
    keys = sorted(set().union(*(r["total"] for r in records)))
    out = {}
    for key in keys:
        arr = [r["total"].get(key,0)/1024 for r in records]
        out[key] = {"mean":statistics.mean(arr), "se":statistics.stdev(arr)/math.sqrt(len(arr)) if len(arr)>1 else 0.0}
    return out


if __name__ == "__main__":
    lo, hi = map(int, sys.argv[1:3]) if len(sys.argv)>2 else (0,40)
    results = [measure(s) for s in range(lo,hi)]
    result = {"run":RUN.name,"seeds":[lo,hi],"summary":summarize(results),"records":results}
    # Column counters are useful for follow-up but not necessary as large raw output.
    for r in result["records"]:
        r.pop("columns")
    path = Path(__file__).with_name(f"measure_{lo}_{hi}.json")
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result["summary"],ensure_ascii=False,indent=2))
