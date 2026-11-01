# 保存した評価根拠

- `timed16.csv`: 時間制の 16 入力 × 4 解法。seed 5004〜5019。
- `controlled64.csv`: 共通の設計回数を固定した 64 入力 × 4 解法。seed 5020〜5083。
- `<run-id>.json`: 元の評価 runner の `result.json`。
- `manifest.json`: 元コミット、評価時ソースの SHA-256、現在のソースとの一致、全ケースの独立再生とログ検査の結果。

CSV の空欄はその解法に存在しない指標。`wall_sec` はこの環境での実時間。
各 CSV に得点、操作数、誤表示数、注文数、主要診断値、入力と両ログの SHA-256 を含む。
統計的な比較は `solutions/frontier-eval/screen-*.json` と `controlled-*-vs-*.json` を参照。
入力は `solutions/frontier-eval/generate.py` で再生成できる。
これらの seed は独自 Python 生成器の番号であり、公式 Rust 生成器の同番号の入力ではない。

`export_evidence.py` は上記の run がローカルにある場合だけ、検証済み記録を再出力する。
新たな評価は行わない。
