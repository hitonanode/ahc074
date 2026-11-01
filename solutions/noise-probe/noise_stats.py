#!/usr/bin/env python3
"""評価の雑音と必要なケース数を、runs/ の既存の run から見積もる（README.md）。

    python3 solutions/noise-probe/noise_stats.py [--since 20261101-081416]

- A/A: 同じソース（src/main.cpp が同一）を別々に評価した run の組の、ケースごとの log スコア比の
  標準偏差。出力が決定的な解法（差がすべて 0）は除く。
- A/B: 同時比較（同じ時刻の run）の別解法の組の標準偏差。--since より後の run だけを使う。
- 再現性: 同じ 2 解法をそれぞれ複数回評価していれば、共通の run を持たない 2 つの反復で、ケースごとの
  差の相関を出す（0 なら、どのケースで効くかは雑音で、効果はケースによらず一様）。
- 必要なケース数: A/B の標準偏差の中央値 σ から、差 d を「平均 < −2 SE」で検出する確率（検出力）。
- --split RUN...（同じソースの run を 2 つ以上）: 1 回の実行のぶれ（seed ごとの run 間の分散）を、注文列による
  ぶれと設計の良し悪しのぶれに分ける。各 run の注文を前半 512 と後半 512 に分けた log(前半 / 後半) の分散の
  1/4 を、1024 注文の合計の注文によるぶれとみなす（同じ設計の 2 つの半分の差には注文の偶然しか入らない）。
"""
import argparse
import collections
import hashlib
import itertools
import json
import math
import statistics
import subprocess
from pathlib import Path


def main_checkout() -> Path:
    common = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True,
                            cwd=Path(__file__).resolve().parent).stdout.strip()
    return (Path(__file__).resolve().parent / common).resolve().parent


def load_runs(runs_dir: Path) -> list[dict]:
    out = []
    for d in sorted(runs_dir.iterdir()):
        res, src = d / "result.json", d / "src" / "main.cpp"
        if not res.is_file() or not src.is_file():
            continue
        cases = json.loads(res.read_text())["cases"]
        if len(cases) < 500:
            continue
        out.append({"id": d.name, "group": d.name.split("_")[0], "name": d.name.split("_", 1)[1],
                    "hash": hashlib.md5(src.read_bytes()).hexdigest(),
                    "scores": {c["seed"]: c["score"] for c in cases}})
    return out


def diffs(a: dict, b: dict) -> list[float]:
    """log(score_b / score_a) per seed, over the seeds both solved."""
    return [math.log(b["scores"][s] / a["scores"][s]) for s in sorted(a["scores"])
            if a["scores"][s] > 0 and b["scores"].get(s, 0) > 0]


def corr(x: list[float], y: list[float]) -> float:
    mx, my = statistics.fmean(x), statistics.fmean(y)
    sxy = sum((u - mx) * (v - my) for u, v in zip(x, y))
    return sxy / math.sqrt(sum((u - mx) ** 2 for u in x) * sum((v - my) ** 2 for v in y))


def phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def split_noise(root: Path, run_ids: list[str]) -> None:
    """Per-run noise of the log score, and its part due to the orders (from the two halves of each run)."""
    import sys
    sys.path.insert(0, str(root / "scripts"))
    import replay
    seeds = range(500)
    inputs = {s: replay.load_input(s) for s in seeds}
    logs, v_order = [], []
    for rid in run_ids:
        total, half_ratio = [], []
        for s in seeds:
            out = replay.parse_output(inputs[s], (root / "runs" / rid / "out" / f"{s:04d}.txt").read_text())
            ops = [len(q) for q in out.queries]  # score = total ops (E = 0 for these solutions)
            first, second = sum(ops[:len(ops) // 2]), sum(ops[len(ops) // 2:])
            total.append(math.log(first + second))
            half_ratio.append(math.log(first / second))
        logs.append(total)
        v_order.append(statistics.variance(half_ratio) / 4)
    v_run = statistics.fmean(statistics.variance([lg[s] for lg in logs]) for s in seeds)
    vo = statistics.fmean(v_order)
    print(f"{len(run_ids)} run: 1 回の実行のぶれ sd {100 * math.sqrt(v_run):.3f}%、うち注文による sd "
          f"{100 * math.sqrt(vo):.3f}%（分散の {vo / v_run:.0%}）、設計の良し悪しの sd "
          f"{100 * math.sqrt(max(0.0, v_run - vo)):.3f}%")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="20261101-081416", help="この時刻以降の run だけを使う（解法の世代をそろえる）")
    ap.add_argument("--split", nargs="+", metavar="RUN", help="同じソースの run-id（2 つ以上）でぶれを分ける")
    args = ap.parse_args()
    if args.split:
        split_noise(main_checkout(), args.split)
        return
    runs = [r for r in load_runs(main_checkout() / "runs") if r["group"] >= args.since]

    by_hash = collections.defaultdict(list)
    for r in runs:
        by_hash[r["hash"]].append(r)
    aa = []
    timed = set()  # sources whose runs differ (time-limited, not deterministic)
    for h, rs in by_hash.items():
        for a, b in itertools.combinations(rs, 2):
            d = diffs(a, b)
            if sum(v == 0 for v in d) < len(d) / 5:
                aa.append((a["name"], statistics.stdev(d), statistics.fmean(d)))
                timed.add(h)
    print(f"A/A（同じソースを別々に評価）: {len(aa)} 組、ケースごとの sd の中央値 "
          f"{100 * statistics.median(s for _, s, _ in aa):.3f}%、run 間の平均の差の sd "
          f"{100 * statistics.stdev(m for _, _, m in aa):.3f}%")

    by_group = collections.defaultdict(list)
    for r in runs:
        by_group[r["group"]].append(r)
    ab = []
    for rs in by_group.values():
        for a, b in itertools.combinations(rs, 2):
            d = diffs(a, b)
            if a["hash"] != b["hash"] and sum(v == 0 for v in d) < len(d) / 5:
                ab.append(statistics.stdev(d))
    sigma = statistics.median(ab)
    print(f"A/B（同時比較の別解法）: {len(ab)} 組、ケースごとの sd の中央値 {100 * sigma:.3f}%")

    # Reproducibility of the per-case effect between replicates that share no run. Only time-limited
    # sources: a deterministic one would put its own per-case deviations into both replicates.
    names = collections.defaultdict(set)
    for h in timed:
        names[by_hash[h][0]["name"]].add(h)
    multi = {n: max(hs, key=lambda h: len(by_hash[h])) for n, hs in names.items()}
    cs = []
    for na, nb in itertools.combinations(sorted(multi), 2):
        A, B = by_hash[multi[na]], by_hash[multi[nb]]
        for a1, a2 in itertools.combinations(A, 2):
            for b1, b2 in itertools.combinations(B, 2):
                cs.append(corr(diffs(a1, b1), diffs(a2, b2)))
    if cs:
        print(f"独立な反復どうしのケースごとの差の相関: 平均 {statistics.fmean(cs):+.3f}（{len(cs)} 組）")

    print(f"\n検出力（σ = {100 * sigma:.2f}%、採用 = 平均 < −2 SE）")
    print("  ケース数   SE      d=−0.1%  d=−0.05%  d=0（誤採用）")
    for n in [500, 1000, 2000, 4000, 8000]:
        se = 100 * sigma / math.sqrt(n)
        print(f"  {n:7d}  {se:.4f}%   {phi(0.1 / se - 2):.2f}     {phi(0.05 / se - 2):.2f}      {phi(-2):.3f}")


if __name__ == "__main__":
    main()
