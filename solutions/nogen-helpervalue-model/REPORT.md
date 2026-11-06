# 背景ヘルパーを含む先読み価値

main.cpp: 506901 bytes。

背景順序の現在の価値は純背景だけの補完費用で、実際の補助紙による代替を含まない。全商品の単独補助紙を含める模型を作り、完全な独立注文で測る。取得順位の分布は近似なので結果を見ずには採用しない。

## 測定結果

`20261106-155030_nogen-helpervalue-model`、保存設計64件。studyのgainは手/注文で正が改善。平均±SEを示す。

|指標|平均|SE|
|---|---:|---:|
|study_helpervalue_total_sec|5.10491906|0.03174719|
|study_helpervalue_v0_change|0.00000000|0.00000000|
|study_helpervalue_v0_value_sec|0.00000000|0.00000000|
|study_helpervalue_v1_change|0.03295943|0.00104792|
|study_helpervalue_v1_gain|-0.00270081|0.00116818|
|study_helpervalue_v1_value_sec|0.02906885|0.00041241|
|study_helpervalue_v2_change|0.02702592|0.00102155|
|study_helpervalue_v2_gain|-0.00116730|0.00100965|
|study_helpervalue_v2_value_sec|0.02851833|0.00035494|
|study_helpervalue_v3_change|0.01989794|0.00089570|
|study_helpervalue_v3_gain|-0.00035095|0.00071819|
|study_helpervalue_v3_value_sec|0.02685547|0.00032667|

未来注文は使用せず、実際の印刷と注文処理は保存設計のまま。模型の所有色検査・採用提案の補完証明・表示検査を通過した。
