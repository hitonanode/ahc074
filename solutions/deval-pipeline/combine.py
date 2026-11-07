"""Compose disjoint changes against ordered8; fail on overlapping edits."""
import sys,difflib
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
name,*variants=sys.argv[1:]
base=(R/'solutions/deval-ordered8/main.cpp').read_text().splitlines(keepends=True)
edits=[]
for variant in variants:
 other=(R/'solutions'/variant/'main.cpp').read_text().splitlines(keepends=True)
 for tag,a,b,c,d in difflib.SequenceMatcher(None,base,other,autojunk=False).get_opcodes():
  if tag!='equal':edits.append((a,b,other[c:d],variant))
edits.sort(key=lambda e:(e[0],e[1]))
for left,right in zip(edits,edits[1:]):assert left[1]<=right[0],(left[3],right[3],left[:2],right[:2])
s=base[:]
for a,b,replacement,v in reversed(edits):s[a:b]=replacement
s=''.join(s);p=R/'solutions'/name;p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: `solutions/deval-ordered8`。\n\n次の独立した変更を併用する。\n\n'+''.join('- `'+v+'`: '+(R/'solutions'/v/'README.md').read_text().split('\n\n',1)[1].replace('\n',' ').strip()+'\n' for v in variants)+'\n元の8候補と全ての探索予算は固定。時間不足の切り替えなし。選ばれた最終設計をDesignStoreに保存する。\n')
print(name,len(s.encode()),'bytes',len(edits),'edits')
