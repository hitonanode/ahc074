# astra-triples（設計プローブ）

改良元: なし。提出用解法ではなく、`imp-gla` が生成した汎用6紙を固定して3商品1枚共有の実現性を全列挙する解析。

`probe.cpp INPUT OUTPUT` は、2商品間の互換グラフの三角形を列挙し、3商品全体の相違窓を穴とした紙について、各商品の要求する比較関係が非巡回か調べる。さらに、汎用層以外に3商品で一致するハンドル窓があることを確認する。三角形であることだけでは十分でないため、3商品の共通の穴集合上で改めて検証する。

紙1枚で3商品を表示できても、穴の増加や取得費用を含めた有利さは保証しない。出力は表現可能性の測定であり、提出解法のスコアではない。

`results.csv` の基準は `20261101-073201_imp-gla` のcase 0〜15。入力は公式seedと異なる `astra-generated-v1` で、`solutions/astra-eval/prepare.py` が作る独立ディレクトリで再生成できる。プローブが読む汎用6枚だけを `reference-generic/` に保存したので、時計に依存する基準設計を再実行せず追試できる。入力と保存した汎用紙のSHA256は `reference_manifest.json` にある。

```sh
g++ -std=c++23 -O2 solutions/astra-triples/probe.cpp -o /tmp/astra-triples-probe
/tmp/astra-triples-probe tools/in/0000.txt solutions/astra-triples/reference-generic/0000.txt
```
