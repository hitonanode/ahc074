#!/usr/bin/env python3
"""同じ版の選定64seedの反復をseedごとに平均し、64個の値からSEを求める。"""
from pathlib import Path
import csv,json,math,statistics
h=Path(__file__).resolve().parent
records={}
for f in sorted(h.glob('*.json')):
 d=json.loads(f.read_text())
 if 'config' not in d or not isinstance(d['config'],dict):continue
 c=d['config']
 if c.get('base')!='base' or c.get('fixed') or c.get('seeds')!='24-88' or 'compare' not in d:continue
 b=c['candidate'];rows=list(csv.DictReader((h/(f.stem+'.csv')).open()))
 base={int(r['seed']):r for r in rows if r['binary']=='base'}
 candidate={int(r['seed']):r for r in rows if r['binary']==b}
 rr=records.setdefault(b,{'labels':[],'differences':{},'end_max':0,'seeds':64})
 rr['labels'].append(f.stem)
 for seed,r in candidate.items():
  rr['differences'].setdefault(seed,[]).append(100*math.log(float(r['gobj_after'])/float(base[seed]['gobj_after'])))
  rr['end_max']=max(rr['end_max'],float(r['end_sec']))
summary={}
for b,r in records.items():
 dd=[statistics.mean(x) for x in r['differences'].values()]
 summary[b]={'labels':r['labels'],'n':len(dd),'replicates':len(r['labels']), 'log_pct':statistics.mean(dd),'se_pct':statistics.stdev(dd)/math.sqrt(len(dd)), 'win':sum(x<0 for x in dd),'tie':sum(x==0 for x in dd),'loss':sum(x>0 for x in dd),'end_max':r['end_max']}
(h/'selection-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
for b,r in sorted(summary.items(),key=lambda x:x[1]['log_pct']):
 if b.startswith('cross') or r['log_pct'] < -2*r['se_pct']:print(b,r)
