"""A second resident-controller design: borrow one GENERIC window as the port.

This keeps all 28 ordinary columns. The new port is a hole in every ordinary
dedicated and generic sheet, and is printed by the two existing single-product
controllers. Its color must now be controlled on every order. One duplicated
comparator window is removed, so all 15 comparator witnesses remain. Exact
legal six-sheet BFS separately counts the change in generic moves.
"""
import sys
sys.dont_write_bytecode=True
import itertools,collections,json,math,statistics
from concurrent.futures import ThreadPoolExecutor
from resident_probe import Resident,HERE
from routing_search import Data
from measure import load

class Borrowed(Resident):
    def __init__(self,seed):
        self.seed=seed;self.h=4;self.first=25
        self.inp,self.out,gm,hm,self.hs,self.col,self.serves,self.ded=load(seed)
        self.members=[k for k in range(6,192) if self.col[k]>=25]
        def h3(a):return sum(((a>>self.hs[25+i])&1)<<i for i in range(3))
        by_edge=collections.defaultdict(list)
        for w in range(64):
            if gm>>w&1:by_edge[tuple(k for k in range(6) if self.out.designs[k].opaque>>w&1)].append(w)
        options=[]
        for edge,ws in by_edge.items():
            if len(ws)<2:continue
            for w in ws:
                controllers=[];quality=0
                for b in range(2):
                    candidates=[k for k in self.members if self.col[k]==27 and len(self.serves[k])==1 and self.inp.target[self.serves[k][0]]>>w&1==b]
                    if not candidates:break
                    def score(k):
                        color=h3(self.inp.target[self.serves[k][0]])
                        return sum(3-(color^h3(a)).bit_count() for a in self.inp.target if a>>w&1==b)
                    k=max(candidates,key=score);controllers.append(k);quality+=score(k)/256
                if len(controllers)==2:
                    generic_hole_rate=sum(not(self.out.designs[self.ded[u]].opaque>>w&1) for u in range(256))/256
                    options.append((quality+.2*generic_hole_rate,w,controllers))
        assert options
        _,self.port,self.ctrl=max(options)
        self.color={k:self.bits(self.inp.target[self.serves[k][0]]) for k in self.members}
        self.common={k:15 for k in self.members}
        for k in self.members:
            for u in self.serves[k]:self.common[k]&=~(self.color[k]^self.bits(self.inp.target[u]))
        self.base={k:self.bits(self.out.designs[k].opaque) for k in self.members}
        self.regular=[k for k in self.members if k not in self.ctrl]
        self.place={k:self.col[k]-25 for k in self.regular}
        self.gmask=gm
    def bits(self,a):
        return sum(((a>>self.hs[25+i])&1)<<i for i in range(3))|(((a>>self.port)&1)<<3)
    def generic_costs(self):
        perms=list(itertools.permutations(range(6)));index={p:i for i,p in enumerate(perms)}
        displays=[];edges=[]
        for p in perms:
            cov=black=0
            for k in p:black|=self.out.designs[k].black&~cov;cov|=self.out.designs[k].opaque
            displays.append(black);es=[]
            for i in range(5):
                for d in range(6):
                    if d==i:continue
                    q=list(p);k=q.pop(i);q.insert(d,k);es.append(index[tuple(q)])
            edges.append(es)
        costs=[]
        for remove in (False,True):
            current=0;cost=0;mask=self.gmask&~((1<<self.port) if remove else 0)
            for u in self.inp.requests:
                holes=mask&~self.out.designs[self.ded[u]].opaque;a=self.inp.target[u]
                queue=collections.deque([(current,0)]);seen={current}
                while queue:
                    s,d=queue.popleft()
                    if not((displays[s]^a)&holes):current=s;cost+=d;break
                    for t in edges[s]:
                        if t not in seen:seen.add(t);queue.append((t,d+1))
            costs.append(cost)
        return costs

def one(seed):
    data=Borrowed(seed);base=Data(seed).evaluate('baseline',1024,False,64)
    generic=data.generic_costs();rows=[]
    for kind in ('full','split','short'):
        r=data.run(kind,1024,False,64);rows.append({'kind':kind,**r});print(seed,kind,r.get('cost'),generic,flush=True)
    return {'seed':seed,'port':data.port,'controllers':data.ctrl,'baseline':base,'generic_costs':generic,'results':rows}

if __name__=='__main__':
    lo,hi=map(int,sys.argv[1:3]) if len(sys.argv)>2 else (0,8)
    with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(one,range(lo,hi)))
    summary={}
    for kind in ('full','split','short'):
        diffs=[];costs=[];gc=[]
        for r in records:
            x=next(x for x in r['results'] if x['kind']==kind);assert x['status']=='ok'
            g=(r['generic_costs'][1]-r['generic_costs'][0])/1024
            diffs.append(x['cost']-r['baseline']['cost']+g);costs.append(x['cost']);gc.append(g)
        def stat(xs):return {'mean':statistics.mean(xs),'se':statistics.stdev(xs)/math.sqrt(len(xs))}
        summary[kind]={'local_cost':stat(costs),'difference_including_generic':stat(diffs),'generic_difference':stat(gc),'wins':sum(d<0 for d in diffs),'ties':sum(d==0 for d in diffs),'losses':sum(d>0 for d in diffs)}
    (HERE/f'borrowed_{lo}_{hi}.json').write_text(json.dumps({'seeds':[lo,hi],'summary':summary,'records':records},indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)
