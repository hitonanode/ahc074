# 背景ヘルパー需要の実計画による推定

main.cpp: 489980 bytes。

通常の全商品の補完は背景だけで成立するため、現行ng_add_helper_demandは追加需要をほとんど与えない。しかし実プランは背景補助紙を使う。代理的な被覆率ではなく、独立注文の実際の使用頻度で重みを学習したときの潜在利得を測る。

## この作業での保存結果

main.cpp: **489980 bytes**。全評価はpahcer_run.py、ビルドと分析は共有flockで直列化した。

### 20261106-182416_nogen-helper-demand-model

64 seed、WA 0件、主注文平均 10372.875000。保存設計上の注文比較。
req_sec: 平均 0.648557、p99 0.752270、最大 0.752270秒、2秒超 0件。
end_sec: 平均 1.500673、p99 1.687300、最大 1.687300秒、2秒超 0件。
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
|study_demand_max|+5.300781250 ± 0.117874762|64|
|study_demand_total|+136.068359375 ± 1.008412384|64|
|study_demand_total_sec|+10.561625469 ± 0.060931473|64|
|study_demand_train_sec|+1.320434844 ± 0.011116272|64|
|study_demand_v0_gain|-0.002716065 ± 0.003259381|64|
|study_demand_v1_gain|-0.003395084 ± 0.003801850|64|
|study_demand_v2_gain|-0.007110595 ± 0.004219441|64|
|study_demand_v3_gain|-0.002426149 ± 0.003170584|64|
|study_demand_v4_gain|-0.003265382 ± 0.003729323|64|
|study_demand_v5_gain|-0.006301883 ± 0.004359458|64|

外部負荷（meta）: `{"mean_cores": 0.062, "max_cores": 0.265, "interval_sec": 2.0, "seconds": 31.6}`。

## 判断

保持されている背景ヘルパーを需要に数えると、前主紙や前から出ている紙の再利用を新規アクセスとして重複計上する。結果も改善なし。修正したhelper-access-modelを参照。
