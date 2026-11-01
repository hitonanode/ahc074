# frontier-eval

改良元: なし（解法ではなく、この環境用の評価補助）。

- `tester.cpp` は `tools/src/lib.rs` の対話、可視性、差し込み、誤りと得点計算を C++ に移植する。未来の注文は子プロセスへ渡さない。出力は記録用に標準出力へ中継し、判定を標準エラーへ出す。Rust ツールチェーンのない環境でのみ使用する。
- `generate.py` は各64窓の32要素部分集合を一様に選んで相異なる256バーコードを作り、初回一様・以後直前以外に一様な1024注文を作る。Python `random.Random` 使用。ファイル番号5000以降は独自Python seedであり、公式Rust生成器の同番号とは一致しない。
- `compare.py` は既存 `scripts/pahcer_run.py` の比較関数を使い、実行時のseed範囲・並列数とログ保存方法を差し替える入口。コンパイル、同一seed内の順番交替、排他ロック、集計は元スクリプトの処理を用いる。共通ソースは編集しない。
- 実行中のログファイルを環境が途中状態で同期する現象への対策として、各ケースのstdout/stderrをPIPEでメモリに受け、プロセス終了後に同じディレクトリの一時ファイルへ全量を書き、`fsync` と `os.replace` で最終名に確定する。最終ログは対話中に一切書き足さない。`result.json` の各caseにstdout/stderrのバイト数とSHA-256を残す。Score抽出・60秒timeout・経過時間の計測範囲は元runnerと同じ。
- ビルド: `g++ -std=c++23 -O2 solutions/frontier-eval/tester.cpp -o tools/target/release/tester`
- 生成: `python3 solutions/frontier-eval/generate.py --start 5000 --count 128`
- 比較: `python3 solutions/frontier-eval/compare.py --compare solutions/imp-lean solutions/<candidate> --seeds 5000-5128 --threads 4 --no-record -c '<実験内容>'`
- `selftest.py` は小さな既知の合法・不正出力とランダムな合法遷移で、移植テスターを `scripts/replay.py` に照合する。解法の性能評価は必ず上の比較入口から行う。
- `test_atomic_logs.py` は大きな既知ログ2本、異常終了、timeoutを検査し、書き込み中の最終ファイルが不存在か完成済みのどちらかであることと、記録されたハッシュ・バイト数を確認する。
- 集計: `python3 solutions/frontier-eval/summarize_compare.py <baseline-run-id> <candidate-run-id> [--json <出力先>]`。保存済み結果だけから手数、得点差とSE、対数比とSE、勝分敗、WA、誤り、2秒超え、時間、fallbackをまとめる。
- テスターは `solver_cpu_sec`（子解法のuser+system CPU）、`tester_cpu_sec`（テスター自身のCPU）、`tester_wall_sec`（対話全体のwall）をstderrに出す。いずれも時計倍率を掛けない実秒。解法が出す `end_sec` / `req_sec` の倍率付き時計とは区別する。
- 中継stdoutの `fwrite` / `fflush` を検査し、失敗時は得点0として扱う。`tester_relay_bytes` と `tester_relay_fnv64`（FNV-1a、16進）をstderrへ記録し、保存されたstdoutの長さと内容がテスターの完了時点と一致するか確認できる。

この環境の実行時間は元リポジトリの測定環境やAtCoderと未較正である。`CLOCK_SCALE=1.1` は元の比較スクリプト通りとし、得点差と時間を区別して報告する。
公式Rustバイナリとの実行結果の直接照合は未実施。移植コードは公式ソースを根拠とし、独立実装の `replay.Game` で可視性・遷移・得点を照合する。
