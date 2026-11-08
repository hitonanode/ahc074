改良元: solutions/dcomp-stack-b

Vのcover期待値のDPで、先頭費用dp[lo]が厳密に増える位置だけを次の候補にする。dpが同じ区間ではsavingは減る一方なので最初の位置に勝てない。最初のlo、元の同点選択、gainのdouble演算は維持し、飛ばした区間のwrong bit数だけ整数savingから引く。検証版は全sampleで旧DPを再計算し、各dpのdouble bitとprev/picked/depthを照合する。

設計候補・Vの式・注文予算・乱数は不変。固定予算、ログ・実験スイッチ・DesignStoreを維持、時間fallbackなし。
