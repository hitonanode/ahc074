# 最終候補の3倍時計検査

main.cpp: 498719 bytes。

## この作業での保存結果

main.cpp: **498719 bytes**。全評価はpahcer_run.py、ビルドと分析は共有flockで直列化した。

### 20261106-195606_nogen-floor-prekeep-clock3

500 seed、WA 0件、主注文平均 11224.912000。通常評価。
保存SOTA比: +8.45721402 ± 0.05515493 %、0/0/500（500件）。
通常core-post5比: +7.92753259 ± 0.05351122 %、0/0/500（500件）。
req_sec: 平均 0.171368、p99 0.257993、最大 0.280544秒、2秒超 0件。
end_sec: 平均 1.712062、p99 1.803170、最大 1.867340秒、2秒超 0件。
product_only_design_failed: 平均 0.000000、最大 0.000000、非0 0件。
inverse_initialization_ok: 平均 1.000000、最大 1.000000、非0 500件、0は0件。
audit_owner_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_unowned_papers: 平均 0.000000、最大 0.000000、非0 0件。
audit_cap_violations: 平均 0.000000、最大 0.000000、非0 0件。
audit_product_papers: 平均 191.000000、最大 191.000000、非0 500件。
self_wrong: 平均 0.000000、最大 0.000000、非0 0件。
light_requests: 平均 952.094000、最大 1024.000000、非0 500件。
op_label_errors: 平均 0.000000、最大 0.000000、非0 0件。

外部負荷（meta）: `{"mean_cores": 0.08, "max_cores": 0.29, "interval_sec": 2.0, "seconds": 29.0}`。

## 判断

通常設計から500件、WA・product_only_design_failed・所有色違反・無所有紙・cap違反はいずれも0。inverse_initialization_ok=0も0件。初期所有者1窓不一致の1件は修復され、初期化は成功。end_sec最大1.867340秒。通常同500件比+7.954948±0.053604%、平均11224.912。保存出力の独立監査95500枚も違反0。
