#!/usr/bin/env python3
"""runs/ に保存された出力を再生し、評価結果を AI が読みやすいテキストで観察する。

RUN には run-id、その末尾の解法名（複数あれば最新）、run ディレクトリのパスを指定できる。
ケース単位のコマンド (queries, state, design, stats --seed) には、出力ファイルのパスも指定できる。

    scripts/observe.py runs     [--ref RUN] [--all] [--sort ratio|time] [--top 30]
    scripts/observe.py cases    RUN [--vs RUN2] [--top 15]
    scripts/observe.py stats    RUN [--vs RUN2] [--seed S]
    scripts/observe.py queries  RUN SEED [--from R] [--to R] [--wrong] [--all]
    scripts/observe.py state    RUN SEED --request R [--after] [--top 24]
    scripts/observe.py design   RUN SEED
    scripts/observe.py log      RUN SEED [--tail N]
    scripts/observe.py verify   RUN
"""

import argparse
import json
import math
import os
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay  # noqa: E402

QUERY_LINE_LIMIT = 200
PAPER_LEGEND = ("windows (window 0 first): '0'/'1' = this paper is the visible paper there (white/black), "
                "'-' = opaque but covered by a paper above, ' ' = hole")


# ---------------------------------------------------------------- helpers


def load_case(target: str, seed: int):
    """Returns (label, input, output) for a run (or an output file) and a seed."""
    path = Path(target)
    if path.is_file():
        label, out = str(path), path
    else:
        run = replay.resolve_run(target)
        label, out = run.name, replay.out_path(run, seed)
    inp = replay.load_input(seed)
    return label, inp, replay.parse_output(inp, out.read_text(errors="replace"))


def result_line(rep: replay.Replay) -> str:
    g = rep.game
    head = f"E={g.mistakes} T={g.moves} processed={g.completed}/{rep.inp.r}"
    if rep.error:
        return f"WA ({rep.error}); the judge scores 0. {head} before the error"
    return f"score={g.score()} (= 2K*E + T = {2 * rep.inp.k}*{g.mistakes} + {g.moves}); {head}"


def paper_row(game: replay.Game, k: int, covered: int) -> str:
    p = game.papers[k]
    n = game.inp.n
    chars = []
    for j in range(n):
        bit = 1 << j
        if not p.opaque & bit:
            chars.append(" ")
        elif covered & bit:
            chars.append("-")
        else:
            chars.append("1" if p.black & bit else "0")
    return "".join(chars)


def diff_row(a: int, b: int, n: int) -> str:
    return "".join("^" if (a ^ b) >> j & 1 else " " for j in range(n))


def finished_runs() -> list[tuple[Path, dict, dict[int, int]]]:
    found = []
    for d in replay.finished_run_dirs():
        try:
            found.append((d, json.loads((d / "meta.json").read_text()), replay.run_scores(d)))
        except (OSError, ValueError, KeyError):
            continue
    return found


def log_ratio(a: dict[int, int], b: dict[int, int], seeds) -> tuple[float, float, int, int, int] | None:
    """Mean and standard error of log(a / b) over seeds valid in both (negative: a is better),
    and the counts of seeds where a is better / equal / worse."""
    diffs = [math.log(a[s] / b[s]) for s in seeds if a.get(s, 0) > 0 and b.get(s, 0) > 0]
    n = len(diffs)
    if not n:
        return None
    mean = sum(diffs) / n
    se = math.sqrt(sum((d - mean) ** 2 for d in diffs) / (n - 1) / n) if n > 1 else float("nan")
    return mean, se, sum(d < 0 for d in diffs), sum(d == 0 for d in diffs), sum(d > 0 for d in diffs)


def mean_valid(values) -> float | None:
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def num(x, fmt: str) -> str:
    return "-" if x is None or (isinstance(x, float) and math.isnan(x)) else fmt.format(x)


# ---------------------------------------------------------------- runs


