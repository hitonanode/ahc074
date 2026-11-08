改良元: solutions/legal-tie-fast

窓探索から独立な 2 系統を実行し、V で完成設計を選ぶ。各系統は map と gopt と総 anneal を半分にし、2 枝＋2 refinish。合計の反復数、通常 finishing 4 回と refinish 4 回は元と同じ。初期列順の DP は最終候補だけに適用。dc_map_chosen は選ばれた系統、dc_total_design_sec は両系統の合計時間。

注文処理は改良元と同一。固定反復回数で動作し、時間による省略はしない。
