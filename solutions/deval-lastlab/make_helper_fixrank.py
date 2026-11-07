from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-helper-wide/main.cpp').read_text()
a='score += fixes[__builtin_ctzll(z)];';assert s.count(a)==1
for tag,value in [('half','.5'),('heavy','1.5')]:
 p=root/'solutions'/('deval-helper-'+tag);p.mkdir()
 x=s.replace(a,'score += '+value+'*fixes[__builtin_ctzll(z)];');assert len(x.encode())<=522000
 (p/'main.cpp').write_text(x)
 (p/'README.md').write_text('改良元: `solutions/deval-helper-wide`。\n\n単独helperの事前順位で、覆わないhandleのfix費用だけに'+value+'を掛ける。実際の残りhandleはfillerでも修正するので、fixのみの見積りを弱める（または対照として強める）。候補実行後のplan_costと選択は変えない。設計・候補数・注文予算・ログ・trace・profilerは同じ。時刻による切替えはない。\n')
