# 構造の研究用模型

改良元: なし（提出用解法ではなく、`solutions/imp-combo` と保存済み出力を対象にした研究）。

目的は、現在の約 10.43 手/注文から 0.3 手以上を減らす構造を探し、安い模型で反証すること。結論と測定条件は `REPORT.md`、数値の要約は `SUMMARY.json`、ケースごとの整数手数は `cases.csv` と `controllers.csv` に記す。未来の注文は保存済み方策の分析・評価にだけ使い、模型のオンライン意思決定には渡さない。

ファイルの生成・変更はこのディレクトリ内に限定する。既存評価の再生では Python のバイトコード生成を禁止する。提出評価・共通履歴の更新は行わない。

## 模型と主な設定

- `capped_mdp.cpp`: 専用六枚と不動の外部層、三ハンドル、5040状態の平均費用問題。主設定は内部注文確率0.18、Bellman残差幅1e−8。移動には可視性を要求し、表示だけでなく指定紙の取り出しと後の回収を数える。
- `long_module.cpp`: 実際の長い列を全枚数残す局所模型。外部層は動かせない。幅64、将来アクセス費用の係数1.0、最大探索深さ90。全商品を先に表示可能性検査し、オンライン処理は現在の注文だけを見る。出力CSVの `internal_moves` / `external_moves` は内部紙を要求する注文／外部注文での移動総数。`constructive_used` は合法な初期構成経路が選ばれた回数で、失敗を捨てた数ではない。
- `routing_search.py` / `validate_routing.py`: 色の値に応じた取り出し窓の探索と固定候補集合の検査。選択用模擬注文384、実注文1024。候補を作ったseed 0〜3と、評価用seed 4〜39を分ける。候補集合は `validate_routing.py` の `POOL`。
- `resident_probe.py` / `validate_resident.py`: 既存二枚を常駐の修復紙へ兼用。一列を私有窓にし、失った列の紙を再分配する。
- `borrowed_port.py`: 一列を失わず、汎用窓を一個転用。転用窓の全注文での色修復と、六枚の合法順序グラフでの汎用操作の差を数える。
- `measure.py` / `project_module.py` / `background.py`: 保存済み出力の費用・列外への穴埋め・白背景の使用可能性の計測。
- `controller_audit.py` / `verify_model.py`: 模型の操作列を `scripts/replay.py` で独立再生し、補助紙の仕事を分類する。
- `physical_feasibility.py`: 全192枚・64窓で全256商品の表示可能性を検査。
- `physical_trace.py` / `physical_replay.py` / `serve_output.py`: 全28ハンドル模型へ実際の六枚の汎用紙を戻し、先頭64注文の具体的な操作列を独立再生と公式テスターで照合する。短縮入力への生成済み出力の再送であり、提出解法の性能評価ではない。

模型は提出用の速度ではない。比較実験は固定幅・固定注文数で行い、実行時間を打ち切りに使わない。長い列の模型の時計には `CLOCK_SCALE`（既定1.0）を掛ける。乱数は全て定数種を使う。Pythonのドライバは最大4個のC++子プロセスを使い、以下を順に実行すれば同時プロセス数は12未満。

## 再現

リポジトリのルートで実行する。保存済み run と入力2000件が同じパスに必要。標準ライブラリだけを使い、numpyは不要。

```sh
g++ -std=c++23 -O2 solutions/astra-struct/capped_mdp.cpp -o solutions/astra-struct/capped_mdp
g++ -std=c++23 -O2 solutions/astra-struct/long_module.cpp -o solutions/astra-struct/long_module
solutions/astra-struct/capped_mdp fixed 0 0 > solutions/astra-struct/capped_000.csv
solutions/astra-struct/capped_mdp fixed 0.18 30 > solutions/astra-struct/capped_018.csv
solutions/astra-struct/capped_mdp fixed 0.30 0 > solutions/astra-struct/capped_030.csv
python3 solutions/astra-struct/measure.py 0 40
python3 solutions/astra-struct/project_module.py 0 40
python3 solutions/astra-struct/background.py
python3 solutions/astra-struct/validate_routing.py 0 40 --width 64
python3 solutions/astra-struct/validate_resident.py 0 8
python3 solutions/astra-struct/borrowed_port.py 0 8
python3 solutions/astra-struct/controller_audit.py 0 8
python3 solutions/astra-struct/physical_feasibility.py
python3 solutions/astra-struct/physical_replay.py
python3 solutions/astra-struct/summarize.py
```

結果の差は整数の移動数から算出する。時間だけは実行環境に依存する。候補集合を作った探索そのものを追う場合は `routing_search.py SEED --trials 150 --count 256 --width 24` を使えるが、報告の固定候補比較を再現するための前提ではない。

中間JSON、ログ、`work/` 内の入力と操作列、二つの実行ファイルは再現時に生成される。納品状態では、本文・説明・要約・CSV二つとソースだけを残している。
