# 窓とペア両側・列を同時に変更

main.cpp: 510991 bytes。

片側所有者固定の模型は窓交換24候補のうち23.9候補が不成立だった。この模型は不成立ペアの両端を解放し、全単位を列へ割り当て直す。全商品の通常フィラー価値を含むが、背景ヘルパーは独立注文で検証する。

## 測定結果

`20261106-155151_nogen-jointwindow-free-model`、保存設計32件。studyのgainは手/注文で正が改善。平均±SEを示す。

|指標|平均|SE|
|---|---:|---:|
|study_jointwindow_candidates|4.00000000|0.00000000|
|study_jointwindow_chosen|0.56250000|0.30432865|
|study_jointwindow_design_sec|0.96525419|0.03646138|
|study_jointwindow_model_gain|0.01333504|0.00381450|
|study_jointwindow_owner_bad|0.00000000|0.00000000|
|study_jointwindow_rejected|12.21875000|0.46821206|
|study_jointwindow_selected_gain|-0.04774473|0.01597727|
|study_jointwindow_static_gain|-0.05621334|0.01288031|
|study_jointwindow_total_sec|8.08756875|0.10420883|

未来注文は使用せず、実際の印刷と注文処理は保存設計のまま。模型の所有色検査・採用提案の補完証明・表示検査を通過した。
