from pathlib import Path
import sys,re,statistics,json
root=Path('/home/sato/ahc074/runs');results={}
for name in sys.argv[1:]:
 r=root/name;files=list((r/'err').glob('*.txt'))+list((r/'orders').glob('*/err/*.txt'))
 rows=[{k:float(v) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',p.read_text(),re.M)} for p in files]
 keys=[k for k in rows[0] if (k.startswith(('old_','value_','reserve_','tail_probe_')) and not k[-1].isdigit()) or k in ['req_sec','self_wrong','op_label_errors']]
 d={k:statistics.mean(row.get(k,0) for row in rows) for k in keys};results[name]=d
 print(name,'orders',len(rows),json.dumps(d,indent=2),flush=True)
 if 'oracle' in name:
  b=root/(name[:15]+'_argon-req-filldp-positive')
  outs=list((r/'out').glob('*.txt'))+list((r/'orders').glob('*/out/*.txt'))
  print('baseline stdout matches',sum(p.read_bytes()==(b/p.relative_to(r)).read_bytes() for p in outs),'/',len(outs),flush=True)
