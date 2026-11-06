# 粗い設計を選んでから列を改善する模型

main.cpp: 490597 bytes。

完全な再出発3つを1024注文で選ぶと、128設計で独立4096注文に+0.036730±0.006577手/注文の潜在利得があった。残り差の大きな割合だが、複数の完全設計を実装する時間はない。75kの窓探索と1Mの列探索で選別し、選択後の9.5M列探索にも利得が残るかを先に検査する。

## この作業での保存結果

main.cpp: **490597 bytes**。全評価はpahcer_run.py、ビルドと分析は共有flockで直列化した。

### 20261106-200109_nogen-coarse-select-model

64 seed、WA 0件、主注文平均 10372.875000。保存設計上の注文比較。
req_sec: 平均 0.638988、p99 0.725903、最大 0.725903秒、2秒超 0件。
end_sec: 平均 1.489292、p99 1.682150、最大 1.682150秒、2秒超 0件。
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
|study_coarse_h1024_gain|-0.012432098 ± 0.010853223|64|
|study_coarse_h1024_selection_gain|+0.012477867 ± 0.006921804|64|
|study_coarse_h1024_selection_sec|+1.400064063 ± 0.013202294|64|
|study_coarse_h128_gain|-0.017284402 ± 0.011578611|64|
|study_coarse_h128_selection_gain|+0.007625573 ± 0.006957136|64|
|study_coarse_h128_selection_sec|+0.229203922 ± 0.002528690|64|
|study_coarse_h256_gain|-0.012615199 ± 0.010546826|64|
|study_coarse_h256_selection_gain|+0.012294767 ± 0.007218762|64|
|study_coarse_h256_selection_sec|+0.394217797 ± 0.004127954|64|
|study_coarse_h512_gain|-0.006019596 ± 0.010060035|64|
|study_coarse_h512_selection_gain|+0.018890372 ± 0.007431505|64|
|study_coarse_h512_selection_sec|+0.729100203 ± 0.007166342|64|
|study_coarse_h64_gain|-0.011379233 ± 0.011517218|64|
|study_coarse_h64_selection_gain|+0.013530720 ± 0.006475701|64|
|study_coarse_h64_selection_sec|+0.147085219 ± 0.001741982|64|
|study_coarse_oracle_gain|+0.013320920 ± 0.009473933|64|
|study_coarse_owner_bad|+0.000000000 ± 0.000000000|64|
|study_coarse_setup_sec|+0.447005156 ± 0.003545926|64|
|study_coarse_single_gain|-0.024909975 ± 0.011271777|64|
|study_coarse_total_sec|+10.795395469 ± 0.055545346|64|
|study_fine_setup_sec|+1.011583047 ± 0.006541889|64|

外部負荷（meta）: `{"mean_cores": 0.095, "max_cores": 0.32, "interval_sec": 2.0, "seconds": 31.8}`。

## 判断

窓75kは基準乱数だけで−0.024910±0.011272手/注文。2粗候補の1024注文選択後でも基準から−0.012432±0.010853で改善なし。選択の上界（検証結果を見て良い方を選ぶoracle）は+0.013321±0.009474で未確定。窓探索を減らしすぎているため、300kの対照で切り分けた。
