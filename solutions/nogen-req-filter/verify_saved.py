"""保存済み出力の完全一致を比較する。解法を実行せず、共有ロック下で使う。"""
import sys
from pathlib import Path
root=Path('/home/sato/ahc074/runs')
a,b=(root/x for x in sys.argv[1:3])
paths=sorted(b.glob('out/*.txt'))+sorted(b.glob('orders/*/out/*.txt'))
same=0; different=[]; missing=[]
for p in paths:
    q=a/p.relative_to(b)
    if not q.exists(): missing.append(str(p.relative_to(b)))
    elif p.read_bytes()==q.read_bytes(): same+=1
    else: different.append(str(p.relative_to(b)))
print('same',same,'different',len(different),'missing',len(missing))
print('different_first',different[:10], 'missing_first',missing[:10])
if different or missing: sys.exit(1)
