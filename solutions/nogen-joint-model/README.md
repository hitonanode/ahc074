改良元: solutions/nogen-owned-g34

保存設計を使い、背景窓と背景6商品の色を固定したまま、キャップ窓を各ハンドル窓または
元の窓に変え、商品ペア・列・ハンドル順を組み直す測定版。各候補で400万反復の焼きなまし、
3万回のフィラーclimb、4回の再割り当てを行う。将来の注文は使わない。
実際に印刷する紙・注文処理は保存設計のまま。測定は2秒を超えるため記録対象外とする。

study_saved / study_oldcap / study_bestcap の col, hole, gc, merit は、保存設計・元のキャップでの
組み直し・最良キャップの列費用、ハンドル費用、背景費用、フィラー価値を引いた合計（注文あたり）。
study_cap_gain は元のキャップから最良キャップへの模型改善。study_saved_gain は保存設計からの改善。
study_cap_success / window / changed は設計成立候補数、選んだ物理窓、元から変わったか。
study_perf_gain / holes は同じ保存設計での既存穿孔モデルの改善と穴数。study_total_sec は測定時間。
所有監査・DesignStore版2・時計倍率・既存の指標とラベルを維持する。
