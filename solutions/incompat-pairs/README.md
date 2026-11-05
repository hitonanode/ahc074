改良元: solutions/esw-clean

不整合対と、既存の紙による修復の採算を調べる研究用ディレクトリ。
`main.cpp` は比較元をそのまま保存したもの。提出用の動作は変えていない。
CLOCK_SCALE、LOCAL_BENCH、DesignStore、全ログ・実験設定・プロファイラ・段の目印を維持する。

`analyze.cpp` は保存済み設計だけを読む分析器。解法やテスターを再実行しない。
比較器の全720順序から、近い対を整合させるのに除く必要がある窓数を厳密に数える。
また、補助紙を置く前に正しい比較関係の始点をすべて除き、残る窓を既存の商品紙で覆えるかを判定する。
修復を無料と仮定した値や設計モデルの値は、実測スコアと区別して REPORT.md に記す。

分析は `run_analysis.py` で実行する。評価と同じ `runs/.lock` の共有ロックを取得してから計算し、
評価の排他ロックと重ならないようにする。結果はこのディレクトリ内だけに保存する。
新しい対話解法を試す場合は、別の `solutions/incompat-*` ディレクトリに置く。

分析器のビルド（評価が走っていないことを `scripts/pahcer_run.py --status` で確かめる）:

```sh
flock -s /home/sato/ahc074/runs/.lock g++ -std=c++23 -O2 -Wall -Wextra -DLOCAL_BENCH -DCLOCK_SCALE=1.1 solutions/incompat-pairs/analyze.cpp -o solutions/incompat-pairs/analyze
```

ビルドの終了を待ってから実行する。

```sh
python3 solutions/incompat-pairs/run_analysis.py --seeds 0-200 --output counts-200.json
python3 solutions/incompat-pairs/run_analysis.py --seeds 0-32 --model-iters 14900000 --output models-helper-32.json
```

既定の参照元は `--run 20261105-084037_esw-clean` と、同一の設計を保存した
`--design-run 20261105-080311_esw-speed`。全紙の模様の一致と再生の合法性を確認する。
`--model-iters` の指定時は、窓の割り当てを固定し、esw-clean の設計の焼きなまし・
穴埋めの山登り・再割り当てを使って仮想の修復価格を比べる。提出用の計測ではない。

JSON の主な項目:

- `errors_hist[k]`: 近い対のうち、比較器を整合させる最少除外窓数が k の組数。
- `rescuable`: 両商品の側に使える既存の補助紙がある対の数。ハンドルの一致も必要。
- `replay_*`: 基準の保存出力で、補助紙が前の商品紙・可視・移動済みだった頻度。
  `new_moves_sum` は、基準が動かす紙をすべて無料で使った場合にも、補助紙を露出・配置するため新たに動かす必要がある紙数。
- `helper_validation_checks`: 残留グラフによる判定と、720 順序 × 7 挿入位置の総当たりを照合した数。不一致なら停止する。
- `models`: mode 0 は通常の整合対のみ。1～6 は 1 窓を無料～2.5 手で仮想修復、
  7 は 2 窓までを 1 手で仮想修復。8 は既存補助紙を、平均露出費用・配置返却 1.8 手・
  ハンドル被覆 1 窓あたり 0.5 手の割引で価格付け。9 は 8 の露出費用も無料にしたもの。
  8 / 9 の `fee` は配置返却分、1～7 の `fee` は修復の追加分を表す。

模型の紙・列の組み替えで補助紙が消えること、価格付け時の最良の列と実際の配置列が違うことは
mode 8 / 9 では無視する。補助紙側に有利な仮定で、実現可能な計画や厳密な下限ではない。
元の stderr 指標は `main.cpp` にすべて残してあり、分析器は JSON に追加の集計を出す。
