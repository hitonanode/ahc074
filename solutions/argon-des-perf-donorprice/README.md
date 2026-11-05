改良元: solutions/argon-des-perf-condbound

D2のdonor側の条件付き差分。目標紙がdonor列の窓を覆う場合、その列頭色を反転しても
その列から取る紙の価格しか変わらない。既存DPと1列の辺で両色の差分を求め、色確率で平均する。
他の場合は従来の標本値を使う。自目標の補正、候補順、標本数8、係数0.5は維持する。
受理判定と利益上限にはdonorの補正も入れ、元の標本値のキャッシュはそのまま保持する。

`perf_donor_conditioned` は受理した候補の補正後のdonor利益（手/注文）。
`perf_donor_changed_samples` はdonorの再計算標本数、`perf_donor_conditioned_samples` は補正できた標本数。
追加の環境変数はない。既存ログ・指標・@paper/@ops・プロファイラ・予算スイッチ、
CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印と目次を保持。未来の注文は使わない。
