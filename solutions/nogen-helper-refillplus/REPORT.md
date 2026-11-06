# 再利用を追加候補にする

main.cpp: 488888 bytes。前案は全回収候補を失うため悪化した。通常候補を維持して追加効果を切り分ける。

## この作業での保存結果

main.cpp: **488888 bytes**。全評価はpahcer_run.py、ビルドと分析は共有flockで直列化した。

### 20261106-185538_nogen-helper-refillplus

500 seed、WA 0件、主注文平均 10368.500000。保存設計上の注文比較。
固定設計基準core-post5比: -0.00943025 ± 0.00214679 %、293/1/206（500件）。
req_sec: 平均 0.698742、p99 0.789158、最大 0.803967秒、2秒超 0件。
end_sec: 平均 1.557406、p99 1.708390、最大 1.729200秒、2秒超 0件。
product_only_design_failed: 平均 0.000000、最大 0.000000、非0 0件。
inverse_initialization_ok: 平均 1.000000、最大 1.000000、非0 500件、0は0件。
audit_owner_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_unowned_papers: 平均 0.000000、最大 0.000000、非0 0件。
audit_cap_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_product_papers: 平均 191.000000、最大 191.000000、非0 500件。
self_wrong: 平均 0.000000、最大 0.000000、非0 0件。
light_requests: 平均 0.000000、最大 0.000000、非0 0件。
op_label_errors: 平均 0.000000、最大 0.000000、非0 0件。

外部負荷（meta）: `{"mean_cores": 0.067, "max_cores": 0.28, "interval_sec": 2.0, "seconds": 58.4}`。

## 判断

通常計画を維持した追加なら−0.009430±0.002147%。ただしreq約+0.05秒を使い、現G36の時間余裕を超える。より効果の大きいprejoint/preone/pretwoを優先する。
