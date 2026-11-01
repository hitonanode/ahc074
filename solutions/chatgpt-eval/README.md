# この PR の比較実験を再現するための補助ツール

改良元: なし（提出用の解法ではない）。

この環境には Rust コンパイラがないため、`tester.cpp` は公式 `tools/src/lib.rs` と同じ紙の可視性、挿入位置、注文の成否、得点を検査する C++ の対話アダプタである。
解法へ渡すのは最初の公開情報と、処理中の注文 1 件だけであり、未来の注文は渡さない。出力の形式、紙が見えているか、操作上限、異常終了、最終注文後の余計な出力を検査する。
これは公式 Rust テスターそのものではない。結果は既存 `scripts/replay.py` でも独立に全操作を再生して検証する。

`run_compare.py` は既存の `scripts/pahcer_run.py` を読み込み、その同一seedごとの実行順・比較・記録処理を使う。共通スクリプトは編集しない。テスター、並列数、追加ケースの範囲をメモリ上で設定し、完了した出力の独立再生検証を加える。通常のコンパイル条件は元の `-std=c++23 -O2 -DCLOCK_SCALE=1.1` のまま。既定の並列数は 2。`--official` を付ければ公式 Rust テスターを使う。

```sh
python3 solutions/chatgpt-eval/generate.py --start 10000 --end 10080
python3 solutions/chatgpt-eval/self_test.py
python3 solutions/chatgpt-eval/run_compare.py --jobs 2 \
  --compare solutions/imp-910 solutions/<候補> --seeds 10000-10064 \
  --no-record -c 'ChatGPT: 同一の新規生成ケースによる比較'
python3 scripts/observe.py verify <run-id>
```

生成器は Python 標準ライブラリの MT19937 を使い、64 ビット中 32 個が 1 のバーコードを重複なしで 256 個、連続して同じ番号が来ない注文を 1024 個生成する。問題の指定と同じ分布だが、公式 Rust 版の ChaCha20 と同じ seed のケースにはならない。各入力の SHA-256 を `cases-<start>-<end>.json` に記録する。

`--seeds` で新規生成ケースを指定したときは、全入力の存在を確認したうえで、メモリ上の設定範囲だけを拡張する。ルートの設定ファイルや既存の生成ケースは変更しない。

評価時の `meta.json` にはアダプタの種別、ソース SHA-256、指定並列数を追記する。結果の時間はこの環境での対話を含む壁時計時間であり、AtCoder 実機への換算値ではない。元リポジトリの `CLOCK_SCALE=1.1` は保つが、この環境への較正済み係数ではない。

`--cxx-flag=-DCHOICE_CHECK` のように追加のコンパイルフラグを指定でき、実際のコマンドとともに記録する。固定探索回数や救済紙の実験用環境変数も、既知の非機密キーだけを `experiment_environment` に記録する。通常版の結果と検査版の時間を混同しない。

比較時の stdout/stderr はパイプから同時に読み取り、メモリ内で最後まで保持する。採点結果の抽出と既存 `scripts/replay.py` による全操作の可視性・得点検証には、この同じバイト列を使う。その後、最終パスへ atomic rename で公開する。実行中の出力ファイルを再読込する方式で観測されたログの不整合を避けるためである。記録したテスターの得点と出力が一致しない場合は、そのケースをスコア 0 として失敗扱いにする。
`result.json` の各ケースには `artifact_verified`、検証前のテスタースコア、再生スコア、stdout/stderr の SHA-256 を残す。実行時間はテスターの起動から終了までを `time.perf_counter()` で測り、その後の再生検証時間は含まない。実行順・並列化・コンパイル・集計は元 runner を使い、ケースの起動部分だけをパイプによる収集に差し替える。

## 救済紙の表現力の調査

`rescue-feasibility/` には、救済紙 2 枚で表示できる部分パターンを列挙する研究用の `probe.cpp`、再現用の 6 枚の紙の模様、測定 CSV、考察を置いた。提出用の解法ではなく、操作回数の評価結果でもない。詳しくは同ディレクトリの README を参照。

## 記録と集計

最終結果と解釈は [検証レポート](../../docs/chatgpt-multiroute-rescue-study.md) を参照。`experiments.json` は比較群を定義し、`results/` には集計、ケース別CSV、metadata/result/診断値のJSONを保存する。`summarize.py` は全ケースの検証成功、stdout/stderrのSHA-256、独立再生スコアを確認し、不完全なrunの集計を拒否する。

```sh
python3 solutions/chatgpt-eval/summarize.py solutions/chatgpt-eval/experiments.json \
  --output solutions/chatgpt-eval/results
```

上のコマンドには元の `runs/` が必要。別環境では同じ入力で比較を再実行し、そのrun-idを記したmanifestを指定する。時間で探索を打ち切るため、スコア・出力ハッシュは再実行ごとに変わり得る。