def cmd_runs(args) -> None:
    runs = finished_runs()
    if not runs:
        print("no finished run")
        return
    seeds = set(replay.all_seeds())
    full = [r for r in runs if seeds <= r[2].keys()]
    if args.ref:
        ref_dir = replay.resolve_run(args.ref)
        ref = next((r for r in runs if r[0] == ref_dir), None)
        if ref is None:
            raise LookupError(f"正常に終わった run ではありません: {args.ref}")
        why = "chosen with --ref"
    else:
        pool = [r for r in full if not any(r[2][s] == 0 for s in seeds)] or full or runs
        ref = min(pool, key=lambda r: mean_valid(r[2][s] or None for s in r[2]) or float("inf"))
        why = "the run with the best mean score over all seeds" if pool[0] in full else "the best mean score"
    print(f"ref (*) = {ref[0].name}: {why}")
    print("diff = mean over the seeds both runs solved of log(score / ref score), in % (negative is better),"
          " ± standard error; W/D/L = seeds better / equal / worse than ref. Mean score, E, T leave WA out.")
    rows = []
    for d, meta, scores in runs:
        if not args.all and not seeds <= scores.keys():
            continue
        summary = meta.get("summary", {})
        comment = ("[no-record] " if not meta.get("record", True) else "") + (meta.get("comment") or "")
        rows.append((d, len(scores), sum(s == 0 for s in scores.values()),
                     mean_valid(s or None for s in scores.values()), summary.get("average_E"),
                     summary.get("average_T"), log_ratio(scores, ref[2], scores.keys()),
                     summary.get("max_execution_time"), comment))
    if args.sort == "ratio":
        rows.sort(key=lambda r: (r[6] is None, r[6][0] if r[6] else 0, r[0].name))
    else:
        rows.sort(key=lambda r: r[0].name, reverse=True)
    print(f"   {'run-id':<40} {'seeds':>5} {'WA':>3} {'score':>9} {'E':>7} {'T':>8} {'diff%':>8} {'±':>6}"
          f" {'W/D/L':>13} {'maxT':>5}  comment")
    for d, n, wa, score, e, t, ratio, max_time, comment in rows[:args.top]:
        mark = "*" if d == ref[0] else " "
        diff = f"{100 * ratio[0]:>+8.3f} {100 * ratio[1]:>6.3f} {ratio[2]:>4}/{ratio[3]:>3}/{ratio[4]:>4}" if ratio else \
            f"{'-':>8} {'-':>6} {'-':>13}"
        print(f"{mark}  {d.name:<40} {n:>5} {wa:>3} {num(score, '{:.1f}'):>9} {num(e, '{:.3f}'):>7}"
              f" {num(t, '{:.1f}'):>8} {diff} {num(max_time, '{:.2f}'):>5}  {comment[:60]}")
    if len(rows) > args.top:
        print(f"... (+{len(rows) - args.top} more; use --top)")


# ---------------------------------------------------------------- cases


