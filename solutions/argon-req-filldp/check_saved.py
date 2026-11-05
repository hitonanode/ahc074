from pathlib import Path
import sys,json,re
root=Path('/home/sato/ahc074/runs')
b=root/sys.argv[1];c=root/sys.argv[2]
outs=list((b/'out').glob('*.txt'))+list((b/'orders').glob('*/out/*.txt'))
bad=[str(p.relative_to(b)) for p in outs if p.read_bytes()!=(c/p.relative_to(b)).read_bytes()]
print('stdout',len(outs),'differences',len(bad),bad[:10])
logs=list((c/'err').glob('*.txt'))+list((c/'orders').glob('*/err/*.txt'))
rows=[{k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',p.read_text(),re.M)} for p in logs]
keys=[k for k in rows[0] if (k.startswith('r2_') or k.startswith('value_filler_')) and not k[-1].isdigit()]
print(json.dumps({k:sum(row.get(k,0) for row in rows)/len(rows) for k in keys},indent=2))
print('errors',{k:sum(row.get(k,0) for row in rows) for k in ['self_wrong','op_label_errors']})
