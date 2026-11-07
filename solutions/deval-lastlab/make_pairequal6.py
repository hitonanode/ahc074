from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-helpeq1/main.cpp').read_text()
a='auto pk = best_interleave_pair(states_by_distance, u, pp.x, pp.y, base_generic);'
assert s.count(a)==1
s=s.replace(a,'auto pk = best_interleave_pair(states_by_distance, u, pp.x, pp.y, base_generic + 1);')
a='        if (pair_picks.size() > 6) pair_picks.resize(6);'
assert s.count(a)==1
for screen in [False,True]:
 name='deval-paireq-screen' if screen else 'deval-paireq1';p=root/'solutions'/name;p.mkdir()
 extra='''        int pair_equal_count=0;
        double helper_baseline=base_generic;
        for (double f:fixes) helper_baseline+=f;
        std::erase_if(pair_picks,[&](const auto& p){return p.second.distance==base_generic && (SCREEN++pair_equal_count>1);});
'''.replace('SCREEN','p.first>helper_baseline || ' if screen else '')
 if not screen: extra=extra.replace('        double helper_baseline=base_generic;\n        for (double f:fixes) helper_baseline+=f;\n','')
 x=s.replace(a,extra+a);assert len(x.encode())<=522000;(p/'main.cpp').write_text(x)
 (p/'README.md').write_text('改良元: `solutions/deval-helpeq1`。\n\n単独helperに加え、2枚helperにも汎用紙の移動数が通常と同じ候補を許す。同距離の2枚helperは見積り上位1件、全体は従来どおり上位6件まで。'+('追加候補は見積りが通常のgeneric移動数とhandle fixの和を超えないものに限る。' if screen else '')+'設計・その他の固定予算、ログとスイッチを保つ。\n')
 print(name,len(x.encode()))
