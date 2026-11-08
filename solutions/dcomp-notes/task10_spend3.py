from pathlib import Path
import re
r=Path(__file__).resolve().parents[2];base=(r/'solutions/dcomp-eject-known/main.cpp').read_text()
variants=[('pl3',{'PLAN_LIMIT':'3'}),('ns4',{'NS_ROUNDS':'4'}),('sl50',{'NEUTRAL_SLACK':'.5'}),('alt100',{'NS_ALTERNATE':'1','NS_ALTERNATE_GAP':'1.0'})]
for name,settings in variants:
 s=base
 for key,value in settings.items():
  old=re.search(r'if\(std::strcmp\(name,"'+key+r'"\)==0\)return "[^"]+";',s);new=f'if(std::strcmp(name,"{key}")==0)return "{value}";'
  if old:s=s[:old.start()]+new+s[old.end():]
  else:
   a='if(const char* value=std::getenv(local.c_str()))return value;';assert s.count(a)==1;s=s.replace(a,a+'\n        '+new)
 if name=='alt100':
  a='                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), 4);';assert s.count(a)==1;s=s.replace(a,a.replace(', 4);',', 2);'))
 p=r/'solutions'/('dcomp-spend-'+name);assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: solutions/dcomp-eject-known\n\n固定の注文予算の追加試行。既定値: '+', '.join(f'{k}={v}' for k,v in settings.items())+('、次点の取り出しは最大2回。' if name=='alt100' else '。')+' 環境変数による実験設定を優先。設計・ログ・DesignStoreを維持、時間fallbackなし。\n')
