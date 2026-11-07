from merge_exact import *
s=read('deval-equalfund-fast');a='c.cost <= baseline_value + 1.5';assert s.count(a)==1;s=s.replace(a,'c.cost <= baseline_value + 1.0')
emit('deval-equalfund-gap1','deval-equalfund-fast',s,
'''PLAN_SHORTLIST=6で1手長い計画を追加後処理する条件をraw plan_cost差≤1.5から≤1.0へ絞る。穴あけ前rematch1回、完成8設計、単独helper同距離top1/総数3、NEUTRAL_WIDTH=4、NS_ROUNDS=2と整数SIMDの出力同一変更は改良元と同じ。設計の乱数・結果は改良元と同じで、追加後処理の固定条件だけを変える。''')
