# ahc074

https://atcoder.jp/contests/ahc074/tasks/ahc074_a

AI の使い方の参加記（With AI 部門）: https://hitonanode.github.io/ahc074/ （ソースは [writeup/index.html](writeup/index.html)）

agent 向けの説明は [AGENTS.md](AGENTS.md)（CLAUDE.md はそのシンボリックリンク）。

解法は solutions/<name>/ に置き、main.cpp（提出するソース）と README.md（その解法の内容、または改良元の解法との差分の説明）を必ず含める。

## よく使うコマンド

```sh
# 評価（全 2000 ケース。runs/<run-id>/ に stdout・stderr・ソース・結果が残る。同時に 1 つだけ走る）
scripts/pahcer_run.py solutions/<name> -c "コメント"
# 複数の解法を seed ごとに交互に実行して比べる（最初が基準）
scripts/pahcer_run.py --compare solutions/<基準> solutions/<候補> -c "コメント"
# 既存の run（500 ケースの run や --seeds の run）に、未評価の seed を加えて全ケースにする
scripts/pahcer_run.py --extend <run-id> [<run-id> ...] -c "コメント"

# テキストで観察（AI 向けのビジュアライザ）
scripts/observe.py runs
scripts/observe.py cases <run> [--vs <run2>]
scripts/observe.py stats <run> [--vs <run2>]
scripts/observe.py queries <run> <seed> [--wrong]
scripts/observe.py state <run> <seed> --request <r>

# ダッシュボード（評価のたびに runs/report.html が自動で作り直される）
scripts/serve_report.py      # http://localhost:8074/report.html
```

ダッシュボードはファイルとして開いても表は見られるが、出力を読み込んだ公式ビジュアライザを並べるには
`scripts/serve_report.py` 経由（HTTP）で開く（初回に公式ビジュアライザを runs/.vis/ へ取ってくる）。