def cmd_cases(args) -> None:
    run_a = replay.resolve_run(args.run)
    ma = replay.run_metrics(run_a)
    if args.vs:
        run_b = replay.resolve_run(args.vs)
        mb = replay.run_metrics(run_b)
        score_b = {s: m["judge_score"] for s, m in mb.items()}
        name_b = "B"
        print(f"A = {run_a.name}\nB = {run_b.name}")
    else:
        mb = None
        score_b = replay.best_scores()
        name_b = "best"
        print(f"A = {run_a.name}, compared with the best score of each seed (pahcer/best_scores.json)")
    score_a = {s: m["judge_score"] for s, m in ma.items()}
    seeds = sorted(set(score_a) & set(score_b))
    wa = [s for s in seeds if score_a[s] == 0 or score_b[s] == 0]
    seeds = [s for s in seeds if s not in wa]
    if not seeds:
        print("no seed solved by both")
        return
    stats = log_ratio(score_a, score_b, seeds)
    print(f"{len(seeds)} seeds (lower is better; WA excluded: {wa[:10] if wa else 'none'})")
    print(f"mean score: A {sum(score_a[s] for s in seeds) / len(seeds):.1f}, "
          f"{name_b} {sum(score_b[s] for s in seeds) / len(seeds):.1f}; "
          f"mean log(A/{name_b}) {100 * stats[0]:+.3f}% ± {100 * stats[1]:.3f}%; "
          f"A better on {stats[2]}, equal on {stats[3]}, worse on {stats[4]}")
    ratio = {s: score_a[s] / score_b[s] for s in seeds}
    ranked = sorted(seeds, key=lambda s: ratio[s])

    def eb(s):
        return f" {mb[s]['E']:>4} {mb[s]['T']:>6}" if mb else ""

    sections = [(f"A is worse than {name_b} (largest A/{name_b})", ranked[::-1][:args.top])]
    if mb is not None:
        sections.append((f"A is better than {name_b} (smallest A/{name_b})", ranked[:args.top]))
    for title, chosen in sections:
        print(f"\n{title}:")
        print(f"{'seed':<4} {'A':>7} {'E_A':>4} {'T_A':>6} {name_b:>7}" + (f" {'E_B':>4} {'T_B':>6}" if mb else "")
              + f" {'A/' + name_b:>7}")
        for s in chosen:
            print(f"{s:04d} {score_a[s]:>7} {ma[s]['E']:>4} {ma[s]['T']:>6} {score_b[s]:>7}{eb(s)} {ratio[s]:>7.4f}")


# ---------------------------------------------------------------- stats

METRICS = [
    ("score", "score (2K*E + T)", "{:.1f}"),
    ("E", "E (wrong requests)", "{:.3f}"),
    ("T", "T (moves)", "{:.1f}"),
    ("ops_mean", "moves per request: mean", "{:.3f}"),
    ("ops_p50", "moves per request: median", "{:.2f}"),
    ("ops_p90", "moves per request: p90", "{:.2f}"),
    ("ops_max", "moves per request: max", "{:.2f}"),
    ("zero_op_share", "requests with 0 moves", "{:.2%}"),
    ("mismatch_on_wrong", "mismatched windows / wrong req", "{:.2f}"),
    ("moved_pos_mean", "position of moved paper (0=top)", "{:.2f}"),
    ("insert_d_mean", "insert depth d", "{:.2f}"),
    ("to_top_share", "moves to the top (d=0)", "{:.2%}"),
    ("to_bottom_share", "moves to the bottom (d=K-1)", "{:.2%}"),
    ("distinct_papers_moved", "distinct papers moved", "{:.1f}"),
    ("hole_share", "hole share of the designs", "{:.2%}"),
    ("papers_all_holes", "papers with only holes", "{:.2f}"),
    ("papers_no_holes", "papers without holes", "{:.2f}"),
    ("execution_time", "execution time (s)", "{:.3f}"),
]


def stats_column(cases: dict[int, dict], seeds: list[int]) -> tuple[list[str], dict[str, float]]:
    valid = [s for s in seeds if not cases[s]["error"]]
    values = [f"{len(valid)} / {len(seeds) - len(valid)}"]
    for key, _, fmt in METRICS:
        xs = [cases[s][key] for s in valid if cases[s].get(key) is not None
              and not (isinstance(cases[s][key], float) and math.isnan(cases[s][key]))]
        values.append(fmt.format(sum(xs) / len(xs)) if xs else "-")
    names: dict[str, list[float]] = {}
    for s in valid:
        for name, v in cases[s].get("stderr", {}).items():
            names.setdefault(name, []).append(v)
    return values, {name: sum(v) / len(v) for name, v in names.items()}


