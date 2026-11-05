"""Global feasibility of comparators for saved final pairs, modulo sheet relabeling.

Only barcodes and DesignStore are read. Run with whenidle.sh, one CPU worker.
An UNSAT after blocking comparators proves that the listed assignments exhaust
all complete six-sheet comparators for these fixed 38 physical windows and pairs.
"""
import argparse, itertools, json, time
from pathlib import Path
from ortools.sat.python import cp_model

HERE=Path(__file__).resolve().parent
ROOT=Path('/home/sato/ahc074')
EDGES=list(itertools.combinations(range(6),2))
INDEX={e:i for i,e in enumerate(EDGES)}

def load_design(seed,run):
    with (ROOT/'tools/in'/f'{seed:04d}.txt').open() as f:
        n,k,p,r=map(int,f.readline().split())
        original=[sum((c=='1')<<j for j,c in enumerate(f.readline().strip())) for _ in range(p)]
    h=0xcbf29ce484222325
    for a in original:
        for byte in a.to_bytes(8,'little'):h=((h^byte)*0x100000001b3)&((1<<64)-1)
    result={}
    with (ROOT/'runs'/run/'design'/f'{h:016x}.txt').open() as f:
        for line in f:
            key,*v=line.split()
            if key=='stderr':break
            if key in ['permutation','A','edge','polarity','papers','columns','ded','handle']:
                result[key]=list(map(int,v[1:]));assert len(result[key])==int(v[0])
            else:result[key]=float(v[0]) if key=='end_sec' else int(v[0])
    assert result['G']==38 and result['M']==6 and not result['emergency']
    served=[[]for _ in range(192)]
    for u,k in enumerate(result['ded']):served[k].append(u)
    result['pairs']=[us for us in served if len(us)==2]
    assert len(result['pairs'])==71
    return result

def canonical(d):
    seen={};codes=[]
    for w in range(38):
        lo,hi=d['edge'][2*w:2*w+2];pol=d['polarity'][w]
        a,b=(lo,hi) if pol==0 else (hi,lo)
        for x in [a,b]:
            if x not in seen:seen[x]=len(seen)
        a,b=seen[a],seen[b]
        codes.append(2*INDEX[tuple(sorted([a,b]))]+int(a>b))
    return codes

