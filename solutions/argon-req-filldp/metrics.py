from pathlib import Path
import sys,re,statistics,json
out={}
for run in sys.argv[1:]:
 r=Path('/home/sato/ahc074/runs')/run
 logs=list((r/'err').glob('*.txt'))+list((r/'orders').glob('*/err/*.txt'))
 rows=[dict((k,float(v)) for k,v in re.findall(r'^(\w+) = ([-+\d.eE]+)$',p.read_text(),re.M)) for p in logs]
 stats={k:statistics.mean(x[k] for x in rows if k in x) for k in rows[0] if k.startswith('r2_') or k in ['self_wrong','op_label_errors','req_sec']}
 out[run]=stats
 print(run,len(rows),json.dumps(stats,ensure_ascii=False))
