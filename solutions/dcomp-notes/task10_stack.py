"""Combine isolated exact patches with context; fail on overlap or ambiguous anchors."""
from pathlib import Path
import difflib,re
r=Path(__file__).resolve().parents[2]
def read(n):return (r/'solutions'/n/'main.cpp').read_text()
def delta(s,a,b):
 aa=a.splitlines(True);bb=b.splitlines(True)
 groups=list(difflib.SequenceMatcher(None,aa,bb,autojunk=False).get_grouped_opcodes(3))
 for group in groups:
  x=''.join(aa[group[0][1]:group[-1][2]]);y=''.join(bb[group[0][3]:group[-1][4]])
  assert s.count(x)==1,(x[:160],s.count(x));s=s.replace(x,y)
 return s
base=read('dcomp-screen-replay');s=read('dcomp-eject-geometry')
for patch in ['dcomp-next-prefix','dcomp-donor4']:
 s=delta(s,base,read(patch))
# The nine-candidate control isolates speedups against the SOTA; the requested
# ten-candidate build remains available separately.
nine=delta(s,read('dcomp-ten-fast'),read('dcomp-nine-fast'))
for name,src,n,spend in [('dcomp-stack-nine',nine,9,False),('dcomp-stack-ten',s,10,False),('dcomp-stack-alt75',nine,9,True)]:
 if spend:
  src=delta(src,base,read('dcomp-spend-alt75-e2'))
  for key,v in [('NEUTRAL_WIDTH','6'),('POST_CANDIDATES','8')]:
   src,num=re.subn(r'(if\(std::strcmp\(name,"'+key+r'"\)==0\)return ")[^"]+(";)',lambda m:m[1]+v+m[2],src);assert num==1
 p=r/'solutions'/name;assert not p.exists();p.mkdir();(p/'main.cpp').write_text(src)
 (p/'README.md').write_text('改良元: solutions/combo-m1-nine\n\n窓のsparsebitsはGCCだけで使い、Clangは親の処理を使う。設計rematchのdonorの整数maskを4対象ずつ計算し、浮動小数点は元の順序。注文は可換なanchor候補のリンク・合法性再生を共有し、取り出し側の既知のリンクと表示条件を再利用。空の修復区間では深いorderの構成を省く。next_costは64/128枚までの正確な途中状態を完全keyで保存する。\n\n設計候補は'+str(n)+'本。'+('注文探索はNS_ALTERNATE=1、gap .75、alternateの取り出し最大2回、NEUTRAL_WIDTH=6、POST_CANDIDATES=8。' if spend else '注文探索予算はcombo-m1-nineと同じ。')+'環境変数による実験スイッチを優先。固定回数のみ、時間fallbackなし。ログ・metrics・@paper/@ops・DesignStore・目次を維持。\n')
