"""Fixed candidate pool; choose on independent synthetic orders, test once.

At most four external C++ processes. The baseline is only a comparison; the
selected new design never switches opacity or algorithms during the sequence.
"""
import sys
sys.dont_write_bytecode=True
import argparse,json,statistics,math
from concurrent.futures import ThreadPoolExecutor
from routing_search import Data,HERE

POOL=['conditional:317277','53733717','76643143','67233171','11413732']

def one(seed,width):
    data=Data(seed);training=[]
    for v in POOL:
        training.append({'variant':v,**data.evaluate(v,384,True,width,441739)})
    best=min(training,key=lambda r:r['cost'])['variant']
    rec={'seed':seed,'width':width,'selected':best,'training':training,
         'baseline':data.evaluate('baseline',1024,False,width),
         'selected_actual':data.evaluate(best,1024,False,width),
         'conditional_actual':data.evaluate(POOL[0],1024,False,width)}
    print(seed,best,rec['baseline']['cost'],rec['selected_actual']['cost'],rec['conditional_actual']['cost'],flush=True)
    return rec

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('lo',type=int);ap.add_argument('hi',type=int);ap.add_argument('--width',type=int,default=64);args=ap.parse_args()
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(lambda s:one(s,args.width),range(args.lo,args.hi)))
    projection=json.loads((HERE/'projection_0_40.json').read_text())['records'];saved={r['seed']:r for r in projection}
    summary={}
    for label,values in {
        'baseline_local':[r['baseline']['cost'] for r in rows],
        'selected_local':[r['selected_actual']['cost'] for r in rows],
        'conditional_local':[r['conditional_actual']['cost'] for r in rows],
        'selected_minus_local_baseline':[r['selected_actual']['cost']-r['baseline']['cost'] for r in rows],
        'selected_minus_saved_module_moves':[r['selected_actual']['cost']-saved[r['seed']]['moves']/1024 for r in rows],
        'conditional_minus_saved_module_moves':[r['conditional_actual']['cost']-saved[r['seed']]['moves']/1024 for r in rows],
        'saved_module_moves':[saved[r['seed']]['moves']/1024 for r in rows],
        'exports':[saved[r['seed']]['exports']/1024 for r in rows],
    }.items():
        summary[label]={'mean':statistics.mean(values),'se':statistics.stdev(values)/math.sqrt(len(values)),'wins':sum(v<0 for v in values),'ties':sum(v==0 for v in values),'losses':sum(v>0 for v in values)}
    result={'seeds':[args.lo,args.hi],'pool':POOL,'width':args.width,'summary':summary,'records':rows}
    (HERE/f'validation_{args.lo}_{args.hi}_{args.width}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)
