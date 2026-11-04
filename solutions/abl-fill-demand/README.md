# 穴埋め需要を返却位置に入れない（head-demand / head-excess）

改良元: solutions/eject-single-window。

注文処理で紙を列へ戻す深さを決める将来費用（adaptive_weights）に、その紙が他の目標の穴埋めに使われる需要（直す窓数 − 1.6 手の正の部分の期待値、係数 0.25、列内平均で規格化）を足す処理を行わない（FILL_DEMAND_WEIGHT = 0）。重みは as6-canon と同じく直接の取り出し頻度だけになる。

アブレーション（PR 90 の最良 solutions/eject-single-window から部品を 1 つずつ外す）の 1 つ。ここに書いた変更以外（紙の設計・時間配分・注文処理・CLOCK_SCALE・乱数 seed）は改良元と同じ。評価結果は trial_log.md に書く。
