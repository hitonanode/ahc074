# ペア注文の回収と修復の近傍

main.cpp: 487317 bytes。

pair注文のhelp/fret/fix差を同時に減らす余地を、既存の中立書換えの候補条件だけ変えて測る。固定500設計×2注文列で利得と追加時間を判定する。

## この作業での保存結果

main.cpp: **487317 bytes**。全評価はpahcer_run.py、ビルドと分析は共有flockで直列化した。

### 20261106-190918_nogen-neutral-mixedowners

500 seed、WA 0件、主注文平均 10371.938000。保存設計上の注文比較。
固定設計基準core-post5比: +0.01779955 ± 0.00262002 %、194/2/304（500件）。
req_sec: 平均 0.650618、p99 0.751755、最大 0.762327秒、2秒超 0件。
end_sec: 平均 1.508959、p99 1.654970、最大 1.698300秒、2秒超 0件。
product_only_design_failed: 平均 0.000000、最大 0.000000、非0 0件。
inverse_initialization_ok: 平均 1.000000、最大 1.000000、非0 500件、0は0件。
audit_owner_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_unowned_papers: 平均 0.000000、最大 0.000000、非0 0件。
audit_cap_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_product_papers: 平均 191.000000、最大 191.000000、非0 500件。
self_wrong: 平均 0.000000、最大 0.000000、非0 0件。
light_requests: 平均 0.000000、最大 0.000000、非0 0件。
op_label_errors: 平均 0.000000、最大 0.000000、非0 0件。

外部負荷（meta）: `{"mean_cores": 0.072, "max_cores": 0.549, "interval_sec": 2.0, "seconds": 114.1}`。

## 判断

最終表示の担当が1紙だけでも許す案は約+0.018%悪化。不採用。
