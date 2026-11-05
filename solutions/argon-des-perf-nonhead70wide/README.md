改良元: solutions/argon-des-perf-gaincache

基準のheadへの穿孔を係数0.7で終えた後、各列・色の2番目の紙も穿孔候補にする。
2番目の紙の露出確率を0.125、headを残りの確率とする固定した紙ID標本を使う。
色は独立の8標本、owner側の色条件付けと上限、差分キャッシュは基準と同じ。
追加段でも係数0.7を使う。headは最初の設計で一度だけ決める。

追加のd2_trials/viable/acceptedは第2段の候補・事前評価通過・受理数。
d2_cost_delta/profit_delta/corrected_deltaは穴コスト・未補正利益・補正利益の変化（手/注文）。
d2_secは追加段の時間。追加の環境変数はない。
全既存ログ・@paper/@ops・プロファイラ・予算スイッチ、CLOCK_SCALE、LOCAL_BENCH、
DesignStore、段の目印と目次を保持する。
