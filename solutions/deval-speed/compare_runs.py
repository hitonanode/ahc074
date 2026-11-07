"""Paired timing and stdout identity. Run under the shared flock."""
from pathlib import Path
import argparse,json,hashlib,re
import numpy as np
RUNS=Path('/home/sato/ahc074/runs')
def load(run):
    metrics=json.loads((RUNS/run/'metrics.json').read_text())['cases']
    return {int(k):v for k,v in metrics.items()}
def main():
    p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('candidate');p.add_argument('output');a=p.parse_args()
    x=load(a.reference);y=load(a.candidate);seeds=sorted(set(x)&set(y))
    sx={int(c['seed']):c['score'] for c in json.loads((RUNS/a.reference/'result.json').read_text())['cases']}
    sy={int(c['seed']):c['score'] for c in json.loads((RUNS/a.candidate/'result.json').read_text())['cases']}
    wa=[s for s in seeds if sx.get(s,0)<=0 or sy.get(s,0)<=0]
    if wa:
        out={'reference':a.reference,'candidate':a.candidate,'n':len(seeds),'wa':wa,'status':'invalid'}
        Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
        print('invalid comparison',a.candidate,'WA',len(wa));return
    def times(case):
        d=dict(case['stderr']);d['judge']=1.04*d['helper_end_sec']+1.35*d['req_sec']+d['end_sec']-d['helper_end_sec']-d['req_sec'];return d
    xt=[times(x[s]) for s in seeds];yt=[times(y[s]) for s in seeds]
    stage={}
    for key in ['judge','end_sec','helper_end_sec','map_end_sec','dv_anneal_sec','dv_finish_sec','dv_eval_sec','req_sec','climb_end_sec','match_sec','perforation_sec','d2_rematch_sec']:
        if not all(key in row for row in xt+yt):continue
        b=np.array([r[key] for r in xt]);c=np.array([r[key] for r in yt]);diff=c-b
        stage[key]={'reference_mean':float(b.mean()),'candidate_mean':float(c.mean()),'delta':float(diff.mean()),'se':float(diff.std(ddof=1)/len(seeds)**.5),
                    'ratio':float(c.mean()/b.mean()),'reference_p99':float(np.quantile(b,.99)),'candidate_p99':float(np.quantile(c,.99)),
                    'reference_max':float(b.max()),'candidate_max':float(c.max())}
    left=RUNS/a.reference/'out';right=RUNS/a.candidate/'out'
    mismatches=[];changed_count=[];unexplained=[]
    for f in sorted(left.glob('*.txt')):
        g=right/f.name
        if not g.exists():continue
        seed=int(f.stem)
        countdiff=x[seed]['stderr'].get('dv_candidates')!=y[seed]['stderr'].get('dv_candidates')
        if countdiff:changed_count.append(seed)
        if f.read_bytes()!=g.read_bytes():
            mismatches.append(seed)
            if not countdiff:unexplained.append(seed)
    sx={int(c['seed']):c['score'] for c in json.loads((RUNS/a.reference/'result.json').read_text())['cases']}
    sy={int(c['seed']):c['score'] for c in json.loads((RUNS/a.candidate/'result.json').read_text())['cases']}
    assert min([sx[s] for s in seeds]+[sy[s] for s in seeds])>0
    diff=np.array([100*np.log(sy[s]/sx[s]) for s in seeds])
    out={'reference':a.reference,'candidate':a.candidate,'n':len(seeds),'stdout_mismatches':mismatches,'candidate_count_changes':changed_count,'unexplained':unexplained,
         'score':{'mean':float(diff.mean()),'se':float(diff.std(ddof=1)/len(seeds)**.5),'wtl':[int((diff<0).sum()),int((diff==0).sum()),int((diff>0).sum())]},'time':stage}
    Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
    print('n',len(seeds),'identity',len(seeds)-len(mismatches),'mismatches',len(mismatches),mismatches[:20],'count changes',len(changed_count),'unexplained',len(unexplained),unexplained[:20])
    print('score',out['score'])
    for k,v in stage.items():print(k,f"{v['reference_mean']:.6f} -> {v['candidate_mean']:.6f} delta {v['delta']:+.6f} +- {v['se']:.6f} ratio {v['ratio']:.4f}")
if __name__=='__main__':main()
