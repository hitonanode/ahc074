from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-helper-future/main.cpp').read_text()
x=s.replace('if (pk.distance >= base_generic) continue;','if (pk.distance > base_generic+1) continue;')
x=x.replace('        const auto fixes = fix_costs(u, ~paper[d].opaque & hmask);','''        const auto fixes = fix_costs(u, ~paper[d].opaque & hmask);
        const double baseline_estimate=base_generic+std::accumulate(fixes.begin(),fixes.end(),0.);''')
x=x.replace('            picks.push_back({score, pk});','''            if(pk.distance>=base_generic && score>baseline_estimate-1.)continue;
            picks.push_back({score, pk});''')
x=x.replace('        if (picks.size() > 6) picks.resize(6);','''        int extra_count=0;
        std::erase_if(picks,[&](const auto& p){return p.second.distance>=base_generic && ++extra_count>1;});
        if (picks.size() > 6) picks.resize(6);''')
p=root/'solutions/deval-helperplus1';p.mkdir();(p/'main.cpp').write_text(x)
(p/'README.md').write_text('''改良元: `solutions/deval-helper-future`。

単独helperはgeneric移動数が補助紙なしより1多い場合まで候補にする。ただし同数以上の追加候補は、従来の距離＋掘り＋1.8＋未被覆handleの修正見積りが、補助紙なしのgeneric＋修正見積りより1以上小さいものに限り、見積り上位1件までに絞る。generic移動を減らす従来候補と合計で上位6件を実行する。最終採否は元のplan_costと合法性検査による。同距離goalは既存futureを優先。設計・時間予算・他の探索回数は固定で、時計による切替えはない。
''')
assert len(x.encode())<=522000
print(p.name,len(x.encode()))