def model_for(d,cost_rows=None,target=None):
    m=cp_model.CpModel()
    choice=[[m.new_bool_var(f'w{w}c{c}')for c in range(30)]for w in range(38)]
    flat=[]
    for w in range(38):
        m.add_exactly_one(choice[w])
        for color in [0,1]:
            v=m.new_int_var(0,5,f'w{w}color{color}')
            m.add(v==sum(EDGES[c//2][int((c&1)!=color)]*choice[w][c]for c in range(30)))
            flat.append(v)
    # First-use labeling eliminates the whole 6! sheet-name symmetry.
    m.add(flat[0]==0);mx=flat[0]
    for i,v in enumerate(flat[1:]):
        m.add(v<=mx+1);nxt=m.new_int_var(0,5,f'prefix{i}')
        m.add_max_equality(nxt,[mx,v]);mx=nxt
    for e in range(15):m.add(sum(choice[w][2*e]+choice[w][2*e+1]for w in range(38))>=1)
    A=d['A']
    cost_vars=[]
    for p,(u,v) in enumerate(d['pairs']):
        if cost_rows is None:
            order=[m.new_bool_var(f'p{p}e{e}')for e in range(15)]
            for a,b,c in itertools.combinations(range(6),3):
                ab,bc,ac=order[INDEX[a,b]],order[INDEX[b,c]],order[INDEX[a,c]]
                m.add_bool_or([ab.Not(),bc.Not(),ac])
                m.add_bool_or([ab,bc,ac.Not()])
        else:
            # A transitive, asymmetric relation containing every required arc.
            # It may be a strict extension; a lower cost bound remains valid.
            rel={(a,b):m.new_bool_var(f'p{p}r{a}{b}')for a in range(6)for b in range(6)if a!=b}
            for a,b in EDGES:m.add_at_most_one([rel[a,b],rel[b,a]])
            paths={}
            for a,b,c in itertools.permutations(range(6),3):
                q=m.new_bool_var(f'p{p}path{a}{b}{c}')
                m.add_bool_and([rel[a,b],rel[b,c]]).only_enforce_if(q)
                m.add_bool_or([rel[a,b].Not(),rel[b,c].Not(),q])
                m.add_implication(q,rel[a,c]);paths[a,b,c]=q
            covers=[]
            for a,b in rel:
                q=m.new_bool_var(f'p{p}cover{a}{b}')
                intermediate=[paths[a,c,b]for c in range(6)if c not in [a,b]]
                m.add_implication(q,rel[a,b])
                for z in intermediate:m.add_at_most_one([q,z])
                m.add_bool_or([rel[a,b].Not(),q,*intermediate]);covers.append(q)
            degrees=[]
            for a in range(6):
                deg=m.new_int_var(0,35,f'p{p}degree{a}')
                m.add(deg==6*sum(rel[b,a]for b in range(6)if b!=a)+sum(rel[a,b]for b in range(6)if b!=a))
                degrees.append(deg)
            # Six inputs, fixed insertion sorting network; min/max are exact.
            for i in range(1,6):
                for j in range(i,0,-1):
                    lo=m.new_int_var(0,35,f'p{p}lo{i}{j}');hi=m.new_int_var(0,35,f'p{p}hi{i}{j}')
                    m.add_min_equality(lo,[degrees[j-1],degrees[j]])
                    m.add_max_equality(hi,[degrees[j-1],degrees[j]])
                    degrees[j-1],degrees[j]=lo,hi
            cover_count=m.new_int_var(0,15,f'p{p}covers');m.add(cover_count==sum(covers))
            value=m.new_int_var(0,4380,f'p{p}cost')
            m.add_allowed_assignments(degrees+[cover_count,value],cost_rows);cost_vars.append(value)
        for w in range(38):
            if not ((A[u]^A[v])>>w&1):continue
            for code in range(30):
                agrees=(A[u]>>w&1)==(code&1)
                if cost_rows is None:
                    above=order[code//2];required=above if agrees else above.Not()
                else:
                    a,b=EDGES[code//2];required=rel[a,b] if agrees else rel[b,a]
                m.add_bool_or([choice[w][code].Not(),required])
    if target is not None:m.add(sum(cost_vars)<=target)
    cuts=0
    for w,z in itertools.combinations(range(38),2):
        parity={((A[u]>>w)^(A[u]>>z))&1 for u,v in d['pairs'] if (A[u]^A[v])>>w&1 and (A[u]^A[v])>>z&1}
        for e in range(15):
            if len(parity)==2:
                m.add_at_most_one(choice[w][2*e:2*e+2]+choice[z][2*e:2*e+2]);cuts+=1
            elif len(parity)==1:
                q=next(iter(parity))
                for pol in [0,1]:
                    m.add_bool_or([choice[w][2*e+pol].Not(),choice[z][2*e+(pol^q^1)].Not()]);cuts+=1
    return m,choice,cuts

def solve(seed,args):
    d=load_design(seed,args.run);base=canonical(d)
    cost_rows=target=None
    if args.cost_bound:
        from bound_cost import table,cost
        t=table();value,_=cost(d,base,t)
        profiles=json.loads((HERE/'cover-profiles.json').read_text())
        cost_rows=[r['profile']+[r['min']]for r in profiles]
        target=round(value*720*256)-int(args.gain*720*256+0.999999)
    m,choice,cuts=model_for(d,cost_rows,target)
    assignments=[base];statuses=[];start=time.monotonic()
    for w,c in enumerate(base):m.add_hint(choice[w][c],1)
    while time.monotonic()-start<args.seconds and len(assignments)<=args.max_solutions:
        prev=assignments[-1]
        m.add_bool_or([choice[w][c].Not()for w,c in enumerate(prev)])
        solver=cp_model.CpSolver()
        solver.parameters.num_search_workers=1
        solver.parameters.random_seed=317
        solver.parameters.max_time_in_seconds=max(.01,args.seconds-(time.monotonic()-start))
        status=solver.solve(m)
        statuses.append({'status':solver.status_name(status),'seconds':solver.wall_time,
                         'branches':solver.num_branches,'conflicts':solver.num_conflicts})
        if status not in [cp_model.OPTIMAL,cp_model.FEASIBLE]:break
        codes=[next(c for c in range(30)if solver.value(choice[w][c]))for w in range(38)]
        assignments.append(codes)
    return {'seed':seed,'seconds':time.monotonic()-start,'pairwise_cuts':cuts,'statuses':statuses,
            'complete':bool(statuses)and statuses[-1]['status']=='INFEASIBLE','assignments':assignments,
            'cost_bound_target':target,'hamming':[sum(a!=b for a,b in zip(base,x))for x in assignments]}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',default='20261105-151134_esw-slim')
    p.add_argument('--seeds',default='0-4');p.add_argument('--seconds',type=float,default=60)
    p.add_argument('--max-solutions',type=int,default=64);p.add_argument('--output',default='csp-4.json')
    p.add_argument('--cost-bound',action='store_true');p.add_argument('--gain',type=float,default=.001)
    a=p.parse_args();lo,hi=map(int,a.seeds.split('-'));rows=[]
    for seed in range(lo,hi):
        row=solve(seed,a);rows.append(row)
        print(seed,row['seconds'],len(row['assignments']),row['complete'],row['hamming'],flush=True)
        (HERE/a.output).write_text(json.dumps({'run':a.run,'rows':rows},indent=2)+'\n')
