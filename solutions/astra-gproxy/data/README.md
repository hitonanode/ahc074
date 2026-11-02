# 保存した実験記録

- research/features.tsv: seed 24〜87 × MAP_SEED 0〜11 の 768 設計。割り当て終了時の特徴量と最終模型の内訳。analysis.txt / analysis.json に相関・回帰を保存。
- researchsim/features.tsv: 同じ 768 設計に乱数の注文列 4 本ずつを加えた結果。analysis-sim.txt に模擬手数に対する相関・回帰を保存。
- research-summary.json / .txt: 入力を単位とする標準誤差、模型の内訳の回帰、検証入力での予測誤差。summarize_research.py で TSV から再集計できる。
- base、bias003 など: 固定回数の比較。各 seed の JSON は模型費用・模擬手数・誤表示・探索回数など。config.json に係数と回数。summary.tsv の列は seed / MAP_SEED / sim_moves / model_cost / sim_wrong。
- final-fixed: 提出候補の固定回数模擬。集計の高速化前の calib と 64 件すべてで費用・手数・探索回数が一致。
- holdout-base / holdout-calib: 未使用入力 seed 88〜151 の固定回数模擬。
- tester-final: 提出候補の通常ビルドと元の解法の比較。seed ごとの JSON の results の 0 が元、1 が候補。err は公式テスターを含む stderr。config.json に使用したバイナリのハッシュを保存。
- tester-calib: 集計の高速化前の時間制限版。
- fixed_*.txt: 基準に対するケースごとの log 比と標準誤差、模型費用の差。
- final-source.diff: 元の解法との提出ソースの差分。

大きな割り当ての生データ（A、比較器、選んだ対と全候補対の一覧）は削除し、特徴量 TSV を残した。analyze.py の特徴量抽出から再実行する場合は、build_probe.py で研究用ソースを生成し、run_experiments.py の --research（模型のみ）または --env DUMP_MAP=1（模擬込み）で生データを再生成する。
