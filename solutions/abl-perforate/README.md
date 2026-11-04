# 補助穴を外す（perforated-eight）

改良元: solutions/eject-single-window。

各列・各色の先頭候補の紙の取り出し窓より浅いハンドルに穴を開ける段（Perforation、1.39 秒まで）を行わない。紙の印刷は列の設計どおり（三角形の不透明部分と対の違いの穴だけ）。

アブレーション（PR 90 の最良 solutions/eject-single-window から部品を 1 つずつ外す）の 1 つ。ここに書いた変更以外（紙の設計・時間配分・注文処理・CLOCK_SCALE・乱数 seed）は改良元と同じ。評価結果は trial_log.md に書く。
