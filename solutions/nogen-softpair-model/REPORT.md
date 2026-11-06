# 補助紙によるペア制約の緩和

main.cpp: 506986 bytes。

全商品の補助紙価値を含む再割当模型は32件で最大0.0046±0.00235手と未確定だった。背景単独で成立するペアだけという構造制約を緩め、ペア空間を広げる潜在利得を実再生で測る。静的な緩和費用だけでは採用しない。

## 測定結果

`20261106-145816_nogen-softpair-model`、保存設計32件。studyのgainは手/注文で正が改善。平均±SEを示す。

|指標|平均|SE|
|---|---:|---:|
|study_soft_base|10.15595625|0.01392326|
|study_soft_edges|1075.31250000|8.84902919|
|study_soft_total_sec|6.40421594|0.21849446|
|study_soft_v0_changed|9.59375000|2.64417321|
|study_soft_v0_failed_targets|0.00000000|0.00000000|
|study_soft_v0_gain|-0.00012207|0.00257536|
|study_soft_v0_owner_bad|0.00000000|0.00000000|
|study_soft_v0_pairs|0.00000000|0.00000000|
|study_soft_v0_rematch_sec|0.01278693|0.00022949|
|study_soft_v1_changed|21.31250000|4.26714698|
|study_soft_v1_failed_targets|2.46875000|0.48356950|
|study_soft_v1_gain|0.00071716|0.00077390|
|study_soft_v1_owner_bad|0.00000000|0.00000000|
|study_soft_v1_pairs|1.43750000|0.28375897|
|study_soft_v1_rematch_sec|0.01276025|0.00030286|
|study_soft_v2_changed|12.68750000|3.19508112|
|study_soft_v2_failed_targets|0.31250000|0.15185347|
|study_soft_v2_gain|0.00028992|0.00142321|
|study_soft_v2_owner_bad|0.00000000|0.00000000|
|study_soft_v2_pairs|0.21875000|0.08676971|
|study_soft_v2_rematch_sec|0.01330060|0.00031228|
|study_soft_v3_changed|8.56250000|2.43625899|
|study_soft_v3_failed_targets|0.09375000|0.06896959|
|study_soft_v3_gain|-0.00039673|0.00126279|
|study_soft_v3_owner_bad|0.00000000|0.00000000|
|study_soft_v3_pairs|0.06250000|0.04347552|
|study_soft_v3_rematch_sec|0.01325014|0.00026463|
|study_soft_v4_changed|9.18750000|2.50380255|
|study_soft_v4_failed_targets|0.00000000|0.00000000|
|study_soft_v4_gain|-0.00129700|0.00211325|
|study_soft_v4_owner_bad|0.00000000|0.00000000|
|study_soft_v4_pairs|0.00000000|0.00000000|
|study_soft_v4_rematch_sec|0.01347006|0.00025561|

未来注文は使用せず、実際の印刷と注文処理は保存設計のまま。模型の所有色検査・採用提案の補完証明・表示検査を通過した。
