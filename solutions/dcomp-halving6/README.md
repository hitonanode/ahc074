改良元: solutions/dcomp-climb-cache（その元はlegal-tie-fast）

共有prefixは元のまま、その後の総anneal反復数を6枝へ等分する。各枝の未仕上げ設計をVで評価し、上位4枝だけ元のfiller climb・rematch・穿孔・後段rematchまで仕上げる。従来の4回の再仕上げも保ち、完成した8候補からVで最終選択する。Vの学習は変更しない。

すべて固定反復数・固定乱数。生のVは仕上げ後を完全には予測しないため、完成設計の8列リプレイで有効性を判断する。注文処理はlegal-tie-fastのまま。時間による切替なし。dc_screen_secは仕上げ前の6候補の選別時間、@dc_rawbranchは枝番号・生のV・通過フラグ。
