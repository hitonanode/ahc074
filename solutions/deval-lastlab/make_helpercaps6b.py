from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
for src,name in [('deval-helpeq1','deval-helpeq-tight'),('deval-paireq-lazy','deval-paireq-tight')]:
 s=(root/'solutions'/src/'main.cpp').read_text()
 a='if (picks.size() > 6) picks.resize(6);';assert s.count(a)==1;s=s.replace(a,'if (picks.size() > 2) picks.resize(2);')
 a='if (pair_picks.size() > 6) pair_picks.resize(6);';assert s.count(a)==1;s=s.replace(a,'if (pair_picks.size() > 3) pair_picks.resize(3);')
 p=root/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: `solutions/'+src+'`。\n\n単独helperの計画候補を上位2件、2枚helperを上位3件までに制限する。候補を作る条件と距離・handle見積りの順は保つ。同距離の追加候補を残しつつ、下位候補の計画費用を減らす実験。設計、その他の固定予算、ログ・注釈・スイッチは元と同じ。\n')
 print(name,len(s.encode()))
