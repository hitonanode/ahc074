# 窓・ペア・列の同時近傍

main.cpp: 510181 bytes。

固定ペアで窓を動かす近傍はほぼ空だったので、移動所有者の一括再割当で実行可能性を修復する。全商品の通常フィラー価値を使うが、背景ヘルパー価値はまだ静的式に含めず、全注文処理の独立再生で測る。試行予算は本番へ移す前の潜在利得測定用。

初回模型run 20261106-154450 は、列を動かした後も旧紙番号順を保ったため初期積層が崩れ、模型再生で失敗した。正式比較前に列順・同色順の再印刷へ修正した。修正後 main.cpp: 510181 bytes。

## 測定結果

`20261106-154533_nogen-jointwindow-model`、保存設計32件。studyのgainは手/注文で正が改善。平均±SEを示す。

|指標|平均|SE|
|---|---:|---:|
|study_jointwindow_candidates|1.09375000|0.06896959|
|study_jointwindow_chosen|-0.53125000|0.08962708|
|study_jointwindow_design_sec|0.12454013|0.00486383|
|study_jointwindow_model_gain|0.00000000|0.00000000|
|study_jointwindow_owner_bad|0.00000000|0.00000000|
|study_jointwindow_rejected|23.90625000|0.06896959|
|study_jointwindow_selected_gain|-0.00515747|0.00725766|
|study_jointwindow_static_gain|-0.00581360|0.00869701|
|study_jointwindow_total_sec|3.05033000|0.10348603|

未来注文は使用せず、実際の印刷と注文処理は保存設計のまま。模型の所有色検査・採用提案の補完証明・表示検査を通過した。
