# chatgpt-eval

改良元: なし（解法ではなく、Rust が利用できない環境の評価用アダプター）。

`tester.cpp` は `tools/src/lib.rs` と `tools/src/bin/tester.rs` の対話、紙の可視性、操作、得点計算を C++ に移したもの。公式 Rust バイナリそのものではない。実際に子プロセスへ注文を 1 つずつ送るので、解法が将来の注文を読むことはできない。各操作直前に可視性を検査し、範囲外、余分な出力、途中終了、異常終了を拒否する。

`run_compare.py` は既存の `scripts/pahcer_run.py` を読み込み、その `evaluate_compare` / `evaluate_extend` を使う。テスターのパス、並列数、新しい入力 ID の範囲を明示する。コンパイル条件、同じ seed の交互実行、標準誤差、ソースのスナップショットは元の評価器をそのまま使い、子プロセスの起動・出力取得と指標の供給を下記の方式へ差し替える。通常の Rust 環境では、このアダプターを使わず `scripts/pahcer_run.py --compare ...` で再評価する。

テスターは `fwrite` / `fflush` の戻り値を検査する。アダプターは `subprocess.run(capture_output=True)` の PIPE で stdout/stderr を取得し、取得した bytes を比較の終了まで親のメモリに保持する。Scoreの抽出、可視性付き独立再生、E/Tなどの指標は、この bytes のみから計算する。子プロセスの出力を通常ファイルへ直接接続しない。

集計前に、入力・全stdout/stderr・得点・hashを単一の gzip JSON archiveへ親から atomic保存し、readbackとhashを検証する。通常の `out/` と `err/` は親からatomic保存して生成する。もし個別ファイルが失われた場合は保持したbytesから復元し、復元を明示的にログ・メタデータへ記録する。これはsolverの再実行ではない。捕捉bytesの採点・可視性検査の不一致、archiveの不一致、復元できない個別ファイルの不一致は比較を無効として扱い、solverの自動再試行はしない。

`meta.json` の `capture_archive` に証拠archiveのパスとhash、`evaluation_environment` に4つの実験用環境変数だけを保存する。各ケースには192枚の設計を行単位で正規化した `paper_design_sha256` も保存し、固定設計の比較を確認できる。`--extend` はこのPIPE版で取得したarchiveを持つrunにのみ使える。

別プロセスでの検証は `python3 solutions/chatgpt-eval/verify_archive.py <archive> --expected-sha256 <hash> --check-materialized`。archiveに保存した入力と出力から全ケースを可視性付きで再生し、必要なら通常ファイルとのbyte一致も確認する。

この変更の契機は `20261101-161140_*` の比較で、実行直後には正常な Score が読めた5件について、後で保存 stdout が途中 EOF、stderr が一部または全部消失している不整合が見つかったこと。`fsync` と1並列にしても `20261101-161818_*` で再発したため、両比較の結果は無効として、子出力を通常ファイルに直結しない方式へ変更した。正確な原因を確定したとは主張しない。過去の出力・採点値は変更しない。

```sh
python3 solutions/chatgpt-eval/run_compare.py --threads 2 \
  --compare solutions/imp-combo solutions/<candidate> --seeds 0-32 \
  --no-record -c "C++ tester adapter; same inputs; CLOCK_SCALE=1.1"
```

`generate.py` は問題文どおりの分布（64 bit 中 32 bit が 1、256 種を重複なし、連続注文は異なる）で新しい入力を作る。Python の標準乱数を使うため、公式 ChaCha20 の同一 seed と同じ入力にはならない。出力に付く番号はケースの識別子であり、公式 seed ではない。既存ファイルは上書きしない。`manifest.json` に乱数 seed、入力の SHA-256、生成方式を保存する。

```sh
python3 solutions/chatgpt-eval/generate.py --out tools/in --start 100000 --count 64 --seed 74020261102
```

実行環境の CPU、コンパイラ、テスターが元の評価環境と違うため、絶対時間と既存の過去スコアの直接比較には使わない。同時比較の両者を同じ条件で実行し、AtCoder 上の時間適合性は公式テスターと対象環境で改めて確認する。

評価器自身のテストは `python3 solutions/chatgpt-eval/selftest.py`。問題文の例、未来の注文を渡さないこと、不可視紙、範囲外、余分な出力、途中終了、異常終了、穴だけの紙、Unicode 空白、乱数による合法操作列の再生を検査する。これは解法のベンチマークではない。

`analyze_relocations.py RUN [RUN ...] --legal --output FILE` は保存済み出力を再生し、同じ最終紙順を保った操作短縮の余地を解析する。無制約の下界 `K-LCS`、重複して動かした枚数に加え、動かさない紙によって初期位置で完全に覆われる紙を除外した共通部分列の探索を行う。この追加条件は合法な全操作列に必要であり、強化下界を与える。さらに、その固定集合以外の紙を各1回だけ動かす計画を合法 DFS で探索する。紙を固定済みの最終順序の隣接紙の間へ挿入する全候補を列挙するので、指定した固定集合と各1回という制限下では完全探索になる。探索上限に達した注文は明示的に数える。短縮を見つけた場合は、既存 `replay.Game` の可視性検査を使って置換前後の全192枚の順序の一致を検証する。
