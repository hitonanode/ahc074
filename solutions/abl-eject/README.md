# 2 削除 + 1 修復を外す（eject-one ほか）

改良元: solutions/eject-single-window。

後処理の最後に、選んだ計画から 2 操作を消し、表示を直す 1 枚の移動を途中に挿入する試行（eject-one、eject-lean、eject-quick の再後処理、eject-single-window の 1 窓の条件を含む）を行わない（mid_eject_mode = 0）。

eject-one でこの処理の時間を作るために 0.10 秒早めた設計の締切も、as6-canon（とその後の段）の値に戻す: 焼きなまし 1.205 → 1.305 秒、穴埋め山登り 1.26 → 1.36 秒、一括再割当 1.345 → 1.445 秒、補助穴 1.39 → 1.49 秒、補助表 1.45 → 1.55 秒。

アブレーション（PR 90 の最良 solutions/eject-single-window から部品を 1 つずつ外す）の 1 つ。ここに書いた変更以外（紙の設計・時間配分・注文処理・CLOCK_SCALE・乱数 seed）は改良元と同じ。評価結果は trial_log.md に書く。

ablation_stats.py は、PR 90 のアブレーション全体（solutions/abl-*）の集計スクリプト（run の差、勝/分/敗、軽量処理を使わなかった seed だけでの差、差の和）。使い方は冒頭のコメント。
