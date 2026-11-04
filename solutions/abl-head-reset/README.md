# 先頭色の確率の返却効果を外す（reset-head）

改良元: solutions/eject-single-window。

列の一番上の紙の色の確率を、reset-head の (y + t·[y > x])/(x+y+t)（t = 担当目標数の 2 倍）から、anchor-match までの y/(x+y)（穴の要求色の比）に戻す。使っている 3 か所（穴埋め山登りの先頭の模型、先頭の一括再割当、補助穴の設計の先頭色の標本）すべてで t = 0 にする。

一括再割当では、割当を変えるたびに確率を計算し直すこと（dynamic）と、要求数が先頭色の確率を変える効果の微分（derivative）も外す（rematch_probability(…, 0.0, false, false, …)。anchor-match の rematch_head と同じ動作）。穴費用の返却効果（reset-majority）は残す。

アブレーション（PR 90 の最良 solutions/eject-single-window から部品を 1 つずつ外す）の 1 つ。ここに書いた変更以外（紙の設計・時間配分・注文処理・CLOCK_SCALE・乱数 seed）は改良元と同じ。評価結果は trial_log.md に書く。
