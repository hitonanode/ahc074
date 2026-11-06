# 最終候補の2倍時計検査

main.cpp: 498719 bytes。

## この作業での保存結果

main.cpp: **498719 bytes**。全評価はpahcer_run.py、ビルドと分析は共有flockで直列化した。

### 20261106-194741_nogen-floor-prekeep-clock2

500 seed、WA 0件、主注文平均 10871.812000。通常評価。
保存SOTA比: +5.26169124 ± 0.05765961 %、0/0/500（500件）。
通常core-post5比: +4.73200981 ± 0.04248972 %、0/0/500（500件）。
req_sec: 平均 0.284702、p99 0.345965、最大 0.349793秒、2秒超 0件。
end_sec: 平均 1.702430、p99 1.719560、最大 1.728610秒、2秒超 0件。
product_only_design_failed: 平均 0.000000、最大 0.000000、非0 0件。
inverse_initialization_ok: 平均 1.000000、最大 1.000000、非0 500件、0は0件。
audit_owner_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_unowned_papers: 平均 0.000000、最大 0.000000、非0 0件。
audit_cap_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_product_papers: 平均 191.000000、最大 191.000000、非0 500件。
self_wrong: 平均 0.000000、最大 0.000000、非0 0件。
light_requests: 平均 792.540000、最大 938.000000、非0 500件。
op_label_errors: 平均 0.000000、最大 0.000000、非0 0件。

外部負荷（meta）: `{"mean_cores": 0.08, "max_cores": 0.29, "interval_sec": 2.0, "seconds": 29.0}`。

## 判断

通常設計から500件、WA・product_only_design_failed・所有色違反・無所有紙・cap違反はいずれも0。inverse_initialization_ok=0も0件。end_sec最大1.728610秒。通常同500件比+4.759426±0.042198%、平均10871.812。保存出力の独立監査95500枚も違反0。
