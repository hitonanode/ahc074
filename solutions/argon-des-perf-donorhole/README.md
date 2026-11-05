改良元: solutions/argon-des-perf-gaincache

donor側の差分も、穴を開ける窓の色の両側を計算して条件付けする。
目標紙に穴があって他のdonor区間も影響を受ける場合は、変更前後の全列DPを再計算する。
目標がdonor列の窓を覆う場合は、従来の1列再評価を使う。
受理式と上限には補正差分を加え、元の色標本のキャッシュと差分再構築は維持する。
係数0.7、標本数8、候補順は基準と同じ。未来の注文は使わない。

perf_donor_conditioned / perf_donor_correctionは受理した候補の補正後donor利益と補正量（手/注文）。
perf_donor_changed_samples / perf_donor_full_samplesは評価した標本数と全列DPが必要だった標本数。
追加の環境変数はない。全既存ログ・@paper/@ops・プロファイラ・予算スイッチ、CLOCK_SCALE、
LOCAL_BENCH、DesignStore、段の目印と目次を保持する。
