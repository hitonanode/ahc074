from pathlib import Path
import difflib,re
r=Path(__file__).resolve().parents[2]
def read(n):return (r/'solutions'/n/'main.cpp').read_text()
def delta(s,a,b):
 aa=a.splitlines(True);bb=b.splitlines(True)
 for g in difflib.SequenceMatcher(None,aa,bb,autojunk=False).get_grouped_opcodes(3):
  x=''.join(aa[g[0][1]:g[-1][2]]);y=''.join(bb[g[0][3]:g[-1][4]])
  assert s.count(x)==1,(x[:90],s.count(x));s=s.replace(x,y)
 return s
s=delta(read('dcomp-stack-nine'),read('dcomp-screen-replay'),read('dcomp-hungway-mask'))
for name,gap,wide in [('dcomp-stack-b',None,False),('dcomp-alt100','1.0',False),('dcomp-alt100-wide','1.0',True),('dcomp-alt125','1.25',False),('dcomp-alt150','1.5',False)]:
 src=s
 if gap:
  src=delta(src,read('dcomp-eject-known'),read('dcomp-spend-alt100'))
  src=src.replace('if(std::strcmp(name,"NS_ALTERNATE_GAP")==0)return "1.0";',f'if(std::strcmp(name,"NS_ALTERNATE_GAP")==0)return "{gap}";')
  if wide:
   for key,v in [('NEUTRAL_WIDTH','6'),('POST_CANDIDATES','8')]:
    src,n=re.subn(r'(if\(std::strcmp\(name,"'+key+r'"\)==0\)return ")[^"]+(";)',lambda m:m[1]+v+m[2],src);assert n==1
 p=r/'solutions'/name;assert not p.exists();p.mkdir();(p/'main.cpp').write_text(src)
 (p/'README.md').write_text('改良元: solutions/dcomp-stack-nine\n\nHungarianの4列分way更新を同じ整数maskによるstoreに置き換える。浮動小数点計算と列挙順は変えない。'+('注文のalternate再編集を有効にし、gap '+gap+'、追加の取り出しは最大2回。'+('NEUTRAL_WIDTH=6、POST_CANDIDATES=8。' if wide else '') if gap else '注文予算はcombo-m1-nineと同じ。')+'設計は9候補のまま。すべて固定予算、時間fallbackなし。ログ、trace、profiler、実験スイッチ、DesignStoreを維持。\n')
