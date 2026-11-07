from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-helpeq1/main.cpp').read_text()
a='if (picks.size() > 6) picks.resize(6);';assert s.count(a)==1;s=s.replace(a,'if (picks.size() > 3) picks.resize(3);')
for cap in [1,2]:
 name=f'deval-helper3-eq{cap}';p=root/'solutions'/name;p.mkdir();x=s.replace('++equal_count>1','++equal_count>'+str(cap))
 (p/'main.cpp').write_text(x);(p/'README.md').write_text('改良元: `solutions/deval-helpeq1`。\n\n単独helperの全候補上限を6から3へ減らす。同generic距離の追加候補は見積り上位'+str(cap)+'件まで。汎用紙の移動数を減らす通常候補も同じ順位表に入れ、合計上位3件を実際の計画で比較する。2枚helper、設計、他の注文予算とログは従来通り。時刻では予算を変えない。\n');print(name,len(x.encode()))
