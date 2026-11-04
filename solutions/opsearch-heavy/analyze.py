"""Independently replay #heavy counterfactuals and classify changes and candidate predictors."""
import argparse
from collections import Counter, defaultdict
import fcntl
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import replay


def path_token(token):
    return [] if token == "-" else [(int(k), int(d), label) for k, d, label in (x.split(":") for x in token.split(","))]


def align(a, b):
    """LCS of paper IDs; among equal lengths prefer matches with the same label."""
    n, m = len(a), len(b)
    dp = [[(0, 0)] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            best = max(dp[i + 1][j], dp[i][j + 1])
            if a[i][0] == b[j][0]:
                tail = dp[i + 1][j + 1]
                best = max(best, (tail[0] + 1, tail[1] + (a[i][2] == b[j][2])))
            dp[i][j] = best
    pairs = []
    i = j = 0
    while i < n and j < m:
        tail = dp[i + 1][j + 1]
        if a[i][0] == b[j][0] and dp[i][j] == (tail[0] + 1, tail[1] + (a[i][2] == b[j][2])):
            pairs.append((i, j)); i += 1; j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def anchors(start, path):
    order = start.copy()
    result = []
    for k, d, label in path:
        order.remove(k)
        result.append(order[d - 1] if d else -1)
        order.insert(d, k)
    return result


def analyze(run):
    hist = defaultdict(Counter)
    predictors = defaultdict(lambda: [0, 0, 0, 0])  # samples, shortens, beats incumbent, saved moves
    filters = defaultdict(lambda: [0, 0, 0, 0])
    examples = []
    totals = Counter()
    terms = Counter()
    for seed in sorted(replay.run_cases(run)):
        inp = replay.load_input(seed)
        out = replay.parse_output(inp, replay.out_path(run, seed).read_text())
        err = replay.err_path(run, seed).read_text()
        ann = replay.parse_annotations(err, inp.k)
        assert not out.error and not replay.check_annotations(ann, out), seed
        traces = {}
        for line in err.splitlines():
            if line.startswith("#heavy "):
                t = line.split()
                assert len(t) == 13 and "=" not in line
                r, u = int(t[1]), int(t[2])
                assert r not in traces and inp.requests[r] == u
                traces[r] = (t[3], int(t[4]), list(map(float, t[5:11])), path_token(t[11]), path_token(t[12]))
            elif line.startswith("#heavycand "):
                t = line.split()
                assert len(t) == 16 and "=" not in line
                r, round_, rank, parent, n = map(int, (t[1], t[2], t[4], t[5], t[6]))
                op, gap = t[3], float(t[7])
                repeat, dead, removed, added, final = map(int, t[8:13])
                won = int(t[15])
                gains = [1, int(final < n), won, n - final]
                rank_bin = str(rank) if rank <= 4 else "5-8" if rank <= 8 else "9-16" if rank <= 16 else "17+"
                gap_bin = "<=0" if gap <= 1e-9 else "0-.25" if gap <= .25 else ".25-.75" if gap <= .75 else ">.75"
                features = {"operator": op, "rank": rank_bin, "gap": gap_bin,
                            "repeat": str(min(repeat, 3)), "dead": str(min(dead, 6)),
                            "removed": str(removed), "added": str(added), "round": str(round_)}
                for key, value in features.items():
                    bucket = predictors[key + ":" + value]
                    for j in range(4): bucket[j] += gains[j]
                conditions = {"all": True, "rank1": rank <= 1, "rank2": rank <= 2, "rank4": rank <= 4,
                              "gap0": gap <= 1e-9, "gap025": gap <= .25, "repeat": repeat > 0,
                              # added is a multiset difference: an extra use of an existing paper
                              # also counts. Do not call this a strict new-paper feature.
                              "added_paper_occurrence": added > 0, "shorter": n < parent,
                              "rank2_gap025": rank <= 2 and gap <= .25,
                              "rank4_added_occurrence": rank <= 4 and added > 0}
                for key, keep in conditions.items():
                    if keep:
                        for j in range(4): filters[key][j] += gains[j]
        game = replay.Game(inp, out.designs)
        for r, actual in enumerate(out.queries):
            if r in traces:
                op, round_, costs, before, after = traces[r]
                bc, ac, bf, bn, af, an = costs
                assert [(k, d) for k, d, tag in after] == actual
                assert [tag for k, d, tag in after] == ann.ops[r]
                assert abs(bc - len(before) - bf - bn) < 1e-7
                assert abs(ac - len(after) - af - an) < 1e-7 and ac <= bc + 1e-7
                for path in (before, after):
                    trial = replay.Game(inp, out.designs)
                    trial.order = game.order.copy()
                    for k, d, tag in path: trial.move(k, d)
                    assert trial.finish(r), (seed, r)
                kind = "shorter" if len(after) < len(before) else "same_length" if len(after) == len(before) else "longer"
                pairs = align(before, after)
                ai, bi = {i for i, j in pairs}, {j for i, j in pairs}
                removed = [p for i, p in enumerate(before) if i not in ai]
                added = [p for j, p in enumerate(after) if j not in bi]
                ba, aa = anchors(game.order, before), anchors(game.order, after)
                anchor_changes = sum(ba[i] != aa[j] for i, j in pairs)
                columns = sorted({ann.papers["col"][k] for k, d, tag in removed + added} - {"-"}, key=int)
                totals["changed"] += 1
                totals[kind] += 1
                totals["moves_saved"] += len(before) - len(after)
                totals["anchor_changes"] += anchor_changes
                hist["operator_" + kind][op] += 1
                hist["round_" + kind][str(round_)] += 1
                hist["removed_added_" + kind][f"{len(removed)}->{len(added)}"] += 1
                hist["columns_" + kind][str(len(columns))] += 1
                hist["removed_labels_" + kind].update(p[2] for p in removed)
                hist["added_labels_" + kind].update(p[2] for p in added)
                hist["relabel_" + kind].update(before[i][2] + "->" + after[j][2] for i, j in pairs if before[i][2] != after[j][2])
                labels = {p[2] for p in removed}
                categories = []
                if labels & {"dig", "fdig", "hdig"} and labels & {"ret", "fret"}: categories.append("dig_and_return")
                if labels & {"fill", "fix", "relevel"}: categories.append("filler_or_fix_removed")
                if any(ann.papers["role"][p[0]] == "generic" for p in removed + added): categories.append("generic_rewrite")
                if "help" in labels or "hdig" in labels: categories.append("helper_removed")
                for c in categories: hist["categories_" + kind][c] += 1
                terms["cost_saved"] += bc - ac
                terms["filler_saved"] += bf - af
                terms["next_saved"] += bn - an
                if len(after) < len(before):
                    examples.append({"seed": seed, "r": r, "u": inp.requests[r], "op": op, "round": round_,
                                     "lengths": [len(before), len(after)], "costs": costs, "before": before, "after": after,
                                     "removed": removed, "added": added, "columns": columns, "categories": categories,
                                     "paper_columns": {str(k): ann.papers["col"][k] for k, d, tag in before + after},
                                     "start_order": game.order.copy()})
            for k, d in actual: game.move(k, d)
            assert game.finish(r), (seed, r, "actual output")
        assert game.score() == replay.run_cases(run)[seed]["score"]
        totals["verified_requests"] += len(out.queries)
        print(f"verified seed {seed}: {len(traces)} changed requests", file=sys.stderr, flush=True)
    return {"run": run.name, "totals": totals, "cost_terms": terms, "histograms": hist,
            "predictors": dict(predictors), "filters": dict(filters), "examples": examples}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with (replay.runs_dir() / ".lock").open("rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        result = analyze(replay.resolve_run(args.run))
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("examples", "predictors")}, ensure_ascii=False, indent=2))
