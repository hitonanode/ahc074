from pathlib import Path
import re
r=Path(__file__).resolve().parents[2];base=(r/'solutions/dcomp-screen-replay/main.cpp').read_text()
variants=[('alt25-e2',{'NS_ALTERNATE':'1','NS_ALTERNATE_GAP':'.25'},2),('alt75-e2',{'NS_ALTERNATE':'1','NS_ALTERNATE_GAP':'.75'},2),('alt75-e4',{'NS_ALTERNATE':'1','NS_ALTERNATE_GAP':'.75'},4),('rmin0',{'REPEAT_MIN':'0'},None)]
for name,settings,rounds in variants:
 s=base
 for key,value in settings.items():
  old=re.search(r'if\(std::strcmp\(name,"'+key+r'"\)==0\)return "[^"]+";',s)
  new=f'if(std::strcmp(name,"{key}")==0)return "{value}";'
  if old:s=s[:old.start()]+new+s[old.end():]
  else:
   a='if(const char* value=std::getenv(local.c_str()))return value;';assert s.count(a)==1;s=s.replace(a,a+'\n        '+new)
 if rounds is not None:
  a='                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), 4);'
  assert s.count(a)==1;s=s.replace(a,a.replace(', 4);',f', {rounds});'))
 p=r/'solutions'/('dcomp-spend-'+name);assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: solutions/dcomp-screen-replay\n\n出力同一の短縮で空けた時間を注文探索へ配る試行。固定の既定値: '+', '.join(f'{k}={v}' for k,v in settings.items())+('、次点の取り出しを'+str(rounds)+'回。' if rounds else '。')+'\n\n設計は10候補のまま。環境変数による実験設定を優先し、時計による候補数変更やfallbackはない。設定はseed 0〜499の固定設計・4注文列で選ぶ。ログとDesignStoreを保持する。\n')