def cmd_stats(args) -> None:
    targets = [args.run] + ([args.vs] if args.vs else [])
    labels, columns = [], []
    if args.seed is not None:
        seeds = [args.seed]
        for target in targets:
            label, inp, out = load_case(target, args.seed)
            m = replay.case_metrics(inp, out)
            path = Path(target)
            err = None if path.is_file() else replay.err_path(replay.resolve_run(target), args.seed)
            m["stderr"] = replay.stderr_stats(err.read_text(errors="replace")) if err and err.exists() else {}
            m["execution_time"] = None
            labels.append(label)
            columns.append({args.seed: m})
        print(f"seed {args.seed:04d}")
    else:
        runs = [replay.resolve_run(t) for t in targets]
        labels = [r.name for r in runs]
        columns = [replay.run_metrics(r) for r in runs]
        seeds = sorted(set.intersection(*(set(c) for c in columns)))
        mismatched = [(r.name, s) for r, c in zip(runs, columns) for s in seeds
                      if c[s]["score"] != c[s]["judge_score"]]
        if mismatched:
            print(f"WARNING: the replayed score differs from result.json for {len(mismatched)} cases,"
                  f" e.g. {mismatched[:3]}; the replay rules may be wrong.")
        print(f"{len(seeds)} seeds" + (" present in both runs" if args.vs else ""))
    names = ["A", "B"][:len(labels)]
    for name, label in zip(names, labels):
        print(f"{name} = {label}")
    results = [stats_column(c, seeds) for c in columns]
    print(f"{'metric':<34}" + "".join(f"{n:>14}" for n in names))
    rows = ["cases (valid / WA)"] + [label for _, label, _ in METRICS]
    for i, row in enumerate(rows):
        print(f"{row:<34}" + "".join(f"{v[0][i]:>14}" for v in results))
    stderr_names = sorted(set().union(*(r[1] for r in results)))
    if stderr_names:
        print("stderr `name = value` (mean over valid cases that print it):")
        for name in stderr_names:
            print(f"  {name:<32}" + "".join(f"{num(r[1].get(name), '{:.6g}'):>14}" for r in results))
    print("(means over valid cases; per-request metrics are means of per-case values)")


# ---------------------------------------------------------------- queries


def parse_request(text: str, total: int) -> int:
    if text.endswith("%"):
        r = round(total * float(text[:-1]) / 100)
    elif text == "end":
        r = total
    else:
        r = int(text)
    return max(0, min(r, total))


def cmd_queries(args) -> None:
    label, inp, out = load_case(args.run, args.seed)
    rep = replay.replay(inp, out)
    total = len(rep.queries)
    start = parse_request(args.from_, total)
    end = parse_request(args.to, total) if args.to is not None else (total if args.wrong else min(start + 30, total))
    print(f"[{label}] seed {args.seed:04d}")
    print(result_line(rep))
    print("r: request index, a: requested barcode, m: moves, ok: display matches, mis: mismatched windows."
          " A move is k@pos>d: paper k, at position pos before the move (0 = top), inserted at depth d.")
    shown = 0
    for q in rep.queries[start:end]:
        if args.wrong and q.correct:
            continue
        if shown >= QUERY_LINE_LIMIT and not args.all:
            print(f"(stopped at {QUERY_LINE_LIMIT} lines; pass --all or narrow --from/--to)")
            break
        moves = " ".join(f"{k}@{p}>{d}" for (k, d), p in zip(q.ops, q.positions))
        print(f"r={q.r:>4} a={q.target:>3} m={len(q.ops):>3} ok={'Y' if q.correct else 'N'} mis={q.mismatch:>2}  {moves}")
        shown += 1
    if rep.error and len(rep.queries) < len(out.queries):
        r = len(rep.queries)
        print(f"r={r:>4} a={inp.requests[r]:>3} invalid: {rep.error}; moves: "
              + " ".join(f"{k}>{d}" for k, d in out.queries[r]))


# ---------------------------------------------------------------- state


