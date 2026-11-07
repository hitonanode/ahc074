from merge_exact import *
s=read('deval-equalfund6')
s=delta(s,read('deval-trim6b'),read('deval-ejectsimd6'))
s=delta(s,read('deval-trim6b'),read('deval-keypack6'))
s=drop_dead_features(s)
emit('deval-equalfund-fast','deval-equalfund6',s,
'''注文のeject修復紙の必要条件を4紙ずつ整数AVX2で検査し、通過候補を元の紙番号順で処理する。adaptive_next_costのcache keyは16byteずつ読み、8laneのshuffle tableで元の順に詰める。非column紙の番号配置が通常と違うときは元の走査を使う。hash、全キー照合、浮動小数点計算、候補の受理順を保つ。どの設定からも呼ばれないVのfeature exportメソッド2つと、それに関する古いコメントを削除して容量を確保した。

設計は最初4枝の穴あけ前rematchを1回にし、完成8候補からVで選ぶ。単独helperはgeneric距離が同じ見積り上位1件を許し、従来のstrict候補と合わせて上位3件。goalの同距離はfutureが小さい方を選ぶ。NEUTRAL_WIDTH=4、NS_ROUNDS=2、PLAN_SHORTLIST=6（1手長い計画もraw gap≤1.5なら後処理）。ログの意味と他の設定は改良元を引き継ぐ。''')
