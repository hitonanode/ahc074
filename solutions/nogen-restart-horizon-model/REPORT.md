# 探索再出発を短い注文再生で選べるか

main.cpp: 490293 bytes。

cap対照模型32件では、同じ物理窓63での3再出発を1024訓練注文で選ぶと独立4096注文に+0.041298±0.012442手/注文。設計3回分も訓練も現時間枠に入らないため、そのうち選択再生を短くできるかを測る。実装の前提となる選別能力の模型であり、このまま提出する案ではない。

## この作業での保存結果

main.cpp: **490293 bytes**。全評価はpahcer_run.py、ビルドと分析は共有flockで直列化した。

### 20261106-195132_nogen-restart-horizon-model

64 seed、WA 0件、主注文平均 10372.875000。保存設計上の注文比較。
req_sec: 平均 0.637177、p99 0.769783、最大 0.769783秒、2秒超 0件。
end_sec: 平均 1.488622、p99 1.697130、最大 1.697130秒、2秒超 0件。
product_only_design_failed: 平均 0.000000、最大 0.000000、非0 0件。
inverse_initialization_ok: 平均 1.000000、最大 1.000000、非0 64件、0は0件。
audit_owner_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_unowned_papers: 平均 0.000000、最大 0.000000、非0 0件。
audit_cap_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_product_papers: 平均 191.000000、最大 191.000000、非0 64件。
self_wrong: 平均 0.000000、最大 0.000000、非0 0件。
light_requests: 平均 0.000000、最大 0.000000、非0 0件。
op_label_errors: 平均 0.000000、最大 0.000000、非0 0件。

模型の利得は正が改善、単位は手/注文（時間指標を除く）。±はseed間SE。

|指標|平均 ± SE|件数|
|---|---:|---:|
|study_restart_failed|+0.000000000 ± 0.000000000|64|
|study_restart_h1024_gain|+0.045223236 ± 0.008540324|64|
|study_restart_h1024_selection_sec|+2.693912812 ± 0.016913089|64|
|study_restart_h1024_train_gain|+0.107254036 ± 0.011592213|64|
|study_restart_h128_gain|+0.025962839 ± 0.010034985|64|
|study_restart_h128_selection_sec|+0.438848438 ± 0.002773589|64|
|study_restart_h128_train_gain|+0.185180648 ± 0.021858550|64|
|study_restart_h256_gain|+0.030227672 ± 0.009865381|64|
|study_restart_h256_selection_sec|+0.762253359 ± 0.005156759|64|
|study_restart_h256_train_gain|+0.163635301 ± 0.018010949|64|
|study_restart_h512_gain|+0.034778612 ± 0.009692432|64|
|study_restart_h512_selection_sec|+1.405546719 ± 0.009748269|64|
|study_restart_h512_train_gain|+0.137878409 ± 0.014805364|64|
|study_restart_h64_gain|+0.020862580 ± 0.010252840|64|
|study_restart_h64_selection_sec|+0.277312703 ± 0.001946167|64|
|study_restart_h64_train_gain|+0.328857344 ± 0.033985222|64|
|study_restart_owner_bad|+0.000000000 ± 0.000000000|64|
|study_restart_setup_sec|+2.359660469 ± 0.017628672|64|
|study_restart_total_sec|+15.514750000 ± 0.062501817|64|

外部負荷（meta）: `{"mean_cores": 0.036, "max_cores": 0.14, "interval_sec": 2.0, "seconds": 44.5}`。

## 判断

64保存設計。通常の要求処理で候補を選ぶと短い訓練でも正の独立利得が残るが、3再出発の設計2.360秒に加えて、4候補の128注文選択0.439秒、1024注文選択2.694秒が必要。このままでは時間枠へ入らない。途中設計の共有などで候補生成そのものを安くする必要がある。
