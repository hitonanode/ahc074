from pathlib import Path
import difflib
old=Path('solutions/argon-req-ejectstats-v2/main.cpp').read_text()
newbase='argon-des-perf-rematch-v2'
new=Path('solutions',newbase,'main.cpp').read_text()
for donor,name in [('argon-req-k2late-direct','argon-req-k2direct-v2'),('argon-req-k2late-directwide','argon-req-k2directwide-v2'),('argon-req-rawscreen','argon-req-rawscreen-v2'),('argon-req-rawscreen-both','argon-req-rawscreen-both-v2')]:
 p=Path('solutions')/name;assert not p.exists();p.mkdir()
 target=Path('solutions',donor,'main.cpp').read_text()
 lines=list(difflib.unified_diff(old.splitlines(keepends=True),target.splitlines(keepends=True),n=3))[2:]
 hunks=[];a=[];b=[]
 for line in lines:
  if line.startswith('@@'):
   if a or b:hunks.append((''.join(a),''.join(b)))
   a=[];b=[]
  elif line.startswith(' '):a.append(line[1:]);b.append(line[1:])
  elif line.startswith('-'):a.append(line[1:])
  elif line.startswith('+'):b.append(line[1:])
 if a or b:hunks.append((''.join(a),''.join(b)))
 s=new
 for a,b in hunks:
  assert s.count(a)==1,(donor,s.count(a),a[:80]);s=s.replace(a,b,1)
 (p/'main.cpp').write_text(s)
 desc=Path('solutions',donor,'README.md').read_text().replace('改良元: solutions/argon-req-ejectstats-v2','改良元: solutions/'+newbase,1)
 (p/'README.md').write_text(desc+'\nPR #145の設計変更をそのまま継承し、要求処理の差分だけを移植した。\n')
 (p/'port.txt').write_text(f'{donor}: {len(hunks)} unique request-code hunks applied to {newbase}\n')
 print(p)