def cmd_state(args) -> None:
    label, inp, out = load_case(args.run, args.seed)
    r = args.request
    if not 0 <= r < inp.r:
        raise LookupError(f"--request は 0〜{inp.r - 1} で指定してください")
    rep = replay.replay(inp, out, stop_after=r + 1 if args.after else r)
    game = rep.game
    print(f"[{label}] seed {args.seed:04d}: state {'after' if args.after else 'before'} request {r}"
          f" (a={inp.requests[r]})")
    if rep.error:
        print(f"WA before this point: {rep.error}")
    print(f"so far: E={game.mistakes} T={game.moves}")
    if r < len(out.queries):
        print(f"moves of request {r}: " + (" ".join(f"{k}>{d}" for k, d in out.queries[r]) or "(none)"))
    target = inp.target[inp.requests[r]]
    shown = game.display()
    n = inp.n
    print(f"{'display':<20}{replay.mask_text(shown, n)}")
    print(f"{'requested':<20}{replay.mask_text(target, n)}")
    print(f"{'mismatch':<20}{diff_row(shown, target, n)}  ({(shown ^ target).bit_count()} windows)")
    print(PAPER_LEGEND)
    covered = 0
    print(f"{'pos paper  vis':<20}")
    for pos, k in enumerate(game.order[:args.top]):
        row = paper_row(game, k, covered)
        vis = (game.papers[k].opaque & ~covered).bit_count()
        print(f"{pos:>3} {k:>5} {vis:>4}    {row}")
        covered |= game.papers[k].opaque
    uncovered = n - covered.bit_count()
    rest = len(game.order) - args.top
    if rest > 0:
        covered_all = covered
        visible_below = []
        for pos, k in enumerate(game.order[args.top:], args.top):
            e = game.papers[k].opaque & ~covered_all
            if e:
                visible_below.append(f"{k}@{pos}:{e.bit_count()}")
            covered_all |= game.papers[k].opaque
        print(f"... {rest} more papers; visible among them (paper@pos:windows): "
              + (" ".join(visible_below) if visible_below else "none"))
    print(f"windows not covered by the top {min(args.top, len(game.order))} papers: {uncovered}")


# ---------------------------------------------------------------- design


def cmd_design(args) -> None:
    label, inp, out = load_case(args.run, args.seed)
    rep = replay.replay(inp, out, check=False)
    moved: dict[int, int] = {}
    for q in rep.queries:
        for k, _ in q.ops:
            moved[k] = moved.get(k, 0) + 1
    m = replay.design_metrics(inp, out.designs)
    print(f"[{label}] seed {args.seed:04d}: {len(out.designs)} papers designed; holes {m['hole_share']:.2%},"
          f" only holes {m['papers_all_holes']}, no holes {m['papers_no_holes']}")
    print("k: paper, '0' white, '1' black, '.' hole; opaque/black: window counts; moved: times moved")
    print(f"{'k':>3} {'opaque':>6} {'black':>5} {'moved':>5}  pattern")
    for k, p in enumerate(out.designs):
        print(f"{k:>3} {p.opaque.bit_count():>6} {p.black.bit_count():>5} {moved.get(k, 0):>5}  {p.pattern}")


# ---------------------------------------------------------------- log, verify


def cmd_log(args) -> None:
    run = replay.resolve_run(args.run)
    text = replay.err_path(run, args.seed).read_text(errors="replace")
    lines = text.splitlines()
    if args.tail and len(lines) > args.tail:
        print(f"(last {args.tail} of {len(lines)} lines)")
        lines = lines[-args.tail:]
    print("\n".join(lines))


def _verify_job(job: tuple[str, int]) -> tuple[int, int, str | None]:
    run, seed = job
    inp = replay.load_input(seed)
    rep = replay.replay(inp, replay.parse_output(inp, replay.out_path(Path(run), seed).read_text(errors="replace")))
    return seed, rep.score, rep.error


