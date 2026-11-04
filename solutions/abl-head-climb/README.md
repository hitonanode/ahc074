# 先頭の紙による穴埋め山登りを外す（head-design）

改良元: solutions/eject-single-window。

焼きなましの後の穴埋め山登り（filler_climb）を、head-design のもの（各列・各色で先頭に残りやすい最強の紙の、直す窓数 − 1.6 手の正の期待値を係数 1.0 で評価）から、as6-canon のもの（列の全紙の平均の穴埋め利益 − 3、係数 0.3）に戻す。交換の種類・時間（1.26 秒まで）は同じ。山登りの最初に穴費用の t を計算し直す点（reset-majority）は残す。

その後の先頭の一括再割当（anchor-match）は head-design と同じ先頭利益の式のまま行う。

アブレーション（PR 90 の最良 solutions/eject-single-window から部品を 1 つずつ外す）の 1 つ。ここに書いた変更以外（紙の設計・時間配分・注文処理・CLOCK_SCALE・乱数 seed）は改良元と同じ。評価結果は trial_log.md に書く。
