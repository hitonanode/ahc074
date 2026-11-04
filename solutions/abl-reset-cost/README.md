# 穴費用の返却効果を外す（reset-majority）

改良元: solutions/eject-single-window。

設計の模型で、列の取り出し窓の穴費用を reset-majority の (2xy + t·min(x,y))/(x+y+t)（t = 担当目標数の 2 倍）から、as6-canon の 2xy/(x+y)（係数 kHoleWeight は 0.38 のまま）に戻す。焼きなまし・穴埋め山登り・先頭の一括再割当の模型費用と、補助穴（Perforation）の穴費用のすべてで t = 0 にする。

同じ段で入った直接取り出し費用の変更（kRankPriority を 0.85 → 1.0、ランダム順との混合 15% を外す）も戻す（PRIORITY_NUM = 17）。先頭色の確率に入れた返却効果（reset-head）は残す。

アブレーション（PR 90 の最良 solutions/eject-single-window から部品を 1 つずつ外す）の 1 つ。ここに書いた変更以外（紙の設計・時間配分・注文処理・CLOCK_SCALE・乱数 seed）は改良元と同じ。評価結果は trial_log.md に書く。
