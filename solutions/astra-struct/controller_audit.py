"""Attribute the real moves of resident-controller local traces.

Both support choices and policies are fixed before reading test requests.
Every move is replayed independently; counts never stand in for a score.
"""
import sys
sys.dont_write_bytecode=True
import json, math, statistics, subprocess
from concurrent.futures import ThreadPoolExecutor
from borrowed_port import Borrowed
from resident_probe import Resident,HERE
from verify_model import verify

def one(seed,kind):
    data=Borrowed(seed) if kind=='borrowed' else Resident(seed,4)
    work=HERE/'work';work.mkdir(exist_ok=True)
    path=work/f'audit_{kind}_{seed}.trace'
    p=subprocess.run([str(HERE/'long_module'),'64','1.0','4',str(path)],
        input=data.make('full',1024,False),text=True,capture_output=True,check=True,timeout=120)
    assert p.stdout.strip().splitlines()[-1].startswith('ok,')
    verification=verify(path)
    tokens=iter(map(int,path.read_text().split()))
    n,r,h=next(tokens),next(tokens),next(tokens)
    papers=[(next(tokens),next(tokens),next(tokens)) for _ in range(n+1)]
    events=[(next(tokens),next(tokens)) for _ in range(r)]
    order=[n]+list(range(n));port=1<<(h-1);ordinary=port-1
    def display():
        covered=black=0
        for k in order:
            op,b,_=papers[k];black|=b&~covered;covered|=op
        return black
    counts=dict(controller_moves=0,ordinary_moves=0,controller_target_moves=0,
        controller_port_fixes=0,controller_port_breaks=0,controller_port_flips=0,
        controller_handle_fixes=0,controller_handle_breaks=0,
        controller_moves_fixing_2plus_handles=0,controller_moves_port_only=0,
        requested_port_changes=sum(bool((events[i][1]^events[i-1][1])&port) for i in range(1,r)))
    for top,target in events:
        count=next(tokens)
        for _ in range(count):
            k,d=next(tokens),next(tokens);before=display()
            order.remove(k);order.insert(d,k);after=display()
            if k<n-2:counts['ordinary_moves']+=1;continue
            counts['controller_moves']+=1
            counts['controller_target_moves']+=int(k==top)
            wrong_before=before^target;wrong_after=after^target
            fixes=wrong_before&~wrong_after;breaks=wrong_after&~wrong_before
            counts['controller_port_fixes']+=bool(fixes&port)
            counts['controller_port_breaks']+=bool(breaks&port)
            counts['controller_port_flips']+=bool((before^after)&port)
            counts['controller_handle_fixes']+=(fixes&ordinary).bit_count()
            counts['controller_handle_breaks']+=(breaks&ordinary).bit_count()
            counts['controller_moves_fixing_2plus_handles']+=(fixes&ordinary).bit_count()>=2
            counts['controller_moves_port_only']+=bool((before^after)&port) and not ((before^after)&ordinary)
    assert next(tokens,None) is None
    return dict(seed=seed,kind=kind,requests=r,verification=verification,counts=counts)

if __name__=='__main__':
    lo,hi=map(int,sys.argv[1:3]) if len(sys.argv)>2 else (0,8)
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(lambda x:one(*x),[(s,k) for s in range(lo,hi) for k in ('resident','borrowed')]))
    summary={}
    for kind in ('resident','borrowed'):
        selected=[r for r in rows if r['kind']==kind];stats={}
        for key in selected[0]['counts']:
            values=[r['counts'][key]/r['requests'] for r in selected]
            stats[key]={'mean':statistics.mean(values),'se':statistics.stdev(values)/math.sqrt(len(values))}
        summary[kind]=stats
    result={'seeds':[lo,hi],'summary':summary,'records':rows}
    (HERE/f'controller_audit_{lo}_{hi}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
