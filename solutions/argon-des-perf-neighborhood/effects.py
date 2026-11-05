"""Diagnose added holes from recorded operation differences (no policy selection)."""
import argparse, collections, json, statistics, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import replay
HERE=Path(__file__).resolve().parent;ROOT=Path('/home/sato/ahc074/runs')
p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('candidate');p.add_argument('--end',type=int,default=500)
p.add_argument('--general',action='store_true');p.add_argument('--output',default='effects-500.json');a=p.parse_args()
counts=collections.Counter();rows=[];alllabels=[collections.Counter(),collections.Counter()]
for seed in range(a.end):
    inp=replay.load_input(seed);pair=[]
    for run in [a.base,a.candidate]:
        folder=ROOT/run
        out=replay.parse_output(inp,(folder/'out'/f'{seed:04d}.txt').read_text())
        ann=replay.parse_annotations((folder/'err'/f'{seed:04d}.txt').read_text(),192)
        pair.append((out,ann))
    changed=[];own=set();nholes=0;restored=0
    for k,(x,y)in enumerate(zip(pair[0][0].designs,pair[1][0].designs)):
        if x!=y:
            if not a.general:assert not y.opaque&~x.opaque
            changed.append(k);nholes+=(x.opaque&~y.opaque).bit_count()
            restored+=(y.opaque&~x.opaque).bit_count()
            own.update(map(int,pair[0][1].papers['targets'][k].split(',')))
            counts['changed_'+pair[0][1].papers['role'][k]]+=1
    diff=collections.Counter();used=[collections.Counter(),collections.Counter()]
    for q,(bo,co)in enumerate(zip(pair[0][0].queries,pair[1][0].queries)):
        typ='owner'if inp.requests[q]in own else 'other';diff[typ]+=len(co)-len(bo);counts[typ+'_requests']+=1
        for arm,(ops,(_,ann))in enumerate(zip([bo,co],pair)):
            for (k,_),label in zip(ops,ann.labels_of(q,len(ops))):
                alllabels[arm][label]+=1
                if k in changed:used[arm][label]+=1
    counts.update({'changed_cases':bool(changed),'holes':nholes,'restored':restored,'owner_delta':diff['owner'],'other_delta':diff['other']})
    for arm in [0,1]:
        for k,v in used[arm].items():counts[f'changed_paper_arm{arm}_{k}']+=v
    rows.append(dict(seed=seed,papers=changed,holes=nholes,restored=restored,owner_delta=diff['owner'],other_delta=diff['other'],used=[dict(x)for x in used]))
result=dict(base=a.base,candidate=a.candidate,n=a.end,counts=dict(counts),
            label_delta={k:alllabels[1][k]-alllabels[0][k]for k in alllabels[0]},rows=rows)
(HERE/a.output).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items()if k!='rows'},indent=2))
print('worst',sorted(rows,key=lambda r:r['owner_delta']+r['other_delta'],reverse=True)[:3])
