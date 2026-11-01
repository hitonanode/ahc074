# astra-probe

改良元: なし（解法ではなく、`solutions/imp-910` と保存済み出力を調べる調査用）。

本依頼の報告書は `REPORT.md`。新しい計測コード・出力はこのディレクトリ内に保存する。
公式の評価スクリプトは実行しない。既存コード・評価記録・`trial_log.md` は変更しない。
Python は `PYTHONDONTWRITEBYTECODE=1`、C++ は `g++ -std=c++23 -O2` で使用する。
実験値と仮定に基づく見積りを分け、提案した構造を実装済み・改善確認済みとは扱わない。

主なファイル:

- `analyze.py`, `top_cover.py`: 保存 run `20261101-214232_imp-910` の seed 0〜7 を再生する。ハンドルの順は「最初の不透明紙の番号」で復元する。
- `geodesic.cpp`, `bounds_check.py`: 商品集合から一般的な期待スコア下限を計算し、小さい整数の場合の補題を確認する。解法は実行しない。
- `ensemble_bound.py`: 一様な重み 32 の商品を非復元抽出する生成分布について、組合せ数の式から期待スコア下限を計算する。
- `module3_toy.cpp`, `module3_workload.cpp`: 3 窓・6 枚の全合法状態を使った平均費用の小模型。後者は `module_events.py` の出力を標準入力に与える。長い列や紙の取り出し・再挿入は省略した模型である。
- `module_search.cpp`: 同じ workload に対し、自由順序の三角形を基準として六枚の不透明マスクを共同設計する。`filler_audit.py` は、現行出力にも非整列の穴埋め紙が残っていることを確認する。
- `counterexample.py`: 実際の N,K,P と重み 32 を満たす特殊な入力の構成。一般下限の反例用であり、ランダムな入力を解く解法ではない。
- `decoder_model.cpp`, `escape_model.cpp`, `patch_model.cpp`: 枚数の予算を数えた設計目的関数の比較。提出用のオンライン解法ではない。
- `helper_probe.cpp`, `sparse_probe.cpp`, `overlap_probe.cpp`, `nonlinear_probe.cpp`, `overlay_decoder.cpp`, `triples.cpp`, `matching_probe.cpp`: 個別案の棄却実験。定義と制約は各ソース冒頭と `REPORT.md` に記載。
- `summarize.py`: 保存 CSV から、対応する基準との差・seed 間標準誤差・勝分敗を再集計する。

再現コマンドは `REPORT.md` の 6.2。C++ の一部は既存の `imp-910/main.cpp` を読み取り専用で include する。`matching_probe.cpp` だけは調査用にシステムの Boost ヘッダを使う。
初期の設計探索は固定 200 万反復（overlay 系は 400 万反復）、模型内の疑似乱数 seed は定数。時計による打切りを使った公式スコアの比較ではない。
保存 CSV/JSON は調査結果であり、`pahcer/` へ登録していない。
