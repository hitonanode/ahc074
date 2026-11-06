"""保存された @ops だけを集計。共有 flock の下で実行する。"""
import collections,sys
from pathlib import Path
for name in sys.argv[1:]:
    total=collections.Counter();requests=0
    for p in (Path('/home/sato/ahc074/runs')/name/'err').glob('*.txt'):
        for line in p.read_text().splitlines():
            if not line.startswith('@ops '):continue
            requests+=1
            for token in line.split('=',1)[1].split():
                label,sep,n=token.partition('*')
                total[label]+=int(n) if sep else 1
    print(name,'orders',requests,'moves/order',{k:round(v/requests,7) for k,v in sorted(total.items())})
