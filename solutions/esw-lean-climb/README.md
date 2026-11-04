# esw-lean に as6-canon の穴埋め山登りを戻した版（esw-lean-climb）

改良元: solutions/esw-lean

esw-lean と同じく post-prune を外し、head-design の穴埋め山登りの代わりに solutions/as6-canon の山登り（solutions/abl-head-climb と同じもの）を置いた版。esw-lean（山登りなし）と比べて、山登り自体が要るかを見るための対照。

- 山登り（filler_climb、焼きなましの後〜1.26 秒。焼きなましの締切は esw-tidy と同じ 1.205 秒）: 同じ種類（対どうし・単独どうし）で両方の取っ手の色が変わらない 2 単位の列を交換し、模型の費用 − 0.3 × 穴埋めの代理値が下がれば受理する。代理値は、各目標について、その列より深い各列の全単位の穴埋め利益（canon_filler_gain: 覆う穴の範囲で取っ手の色が違う確率の和 − 3、0 以上。取っ手の色の確率は穴の数だけから）の平均の和。
- 固定反復（MAP_ITERS・GOPT_STEPS・ANNEAL_ITERS・CLIMB_ITERS）で、山登りの受理数と代理値が solutions/abl-head-climb と一致することを確かめた。
- 環境変数 CLIMB_ITERS と stderr の climb_iters・climb_accepted・proxy_before・proxy_after・climb_end_sec は esw-tidy と同じ意味。
