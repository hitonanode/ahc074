# 上位 2 案の後処理を外す（post-two）

改良元: solutions/eject-single-window。

終わりの順序が違う上位 2 案をそれぞれ後処理してから選ぶのをやめ、as6-canon と同じく最良の 1 案だけを後処理する（kPostCandidates = 1）。2 案目を選ぶときの同じ紙列の重複除去（eject-tight）も働かなくなる。

アブレーション（PR 90 の最良 solutions/eject-single-window から部品を 1 つずつ外す）の 1 つ。ここに書いた変更以外（紙の設計・時間配分・注文処理・CLOCK_SCALE・乱数 seed）は改良元と同じ。評価結果は trial_log.md に書く。
