# 実験用の評価環境

改良元の解法: なし（提出用解法ではなく、評価を再現する補助ファイル）。

実験全体の結論・比較表は [REPORT.md](REPORT.md)。

この環境には Rust / Cargo がないため、`tester.cpp` は公式の
`tools/src/lib.rs` と `tools/src/bin/tester.rs` の対話・可視性・得点規則を
C++23 / POSIX に移植したもの。解法の出力は元の形で保存し、未公開の注文は
現在の注文を処理し終わるまで解法に渡さない。各手の可視性、移動先、操作数、
紙の形式、余分な出力、異常終了を検査する。対象は通常の ASCII 対話出力。
公式 Rust バイナリそのものではないため、その点は評価報告でも区別する。

再現時は別クローンを用い、既存の公式ケースが `tools/in/` にある場合は退避してから
独自ケースを生成する。生成器は異なる既存入力を検出すると停止する。

```sh
mkdir -p tools/target/release
g++ -std=c++23 -O2 solutions/chatgpt-study/tester.cpp -o tools/target/release/tester
python3 solutions/chatgpt-study/generate.py --count 2000
python3 solutions/chatgpt-study/test_tester.py
python3 solutions/chatgpt-study/run_compare.py --workers 3 --compare solutions/imp-combo solutions/<candidate> --seeds 0-500 --no-record -c 'chatgpt uniform-v1 cases; C++ tester port'
```

`generate.py` のケースは問題文と同じ分布から生成する。バーコードは64窓中32個を
一様に選び、256種類は重複を除く。注文は最初が256択、以後は直前以外の255択。
乱数は Python `random.Random`、各ファイルの seed は `20261102 + index`。
**公式の ChaCha20 生成器の seed 0～1999 と同じケースではない。** ファイル番号は
既存ランナーの入力規約に合わせた識別子であり、生成器の seed と混同しない。
既存の異なる入力ファイルは上書きしない。生成時にケースの SHA-256 一覧を保存する。

比較は既存の `scripts/pahcer_run.py --compare` を無変更で用いる。このモードには
`pahcer` コマンドは不要。`--no-record` により既存の公式 seed のベスト記録を
独自生成ケースで更新しない。出力・スコア・コンパイルコマンドは通常どおり
`runs/<run-id>/` に残る。得点はさらに既存の `scripts/replay.py` で再計算する。

`run_compare.py` はこのプロセス内だけ `os.cpu_count()` を指定worker数へ置き換え、
元の評価器をそのまま実行する。既存の設定ファイルは変更しない。worker数は各runの
commentにも保存する。9並列の予備測定と、CPU競合を減らした3並列の測定は区別する。

`summarize.py` は基準を最初に指定し、同じ入力番号集合の比較をJSONとCSVへ出力する。
入力の現物をmanifestのSHA-256で検査し、`--verify`では独立実装の `replay.py` で
各手の可視性と最終得点を検査する。差は100倍したlog比の平均、±は標準誤差。
平均スコア、操作数、勝分敗、WA/E、時間の中央値・95%点・最大値、fast_requests、
ソースのhash、コンパイルコマンド、実際のリモート基準コミットも保存する。

```sh
python3 solutions/chatgpt-study/summarize.py --runs <baseline-run> <candidate-run> --manifest tools/in/chatgpt_manifest.json --out solutions/chatgpt-study/results/<name> --verify
```

ローカルの実行環境は元の開発機とも AtCoder とも異なる。時計倍率1.1を含む
コンパイル条件は基準・候補で共通にし、この環境での対比較として解釈する。
公式ジャッジ上での時間安全性を確認したとは扱わない。

## 共通の注文列を使う追加実験

`sim_compare.py` は各解法に元からある `SIM_HARNESS` を使い、設計を確定してから
同じ乱数の注文列を8本ずつ流す。設計はこの注文列を参照しない。提出用ソースは
変更せず、`runs/` のコピーでhelper表の初期化期限を外す。通常の対話ループを
通らないため、注文途中の時間による軽量化も行わない。

```sh
python3 solutions/chatgpt-study/sim_compare.py --solutions solutions/imp-combo solutions/chatgpt-match solutions/chatgpt-spectrum solutions/chatgpt-joint-repair --seeds 256-288 --workers 3 --map-iters 0 --gopt-steps 0 --anneal-iters 4000000 --climb-iters 20000 --sim-seqs 8 --output runs/chatgpt-design-sim-reproduce
```

この例は窓割り当てだけを共通の時間予算（0.50秒＋0.11秒）にし、後段の反復数を
揃える比較である。設計自体は解法間で異なり、時間制の部分には実行ごとの変動がある。
`sim_wrong` は解法内の表示照合であり、独立テスターでの可視性検査とは区別する。
提出形式での合法性は、通常の対話比較と独立再生で別に確認する。

全設計段階を通常の時間予算で比較する場合は、`--anneal-iters 0 --climb-iters 0` も指定する。
独立確認の条件は次のとおり。

```sh
python3 solutions/chatgpt-study/sim_compare.py --solutions solutions/imp-combo solutions/chatgpt-spectrum --seeds 512-640 --workers 3 --map-iters 0 --gopt-steps 0 --anneal-iters 0 --climb-iters 0 --sim-seqs 8 --output runs/chatgpt-spectrum-confirm-reproduce
```

こちらもhelper初期化と注文処理の時間制限は外すため、提出の2秒制限の検証ではない。

汎用層MDPだけを同一の紙設計で比較する実験は
`solutions/chatgpt-transition/probe.py` を使う。こちらは全設計反復数を固定し、
設計fingerprintが一致することを必須とする。

## ソースの追跡

基準コミットは `dee23c8fce0eba04e513478629402f20b843e9f0`。
通常の3並列比較の基準 `main.cpp` はそのGit blob
`2d25dd8534c3c31f93760e84605968c74bc96a12` と完全一致する。
最初の9並列予備測定だけは、取得時に末尾の空行が1行多かった。
アルゴリズム上の差はなく、各結果には実際にコンパイルしたソースのhashを保存している。

MDPの通常比較後に、汎用紙を6枚見つけたら残りの紙を走査しない最適化を加えた。
通常比較時の厳密なソースへ戻す差分は
`results/low_contention/mdp_snapshot.patch`。固定設計比較は最適化後のソースで行った。
`results/repair_initial_bug/source_snapshot.patch` は、構成段階の不具合を含む修正前版を
再現するための差分である。どちらも現在の提出用ソースから当時の版へ戻す方向なので、
必要なら別の作業コピーで適用する。修正前の結果は最終候補の性能として扱わない。
