# deval-vmix

改良元: `solutions/deval-vclean`。

後半 4 分岐の generic ペア費用をそれぞれ 1.0 / 1.15 / 0.85 / 1.30 倍として、違う傾向の候補を作る。倍率は開始時に費用表へ掛けるため、焼きなまし内側の更新処理は親と同じ。仕上げの前に元の表を正確に戻し、V16 で完成候補を選ぶ。`DEVAL_GENERIC_SPREAD` は倍率間隔（既定 0.15）。`DEVAL_REHEAT` は第 2 候補以降の開始温度倍率で、最後に 1 へ戻す（既定 1）。

反復数・仕上げ・時間ガード・保存形式は親と同じ。生成は `solutions/deval-vselect/make_mix.py`。
