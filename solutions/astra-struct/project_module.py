"""Project the actual saved policy onto the last three handles plus data cap.

Counts permission/goal violations before treating it as a legal local policy.
Exports to earlier handles are counted separately: the isolated model cannot
claim that their value is retained. All source reads are read-only.
"""
import sys
sys.dont_write_bytecode=True
import json,statistics,math
from pathlib import Path
from measure import load,RUN
import replay

def one(seed,first=25):
    inp,out,gm,hm,hs,col,serves,ded=load(seed)
    members={k for k in range(6,192) if col[k]>=first}
    mm=sum(1<<w for w in hs[first:]);earlier=hm^mm
    game=replay.Game(inp,out.designs)
    count=dict(moves=0,projected_moves=0,permission_failures=0,cap_changes=0,goal_top_failures=0,goal_color_failures=0,exports=0,exporting_papers=0,external_requests=0,internal_requests=0)
    examples=[]
    def projected():
        ans=[];cap=False
        for k in game.order:
            if k in members:ans.append(k)
            elif k<6 and not cap:ans.append(-1);cap=True
        return ans
    for r,ops in enumerate(out.queries):
        d=ded[inp.requests[r]]
        count["internal_requests" if d in members else "external_requests"]+=1
        for k,depth in ops:
            before=projected()
            if k in members:
                count['moves']+=1;cov=0;vis={before[0]}
                for x in before:
                    if x>=0:
                        op=out.designs[x].opaque&mm
                        if op&~cov:vis.add(x)
                        cov|=op
                if k not in vis:
                    count['permission_failures']+=1
                    if len(examples)<6:examples.append([seed,r,k,'local_hidden'])
            game.move(k,depth,check=False)
            after=projected()
            if before!=after:
                count['projected_moves' if k in members else 'cap_changes']+=1
        q=projected()
        expected=d if d in members else -1
        if q[0]!=expected:
            count['goal_top_failures']+=1
            if len(examples)<6:examples.append([seed,r,d,'goal_top'])
        black=cov=0
        for x in q:
            if x>=0:
                p=out.designs[x];black|=p.black&mm&~cov;cov|=p.opaque&mm
        count['goal_color_failures']+=((black^inp.target[inp.requests[r]])&mm)!=0
        # Only holes of the real target paper count as export benefit.
        holes=earlier&~out.designs[d].opaque
        cov=0;exporters=set()
        for k in game.order:
            p=out.designs[k];exposed=p.opaque&~cov&holes;cov|=p.opaque
            if exposed and k in members:
                count['exports']+=exposed.bit_count();exporters.add(k)
        count['exporting_papers']+=len(exporters)
    return {'seed':seed,'n':len(members),**count,'examples':examples}

if __name__=='__main__':
    lo,hi=map(int,sys.argv[1:3]) if len(sys.argv)>2 else (0,40)
    h=int(sys.argv[3]) if len(sys.argv)>3 else 3
    rec=[one(s,28-h) for s in range(lo,hi)];summary={}
    for k in rec[0]:
        if k in ('seed','examples'):continue
        xs=[r[k]/(1 if k=='n' else 1024) for r in rec]
        summary[k]={'mean':statistics.mean(xs),'se':statistics.stdev(xs)/math.sqrt(len(xs)) if len(xs)>1 else 0}
    result={'run':RUN.name,'seeds':[lo,hi],'summary':summary,'records':rec}
    name=f'projection_{lo}_{hi}.json' if h==3 else f'projection_h{h}_{lo}_{hi}.json'
    Path(__file__).with_name(name).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
