# 評価記録

## この作業での保存結果

main.cpp: **490159 bytes**。全評価はpahcer_run.py、ビルドと分析は共有flockで直列化した。

### 20261106-182703_nogen-helper-access-model

64 seed、WA 0件、主注文平均 10372.875000。保存設計上の注文比較。
req_sec: 平均 0.664518、p99 0.801255、最大 0.801255秒、2秒超 0件。
end_sec: 平均 1.516464、p99 1.732580、最大 1.732580秒、2秒超 0件。
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
|study_demand_max|+1.878906250 ± 0.057995457|64|
|study_demand_total|+25.880859375 ± 0.407283005|64|
|study_demand_total_sec|+10.758842031 ± 0.072848264|64|
|study_demand_train_sec|+1.353111563 ± 0.013667681|64|
|study_demand_v0_gain|-0.000816346 ± 0.000999250|64|
|study_demand_v1_gain|-0.000885009 ± 0.001256738|64|
|study_demand_v2_gain|-0.004379277 ± 0.001566323|64|
|study_demand_v3_gain|-0.000625610 ± 0.001015709|64|
|study_demand_v4_gain|-0.000740053 ± 0.001293015|64|
|study_demand_v5_gain|-0.004081727 ± 0.001511194|64|

外部負荷（meta）: `{"mean_cores": 0.046, "max_cores": 0.175, "interval_sec": 2.0, "seconds": 31.9}`。

## 判断

64保存設計。新規に列から取ったヘルパーだけ数えると需要は0.1011回/注文、保持総量の0.5315より大幅に小さい。6係数案の独立再生で改善は確認できず、学習をオンラインへ入れない。
