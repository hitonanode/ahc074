#!/usr/bin/env python3
"""Compare logged legal plans with K-LCS lower bounds for exactly the same final stack."""
import argparse
import bisect
from collections import Counter
import json
from pathlib import Path
import statistics
import sys
import functools
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import replay


def lcs_witness(before, after):
    rank = [0] * len(after)
    for i, x in enumerate(after):
        rank[x] = i
    tails, tail_indices = [], []
    parents = [-1] * len(before)
    for i, x in enumerate(before):
        y = rank[x]
        j = bisect.bisect_left(tails, y)
        if j:
            parents[i] = tail_indices[j - 1]
        if j == len(tails):
            tails.append(y)
            tail_indices.append(i)
        else:
            tails[j] = y
            tail_indices[j] = i
    i = tail_indices[-1]
    kept = set()
    while i >= 0:
        kept.add(before[i])
        i = parents[i]
    return kept


def accessible_lcs(before, after, opaque, min_length, limit=50000):
    """Find a common subsequence whose omitted sheets can escape fixed initial blockers.

    Necessary for every legal relocation plan: before the first move of sheet x,
    every never-moved sheet originally above x still lies above x. They must not
    cover all of x. Returns (kept, states); a limit raises TimeoutError.
    """
    n = len(before)
    rank = [0] * n
    for i, x in enumerate(after): rank[x] = i
    values = [rank[x] for x in before]
    dp = [[0] * (n + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        v = values[i]
        row = dp[i + 1].copy()
        take = 1 + row[v + 1]
        lo, hi = 0, v + 1
        while lo < hi:
            mid = (lo + hi) // 2
            if row[mid] < take: hi = mid
            else: lo = mid + 1
        row[lo:v + 1] = [take] * (v + 1 - lo)
        dp[i] = row
    states = 0
    @functools.lru_cache(None)
    def visit(i, last, cover, need):
        nonlocal states
        states += 1
        if states > limit: raise TimeoutError("accessible LCS state limit")
        if dp[i][last + 1] < need: return None
        if i == n: return 0 if need == 0 else None
        if n - i == need:
            return sum(1 << x for x in before[i:])
        x, v = before[i], values[i]
        if need and v > last and dp[i + 1][v + 1] >= need - 1:
            result = visit(i + 1, v, cover | opaque[x], need - 1)
            if result is not None: return result | (1 << x)
        if opaque[x] & ~cover and dp[i + 1][last + 1] >= need:
            result = visit(i + 1, last, cover, need)
            if result is not None: return result
        return None
    result = visit(0, -1, 0, min_length)
    return (None if result is None else {x for x in before if result >> x & 1}), states


def synthesize_once(before, after, opaque, kept, limit=20000):
    """Exact DFS for a prescribed set of sheets moved exactly once.

    Finalized sheets (initial kept sheets plus those already moved) must always
    be in target relative order. For each visible pending sheet, try every
    insertion position between its nearest finalized target-order neighbors.
    This exhausts every sequence that moves exactly the prescribed sheets once.
    """
    n = len(before)
    movable = [x for x in before if x not in kept]
    full = (1 << len(movable)) - 1
    index = {x:i for i,x in enumerate(movable)}
    rank = [0] * n
    for i,x in enumerate(after): rank[x] = i
    failed = set()
    states = 0
    def visit(order, done):
        nonlocal states
        states += 1
        if states > limit: raise TimeoutError("legal relocation DFS state limit")
        if done == full:
            return [] if list(order) == after else None
        key = (done, order)
        if key in failed: return None
        fixed = kept | {x for x in movable if done >> index[x] & 1}
        visible, covered = [], 0
        for pos,x in enumerate(order):
            if opaque[x] & ~covered and x in index and not done >> index[x] & 1:
                visible.append((pos,x))
            covered |= opaque[x]
        # Try sheets near their final position first; only affects search order.
        visible.sort(key=lambda px:abs(px[0]-rank[px[1]]))
        for pos,x in visible:
            remaining = order[:pos] + order[pos+1:]
            lo, hi = 0, n - 1
            for j,y in enumerate(remaining):
                if y in fixed:
                    if rank[y] < rank[x]: lo = j + 1
                    else:
                        hi = j
                        break
            destinations = list(range(lo, hi + 1))
            destinations.sort(key=lambda d:abs(d-rank[x]))
            for d in destinations:
                if d == pos: continue
                nxt = remaining[:d] + (x,) + remaining[d:]
                result = visit(nxt, done | (1 << index[x]))
                if result is not None: return [(x,d)] + result
        failed.add(key)
        return None
    plan = visit(tuple(before), 0)
    return plan, states


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--legal", action="store_true", help="strengthen bounds and synthesize once-moved plans")
    parser.add_argument("--query-limit", type=int, default=0)
    args = parser.parse_args()
    reports = []
    for run_name in args.runs:
        run = replay.resolve_run(run_name)
        cases = replay.run_cases(run)
        totals = Counter()
        gap_hist = Counter()
        examples = []
        case_records = []
        for seed in sorted(cases):
            inp = replay.load_input(seed)
            out = replay.parse_output(inp, replay.out_path(run, seed).read_text())
            if out.error:
                raise RuntimeError(out.error)
            game = replay.Game(inp, out.designs)
            ct = Counter()
            for r, ops in enumerate(out.queries):
                if args.query_limit and totals["queries"] + ct["queries"] >= args.query_limit:
                    break
                before = game.order.copy()
                initially_visible = set(game.exposed())
                for k, d in ops:
                    game.move(k, d)
                game.finish(r)
                after = game.order.copy()
                kept = lcs_witness(before, after)
                lb = inp.k - len(kept)
                moved = {k for k, _ in ops}
                duplicate = len(ops) - len(moved)
                gap = len(ops) - lb
                # Fixed sheets cannot ever expose a moved sheet whose entire
                # footprint they cover above its initial position. This certifies
                # infeasibility of this particular LCS witness, not all LCSs.
                fixed_cover = 0
                blocked = []
                for k in before:
                    if k in kept:
                        fixed_cover |= out.designs[k].opaque
                    elif not out.designs[k].opaque & ~fixed_cover:
                        blocked.append(k)
                data = dict(queries=1, actual_moves=len(ops), distinct_moved=len(moved),
                            unrestricted_moves=lb, duplicate_moves=duplicate,
                            distinct_excess=len(moved)-lb, gap=gap,
                            queries_with_gap=int(gap > 0),
                            queries_with_duplicate=int(duplicate > 0),
                            initially_hidden_moved=len(moved-initially_visible),
                            lcs_witness_blocked_queries=int(bool(blocked)),
                            lcs_witness_blocked_papers=len(blocked))
                data["unblocked_lcs_gap"] = gap if not blocked else 0
                if args.legal and gap:
                    opaque = [p.opaque for p in out.designs]
                    strong = lb
                    stage = "accessibility"
                    try:
                        legal_kept = kept if not blocked else None
                        while legal_kept is None and strong <= len(moved):
                            legal_kept, states = accessible_lcs(before, after, opaque, inp.k - strong)
                            data["accessibility_search_states"] = data.get("accessibility_search_states",0) + states
                            if legal_kept is None: strong += 1
                        data["visibility_forced_extra"] = strong - lb
                        data["remaining_gap_after_visibility"] = len(ops) - strong
                        data["accessibility_complete_queries"] = 1
                        stage = "synthesis"
                        if strong < len(ops) and legal_kept is not None:
                            plan, states = synthesize_once(before, after, opaque, legal_kept)
                            data["synthesis_search_states"] = states
                            if plan is not None:
                                assert len(plan) == strong
                                data["synthesized_savings"] = len(ops) - len(plan)
                                data["synthesized_queries"] = 1
                                # Independent, visibility-checked replay of the replacement.
                                test = replay.Game(inp,out.designs)
                                test.order = before.copy()
                                for x,d in plan: test.move(x,d)
                                assert test.order == after
                                if data["synthesized_savings"]:
                                    data["synthesis_example"] = {"seed":seed,"query":r,"original":ops,"replacement":plan}
                            else: data["synthesis_failed_queries"] = 1
                    except TimeoutError:
                        data["limited_queries"] = 1
                        data[stage + "_limited_queries"] = 1
                        if stage == "accessibility":
                            # All smaller moved-set sizes were exhausted. Even
                            # on a timeout the current size is a valid lower bound.
                            data["visibility_forced_extra"] = strong - lb
                            data["remaining_gap_after_visibility"] = len(ops) - strong
                example = data.pop("synthesis_example", None)
                if example:
                    examples.append({"seed":seed,"query":r,"gap":gap,"duplicate":duplicate,"synthesized":example})
                ct.update(data)
                gap_hist[gap] += 1
                if gap > 0:
                    examples.append({"seed":seed, "query":r, "moves":len(ops),
                                     "distinct":len(moved), "lower_bound":lb,
                                     "gap":gap, "duplicate":duplicate,
                                     "blocked_in_one_lcs":blocked, "ops":ops})
            if not args.query_limit:
                assert game.score() == cases[seed]["score"]
            totals.update(ct)
            case_records.append({"seed":seed, **dict(ct)})
        nq = totals["queries"]
        report = {"run_id":run.name, "cases":sum(x["queries"] > 0 for x in case_records), "totals":dict(totals),
                  "per_query":{key:value/nq for key,value in totals.items() if key != "queries"},
                  "gap_histogram":dict(sorted(gap_hist.items())), "case_records":case_records,
                  "largest_gap_examples": sorted(examples, key=lambda x:(-x["gap"],-x["duplicate"]))[:30]}
        reports.append(report)
        print(json.dumps({k:v for k,v in report.items() if k not in {"case_records","largest_gap_examples"}},indent=2))
    result = {"definition":"Exact final permutation preserved. K-LCS is an unrestricted lower bound; gaps are potential, not guaranteed legal savings.","reports":reports}
    if args.output:
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")


if __name__ == "__main__":
    main()
