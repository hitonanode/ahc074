"""Build compact retained summaries after the reproduction commands in README.

Input JSONs are transient measurement output. Statistics use independent seeds,
not individual orders, and rejected designs are never scored as real runs.
"""
import sys
sys.dont_write_bytecode=True
import collections,csv,json,math,re,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(name):return json.loads((HERE/name).read_text())
def stats(xs,delta=False):
    result={'n':len(xs),'mean':statistics.mean(xs),
        'se':statistics.stdev(xs)/math.sqrt(len(xs)) if len(xs)>1 else 0}
    if delta:result.update(wins=sum(x<0 for x in xs),ties=sum(x==0 for x in xs),losses=sum(x>0 for x in xs))
    return result

def main():
    measure=read('measure_0_40.json');projection=read('projection_0_40.json')
    saved={r['seed']:r for r in projection['records']}
    routing=read('validation_0_40_64.json')
    rows=routing['records'];rs={}
    assert all(r[k]['status']=='ok' for r in rows for k in ('baseline','selected_actual','conditional_actual'))
    for label,subset in [('all_0_40',rows),('heldout_4_40',[r for r in rows if r['seed']>=4])]:
        datasets={
            'baseline':[r['baseline']['moves']/1024 for r in subset],
            'selected':[r['selected_actual']['moves']/1024 for r in subset],
            'selected_minus_baseline':[(r['selected_actual']['moves']-r['baseline']['moves'])/1024 for r in subset],
            'selected_minus_saved':[(r['selected_actual']['moves']-saved[r['seed']]['moves'])/1024 for r in subset],
            'conditional_minus_saved':[(r['conditional_actual']['moves']-saved[r['seed']]['moves'])/1024 for r in subset],
            'saved':[saved[r['seed']]['moves']/1024 for r in subset],
            'exports':[saved[r['seed']]['exports']/1024 for r in subset]}
        rs[label]={k:stats(v,'minus' in k) for k,v in datasets.items()}
        rs[label]['selections']=dict(collections.Counter(r['selected'] for r in subset))
    rs['training_status']=dict(collections.Counter(t['status'] for r in rows for t in r['training']))
    rs['selected_seconds']=stats([r['selected_actual']['seconds'] for r in rows])
    rs['selected_seconds']['max']=max(r['selected_actual']['seconds'] for r in rows)
    rs['pool']=routing['pool'];rs['width']=routing['width']
    exact=[]
    for filename in ('capped_000.csv','capped_018.csv','capped_030.csv'):
        with (HERE/filename).open() as f:
            for row in csv.DictReader(f):
                if row['name'].startswith('mutation'):continue
                for k in ('access_rate','cost','span'):row[k]=float(row[k])
                row['iters']=int(row['iters']);exact.append(row)
    feasibility=read('physical_feasibility.json')
    audit=read('controller_audit_0_8.json')
    result={
        'saved_run':measure['run'],'units':'moves per order; SE across seeds unless stated',
        'measurement':measure['summary'],'projection':projection['summary'],
        'background':read('background.json'),'exact_capped_mdp':exact,'routing':rs,
        'resident_8_cases':read('resident_validation_0_8.json')['summary'],
        'borrowed_port_8_cases':read('borrowed_0_8.json')['summary'],
        'controller_audit_8_cases':audit['summary'],
        'independent_model_replay':{'series':len(audit['records']),
            'requests':sum(r['verification']['requests'] for r in audit['records']),
            'moves':sum(r['verification']['moves'] for r in audit['records']),
            'mistakes':sum(r['verification']['mistakes'] for r in audit['records'])},
        'physical_feasibility':{k:v for k,v in feasibility.items() if k!='records'},
        'physical_output_64_orders':[read('work/physical0_baseline.json'),read('work/physical0_full.json')],
        'official_tester_replay':{'seed':0,'kind':'resident28 full','N':64,'K':192,'P':256,'R':64,
            'Score':int(re.search(r'Score = (\d+)',(HERE/'work/physical0_full.tester.err').read_text()).group(1)),
            'purpose':'rules verification of prepared output, not a contest benchmark'}
    }
    (HERE/'SUMMARY.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    with (HERE/'cases.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['seed','heldout','selected','local_baseline_moves','selected_moves','conditional_moves','saved_module_moves','saved_exported_holes','selected_seconds'])
        for r in rows:writer.writerow([r['seed'],int(r['seed']>=4),r['selected'],r['baseline']['moves'],r['selected_actual']['moves'],r['conditional_actual']['moves'],saved[r['seed']]['moves'],saved[r['seed']]['exports'],r['selected_actual']['seconds']])
    with (HERE/'controllers.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['family','seed','variant','baseline_moves','candidate_moves','generic_delta_moves','candidate_internal_moves','candidate_external_moves'])
        for family,filename in [('resident','resident_validation_0_8.json'),('borrowed','borrowed_0_8.json')]:
            for r in read(filename)['records']:
                base=r['results'][0] if family=='resident' else r['baseline']
                delta=0 if family=='resident' else r['generic_costs'][1]-r['generic_costs'][0]
                for c in r['results']:
                    if c['kind']=='baseline':continue
                    writer.writerow([family,r['seed'],c['kind'],base['moves'],c['moves'],delta,c['internal'],c['external']])
    print(json.dumps({'retained':['SUMMARY.json','cases.csv','controllers.csv'],'routing_heldout':rs['heldout_4_40'],'verification':result['independent_model_replay']},indent=2))

if __name__=='__main__':main()
