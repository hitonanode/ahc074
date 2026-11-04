# 穴費用の係数 0.38 を 0.40 に戻す（tight-thirty-eight）

改良元: solutions/eject-single-window。

設計の穴費用の係数 kHoleWeight を 0.38 から as6-canon の 0.40 に戻す（焼きなまし・再割当・補助穴の穴費用すべて）。同じ段で入った計算の短縮と計画の重複除去は残す。

アブレーション（PR 90 の最良 solutions/eject-single-window から部品を 1 つずつ外す）の 1 つ。ここに書いた変更以外（紙の設計・時間配分・注文処理・CLOCK_SCALE・乱数 seed）は改良元と同じ。評価結果は trial_log.md に書く。
