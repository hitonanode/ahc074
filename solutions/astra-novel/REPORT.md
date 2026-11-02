# 疎比較グラフの局所検証

## 検証内容

`graph-check.cpp` は本ディレクトリの `main.cpp` を読み込み、6 枚・36 窓の
比較器から辺 `(0,1)`, `(0,2)`, `(0,3)` を順に取り除いた 4 構成を調べる。
欠けた比較窓は辺 `(4,5)` に置き換える。各構成について 720 順列の全遷移を
調べ、動かす紙の不透明部分が上の紙で完全には覆われていないことと、
記録した距離が 1 であることを検査する。

さらに固定乱数 seed 9981 で 3000 組ずつの始点・終点を選び、復元経路の長さが
BFS 距離と一致し、全操作が合法で、指定した終点へ到着することを検査する。
これは汎用層のグラフの検査であり、コンテスト全体の得点評価ではない。

## 再現

リポジトリのルートで実行する。

```sh
g++ -std=c++23 -O2 -DCLOCK_SCALE=1.1 solutions/astra-novel/graph-check.cpp -o solutions/astra-novel/check-report
solutions/astra-novel/check-report
```

保存した出力は `verification.json`。終了コード 0、assertion failure なし。

```text
verified_generic_transitions = 70260
verified_generic_paths = 12000
```

本体では可視性に基づく汎用層の実グラフを使うが、専用紙設計時の `PosetSums` は
完全比較器を前提にした近似を残している。したがってその設計代理費用は、
欠辺のある汎用層の実コストを過小評価し得る。実スコアの採否は同じ生成ケースを
使った基準解法との対比較で判断する。
