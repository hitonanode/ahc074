# 先頭の一括再割当を外す（anchor-match / reset-head）

改良元: solutions/eject-single-window。

穴埋め山登りの後の、共有対の片側を固定した全目標のハンガリアン法による一括再割当（rematch_probability、最大 4 回、1.345 秒まで）を行わない。空いた時間（最大約 0.085 秒）は他の段に回さない（as6-canon と同じく、山登りの後すぐに次の段へ進む）。

アブレーション（PR 90 の最良 solutions/eject-single-window から部品を 1 つずつ外す）の 1 つ。ここに書いた変更以外（紙の設計・時間配分・注文処理・CLOCK_SCALE・乱数 seed）は改良元と同じ。評価結果は trial_log.md に書く。
