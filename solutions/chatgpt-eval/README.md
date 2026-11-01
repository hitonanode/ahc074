# 検証用テスターとケース生成

改良元: なし（提出用解法ではない）。判定規則は `tools/src/lib.rs` と `tools/src/bin/tester.rs` を参照。

この環境には Rust/Cargo がないため、公式の判定処理を `tester.cpp` に移植した。
設計と操作の形式、可視性、挿入位置、各注文 2K 回上限、最終表示、余分な出力、異常終了を検査する。
入力はテスターだけが全体を読み、解法には事前情報と現在の注文だけを順に送る。
提出用ソルバーが未来の注文を読める構成にはしていない。

`run_compare.py` は共通ファイルを変更せず `scripts/pahcer_run.py` を import し、テスターのビルド先と並列数を実行時に指定する。
実行中の stdout/stderr ファイルが途中の状態へ戻る保存不整合を観測したため、テスターの両出力をメモリへ取得し、完了後にファイル全体を atomic replace で保存する。
各ケースの result.json に両出力の SHA-256 も記録する。制限時間の計測はテスター起動から終了までで、終了後のログ保存時間を含まない。
比較順の交替、ソース保存、result/meta JSON、スコア集計は既存の評価スクリプトのまま。
単体のスモーク実行は `--no-record` 付きで使用でき、既存評価器の `prepare_run`・`compare_case`・得点/指標保存関数を組み合わせる（pahcer CLI は不要）。
既定では C++ 移植テスターを使う。Rust/Cargo が使える環境では `--official-tester` を付けると、元の `scripts/pahcer_run.py` のテスタービルド処理をそのまま呼び、公式 Rust テスターを使う。
指定時のコメントと metadata は `official Rust` と記録される。今回の実測に公式 Rust テスターを使ったという意味ではない。

```sh
python3 solutions/chatgpt-eval/generate.py --start 100000 --count 64 --base-seed 0
python3 solutions/chatgpt-eval/check_tester.py
python3 solutions/chatgpt-eval/run_compare.py --threads 4 --compare solutions/imp-gla solutions/NEW --seeds 100000-100064 --no-record -c "generated MT19937 cases; C++ tester port"
```

今回の4者ゲートを、公式 Rust テスターで同じ新規64ケースに対して再評価する例（生成は上記コマンドで1回だけ行う）:

```sh
GATE_COUNT=3 GATE_ARITY=4 GATE_FULL=1 \
python3 solutions/chatgpt-eval/run_compare.py --official-tester --threads 2 \
  --compare solutions/imp-gla solutions/chatgpt-structure \
  --seeds 100000-100064 --no-record \
  -c "official Rust; GATE_COUNT=3 GATE_ARITY=4 GATE_FULL=1"
```

固定探索量でも比べる場合は、同じコマンドの前に `MAP_ITERS=15000 GOPT_STEPS=3000 ANNEAL_ITERS=5000000 CLIMB_ITERS=20000` を追加する。
`--official-tester` を使う場合も生成ケース番号の拡張、seed ごとの実行順の交替、ログの atomic 保存、スコア差と標準誤差の集計は同じ。

`generate.py` は Python の MT19937 と `random.sample(range(64), 32)` を使い、64 窓中ちょうど 32 黒のバーコードを 256 種、直前と異なる一様注文を 1024 件生成する。
問題と同じ分布を使うが、公式 ChaCha20Rng の同番号 seed と一致するとは主張しない。
既存ファイルを上書きせず、ファイルごとの生成 seed と SHA-256 を `generated_manifest.json` に記録する。
正式比較用の新規ケースはファイル番号 100000〜100063 がそのまま生成 seed 100000〜100063 に対応する。
既存の公式生成済ファイル 0〜1999 を変更しないための番号で、専用 wrapper はこの明示範囲を許可する。
初回4件のスモークは同じ内容を番号 1000〜1003 で実施した（元の完全 checkout にはこの番号の公式ケースがあるため、正式比較では使用しない）。
実行時間はこの環境に依存し、公式ジャッジでの 2 秒以内を保証する値ではない。
