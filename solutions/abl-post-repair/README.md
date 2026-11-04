# 削除と差し込み先変更の同時試行を外す（post-rewrite / post-repair）

改良元: solutions/eject-single-window。

後処理で、前の注文の紙の差し込み先を変えると同時に別の 1 操作を消す試行を行わない（post_rewrite_mode = 0）。他の後処理は残す。

アブレーション（PR 90 の最良 solutions/eject-single-window から部品を 1 つずつ外す）の 1 つ。ここに書いた変更以外（紙の設計・時間配分・注文処理・CLOCK_SCALE・乱数 seed）は改良元と同じ。評価結果は trial_log.md に書く。
