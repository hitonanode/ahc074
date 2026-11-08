改良元: solutions/dcomp-combo-ten

焼きなましのSIMD handle費用の除算を、逆数のNewton補正と商のFMA残差補正で計算する。N0/N1/resetは0〜256の整数なので分子は正確な半整数であり、この範囲の全257^3=16,974,593組を独立の数値検査でGCC/Clangとも元のDIVPSとbit一致と確認した。fast-mathは使わず、加算順と採否は維持する。実際のsolverでも出力同一と時間を測る。scalar qfは変更しない。予算・実験スイッチ・ログ・DesignStoreは元のまま。時間fallbackなし。
