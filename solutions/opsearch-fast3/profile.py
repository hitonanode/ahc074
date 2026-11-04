"""Summarize saved time/yield traces. Does not run a solver."""
import sys, json, re
from pathlib import Path
from collections import defaultdict
rid=sys.argv[1]
root=Path('/home/sato/ahc074/runs')/rid
files=list(root.glob('err/*.txt'))+list(root.glob('orders/*/err/*.txt'))
ops=defaultdict(lambda:[0.0]*6)
posts=defaultdict(lambda:[0.0]*4)
post_buckets=defaultdict(lambda:[0.0]*4)
candidates=defaultdict(lambda:[0.0]*5)
for f in files:
    for line in f.read_text().splitlines():
        if line.startswith('#f3op '):
            p=line.split(); req,stage,round_,length,repeats,extras,op,trials,legal,accepts=map(int,p[1:11]); gain=float(p[11]); saved=int(p[12]); sec=float(p[13])
            for key in [(stage,op,'all'),(stage,op,'repeat' if repeats else 'unique'),(stage,op,'long' if length>=8 else 'short')]:
                dst=ops[key]
                for i,v in enumerate([trials,legal,accepts,gain,saved,sec]):dst[i]+=v
        elif line.startswith('#f3post '):
            p=line.split(); req,stage,round_,length,repeats,extras=map(int,p[1:7]);gain=float(p[7]);out=int(p[8]);sec=float(p[9])
            dst=posts[stage]
            for i,v in enumerate([1,gain,length-out,sec]):dst[i]+=v
            keys=[]
            if stage==2: keys.append('eject_round_'+str(round_))
            if stage in (5,6): keys.extend(['neutral_'+('repeat' if repeats else 'unique'), 'neutral_'+('long' if length>=8 else 'short'), 'neutral_fillers_'+('0' if not extras else '1' if extras==1 else '2+')])
            for key in keys:
                for i,v in enumerate([1,gain,length-out,sec]):post_buckets[key][i]+=v
        elif line.startswith('#heavycand '):
            p=line.split(); rnd=int(p[2]);origin=p[3];rank=int(p[4]);parent=int(p[5]);length=int(p[6]);delta=float(p[7]);repeats=int(p[8]);dead=int(p[9]);removed=int(p[10]);added=int(p[11]);out=int(p[12]);gain=float(p[13]);net=float(p[14]);better=int(p[15])
            if len(p)>16:
                dst=candidates[(0,'any','hides1+' if int(p[16]) else 'hides0')]
                for i,v in enumerate([1,better,gain,length-out,max(0,net) if better else 0]):dst[i]+=v
            for key in [(rank,origin,'all'),(rank,origin,'repeat' if repeats else 'unique'),(rank,origin,'same-state' if abs(delta)<1e-9 else 'delta<=0' if delta<=0 else 'delta>0'),(rank,origin,'dead' if dead else 'visible')]:
                dst=candidates[key]
                for i,v in enumerate([1,better,gain,length-out,max(0,net) if better else 0]):dst[i]+=v
print('cases',len(files))
print('stage calls gain moves seconds (per case)')
for k,v in sorted(posts.items()):print(k,*[round(x/len(files),6) for x in v])
print('stage operator type trials legal accepts gain moves seconds (per case)')
for k,v in sorted(ops.items()):
    if k[-1]=='all':print(k,*[round(x/len(files),6) for x in v])
print('rank origin type calls wins gain saved winning_net (per case)')
for k,v in sorted(candidates.items()):print(k,*[round(x/len(files),6) for x in v])
Path('solutions/opsearch-fast3/'+rid+'-profile.json').write_text(json.dumps({'cases':len(files),'posts':{str(k):v for k,v in posts.items()},'ops':{str(k):v for k,v in ops.items()},'candidates':{str(k):v for k,v in candidates.items()}},indent=2)+'\n')

Path('solutions/opsearch-fast3/'+rid+'-buckets.json').write_text(json.dumps({k:[x/len(files) for x in v] for k,v in post_buckets.items()},indent=2)+'\n')
