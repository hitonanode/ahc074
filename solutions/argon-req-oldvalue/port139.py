from pathlib import Path
import difflib
p=Path('solutions/argon-req-completefast-v3');p.mkdir()
old=Path('/home/sato/ahc074/runs/20261106-020046_argon-des-perf-condbound/src/main.cpp').read_text().splitlines(keepends=True)
changed=Path('solutions/argon-req-completefast/main.cpp').read_text().splitlines(keepends=True)
base=Path('solutions/argon-req-oldvalue/base139.cpp').read_text();edits=[]
for tag,a,b,c,d in difflib.SequenceMatcher(None,old,changed,autojunk=False).get_opcodes():
 if tag=='equal':continue
 before=''.join(old[max(0,a-3):a]);oldbody=''.join(old[a:b]);after=''.join(old[b:b+3]);needle=before+oldbody+after
 assert base.count(needle)==1,(tag,a,b)
 pos=base.index(needle)+len(before);edits.append((pos,pos+len(oldbody),''.join(changed[c:d])))
for a,b,t in sorted(edits,reverse=True):base=base[:a]+t+base[b:]
p.joinpath('main.cpp').write_text(base)
doc=Path('solutions/argon-req-completefast/README.md').read_text().replace('改良元: solutions/argon-des-perf-condbound','改良元: solutions/argon-des-perf-gaincache',1)
p.joinpath('README.md').write_text(doc)
print('ported',len(edits),'request-only hunks; lines',len(base.splitlines()))
for pp in [Path('solutions/argon-req-oldvalue/REPORT.md'),Path('solutions/argon-req-completefast/REPORT.md')]:
 text=pp.read_text()
 pp.write_text('> 更新: 最終報告作成時にBASEがPR #139へ進んだため、本ファイルのPR #138比較は履歴として保持する。現在の採用候補は同じ要求処理を移植した `solutions/argon-req-completefast-v3`。新基準で固定・通常比較を再確認する。\n\n'+text)
