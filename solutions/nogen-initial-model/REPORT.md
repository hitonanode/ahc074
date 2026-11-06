# 初期積層で失われた多数色先頭

main.cpp: 505876 bytes。

SOTAの印刷は列の取っ手要求の多数色を先頭にするが、v6のdesign_controlsは先頭白・次黒に固定している。通常の紙番号入替は同点候補順まで変えるため、模型では内部番号を保って初期順序だけ変える。期待利得は最初の数十注文に数～十数手/ケースで、全体約0.05～0.15%の規模。

## 測定結果

`20261106-160426_nogen-initial-model`、保存設計64件。studyのgainは手/注文で正が改善。平均±SEを示す。

|指標|平均|SE|
|---|---:|---:|
|study_initial_total_sec|5.08964469|0.04022824|
|study_initial_v0_changed|0.00000000|0.00000000|
|study_initial_v0_early_saved|0.00000000|0.00000000|
|study_initial_v0_gain|0.00000000|0.00000000|
|study_initial_v1_changed|26.12500000|0.50958083|
|study_initial_v1_early_saved|4.62500000|0.53009620|
|study_initial_v1_gain|0.00251007|0.00028230|
|study_initial_v2_changed|128.20312500|0.92399122|
|study_initial_v2_early_saved|5.07812500|1.12671930|
|study_initial_v2_gain|0.00251007|0.00096185|
|study_initial_v3_changed|129.53125000|0.96875000|
|study_initial_v3_early_saved|5.01562500|1.10632475|
|study_initial_v3_gain|0.00225067|0.00092824|

未来注文は使用せず、実際の印刷と注文処理は保存設計のまま。模型の所有色検査・採用提案の補完証明・表示検査を通過した。
