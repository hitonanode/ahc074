# astra-frontier

改良元: solutions/astra-search4（実験基盤の比較対象）。

構造を変える解法の研究・比較をまとめるディレクトリ。

## 再現用の補助プログラム

- `generate_cases.py`: 問題文どおり、重複のない32個の1を含む64bitの商品256個と、直前の商品を除く一様な注文1024個を生成する。Python の Mersenne Twister を使うため、公式 generator と seed の対応は異なる。入力内容の SHA-256 を manifest に残す。
- `portable_tester.cpp`: Rust がない環境用に、公式 `tools/src/lib.rs` の対話・可視性・得点規則を C++ へ移したテスター。解法へ将来の注文は渡さない。元の Rust テスターと独立な `scripts/replay.py` でも出力を検証する。
- `evaluate.py`: 既存の `scripts/pahcer_run.py` をそのまま呼び出す。CPUの割当てに合わせて並列数のみ指定し、結果は通常の runs/ に保存する。新規に生成したケースは既存 seed と異なるため `--no-record` で pahcer/ の既存値へ混ぜない。

評価結果と判断は `REPORT.md` と `trial_log.md` に記載する。

## 読む順序

1. `REPORT.md`: 提案の数学的な根拠、比較結果、今後試す価値がある変更。
2. `EVALUATION.md`: 同じ生成ケースを使う評価の再現方法、固定仕事量診断、時間計測の限界。
3. `results/*.csv` / `results/*.json`: ケース別スコアと、対比較・再生検査・ソースハッシュを含む集計。
4. `holdout-selection.json`: 未使用500件の評価前に固定した候補とソースハッシュ。
5. `PORTABLE_TESTER_AUDIT.md`: 公式Rustテスターとの静的照合と、今回の出力には影響しない挙動差。

`prepare_workspace.py`は既存の入力を置き換えず、独立した評価先を作る。
`diagnostic_sources.py`は時間制限を超えてよい診断専用コピーを作り、変更点を記録する。
`summarize.py`は既存のrunから集計を再生成し、解法を再実行しない。
