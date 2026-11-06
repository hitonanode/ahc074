# 粗候補選択と窓探索・列探索の予算

main.cpp: 490598 bytes。

75k窓・9.5M列の基準乱数だけでは64設計で−0.024910±0.011272手/注文。選択前に質を落としすぎるため、窓300kへ戻した対照を作る。列4.5Mの再生利得と設計時間を測り、現時間枠へ近づけたときの潜在利得を検査する。

## この作業での保存結果

main.cpp: **490598 bytes**。全評価はpahcer_run.py、ビルドと分析は共有flockで直列化した。

### 20261106-201141_nogen-coarse-col45-model

64 seed、WA 0件、主注文平均 10372.875000。保存設計上の注文比較。
req_sec: 平均 0.632784、p99 0.759910、最大 0.759910秒、2秒超 0件。
end_sec: 平均 1.483028、p99 1.662560、最大 1.662560秒、2秒超 0件。
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
|study_coarse_h1024_gain|+0.002891542 ± 0.007959469|64|
|study_coarse_h1024_selection_gain|+0.016353600 ± 0.006506659|64|
|study_coarse_h1024_selection_sec|+1.334253594 ± 0.012912065|64|
|study_coarse_h128_gain|-0.001625064 ± 0.007847260|64|
|study_coarse_h128_selection_gain|+0.011836991 ± 0.005710995|64|
|study_coarse_h128_selection_sec|+0.222171719 ± 0.002883483|64|
|study_coarse_h256_gain|+0.000011450 ± 0.007895229|64|
|study_coarse_h256_selection_gain|+0.013473505 ± 0.005421711|64|
|study_coarse_h256_selection_sec|+0.378275781 ± 0.004524265|64|
|study_coarse_h512_gain|+0.005683898 ± 0.007455709|64|
|study_coarse_h512_selection_gain|+0.019145949 ± 0.006757986|64|
|study_coarse_h512_selection_sec|+0.695620906 ± 0.007870368|64|
|study_coarse_h64_gain|-0.002189640 ± 0.007962388|64|
|study_coarse_h64_selection_gain|+0.011272415 ± 0.006183715|64|
|study_coarse_h64_selection_sec|+0.143706625 ± 0.002085027|64|
|study_coarse_oracle_gain|+0.024021147 ± 0.006800556|64|
|study_coarse_owner_bad|+0.000000000 ± 0.000000000|64|
|study_coarse_setup_sec|+1.018794781 ± 0.009758722|64|
|study_coarse_single_gain|-0.013462076 ± 0.006392222|64|
|study_coarse_total_sec|+11.407440625 ± 0.046595847|64|
|study_fine_setup_sec|+1.221974219 ± 0.013162516|64|

外部負荷（meta）: `{"mean_cores": 0.052, "max_cores": 0.225, "interval_sec": 2.0, "seconds": 67.3}`。

## 判断

窓300kのまま精列を4.5Mへ減らすと、基準乱数の利得−0.013462±0.006392手/注文。256/1024注文選択後も+0.000011±0.007895 / +0.002892±0.007959で未確定。時間を削ったときの質の損失が選択利得を消し、今回の構成では採用の根拠がない。
