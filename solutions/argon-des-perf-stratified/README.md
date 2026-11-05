改良元: solutions/argon-des-perf-condbound

D2の追加調査。穿孔の色標本数は8、受理係数は0.5。
目標・列ごとに一様分布を等分し、各区間から1個ずつ抽出して並べ替える。
変更窓に対する自目標の条件付き差分と利益上限は基準のまま。
他の設計段、候補順、将来の注文を使わない条件は維持する。

追加指標 `perf_samples` / `perf_weight` は標本数と係数、
`perf_delta_hole` は採用穴の費用増、`perf_predicted_delta` は費用−重み付き利益（手/注文）。
既存のログ・指標・プロファイラ・スイッチ・@paper/@ops・CLOCK_SCALE・LOCAL_BENCH・DesignStore、
段の目印と目次を保持。追加の環境変数はない。
