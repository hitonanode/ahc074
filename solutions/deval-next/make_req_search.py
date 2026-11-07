from pathlib import Path
r=Path(__file__).resolve().parents[2];b=(r/'solutions/deval-seven-wide/main.cpp').read_text()
configs={'deval-plan3':('PLAN_SHORTLIST','3'),'deval-plan4':('PLAN_SHORTLIST','4'),'deval-anchor3':('ONE_ANCHORS','3'),'deval-slack125':('PROMISING_SLACK','1.25'),'deval-slack040':('PROMISING_SLACK','.4'),'deval-round3':('NS_ROUNDS','3')}
for name,(key,value) in configs.items():
 needle='        if(std::strcmp(name,"REPEAT_MIN")==0)return ".05";'
 assert needle in b;s=b.replace(needle,f'        if(std::strcmp(name,"{key}")==0)return "{value}";\n'+needle,1)
 p=r/'solutions'/name;p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s);(p/'README.md').write_text(f'改良元: `solutions/deval-seven-wide`\n\n注文後処理の固定設定 `{key}={value}` だけを変更する。設計は同一。時間不足による軽量化や時間依存の予算はない。\n')
