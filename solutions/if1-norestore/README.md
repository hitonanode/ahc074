# if1-norestore

改良元: solutions/dcomp-combo-dual30

設計の焼きなましで、各段の終わりにその段の最良状態へ戻す処理を、anneal() の最後の段だけにする（途中の段は現在の状態のまま続ける）。dv_best・model_cost を代理指標にした probe。
