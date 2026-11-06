# 補助紙としての利用を狙った比較窓の追加穿孔

main.cpp: 492309 bytes。

取っ手の穿孔と異なり、所有者自身の背景要求は増える。一方、補助紙の誤色が減るので他商品の補助に使える。全状態の補完確認と独立注文でこの交換条件を測る。

## この作業での保存結果

main.cpp: **492309 bytes**。全評価はpahcer_run.py、ビルドと分析は共有flockで直列化した。

### 20261106-181931_nogen-payload-hole-model

32 seed、WA 0件、主注文平均 10360.125000。保存設計上の注文比較。
req_sec: 平均 0.652510、p99 0.740306、最大 0.740306秒、2秒超 0件。
end_sec: 平均 1.512414、p99 1.632170、最大 1.632170秒、2秒超 0件。
product_only_design_failed: 平均 0.000000、最大 0.000000、非0 0件。
inverse_initialization_ok: 平均 1.000000、最大 1.000000、非0 32件、0は0件。
audit_owner_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_unowned_papers: 平均 0.000000、最大 0.000000、非0 0件。
audit_cap_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_product_papers: 平均 191.000000、最大 191.000000、非0 32件。
self_wrong: 平均 0.000000、最大 0.000000、非0 0件。
light_requests: 平均 0.000000、最大 0.000000、非0 0件。
op_label_errors: 平均 0.000000、最大 0.000000、非0 0件。

模型の利得は正が改善、単位は手/注文（時間指標を除く）。±はseed間SE。

|指標|平均 ± SE|件数|
|---|---:|---:|
|study_payload_hole_candidates|+6.468750000 ± 0.215266035|32|
|study_payload_hole_design_sec|+0.007610219 ± 0.000260931|32|
|study_payload_hole_gain|-0.003463744 ± 0.001043743|32|
|study_payload_hole_owner_bad|+0.000000000 ± 0.000000000|32|
|study_payload_hole_total_sec|+6.847839375 ± 0.211096130|32|

外部負荷（meta）: `{"mean_cores": 0.046, "max_cores": 0.18, "interval_sec": 2.0, "seconds": 13.0}`。

## 判断

32保存設計。比較窓の追加穴は模型利得+0.022577±0.001893だが、独立再生−0.003464±0.001044手/注文。不採用。
