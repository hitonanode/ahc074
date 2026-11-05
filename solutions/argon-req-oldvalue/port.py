from pathlib import Path
import difflib,sys
cand,name=sys.argv[1:]
p=Path('solutions')/name;p.mkdir()
old=Path('solutions/argon-req-filldp-positive/main.cpp').read_text().splitlines(keepends=True)
changed=Path('solutions',cand,'main.cpp').read_text().splitlines(keepends=True)
base=Path('/home/sato/ahc074/runs/20261106-005414_argon-des-perf-condbound/src/main.cpp').read_text()
changes=[]
for tag,a,b,c,d in difflib.SequenceMatcher(None,old,changed,autojunk=False).get_opcodes():
 if tag=='equal':continue
 before=''.join(old[max(0,a-3):a]);oldbody=''.join(old[a:b]);after=''.join(old[b:b+3])
 needle=before+oldbody+after
 assert base.count(needle)==1,(tag,a,b,needle[:100])
 pos=base.index(needle)+len(before)
 changes.append((pos,pos+len(oldbody),''.join(changed[c:d])))
for a,b,t in sorted(changes,reverse=True):base=base[:a]+t+base[b:]
p.joinpath('main.cpp').write_text(base)
doc=Path('solutions',cand,'README.md').read_text().splitlines()
doc[0]='改良元: solutions/argon-des-perf-condbound'
p.joinpath('README.md').write_text('\n'.join(doc)+'\n\nPR #138の採用済み基準へ、要求処理の変更だけを移植した。設計側は基準のまま。\n')
print('ported',len(changes),'hunks',cand,'->',name)
