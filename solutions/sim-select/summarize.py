from pathlib import Path
import json,statistics,math
p=Path(__file__).resolve().parent/'models'
rows=[]
for f in sorted(p.glob('[0-9]*.json')):
    try:r=json.loads(f.read_text())
    except json.JSONDecodeError:continue
    if len(r)==7:rows.append(r)
summary={}
def collect(key,selected):
    v=[r[i]['moves']-r[0]['moves']for r,i in zip(rows,selected)]
    summary[key]=dict(n=len(v),mean=statistics.mean(v),se=statistics.stdev(v)/math.sqrt(len(v)) if len(v)>1 else 0,wins=sum(x<0 for x in v),ties=sum(x==0 for x in v),losses=sum(x>0 for x in v),chosen=selected)
for count,choices in [(2,[1,2]),(4,[3,4,5,6])]:
    for key in ['raw','merit','moves']:
        collect(f'{count}/{key}',[min(choices,key=lambda i:r[i][key])for r in rows])
    for kind in range(3):
        for length in range(5):
            for adjusted in ['moves','adjusted']:
                collect(f'{count}/{kind}/{256<<length}/{adjusted}',[min(choices,key=lambda i:r[i]['training'][kind][length][adjusted])for r in rows])
(p/'summary.json').write_text(json.dumps(summary,indent=2))
for key,value in summary.items():print(key,{k:v for k,v in value.items()if k!='chosen'})
