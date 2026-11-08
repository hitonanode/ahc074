改良元: solutions/legal-tie-fast

filler climbでは、各targetとdonorの現在の寄与を保存する。climb中の確率は固定なので、交換前の寄与を引くときの再計算を省ける。動いた2 donorと最大4 targetの新しい寄与だけを計算し、受理時だけ保存値を更新する。元の浮動小数点演算順序と乱数列を保つ。この変更だけの版はdcomp-climb-cache。

短縮した時間で、最良の完成割当から穴を引き継ぐ仕上げを1回追加する。既存の8候補を保持したまま9候補からVで選ぶ。追加候補はfiller climbと最初のrematchを省き、穿孔と後段rematchを通常どおり行う。追加候補のsaltは8。初期列順DPは最後に選んだ設計へ1回だけ適用する。

map450k、gopt133k、annealの反復数・温度と既存8候補は元のまま。すべて固定回数で、時刻による打切り・候補数変更・軽い注文処理はない。注文処理はlegal-tie-fastと同一。

既存のログ・@paper/@ops・実験スイッチ・プロファイラ・DesignStoreを保つ。dv_candidatesは9、dv_chosenは選んだ候補の番号0–8。保存される設計はVで選んだ最終設計。標準runnerの24並列で比較する。
