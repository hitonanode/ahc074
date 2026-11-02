#!/usr/bin/env python3
"""4本を設計単位で合算した差とSE。JSONは小さく永続保存する。"""
import argparse,json,math,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument('labels',nargs='+')
a=p.parse_args()
def meanse(v):
    return {'mean':statistics.mean(v),'se':statistics.stdev(v)/math.sqrt(len(v)) if len(v)>1 else 0}
def load(label):
    out={}
    for f in sorted((ROOT/'results'/label).glob('*.jsonl')):
        rows=[json.loads(x) for x in f.read_text().splitlines()]
        if len(rows)<2:continue
        cfg=json.loads((f.parent/'config.json').read_text())
        if len(rows)!=cfg['seqs']+1:continue
        out[int(f.stem)]={'hash':rows[0]['design_hash'],'nseq':len(rows)-1}
        for k in rows[1]:
            if k!='sequence' and isinstance(rows[1][k],(int,float)):out[int(f.stem)][k]=sum(r[k] for r in rows[1:])
    return out
allrows={name:load(name) for name in a.labels}
base=allrows[a.labels[0]]
report={}
for label,rows in allrows.items():
    n=len(rows)
    if not n:continue
    res={'cases':n,'sequences':sum(r['nseq'] for r in rows.values()),'means_per_request':{}}
    for k in ['total','generic','lift','old_top','old_filler','dig_d','filler','fix','filler_state','candidates','changed','oracle_calls']:
        res['means_per_request'][k]=meanse([r[k]/r['steps'] for r in rows.values()])
    for k in ['wrong','illegal','oracle_bad']:res[k]=sum(r[k] for r in rows.values())
    for k in ['advantage','current_delta','next_delta','terminal_delta','expanded_total','expanded_selected']:
        if k in next(iter(rows.values())):
            res['means_per_request'][k]=meanse([r[k]/r['steps'] for r in rows.values()])
    if label!=a.labels[0]:
        common=sorted(base.keys()&rows.keys())
        assert all(base[s]['hash']==rows[s]['hash'] and base[s]['steps']==rows[s]['steps'] for s in common)
        ds=[100*math.log(rows[s]['total']/base[s]['total']) for s in common]
        res['comparison']={'cases':len(common),'log_ratio_percent':meanse(ds),
          'win_tie_loss':[sum(x<0 for x in ds),sum(x==0 for x in ds),sum(x>0 for x in ds)],'delta_per_request':{}}
        for k in ['total','generic','lift','old_top','old_filler','dig_d','filler','fix','filler_state']:
            res['comparison']['delta_per_request'][k]=meanse([(rows[s][k]-base[s][k])/base[s]['steps'] for s in common])
    report[label]=res
text=json.dumps(report,ensure_ascii=False,indent=2)
(ROOT/'results'/('summary-'+'-'.join(a.labels)+'.json')).write_text(text+'\n')
print(text)
