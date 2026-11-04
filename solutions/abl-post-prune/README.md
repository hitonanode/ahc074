# 2 操作の同時削除を外す（post-prune）

改良元: solutions/eject-single-window。

後処理で、前の注文で持ち上げた紙か穴埋め紙を動かす操作を含む 2 操作をまとめて消す試行を行わない（kPairDeletion = false）。1 操作ずつの削除、差し込み先の変更、削除と差し込み先変更の同時試行、2 削除 + 1 修復は残す。

アブレーション（PR 90 の最良 solutions/eject-single-window から部品を 1 つずつ外す）の 1 つ。ここに書いた変更以外（紙の設計・時間配分・注文処理・CLOCK_SCALE・乱数 seed）は改良元と同じ。評価結果は trial_log.md に書く。