def cmd_verify(args) -> None:
    import multiprocessing
    run = replay.resolve_run(args.run)
    cases = replay.run_cases(run)
    with multiprocessing.get_context("fork").Pool(min(8, os.cpu_count() or 1)) as pool:
        replayed = pool.map(_verify_job, [(str(run), s) for s in sorted(cases)], chunksize=4)
    bad = [(s, score, cases[s]["score"], error) for s, score, error in replayed if score != cases[s]["score"]]
    print(f"{run.name}: {len(cases) - len(bad)} / {len(cases)} cases match the tester's score"
          " (replayed with the visibility check)")
    for s, mine, judge, error in bad[:20]:
        print(f"  seed {s:04d}: replay {mine}, tester {judge}" + (f" ({error})" if error else ""))


# ---------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("runs", help="評価済みの run を一覧し、基準の run と比べる")
    p.add_argument("--ref", help="基準の run（省略時は全ケースで平均スコアが最も良い run）")
    p.add_argument("--all", action="store_true", help="全ケースを評価していない run も表示する")
    p.add_argument("--sort", choices=["ratio", "time"], default="ratio", help="並び順: 基準との差 (既定) か新しい順")
    p.add_argument("--top", type=int, default=30, help="表示する run の数")
    p.set_defaults(func=cmd_runs)

    p = sub.add_parser("cases", help="見るべき seed を選ぶ（ベストや別の run と比べて差の大きいケース）")
    p.add_argument("run")
    p.add_argument("--vs", help="比べる run（省略時はケースごとのベストスコアと比べる）")
    p.add_argument("--top", type=int, default=15, help="表示するケース数")
    p.set_defaults(func=cmd_cases)

    p = sub.add_parser("stats", help="行動の指標と stderr の `名前 = 数値` を run ごと（または 1 ケース）に比べる")
    p.add_argument("run")
    p.add_argument("--vs", help="比べる run")
    p.add_argument("--seed", type=int, help="1 ケースだけの指標を出す")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("queries", help="注文ごとの操作と正誤を 1 行ずつ見る")
    p.add_argument("run")
    p.add_argument("seed", type=int)
    p.add_argument("--from", dest="from_", default="0", help="最初の注文（番号、50%% のような割合、既定 0）")
    p.add_argument("--to", help="この注文の直前まで（既定: --from の 30 個後。--wrong なら最後まで）")
    p.add_argument("--wrong", action="store_true", help="誤った注文だけを表示する")
    p.add_argument("--all", action="store_true", help=f"{QUERY_LINE_LIMIT} 行を超えても全部表示する")
    p.set_defaults(func=cmd_queries)

    p = sub.add_parser("state", help="注文の前（--after なら後）の紙の重なりと表示を見る")
    p.add_argument("run")
    p.add_argument("seed", type=int)
    p.add_argument("--request", type=int, required=True, help="注文の番号 r (0〜R-1)")
    p.add_argument("--after", action="store_true", help="注文 r の操作を適用した後の状態を見る")
    p.add_argument("--top", type=int, default=24, help="上から何枚の紙を表示するか")
    p.set_defaults(func=cmd_state)

    p = sub.add_parser("design", help="設計した紙の模様の一覧")
    p.add_argument("run")
    p.add_argument("seed", type=int)
    p.set_defaults(func=cmd_design)

    p = sub.add_parser("log", help="1 ケースの stderr（末尾はテスターの判定）")
    p.add_argument("run")
    p.add_argument("seed", type=int)
    p.add_argument("--tail", type=int, help="末尾の N 行だけ")
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("verify", help="再生したスコアがテスターのスコアと一致するか（可視性の検査つき）")
    p.add_argument("run")
    p.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    try:
        os.nice(10)  # leave the CPU to evaluations running at the same time
    except OSError:
        pass
    try:
        args.func(args)
    except (LookupError, FileNotFoundError) as e:
        print(f"[observe] {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # allow piping into head
    sys.exit(main())
