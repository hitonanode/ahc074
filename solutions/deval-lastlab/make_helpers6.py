from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-helper-future/main.cpp').read_text()
s=s.replace('if (pk.distance >= base_generic) continue;','if (pk.distance > base_generic) continue;')
def emit(n,t,d):
 p=root/'solutions'/n;p.mkdir();(p/'main.cpp').write_text(t)
 (p/'README.md').write_text('改良元: `solutions/deval-helper-future`。\n\n'+d+'\n\n補助紙の同じ最少generic距離では、既存のfuture値の低い到達状態を選ぶ。設計と列MDPは変更しない。予算は固定、時刻による切替えはない。\n')
 assert len(t.encode())<=522000;print(n,len(t.encode()))
for cap in [1,2,3]:
 x=s.replace('        if (picks.size() > 6) picks.resize(6);',f'''        int equal_count=0;
        std::erase_if(picks,[&](const auto& p){{return p.second.distance==base_generic && ++equal_count>{cap};}});
        if (picks.size() > 6) picks.resize(6);''')
 emit('deval-helpeq'+str(cap),x,f'generic移動数が同じ単独補助紙も許可するが、既存の見積り順で上位{cap}候補までに制限する。移動数を減らす従来の候補は残し、合計上位6候補を実行する。')
x=s.replace('        const auto fixes = fix_costs(u, ~paper[d].opaque & hmask);','''        const auto fixes = fix_costs(u, ~paper[d].opaque & hmask);
        const double baseline_estimate=base_generic+std::accumulate(fixes.begin(),fixes.end(),0.);''')
x=x.replace('            picks.push_back({score, pk});','''            if(pk.distance==base_generic && score>baseline_estimate-1.)continue;
            picks.push_back({score, pk});''')
emit('deval-helpeq-screen',x,'generic移動数が同じ単独補助紙も、従来の距離＋掘り＋1.8＋残る修正の見積りが、補助紙なしのgeneric距離＋修正の見積りより1以上小さいときだけ追加する。')
