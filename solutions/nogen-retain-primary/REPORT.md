# 評価記録

## この作業での保存結果

main.cpp: **493017 bytes**。全評価はpahcer_run.py、ビルドと分析は共有flockで直列化した。

### 20261106-181223_nogen-retain-primary

500 seed、WA 0件、主注文平均 10369.066000。保存設計上の注文比較。
固定設計基準core-post5比: -0.00360161 ± 0.00064380 %、246/105/149（500件）。
req_sec: 平均 0.652439、p99 0.741597、最大 0.751031秒、2秒超 0件。
end_sec: 平均 1.510340、p99 1.642830、最大 1.684600秒、2秒超 0件。
product_only_design_failed: 平均 0.000000、最大 0.000000、非0 0件。
inverse_initialization_ok: 平均 1.000000、最大 1.000000、非0 500件、0は0件。
audit_owner_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_unowned_papers: 平均 0.000000、最大 0.000000、非0 0件。
audit_cap_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_product_papers: 平均 191.000000、最大 191.000000、非0 500件。
self_wrong: 平均 0.000000、最大 0.000000、非0 0件。
light_requests: 平均 0.000000、最大 0.000000、非0 0件。
op_label_errors: 平均 0.000000、最大 0.000000、非0 0件。

外部負荷（meta）: `{"mean_cores": 0.063, "max_cores": 0.22, "interval_sec": 2.0, "seconds": 56.5}`。

## 判断

前主紙もヘルパー候補に含めると固定500×2で約0.004%改善。same-primaryと統合したretain-stackへ引き継ぐ。
