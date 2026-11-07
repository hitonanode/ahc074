from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-shortplus5/main.cpp').read_text()
old='((cfg.plan_shortlist == 5 || (cfg.plan_shortlist == 4 && repeated)) && c.path.size() == chosen_path.size()+1)'
assert s.count(old)==1
for gap in [1,1.5]:
 name='deval-shortgap'+str(int(gap*100));p=root/'solutions'/name;p.mkdir()
 new='((cfg.plan_shortlist == 5 || (cfg.plan_shortlist == 4 && repeated) || (cfg.plan_shortlist == 6 && c.cost <= baseline_value + '+str(gap)+')) && c.path.size() == chosen_path.size()+1)'
 x=s.replace(old,new).replace('int plan_shortlist = get("PLAN_SHORTLIST", mode == 1 ? 5 : 0);','int plan_shortlist = get("PLAN_SHORTLIST", mode == 1 ? 6 : 0);')
 assert len(x.encode())<=522000;(p/'main.cpp').write_text(x)
 (p/'README.md').write_text('改良元: `solutions/deval-shortplus5`。\n\nPLAN_SHORTLIST=6を追加し、1手長い候補の追加後処理を、raw plan_cost が現在の計画の値より'+str(gap)+'以下の差にある場合だけに限定する。従来のモードとログ、固定予算を保つ。設計はflex125-plan3と同じ。\n')
 print(name,len(x.encode()))
