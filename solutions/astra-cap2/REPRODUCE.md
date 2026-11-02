# 再現手順

カレントディレクトリは worktree のルート。新しい記録・実行ファイルは `solutions/astra-cap2/` 内だけに作る。公式 tester と `/home/sato/ahc074/tools/in/` を使い、共通の評価履歴は変更しない。

提出候補 2 本の GCC / Clang ビルド、公式テスターによる 64 ケース比較、初期設置 1 手の削減の固定回数検査、公式スコアと出力手数の照合:

```sh
python3 solutions/astra-cap2/validate_delivery.py
```

研究用バイナリを全て再構築:

```sh
python3 solutions/astra-cap2/build_research.py
```

キャップ枚数と汎用窓の模型比較（各 64 ケース）:

```sh
python3 solutions/astra-cap2/bench.py --label grid-model-64 --model \
  --fixed 400000,100000,20000000,30000 --seeds 24:88 --threads 8 \
  --bins c1g38=solutions/astra-cap2/work/research-c1g38 \
  c0g38=solutions/astra-cap2/work/c0g38 c0g39=solutions/astra-cap2/work/c0g39 \
  c1g39=solutions/astra-cap2/work/c1g39 c2g37=solutions/astra-cap2/work/c2g37 \
  c2g38=solutions/astra-cap2/work/c2g38 c2g36=solutions/astra-cap2/work/c2g36 \
  c2g37mixed=solutions/astra-cap2/work/c2g37mixed \
  c1w2g37=solutions/astra-cap2/work/c1w2g37 c3g36=solutions/astra-cap2/work/c3g36
```

この模型出力を作った後、汎用紙とキャップの兼務の調査は `run_shared.py`、比較を疎にした兼務の調査は `run_sparse.py`。余分な共有対と 5 枚比較器の調査は `sweep.py`。実行は各スクリプトを順番に行い、複数の評価を同時に起動しない。

`cause_probe.cpp` は `work/grid-model-64/c0g39-*.out` を引数として読み、汎用窓を 1 つ解放する反実仮想の CSV を出す。`selector_check.py` は小さな全列挙の検査。全模型は商品一覧だけを使い、注文列を設計に使わない。

`bench.py --model` は解法の stdout を設計ダンプとして保存し、通常モードは公式 tester を介して注文を 1 つずつ渡す。`--fixed` は研究用で、提出候補の通常計測には指定しない。比較の ± はケースを単位とした標準誤差。

終了後に `work/` を削除すると、実行ファイルと大きな出力を除去できる。最終ソースは `main.cpp` と `cand2/main.cpp`。その他の C++ は棄却したものも含む研究用の保存ソースである。
