"""Independently replay the local model as actual opaque / black paper masks.

The cap is immobile; every ordinary sheet has a unique opaque data tag. All
current-request moves are passed through scripts/replay.py's visible-sheet
check, not through the model's own checks. Temporary traces may be removed.
"""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import replay

def verify(path):
    tokens=iter(map(int,Path(path).read_text().split()))
    n,r,h=next(tokens),next(tokens),next(tokens)
    tags=n.bit_length();opaque_tag=((1<<tags)-1)<<h
    raw=[(next(tokens),next(tokens),next(tokens)) for _ in range(n+1)]
    events=[(next(tokens),next(tokens)) for _ in range(r)]
    def number(k):return 0 if k==n else k+1
    designs=[None]*(n+1)
    for k,(op,b,paired) in enumerate(raw):
        tag=number(k)<<h;op|=opaque_tag;b|=tag
        s=''.join('1' if b>>j&1 else '0' if op>>j&1 else '.' for j in range(h+tags))
        designs[number(k)]=replay.Paper(s,op,b)
    values=sorted({b|(number(k)<<h) for k,b in events});lookup={v:i for i,v in enumerate(values)}
    req=[lookup[b|(number(k)<<h)] for k,b in events]
    inp=replay.Input(h+tags,n+1,len(values),r,[replay.mask_text(v,h+tags) for v in values],req)
    game=replay.Game(inp,designs)
    for t in range(r):
        m=next(tokens)
        for _ in range(m):
            k,d=next(tokens),next(tokens);assert k!=n,'cap is not a movable physical sheet'
            game.move(number(k),d,check=True)
        assert game.finish(t),(path,t,'wrong display')
        if raw[events[t][0]][2]:assert game.order[1]==0,'pair generic layer is obscured'
    assert next(tokens,None) is None
    return {'trace':str(path),'sheets':n+1,'windows':h+tags,'requests':r,'moves':game.moves,'mistakes':game.mistakes,'cap_moves':0}

if __name__=='__main__':
    print(json.dumps([verify(p) for p in sys.argv[1:]],indent=2))
