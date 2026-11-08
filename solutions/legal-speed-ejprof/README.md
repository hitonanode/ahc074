# legal-speed-ejprof（取り出し（eject_repairs）の中の時間の内訳を測る版）

改良元: `solutions/legal-speed-prof`。出力は legal-tie-fast と同じ（測るだけ）。提出用ではない。

- 取り出しの 2 手の組ごとの準備（試行の列・最後の並び・表示と上 2 層の持ち主）の時間 `ej_setup_ms`、表示がずれた組の直す紙の候補のループ（生き残った候補の処理を含む）の時間 `ej_loop_ms`、組の数 `ej_pairs`、ループに入った組の数 `ej_loops`、生き残った候補ごとの処理（evaluate を含む）`cfprof_ej_surv_*`。
