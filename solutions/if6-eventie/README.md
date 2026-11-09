# if6-eventie: 頭色の確率で、穴の数が同数のときの戻りを両色に等分する

改良元: solutions/d30a-reset6

- `Design::head_probability` は、取っ手 j の穴が x = y（同数）のとき、戻りの需要 reset をすべて色 0 に与えていた（`y > x` が偽）。これを等分（各色 reset/2）にする。
- 使われる所: 穴埋めの山登り（2.0·nt）、再割り当ての ProbabilityHead、穴あけ（2·demands）。焼きなましの hcost（min(x,y) の形）と V の probabilities は変えない。
- 理由: reset6 で戻りの重みが 3 倍になり、同数の取っ手で「頭は必ず色 0」という根拠のない偏りが強くなった。同数は浅い取っ手（穴が少ない）で起きやすい。
