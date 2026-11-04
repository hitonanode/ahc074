# 穴埋めの山登りと post-prune を外した版（esw-lean）

改良元: solutions/esw-tidy

PR 91 のアブレーション（trial_log.md「PR 90 の改良のアブレーション」）で 2 SE に満たなかった部品のうち、穴埋めの山登りと post-prune をコードごと消した版。消した部品以外（紙の設計・時間配分・注文処理・乱数・CLOCK_SCALE・LOCAL_BENCH）は改良元と同じ。段の目印 `// ==== <段の名前> ====` と冒頭の目次は保った。

## 外したもの

- **穴埋めの山登り（head-design の filler_climb）。** 焼きなましの後、1.205〜1.26 秒に、列の先頭に残る紙の穴埋め利益を目的に、両方の取っ手の色が変わらない 2 単位の列を交換していた山登り。山登りをなくし、その時間は焼きなましに回した（焼きなましの締切 kAnnealEnd を 1.205 → 1.26 秒）。穴埋めの利益の式 filler_gain は先頭を考えた一括再割当が使うので残し、その段の名前を「Filler climb: ...」から「Design: the filler value of a paper (filler_gain)」に変えた。環境変数 CLIMB_ITERS と stderr の climb_iters・climb_accepted・proxy_before・proxy_after・climb_end_sec はなくなった。
- **2 操作の同時削除（post-prune）。** solutions/esw-noprune と同じ。stderr の post_pair_trials・post_pair_accepts はなくなった。

stay-cover・post-repair・post-two・perforated-eight と穴費用の係数 0.38 は残した（理由は solutions/esw-noprune の README）。

山登りを as6-canon のものにした対照が solutions/esw-lean-climb。結果は trial_log.md。
