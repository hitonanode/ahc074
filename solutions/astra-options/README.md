# astra-options（表現の分析用）

改良元: なし。提出用解法ではなく、保存済みの紙の設計と出力を分析するプログラム。

`representation_probe.cpp` は、既存設計の汎用6枚の順序720通り、主紙186枚、主紙の挿入位置7通りを列挙する。主紙が不透明なハンドル窓が目標と一致し、汎用窓の最終表示が目標に完全一致する構成だけを数える。三角形の収納とハンドルを任意に直せるという構造の下で、主紙の候補集合は厳密な値である。動作列の費用や実際のスコアを保証するものではない。

同じ主紙でも汎用層の途中へ入れることで汎用紙が誤色を隠せる。現在の解法が固定している「商品ごとの主紙」を変える余地が、既存の紙のままどれほどあるか調べる。未知の注文は使用しない。

## 補助紙による新しい対の表現

- `helper_probe.cpp`: 汎用6枚だけでは表現できない2商品の共通紙について、既存補助紙を汎用層の間に1枚挿入して両商品を表示できるか調べる。`all-columns` は共通紙の配属先を全28列へ広げ、`punch` は補助紙のハンドル上の誤色を穴にする。`punch-single` は加工する補助紙を単独商品用に限る。補助紙自身のハンドルは必ず残す。
- `helper_punch_g_probe.cpp`: ハンドル上の加工に加え、補助紙の汎用窓上の誤色も穴にできる。汎用紙のうち補助紙より上に置く集合64通りを列挙し、順序制約のDAGで表示可能性を正確に検査する。加工後も、その補助紙が元から担当していた全商品を汎用6枚だけで表示できることを確認する。`single-helpers` は補助紙を単独商品用に限る。両商品には別々の補助紙を選ぶ。
- `verify_punch_witnesses.py`: 上のDAG実装とは独立に、汎用紙の全720順序を直接試し、記録した構成の表示・ハンドル・元の商品への適合を確認する。
- `reproduce_summary.py`: 個別の結果CSVから、小さいケース別集計 `coverage.csv` と検証結果 `witness_verification.json` を再生成する。

基準出力は `reference-output/0000.txt`〜`0007.txt` に保存した。元は `runs/20261101-073041_imp-gla/out/`。紙の設計だけでなく操作列も含むため、補助紙の列内順位の平均も再計算できる。入力は公式seedと異なる `astra-generated-v1` で、`solutions/astra-eval/generate.py` によって再生成する。元の公式 `tools/in/` に上書きせず、評価用の独立ディレクトリで実行する。

```sh
g++ -std=c++23 -O2 solutions/astra-options/representation_probe.cpp -o solutions/astra-options/representation_probe
g++ -std=c++23 -O2 solutions/astra-options/helper_probe.cpp -o solutions/astra-options/helper_probe
g++ -std=c++23 -O2 solutions/astra-options/helper_punch_g_probe.cpp -o solutions/astra-options/helper_punch_g_probe
mkdir -p solutions/astra-options/results

# 入力 tools/in/0000.txt は必ず astra-generated-v1 の case 0 を使う。
solutions/astra-options/representation_probe tools/in/0000.txt solutions/astra-options/reference-output/0000.txt

solutions/astra-options/helper_probe tools/in/0000.txt solutions/astra-options/reference-output/0000.txt all-columns
solutions/astra-options/helper_probe tools/in/0000.txt solutions/astra-options/reference-output/0000.txt all-columns punch-single
solutions/astra-options/helper_probe tools/in/0000.txt solutions/astra-options/reference-output/0000.txt all-columns punch

solutions/astra-options/helper_punch_g_probe tools/in/0000.txt solutions/astra-options/reference-output/0000.txt > solutions/astra-options/results/helper-punch-g-0000.csv
solutions/astra-options/helper_punch_g_probe tools/in/0000.txt solutions/astra-options/reference-output/0000.txt single-helpers
python3 solutions/astra-options/verify_punch_witnesses.py tools/in/0000.txt solutions/astra-options/reference-output/0000.txt solutions/astra-options/results/helper-punch-g-0000.csv --samples 200

# 全8件の再計算と小さい集計の保存。既に results/ があるなら --reuse を付ける。
python3 solutions/astra-options/reproduce_summary.py
```

巨大な列挙結果と実行ファイルはgit管理外とし、集計・基準出力・再現コードを保存する。研究結果、正確な条件、費用モデルの限界は `RESEARCH.md` を参照。
