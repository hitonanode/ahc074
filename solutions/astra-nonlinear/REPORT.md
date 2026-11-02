# 一般印刷規則の局所検証

## 検証内容

`check.cpp` は固定乱数 seed 1701 で各 32 個の `1` を持つ 256 目標を生成し、
6 枚・36 窓の汎用層に 1 sweep の規則探索を行う。探索後の構成と、さらに
非 witness 窓に 4 枚 2:2 の規則を強制した構成の二つを検査する。

差分 26 窓以下の全目標対について、720 順列の表示を紙の不透明部分と色から
直接合成し、前計算した表示と比較する。その表示から両目標の許容順列集合を
直接列挙し、`compatible` と `satisfying` の結果を検査する。

一部の互換な対については、全始点から許容終点集合への最短距離の直接最小値と、
逆向き距離球の和集合から計算した距離和を比較する。復元した経路の長さが最短距離に
一致し、各移動で紙が可視であり、最終表示が要求を満たすことも検査する。

## 再現

```sh
g++ -std=c++23 -O2 -DCLOCK_SCALE=1.1 solutions/astra-nonlinear/check.cpp -o solutions/astra-nonlinear/check-report
solutions/astra-nonlinear/check-report
```

出力全文は `verification.json`。終了コード 0、assertion failure なし。

```text
rule_candidates = 2919
rule_accepted = 13
rule_four = 1
rule_six = 0
rule_cost_sets = 8390
checked_pairs = 6818
checked_paths = 530
```

`checked_pairs` は二つの構成を通じた検査回数であり、異なる入力ケース数ではない。
この乱数初期配置における規則探索の代理費用の改善を、調整済み基準解法に対する
得点の改善と解釈してはならない。実スコアの比較は別途行う。
