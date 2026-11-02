# astra-decoder の研究用コード

改良元: `solutions/as6-cap38p0`。整合緩和の計測は `solutions/compat-price`、七枚の厳密費用表と先着ゲートの距離球計算は PR76 の `cc718c1de52fe81c3c0c2724de276b51f5104317` から移植した。

## 変更点

- `model.cpp`: `COMPAT_FREE=d` で距離d以下の不整合対を許し、`COMPAT_GX=x` でその汎用費用をx/100手に設定する。`MODEL_ONLY=1` で注文処理前に終了。`DUMP_DESIGN=1` で窓の割り当てと選択対をJSON出力する。
- `relax_probe.cpp` / `relax_fees.cpp`: 対ごとに除ける窓数を制限した緩和と、二つの固定キャップの全費用模型。キャップはDの印刷と挿入位置を列挙し、追加紙で専用紙が減ることも数える。
- `gates.cpp`: 白黒穴の602印刷で2〜4窓を同時に変える幅4のビーム。全商品対の両側の可否と厳密な移動費用を求め、毎回対を組み直す。15比較窓は可視性の保証として残す。
- `joint-detail.cpp`: ゲート変更に汎用窓・ハンドル窓の交換を含める。`GATE_WITNESSES=12` では12比較窓だけを保護し、完成時に全印刷から合法移動グラフを作り直す。
- `joint-sa.cpp`: 同じ探索で悪化も受理し、最良状態を保存する追試。
- `shared.cpp`: ゲート探索と最終設計の費用の丸め、同点処理、相方の走査順を揃えた版。最終設計の最初の対集合が探索側の選択と一致することを検査する。
- `forced.cpp`: 部分ビームでは狙った一対を必ず選び、完成時に強制を外して再評価する4窓・8窓変更の追試。
- `six-control.cpp`: 七枚へ移植した探索器を六枚で動かし、探索器の移植による差を分けて測る対照。
- `seven.cpp`: 七枚用の関係行列と候補列挙に、現行の窓交換・比較組変更・複合交換を移した版。固定キャップと現行の列・ハンドル探索を使う。`SPARSE_WINDOWS=m` は六枚の設計からm窓の比較相手を七枚目へ付け替える。疎な場合の最終費用は実際の可視性を使う。
- `seven-tune.cpp`: 七枚版の汎用窓数とハンドル差の重みを変える診断用。`SEVEN_G`、`HANDLE_WEIGHT`（1000で係数1.0）を指定する。

研究結果、採否、限界は [REPORT.md](REPORT.md) にまとめた。これらは研究用プログラムで、不整合対を許す模型を提出用の解法として実行してはいけない。

## 主な計測条件

```sh
g++ -std=c++23 -O2 -DCLOCK_SCALE=1.1 -DSIM_HARNESS solutions/astra-decoder/shared.cpp -o solutions/astra-decoder/shared
python3 solutions/astra-decoder/bench.py --binary shared --label reproduce-shared12 --sim 4 --extra GATE_TRIALS=128 --extra GATE_WITNESSES=12
```

- 対象は既定でseed24〜87。`bench.py --seeds 24-40` で一部を指定できる。解法は最大8プロセス、テスター利用時は最大6組。複数の8並列評価を同時に実行しない。
- 基本の固定回数は `MAP_ITERS=400000`、`GOPT_STEPS=100000`、`ANNEAL_ITERS=20000000`、`CLIMB_ITERS=60000`。`--extra NAME=VALUE` で変更する。
- `GATE_TRIALS=128` が原子的なゲート変更の提案数。`GATE_COMPARATORS=1` は比較器30印刷だけを使う対照。
- `SIM_SEQS=4` の模擬は各1024注文。時間による探索量の変化を除くため、固定回数のときだけhelper構築の時間制限と注文処理の軽量化を解除する。通常の二秒制限の計測とは区別する。
- 乱数はソース内の定数。時計は全て `CLOCK_SCALE` を掛ける。

## 指標と再現用ファイル

`model_cost` は `model_col`（列の掘り）、`model_hole`（ハンドルの穴）、`model_gc`（汎用層）の和。持ち上げ・前紙の戻しを含まない。`pair_gc_mean` は対の注文一件あたり、一様な全汎用順序からの厳密な最短合法手数の平均。

`gobj_after` は元の割り当て段階の目的値。ゲート探索の `decoder_obj_before/after` は最終設計と同じハンドル差係数0.65の目的値で、前者とは直接差し引かない。12窓保護版の探索用距離と、全印刷による最終費用も区別する。`decoder_matching_equal=1` は探索と最終設計の初期対集合が一致したことを示す。

`sim_moves`、`sim_generic` は模擬で実行した総手数と汎用紙の操作数の注文平均。`sim_wrong` は注文列一列あたりの誤表示数。

- `data/`: ケース別の模型指標、基準と整合なしの設計、緩和用の入力。
- `results/<label>/`: ケース別指標、固定回数・ビルドの識別情報、集計。
- `analyze.py`: 六枚の全720順序から最小帰還辺集合を求める。`pair-cycles.json` に各選択対の集合を残す。
- `window-overlap.json`、`vertex-cycles.json`: 除去窓の共有と、帰還頂点集合の解析。
- `verify.cpp`、`verify_sparse.cpp`: 七枚の費用と合法経路の独立な検算。
- `test_gate.py`: 公式テスターと既存 `scripts/replay.py` による可視性・表示・得点の検査。研究用の固定回数検査である。
- `write_report.py` → `finalize_report.py` の順で実行すると、保存した数値から報告書の表を再作成する。

再実行で作られた実行ファイルと大きな出力は、検査後に削除する。結果の全ては本ディレクトリに保存し、共通の評価スクリプトや履歴を変更しない。
