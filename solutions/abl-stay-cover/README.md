# 穴埋め紙の残存と被覆の評価を外す（stay-cover）

改良元: solutions/eject-single-window。

注文の終わりの状態の評価で、残した穴埋め紙が次の注文でもその位置に残せる確率による補正と、その紙が次の目標の穴を無料で覆う期待値による補正（どちらも係数 0.25）を外す（stay_strength = cover_strength = 0）。穴埋め紙は as6-canon と同じく 1 枚 0.6 手で数える。

アブレーション（PR 90 の最良 solutions/eject-single-window から部品を 1 つずつ外す）の 1 つ。ここに書いた変更以外（紙の設計・時間配分・注文処理・CLOCK_SCALE・乱数 seed）は改良元と同じ。評価結果は trial_log.md に書く。
