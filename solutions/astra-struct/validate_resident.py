"""Replicate all controller variants; no selection on test orders."""
import sys
sys.dont_write_bytecode=True
import json,statistics,math
from concurrent.futures import ThreadPoolExecutor
from resident_probe import Resident,HERE

def one(seed):
    data=Resident(seed,4);rows=[]
    for kind in ('baseline','full','split','short'):
        result=data.run(kind,1024,False,64);rows.append({'kind':kind,**result})
        print(seed,kind,result.get('cost'),flush=True)
    return {'seed':seed,'controllers':data.ctrl,'columns':[sum(c==i for c in data.place.values()) for i in range(3)],'results':rows}

if __name__=='__main__':
    lo,hi=map(int,sys.argv[1:3]) if len(sys.argv)>2 else (0,8)
    with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(one,range(lo,hi)))
    summary={}
    for kind in ('baseline','full','split','short'):
        costs=[];deltas=[];di=[];de=[]
        for r in records:
            base=r['results'][0];x=next(v for v in r['results'] if v['kind']==kind)
            assert x['status']=='ok' and base['status']=='ok'
            costs.append(x['cost']);deltas.append(x['cost']-base['cost'])
            di.append((x['internal']-base['internal'])/1024);de.append((x['external']-base['external'])/1024)
        def stat(xs):return {'mean':statistics.mean(xs),'se':statistics.stdev(xs)/math.sqrt(len(xs))}
        summary[kind]={'cost':stat(costs),'difference':stat(deltas),'internal_difference':stat(di),'external_difference':stat(de),'wins':sum(x<0 for x in deltas),'ties':sum(x==0 for x in deltas),'losses':sum(x>0 for x in deltas)}
    result={'seeds':[lo,hi],'handles':4,'width':64,'summary':summary,'records':records}
    (HERE/f'resident_validation_{lo}_{hi}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)
