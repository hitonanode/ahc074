"""Exact PosetSums costs of the global CSP's feasible comparators."""
import argparse,itertools,json,re,time
from pathlib import Path
from csp import load_design,EDGES,HERE

def table():
    text=(HERE.parents[1]/'solutions/esw-slim/main.cpp').read_text()
    block=text.split('constexpr PosetClass kPosetClasses[318] = {',1)[1].split('};',1)[0]
    classes=[(int(r,16),int(v))for r,v in re.findall(r'\{0x([0-9a-f]+)ULL, (\d+)\}',block)]
    assert len(classes)==318
    out={}
    for rel,cost in classes:
        bits=[(i//8,i%8)for i in range(48)if rel>>i&1]
        for p in itertools.permutations(range(6)):
            r=sum(1<<(8*p[a]+p[b])for a,b in bits);out[r]=cost
    assert len(out)==130023
    return out

def close(r):
    for k in range(6):r|=((r>>k)&0x010101010101)*((r>>(8*k))&63)
    return r
def transpose(r):return sum(1<<(8*(i%8)+i//8)for i in range(48)if r>>i&1)
def profiles(t):
    grouped={};extended={}
    for r,v in t.items():
        trans=transpose(r)
        key=tuple(sorted(6*((trans>>(8*i))&63).bit_count()+((r>>(8*i))&63).bit_count()for i in range(6)))
        grouped.setdefault(key,set()).add(v+t[trans])
        covers=sum(bool(r>>(8*a+b)&1) and not (((r>>(8*a))&63)&((trans>>(8*b))&63))
                   for a in range(6)for b in range(6)if a!=b)
        extended.setdefault(key+(covers,),set()).add(v+t[trans])
    rows=[{'profile':key,'min':min(v),'max':max(v),'costs':sorted(v)}for key,v in sorted(grouped.items())]
    (HERE/'degree-profiles.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('Degree profiles:',len(rows),'ambiguous:',sum(r['min']!=r['max']for r in rows),
          'max gap:',max(r['max']-r['min']for r in rows),flush=True)
    rows=[{'profile':key,'min':min(v),'max':max(v),'costs':sorted(v)}for key,v in sorted(extended.items())]
    (HERE/'cover-profiles.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('With cover count:',len(rows),'ambiguous:',sum(r['min']!=r['max']for r in rows),
          'max gap:',max(r['max']-r['min']for r in rows),flush=True)
def cost(d,codes,t):
    total=0;relations=[]
    for u,v in d['pairs']:
        r=0
        for w,code in enumerate(codes):
            if not ((d['A'][u]^d['A'][v])>>w&1):continue
            a,b=EDGES[code//2]
            if (d['A'][u]>>w&1)!=(code&1):a,b=b,a
            r|=1<<(8*a+b)
        r=close(r);assert not(r&0x8040201008040201)
        total+=t[r]+t[transpose(r)];relations.append(r)
    return total/(720*256),relations

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--output',default='csp-cost.json')
    p.add_argument('--profiles',action='store_true');a=p.parse_args()
    source=json.loads((HERE/a.input).read_text());t=table();rows=[]
    if a.profiles:profiles(t)
    for item in source['rows']:
        d=load_design(item['seed'],source['run']);base,rels=cost(d,item['assignments'][0],t)
        values=[]
        for codes in item['assignments']:
            value,newrels=cost(d,codes,t)
            values.append({'gc':value,'delta':value-base,'changed_relations':sum(a!=b for a,b in zip(rels,newrels)),
                           'changes':[(w,a,b)for w,(a,b)in enumerate(zip(item['assignments'][0],codes))if a!=b]})
        row={'seed':item['seed'],'complete':item['complete'],'values':values};rows.append(row)
        print(item['seed'],item['complete'],[(round(x['delta'],8),x['changed_relations'],x['changes'])for x in values],flush=True)
    (HERE/a.output).write_text(json.dumps({'run':source['run'],'rows':rows},indent=2)+'\n')
