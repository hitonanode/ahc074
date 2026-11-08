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
for name,parent,wide in [('dcomp-alt100-h4','dcomp-alt100',False),('dcomp-alt100-w6-h4','dcomp-alt100',True),('dcomp-alt100-wide-h4','dcomp-alt100-wide',False)]:
 s=read(parent); h=read('dcomp-hole4')
 pattern=r'^    __attribute__\(\(target\([^\n]+ double adaptive_next_cost\('
 a=re.search(pattern,s,re.M).start();b=s.index('    // Lexicographic permutation rank',a)
 ha=re.search(pattern,h,re.M).start();hb=h.index('    // Lexicographic permutation rank',ha)
 s=s[:a]+h[ha:hb]+s[b:]
 if wide:
  x='if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "5";';assert s.count(x)==1;s=s.replace(x,x.replace('"5"','"6"'))
 p=r/'solutions'/name;assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: solutions/'+parent+'\n\nnext_costの穴費用を4項同時計算する出力同一高速化を加える。各項は正確な整数/1024で、途中和へ加える順は元のまま。'+('NEUTRAL_WIDTHだけ5から6へ増やす。' if wide else '注文予算は親と同じ。')+'設計は9候補、ALT gap=1、alternate修復は最大2回。すべて固定予算。ログ・profiler・実験スイッチ・DesignStoreを維持、時間fallbackなし。\n')
