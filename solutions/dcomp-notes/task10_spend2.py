from pathlib import Path
import re
r=Path(__file__).resolve().parents[2];base=(r/'solutions/dcomp-screen-replay/main.cpp').read_text()
variants=[('nw6',{'NEUTRAL_WIDTH':'6'}),('exp8',{'POST_CANDIDATES':'8'}),('rwf',{}),('slgap25',{'PLAN_SHORTLIST':'0','PLAN_GAP':'.25'}),('alt50',{'NS_ALTERNATE':'1','NS_ALTERNATE_GAP':'.5'})]
for name,settings in variants:
 s=base
 for key,value in settings.items():
  m=re.search(r'if\(std::strcmp\(name,"'+key+r'"\)==0\)return "[^"]+";',s);new=f'if(std::strcmp(name,"{key}")==0)return "{value}";'
  if m:s=s[:m.start()]+new+s[m.end():]
  else:
   a='if(const char* value=std::getenv(local.c_str()))return value;';assert s.count(a)==1;s=s.replace(a,a+'\n        '+new)
 if name=='rwf':
  a='        for (const auto& f : initial.fillers) initial_extra[f.paper] = true;\n';assert s.count(a)==1
  s=s.replace(a,a+'        std::array<bool,K> end_filler{};\n        for(const auto& f:fillers)end_filler[f.paper]=true;\n')
  a='                if (!initial_extra[k]) continue;\n';assert s.count(a)==1;s=s.replace(a,'                if (!initial_extra[k] && !end_filler[k]) continue;\n')
 if name=='alt50':
  a='                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), 4);';assert s.count(a)==1;s=s.replace(a,a.replace(', 4);',', 2);'))
 p=r/'solutions'/('dcomp-spend-'+name);assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
 desc=', '.join(f'{k}={v}' for k,v in settings.items()) or '削除と付け替えの組を、計画後にfillerとなる紙にも広げる(rwf)'
 (p/'README.md').write_text('改良元: solutions/dcomp-screen-replay\n\n注文探索への時間再配分の単独試験。'+desc+'。'+('次点の取り出しは2回。' if name=='alt50' else '')+'\n\nseed 0〜499の4注文列で選別。時間による変更はなく、固定の既定値のみを変える。環境変数の実験スイッチを優先し、ログとDesignStoreを維持する。\n')
