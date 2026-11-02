"""Turn a whole-H resident model trace into a real N=64,K=192,P=256 output.

The cap is expanded into the ORIGINAL six generic sheets. For every pair order,
reorder these sheets by BFS while they are uncovered, before lifting D. All
operations and all 64 windows are independently checked by scripts/replay.py.
Only the requested trace length is verified; a shortened input is written for
official-tester replay, not presented as a contest score.
"""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import itertools,json,collections
from resident_probe import Resident,HERE
import replay

def convert(seed,kind,trace_path,prefix):
    data=Resident(seed,28);tokens=iter(map(int,Path(trace_path).read_text().split()))
    n,r,h=next(tokens),next(tokens),next(tokens);assert n==186 and h==28
    raw=[(next(tokens),next(tokens),next(tokens)) for _ in range(n+1)]
    events=[(next(tokens),next(tokens)) for _ in range(r)]
    members=data.members if kind=='baseline' else data.regular+data.ctrl
    hm=sum(1<<w for w in data.hs);gm=((1<<64)-1)^hm
    designs=data.out.designs[:6].copy()
    def physical(mask):return sum(((mask>>i)&1)<<w for i,w in enumerate(data.hs))
    for k,source in enumerate(members):
        op=(data.out.designs[source].opaque&gm)|physical(raw[k][0])
        black=(data.out.designs[source].black&gm)|physical(raw[k][1])
        pattern=''.join('1' if black>>j&1 else '0' if op>>j&1 else '.' for j in range(64))
        designs.append(replay.Paper(pattern,op,black))
    inp=replay.Input(64,192,256,r,data.inp.barcodes,data.inp.requests[:r])
    game=replay.Game(inp,designs);local=[n]+list(range(n))
    perms=list(itertools.permutations(range(6)));index={p:i for i,p in enumerate(perms)}
    displays=[];edges=[]
    for p in perms:
        cov=black=0
        for k in p:black|=designs[k].black&~cov;cov|=designs[k].opaque
        assert cov==gm
        displays.append(black)
        es=[]
        for i in range(5):
            for d in range(6):
                if d==i:continue
                q=list(p);k=q.pop(i);q.insert(d,k);es.append((index[tuple(q)],k,d))
        edges.append(es)
    def gen_path(goal,holes):
        start=index[tuple(k for k in game.order if k<6)]
        parents={start:None};queue=collections.deque([start]);end=None
        while queue:
            s=queue.popleft()
            if not ((displays[s]^goal)&holes):end=s;break
            for t,k,d in edges[s]:
                if t not in parents:parents[t]=(s,k,d);queue.append(t)
        assert end is not None
        path=[]
        while parents[end] is not None:
            prev,k,d=parents[end];path.append((k,d));end=prev
        return path[::-1]
    output=[p.pattern for p in designs];generic_moves=0;max_ops=0
    for turn,(top,bits) in enumerate(events):
        assert top!=n
        count=next(tokens);path=[(next(tokens),next(tokens)) for _ in range(count)]
        moves=[];inserted=False
        real_D=top+6;target=inp.target[inp.requests[turn]];holes=gm&~designs[real_D].opaque
        def generic():
            nonlocal inserted,generic_moves
            if inserted:return
            assert local[0]==n
            for k,d in gen_path(target,holes):game.move(k,d,check=True);moves.append((k,d));generic_moves+=1
            inserted=True
        if holes and local[0]==n:generic()
        for k,d in path:
            assert k!=n
            local.remove(k);cp=local.index(n);real_d=d+(5 if d>cp else 0)
            game.move(k+6,real_d,check=True);moves.append((k+6,real_d));local.insert(d,k)
            if holes and not inserted and local[0]==n:generic()
        assert not holes or inserted
        assert game.finish(turn),(seed,kind,turn,'wrong full display')
        assert len(moves)<=384
        max_ops=max(max_ops,len(moves));output.append(str(len(moves)));output.extend(f'{k} {d}' for k,d in moves)
    assert next(tokens,None) is None
    prefix=Path(prefix)
    prefix.with_suffix('.out').write_text('\n'.join(output)+'\n')
    prefix.with_suffix('.in').write_text(f'64 192 256 {r}\n'+'\n'.join(inp.barcodes)+'\n'+'\n'.join(map(str,inp.requests))+'\n')
    result={'seed':seed,'kind':kind,'N':64,'K':192,'P':256,'R':r,'H_moves':game.moves-generic_moves,'generic_moves':generic_moves,'total_moves':game.moves,'E':game.mistakes,'max_moves_per_order':max_ops,'per_order':game.moves/r}
    prefix.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':convert(int(sys.argv[1]),sys.argv[2],sys.argv[3],sys.argv[4])
