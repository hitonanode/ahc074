"""Two existing dedicated sheets become resident multi-window controllers.

One existing handle is made a shared rescue port: all other papers have a hole
there. The two controllers have opposite colors at the port and retain their
own product obligations. Thus the upper controller is visible at any depth;
no extra physical paper is introduced. Other papers in the lost column are
redistributed to the remaining local columns, and their new holes are charged.
The complete long local state, current target extraction, later cap recovery,
and exact visible-sheet transitions are simulated by long_module.cpp.
"""
import sys
sys.dont_write_bytecode=True
import argparse,json,random,subprocess
from pathlib import Path
from measure import load
HERE=Path(__file__).resolve().parent

class Resident:
    def __init__(self,seed,h):
        self.seed=seed;self.h=h;self.first=28-h
        self.inp,self.out,gm,hm,self.hs,self.col,self.serves,self.ded=load(seed)
        self.members=[k for k in range(6,192) if self.col[k]>=self.first]
        self.color={k:self.bits(self.inp.target[self.serves[k][0]]) for k in self.members}
        self.common={k:(1<<h)-1 for k in self.members}
        for k in self.members:
            for u in self.serves[k]:self.common[k]&=~(self.color[k]^self.bits(self.inp.target[u]))
        self.base={k:self.bits(self.out.designs[k].opaque) for k in self.members}
        ctrl=[]
        for b in range(2):
            candidates=[k for k in self.members if self.col[k]==27 and len(self.serves[k])==1 and self.color[k]>>(h-1)==b]
            # Product data only, never future orders. Prefer agreement with the
            # conditional majority of the other handle bits.
            def quality(k):return sum((h-1)-((self.bits(a)^self.color[k])&((1<<(h-1))-1)).bit_count() for a in self.inp.target if self.bits(a)>>(h-1)==b)
            if not candidates:raise ValueError('no single controller of both colors')
            ctrl.append(max(candidates,key=quality))
        self.ctrl=ctrl
        columns={c:[k for k in self.members if self.col[k]-self.first==c] for c in range(h-1)}
        placement={k:self.col[k]-self.first for k in self.members if self.col[k]<27}
        for k in self.members:
            if self.col[k]!=27 or k in ctrl:continue
            weight=len(self.serves[k])
            def score(c):
                v=columns[c];nc=len(v);wc=sum(len(self.serves[x]) for x in v)
                balance=sum(1 if self.color[x]>>c&1 else -1 for x in v)+(1 if self.color[k]>>c&1 else -1)
                holes=((1<<(c+1))-1)&~self.common[k]
                return (wc+weight*nc)/2 + weight*((h-2-c)+holes.bit_count())*.5 + max(0,abs(balance)-1)**2
            legal=[c for c in columns if self.common[k]>>c&1]
            if not legal:raise ValueError('pair has no remaining common access bit')
            c=min(legal,key=score);columns[c].append(k);placement[k]=c
        self.place=placement
        self.regular=[k for c in range(h-1) for k in columns[c]]

    def bits(self,a):return sum(((a>>self.hs[self.first+i])&1)<<i for i in range(self.h))
    def make(self,kind,count,train):
        h=self.h
        if kind=='baseline':members=self.members.copy();masks=self.base.copy()
        else:
            members=self.regular+self.ctrl
            masks={k:((1<<(self.place[k]+1))-1)&self.common[k] for k in self.regular}
            rescue=1<<(h-1)
            for b,k in enumerate(self.ctrl):
                if kind=='full':masks[k]=(1<<h)-1
                elif kind=='split':masks[k]=rescue|sum(1<<j for j in range(h-1) if j%2==b)
                elif kind=='short':masks[k]=rescue|((1<<(h-1 if b else max(1,(h-1)//2)))-1)
                else:raise ValueError(kind)
        index={k:i for i,k in enumerate(members)};cap=len(members)
        if train:
            rng=random.Random(613783+self.seed);requests=[];prev=-1
            for _ in range(count):
                u=rng.randrange(256)
                while u==prev:u=rng.randrange(256)
                requests.append(u);prev=u
        else:requests=self.inp.requests[:count]
        checks=sorted({(index.get(self.ded[u],cap),self.bits(a)) for u,a in enumerate(self.inp.target)})
        lines=[f'{cap} {len(requests)} {len(checks)}']
        for k in members:lines.append(f'{masks[k]} {masks[k]&self.color[k]} {len(self.serves[k])/256} {int(len(self.serves[k])==2)}')
        lines.append(f'0 0 {sum(d not in index for d in self.ded)/256} 0')
        lines.extend(f'{k} {b}' for k,b in checks)
        lines.extend(f'{index.get(self.ded[u],cap)} {self.bits(self.inp.target[u])}' for u in requests)
        return '\n'.join(lines)+'\n'

    def run(self,kind,count,train,width):
        p=subprocess.run([str(HERE/'long_module'),str(width),'1.0',str(self.h)],input=self.make(kind,count,train),text=True,capture_output=True,timeout=180,check=True)
        lines=p.stdout.strip().splitlines();last=lines[-1].split(',') if lines else []
        if not last or last[0]!='ok':return {'status':p.stdout.strip()}
        return {'status':'ok','n':int(last[1]),'cost':float(last[4]),'moves':int(last[3]),'internal':int(last[5]),'external':int(last[6]),'accesses':int(last[7]),'expanded':int(last[9]),'seconds':float(last[10]),'batches':list(map(int,last[11:19])),'constructive_used':int(last[19])}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('seed',type=int);p.add_argument('--handles',type=int,default=4);p.add_argument('--count',type=int,default=1024);p.add_argument('--width',type=int,default=24);p.add_argument('--train',action='store_true')
    args=p.parse_args();data=Resident(args.seed,args.handles);rec=[]
    for kind in ('baseline','full','split','short'):
        result=data.run(kind,args.count,args.train,args.width);rec.append({'kind':kind,**result});print(kind,result,flush=True)
    result={'seed':args.seed,'handles':args.handles,'count':args.count,'width':args.width,'train':args.train,'controllers':data.ctrl,'columns':[sum(c==i for c in data.place.values()) for i in range(args.handles-1)],'results':rec}
    (HERE/f'resident_{args.seed}_{args.handles}_{args.width}.json').write_text(json.dumps(result,indent=2)+'\n')
