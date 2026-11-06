# 評価記録

## この作業での保存結果

main.cpp: **487317 bytes**。全評価はpahcer_run.py、ビルドと分析は共有flockで直列化した。

### 20261106-182807_nogen-control-value3

500 seed、WA 0件、主注文平均 10369.366000。保存設計上の注文比較。
固定設計基準core-post5比: +0.00006623 ± 0.00172441 %、235/3/262（500件）。
req_sec: 平均 0.651972、p99 0.739949、最大 0.795864秒、2秒超 0件。
end_sec: 平均 1.510576、p99 1.642300、最大 1.670030秒、2秒超 0件。
product_only_design_failed: 平均 0.000000、最大 0.000000、非0 0件。
inverse_initialization_ok: 平均 1.000000、最大 1.000000、非0 500件、0は0件。
audit_owner_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_unowned_papers: 平均 0.000000、最大 0.000000、非0 0件。
audit_cap_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_product_papers: 平均 191.000000、最大 191.000000、非0 500件。
self_wrong: 平均 0.000000、最大 0.000000、非0 0件。
light_requests: 平均 0.000000、最大 0.000000、非0 0件。
op_label_errors: 平均 0.000000、最大 0.000000、非0 0件。

外部負荷（meta）: `{"mean_cores": 0.08, "max_cores": 0.39, "interval_sec": 2.0, "seconds": 84.7}`。

## 判断

相対価値反復を増やしても差は2SE未満。1反復を維持。
