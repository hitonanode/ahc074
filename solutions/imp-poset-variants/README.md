# imp-lean の研究版 (NOT FOR MERGE)

共有ソース `experiment.cpp` は `solutions/imp-lean/main.cpp` の
[固定ベース df74cd2d](https://github.com/hitonanode/ahc074/commit/df74cd2d8255b2f68d5c815a88b55238899177ec)
を複製し、実験可能な定数と近傍BFSを追加したものです。

`imp-lean/main.cpp` 自体は変更していません。各 `main.cpp` は
`#define` 設定を指定して、この `experiment.cpp` を取り込む薄いラッパーです。

| マクロ | 意味 |
| --- | --- |
| `IMP_GENERIC_M` | 汎用紙の枚数（6, 7, 8） |
| `IMP_GENERIC_G` | 汎用窓の数（36, 38, 44） |
| `IMP_NEAR_CACHE` | 汎用紙順序の距離2近傍の事前計算・紙番号の再対応を使用 |
| `IMP_DUAL_MEAN` | 共有する両商品の平均費用を評価 |

例（リポジトリのルート）:

```bash
g++ -std=c++23 -O2 -DCLOCK_SCALE=1.1 \
  solutions/imp-poset-cached7-38/main.cpp -o /tmp/imp-cached7
```

7/8枚では6枚用の全距離表を構築せず、設計評価は56/64の開始順序標本で
`Comparator::plan` の最短手数を計算。補助紙の探索は現在状態の距離2近傍に制限。

**重要**: 本コードは今回のPR作成時に原版から再構成した実験用参考コードです。
前回のローカル比較で測ったバイナリと同一である保証はなく、このPR内のファイルで
表のスコアを再測定していません。詳しくは
[`analysis/imp_lean_verification/README.md`](../../analysis/imp_lean_verification/README.md)
を参照してください。
