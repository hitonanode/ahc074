"""Saved-output analysis only; run through whenidle.sh, with one CPU core."""
import argparse, collections, json, math, statistics, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import replay

HERE=Path(__file__).resolve().parent
ROOT=Path('/home/sato/ahc074')

def load_design(seed,run):
    inp=replay.load_input(seed)
    h=0xcbf29ce484222325
    for a in inp.target:
        for byte in a.to_bytes(8,'little'):h=((h^byte)*0x100000001b3)&((1<<64)-1)
    d={}
    with (ROOT/'runs'/run/'design'/f'{h:016x}.txt').open() as f:
        for line in f:
            key,*v=line.split()
            if key=='stderr':break
            if key in ['permutation','A','edge','polarity','papers','columns','ded','handle']:
                d[key]=list(map(int,v[1:]))
            else:d[key]=float(v[0]) if key=='end_sec' else int(v[0])
    return inp,d

def static_heads(d):
    H=d['H'];columns=d['columns'];served=[[]for _ in range(192)]
    for u,k in enumerate(d['ded']):served[k].append(u)
    target=[sum(((a>>h)&1)<<c for c,h in enumerate(d['handle']))for a in d['A']]
    opacity=[0]*192;colors=[0]*192;counts=[[0,0]for _ in range(H)];demands=[0]*H
    for k in range(7,192):
        c=columns[k];u=served[k][0];v=served[k][-1]
        opacity[k]=((1<<(c+1))-1)&~(target[u]^target[v]);colors[k]=target[u]
        for t in served[k]:
            demands[c]+=1
            for j in range(H):
                if not opacity[k]>>j&1:counts[j][target[t]>>j&1]+=1
    prob=[]
    for c,(x,y) in enumerate(counts):
        reset=2*demands[c];p=(y+reset*(y>x))/(x+y+reset)
        prob.append([1-p,p])
    utility=[0.0]*192
    for k in range(7,192):
        c=columns[k]
        for u in range(256):
            mask=opacity[k]&~opacity[d['ded'][u]]
            lo=((colors[k]^target[u])&mask).bit_length()
            if lo>=c:continue
            cover=mask&((1<<c)-1)&~((1<<lo)-1)
            p0=1.;p1=0.;expected=0.
            while cover:
                bit=cover&-cover;cover-=bit;j=bit.bit_length()-1
                p=prob[j][(target[u]>>j&1)^1];expected+=p
                p1=p1*(1-p)+p0*p;p0*=1-p
            utility[k]+=max(0.,expected-(1-p0)-.6*(1-p0-p1))
    rank=[-1]*192;members={};head={}
    for c in range(H):
        for b in [0,1]:
            group=[k for k in range(7,192)if columns[k]==c and (colors[k]>>c&1)==b]
            group.sort(key=lambda k:(-len(served[k]),-utility[k],k))
            members[c,b]=group;head[c,b]=group[0]
            for i,k in enumerate(group):rank[k]=i
    return rank,head,members,utility

def analyze(seed,run):
    inp,d=load_design(seed,run);rank,head,members,utility=static_heads(d)
    r=ROOT/'runs'/run;out=replay.parse_output(inp,(r/'out'/f'{seed:04d}.txt').read_text())
    ann=replay.parse_annotations((r/'err'/f'{seed:04d}.txt').read_text(),192)
    assert not replay.check_annotations(ann,out)
    cols=d['columns'];H=d['H'];game=replay.Game(inp,out.designs)
    hmask=sum(1<<d['permutation'][h]for h in d['handle'])
    physical_to_handle={d['permutation'][h]:c for c,h in enumerate(d['handle'])}
    totals=collections.Counter();byhandle=collections.Counter();top=[0]*192;colortop=[0]*192;fill=[0]*192
    for q,ops in enumerate(out.queries):
        for (k,depth),label in zip(ops,ann.labels_of(q,len(ops))):
            if label in ['fill','reuse','relevel','help','repair']:
                totals[f'{label}_rank{rank[k]}']+=1
            game.move(k,depth,check=False)
        cur=H;gen_seen=False;inplace=[[]for _ in range(H)];fillers=[]
        for pos in range(191,-1,-1):
            k=game.order[pos];c=cols[k]
            if c<0:
                if 1<=k<=6:gen_seen=True
            elif not gen_seen and c<=cur:
                cur=c;inplace[c].append(k)
            elif pos==0 or (pos==1 and game.order[0]==0):pass
            else:fillers.append(k)
        for group in inplace:
            if not group:continue
            group.reverse();top[group[0]]+=1;seen=set()
            for k in group:
                b=int(ann.papers['hcolor'][k])
                if b not in seen:colortop[k]+=1;seen.add(b)
        visible=game.exposed()
        for k in fillers:
            totals[f'occupancy_rank{rank[k]}']+=1;fill[k]+=1
            bits=visible.get(k,0)&hmask
            totals[f'visible_handles_rank{rank[k]}']+=bits.bit_count()
            while bits:
                bit=bits&-bits;bits-=bit
                byhandle[f'{rank[k]}:{physical_to_handle[bit.bit_length()-1]}']+=1
        totals['orders']+=1
    # Every head which was perforated must belong to the reconstructed first rank.
    bad=[k for k in range(7,192)if int(ann.papers['perf'][k]) and rank[k]!=0]
    assert not bad,(seed,bad)
    return dict(seed=seed,counts=dict(totals),handles=dict(byhandle),top=top,colortop=colortop,
                filler=fill,rank=rank,utility=utility,columns=cols,
                colors=[int(x)if x!='-' else -1 for x in ann.papers['hcolor']])

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',default='20261105-151134_esw-slim')
    p.add_argument('--start',type=int,default=0);p.add_argument('--end',type=int,default=200)
    p.add_argument('--output',default='exposure-200.json');a=p.parse_args()
    rows=[]
    for seed in range(a.start,a.end):
        rows.append(analyze(seed,a.run))
        if len(rows)%20==0:print('done',len(rows),flush=True)
    counts=collections.Counter();handles=collections.Counter();tops=collections.Counter();ctops=collections.Counter()
    for row in rows:
        counts.update(row['counts']);handles.update(row['handles'])
        for k in range(7,192):
            tops[row['rank'][k]]+=row['top'][k];ctops[row['rank'][k]]+=row['colortop'][k]
    result=dict(run=a.run,n=len(rows),counts=dict(counts),handles=dict(handles),
                top_by_rank=dict(tops),color_top_by_rank=dict(ctops),rows=rows)
    (HERE/a.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in ['rows','handles']},indent=2))

if __name__=='__main__':main()
