"""Value-dependent routing in a long last-three-handle bank.

Each 3-bit target value gets an opacity mask; equal local colors may share
access rules even if they originally belonged to different columns. This is
more than retaining the original own-column handle. The 34--45 actual papers
and all their product obligations remain. Pair differences stay holes.

Search uses synthetic training requests only. Final measurements use the saved
real request sequence with the design fixed. Solver is a legal bounded beam;
search failure is a failure, never a low score. No contest evaluation tools.
"""
import sys
sys.dont_write_bytecode=True
import argparse
import csv
import json
import math
import random
import subprocess
from pathlib import Path
from measure import load

HERE=Path(__file__).resolve().parent

class Data:
    def __init__(self,seed):
        self.seed=seed
        inp,out,gm,hm,hs,col,serves,ded=load(seed)
        self.inp=inp;self.out=out;self.hs=hs;self.col=col;self.serves=serves;self.ded=ded
        self.members=[k for k in range(6,192) if col[k]>=25]
        self.colors={k:self.bits(inp.target[serves[k][0]]) for k in self.members}
        self.common={k:7 for k in self.members}
        for k in self.members:
            for u in serves[k]:self.common[k]&=~(self.colors[k]^self.bits(inp.target[u]))
        self.base={k:self.bits(out.designs[k].opaque) for k in self.members}

    def bits(self,a):return sum(((a>>self.hs[25+i])&1)<<i for i in range(3))

    def masks(self,variant):
        if variant=="baseline":return self.base.copy()
        if variant.startswith("conditional"):
            # Only apply the six-card template where all three bits, not just the
            # own bit, equal that representative's bits.
            template=list(map(int,variant.split(":")[1]));rep=[0,7,1,6,2,5]
            ans=self.base.copy()
            for k in self.members:
                c=self.col[k]-25;role=2*c+((self.colors[k]>>c)&1)
                if self.colors[k]==rep[role]:ans[k]=template[role]&self.common[k]
            return ans
        if variant.startswith("six:"):
            template=list(map(int,variant[4:]));ans={}
            for k in self.members:
                c=self.col[k]-25;role=2*c+((self.colors[k]>>c)&1)
                ans[k]=template[role]&self.common[k]
            return ans
        template=list(map(int,variant))
        return {k:template[self.colors[k]]&self.common[k] for k in self.members}

    def input(self,variant,count=256,train=True,train_seed=441739):
        masks=self.masks(variant)
        members=self.members.copy()
        if len(variant)==8:members.sort(key=lambda k:(masks[k],self.colors[k],k))
        index={k:i for i,k in enumerate(members)};cap=len(members)
        rng=random.Random(train_seed+self.seed)
        if train:
            requests=[];prev=-1
            for _ in range(count):
                u=rng.randrange(256)
                while u==prev:u=rng.randrange(256)
                requests.append(u);prev=u
        else:requests=self.inp.requests[:count]
        checks=sorted({(index.get(self.ded[u],cap),self.bits(a)) for u,a in enumerate(self.inp.target)})
        lines=[f"{cap} {len(requests)} {len(checks)}"]
        for k in members:lines.append(f"{masks[k]} {masks[k]&self.colors[k]} {len(self.serves[k])/256} {int(len(self.serves[k])==2)}")
        lines.append(f"0 0 {sum(d not in index for d in self.ded)/256} 0")
        lines.extend(f"{k} {b}" for k,b in checks)
        lines.extend(f"{index.get(self.ded[u],cap)} {self.bits(self.inp.target[u])}" for u in requests)
        return "\n".join(lines)+"\n"

    def evaluate(self,variant,count=256,train=True,width=24,train_seed=441739):
        text=self.input(variant,count,train,train_seed)
        p=subprocess.run([str(HERE/"long_module"),str(width),"1.0"],input=text,text=True,capture_output=True,timeout=30,check=True)
        lines=p.stdout.strip().splitlines()
        if not lines or not lines[-1].startswith("ok,"):return {"status":p.stdout.strip(),"cost":100}
        v=lines[-1].split(",")
        return {"status":"ok","cost":float(v[4]),"moves":int(v[3]),"n":int(v[1]),"internal":int(v[5]),"external":int(v[6]),"accesses":int(v[7]),"expanded":int(v[9]),"seconds":float(v[10]),"batches":list(map(int,v[11:19])),"constructive_used":int(v[19])}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("seed",type=int);ap.add_argument("--trials",type=int,default=100);ap.add_argument("--count",type=int,default=256);ap.add_argument("--width",type=int,default=24)
    args=ap.parse_args();data=Data(args.seed);rng=random.Random(390148+args.seed)
    cache={};records=[]
    def ev(v):
        if v not in cache:
            res=data.evaluate(v,args.count,True,args.width);cache[v]=res;records.append({"variant":v,**res})
            print(args.seed,v,res["status"],res["cost"],flush=True)
        return cache[v]["cost"]
    ev("baseline")
    for v in ["six:317277","conditional:317277","six:713274","conditional:713274"]:ev(v)
    # Balanced triangular routing by local value, then genuine non-triangular
    # masks. The baseline is not a fallback inside any candidate execution.
    initial=["13777731","17373771","77133177","12345671","77777777"]
    for v in initial:ev(v)
    cur=min(initial,key=lambda v:cache[v]["cost"]);cv=ev(cur);best=cur;bv=cv
    for t in range(args.trials):
        chars=list(cur)
        for _ in range(1+(t%7==6)):
            j=rng.randrange(8);chars[j]=str(rng.randrange(1,8))
        cand="".join(chars);val=ev(cand)
        temp=.15*(1-t/max(1,args.trials))+.01
        if val<cv or rng.random()<math.exp(min(0,(cv-val)/temp)):cur,cv=cand,val
        if val<bv:best,bv=cand,val
    # Evaluate the picked design against the same physical-paper baseline on an
    # independent synthetic sequence and on all actual orders.
    selected=["baseline","conditional:317277",best]
    tests=[]
    for v in selected:
        tests.append({"variant":v,"independent":data.evaluate(v,1024,True,args.width,997451),"actual":data.evaluate(v,1024,False,args.width)})
    result={"seed":args.seed,"training_count":args.count,"beam_width":args.width,"best":best,"records":records,"tests":tests}
    (HERE/f"routing_{args.seed}.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"seed":args.seed,"best":best,"tests":tests}),flush=True)

if __name__=="__main__":main()
