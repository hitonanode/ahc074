# astra-lab: 比較実験の補助ツール

改良元: なし（解法ではなく評価用）。

`bench.py` は既存の `scripts/pahcer_run.py` を import して、その対比較・記録・再生検査を使う。既存スクリプトは変更しない。

- 標準では公式 Rust tester を使う。Rust が利用できない環境では `--portable-judge` を指定し、`judge.cpp` の対話テスターを使う。これは `tools/src/lib.rs` の可視性・移動・表示・得点計算を移植したもので、公式バイナリそのものではない。結果は必ず既存 `scripts/replay.py` と照合する。
- `generate.py` は公式と同じ入力分布（64桁に32個の1、256個の異なる商品、直前と異なる1024注文）を Python の固定 seed で生成する。公式 ChaCha20 の同一 seed と同じケースにはならない。ケース番号と PRNG seed の対応・入力 SHA256 を manifest に残す。
- `--threads` で並列数を指定する。`--no-record` を用いて既存の pahcer 履歴とは混在させない。
- `--input-dir` で新規生成ケースを指定できる。公式 `tools/in/` は置き換えなくてよい。この入力先は各 run の meta.json に記録し、独立検証は `python3 solutions/astra-lab/verify.py RUN...` で行う。
- stdout/stderr は対話の終了までメモリに保持し、完成した記録を atomic rename で公開する。実行途中の不完全なログを他の処理が読み込むことを避ける。
- コンパイラの版・コンパイルフラグ・ソース全体が一致する場合だけ実行バイナリを再利用し、反復比較のビルド時間を削減する。
- `--fixed` は時間差の影響を分離する診断用。指定した回数で設計し、helper の構築打切りと fast-mode のみ診断コピーで無効化する。提出用ソースに変更は加えない。固定回数結果を2秒制限での性能とは解釈しない。

実験結果と実行条件は REPORT.md と results/ に記録する。
