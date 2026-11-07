from pathlib import Path
P=Path(__file__).resolve().parent;root=P.parents[1]
s=(root/'solutions/deval-trim6b/main.cpp').read_text()
def emit(n,text,d):
 p=root/'solutions'/n;p.mkdir();(p/'main.cpp').write_text(text)
 (p/'README.md').write_text('改良元: `solutions/deval-trim6b`。\n\n'+d+'\n\n設計は変えない。全予算固定、時刻による切替えなし。ログ・注釈・実験スイッチを保つ。\n')
 assert len(text.encode())<=522000
 print(n,len(text.encode()))
for mode in [4,5]:
 x=s.replace('get("PLAN_SHORTLIST", mode == 1 ? 3 : 0)',f'get("PLAN_SHORTLIST", mode == 1 ? {mode} : 0)')
 old='(cfg.plan_shortlist == 3 && c.path.size() == chosen_path.size())'
 new='((cfg.plan_shortlist == 3 || cfg.plan_shortlist >= 4) && c.path.size() == chosen_path.size()) || ((cfg.plan_shortlist == 5 || (cfg.plan_shortlist == 4 && repeated)) && c.path.size() == chosen_path.size()+1)'
 assert x.count(old)==1;x=x.replace(old,new)
 emit('deval-shortplus'+str(mode),x,'追加計画のshortlistを拡張し、同手数に加え1手多い候補も許す。'+('同じ紙の複数移動が残る候補に限る。' if mode==4 else '繰返し紙の有無は問わない。')+' 最後に本探索する上限1件は同じ。')
x=s.replace('if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "3";','if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "12";').replace('get("HEAVY_PREDICT", 0)','get("HEAVY_PREDICT", 1)')
emit('deval-rankprobe6',x,'診断専用。neutral候補幅を12にし、既存HEAVY_PREDICTを有効にする。候補のhides/repeats/値と再編集後の改善を記録し、安い順位付けの余地を調べる。絶対時間を採用案の時間として扱わない。')
