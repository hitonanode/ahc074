"""Read-only trace audit. No cache is written outside this directory.

PYTHONDONTWRITEBYTECODE=1 python3 solutions/astra-probe/analyze.py 0 8
Column order is recovered from the FIRST opaque paper at each handle, not its
total opaque count: pair holes make the latter an unreliable ordering.
"""
from pathlib import Path
from collections import Counter, defaultdict
from bisect import bisect_left, bisect_right
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import replay

RUN = Path('/home/sato/ahc074/runs/20261101-214232_imp-910')


def load(seed):
    inp = replay.load_input(seed)
    out = replay.parse_output(inp, (RUN / 'out' / f'{seed:04d}.txt').read_text())
    assert out.error is None
    ps = out.designs
    gm = 0
    for p in ps[:6]:
        gm |= p.opaque
    hs = [j for j in range(64) if not (gm >> j & 1)]
    first = {j: next(k for k in range(6,192) if ps[k].opaque >> j & 1) for j in hs}
    hs.sort(key=first.get)
    starts = [first[j] for j in hs]
    assert len(set(starts)) == 28
    cols = [-1] * 6 + [bisect_right(starts,k)-1 for k in range(6,192)]
    serves = {k: [u for u,a in enumerate(inp.target) if a & ps[k].opaque == ps[k].black] for k in range(6,192)}
    for k in range(6,192):
        assert ps[k].opaque >> hs[cols[k]] & 1
        assert all(not(ps[k].opaque >> j & 1) for j in hs[cols[k]+1:])
        assert len(serves[k]) in (1,2)
    return inp,out,gm,hs,cols,serves


def shown(ps,order):
    covered = 0
    black = 0
    vis = {}
    for k in order:
        e = ps[k].opaque & ~covered
        if e:
            vis[k] = e
            black |= ps[k].black & e
            covered |= e
    return black,vis


def mean_se(xs):
    m = sum(xs)/len(xs)
    se = math.sqrt(sum((x-m)**2 for x in xs)/(len(xs)*(len(xs)-1))) if len(xs)>1 else 0
    return [m,se]


def audit(lo,hi):
    totals = []
    old_totals = []
    groups = defaultdict(Counter)
    opgroups = defaultdict(Counter)
    detail = []
    for seed in range(lo,hi):
        inp,out,gm,hs,cols,serves = load(seed)
        ps = out.designs
        oldhs = sorted(hs,key=lambda j:(-sum(p.opaque>>j&1 for p in ps[6:]),j))
        oldpos = {j:i for i,j in enumerate(oldhs)}
        oldcol = [-1]*6+[max(oldpos[j] for j in hs if ps[k].opaque>>j&1) for k in range(6,192)]
        oldacc = Counter()
        acc = Counter()
        acc['handle_rank_errors'] = sum(a!=b for a,b in zip(oldhs,hs))
        acc['paper_column_errors'] = sum(cols[k]!=oldcol[k] for k in range(6,192))
        order = list(range(192))
        sizes = Counter(cols[6:])
        bycol = [[k for k in range(6,192) if cols[k]==c] for c in range(28)]
        acc['static_uniform_depth'] = sum(len(serves[k])*(sizes[cols[k]]-1)/2 for k in range(6,192))/256
        acc['static_weighted_depth_lower'] = sum(i*len(serves[k]) for cc in bycol for i,k in enumerate(sorted(cc,key=lambda k:-len(serves[k]))))/256
        for r,ops in enumerate(out.queries):
            start = list(order)
            start_display,startvis = shown(ps,start)
            target = inp.target[inp.requests[r]]
            # Final top is the designated paper; verified against its printed colors.
            for k,d in ops:
                order.remove(k)
                order.insert(d,k)
            final_display,_ = shown(ps,order)
            assert final_display == target
            top = order[0]
            assert top >= 6 and inp.requests[r] in serves[top]
            c = cols[top]
            kind = 'pair' if len(serves[top])==2 else 'single'
            above = {k for k in start[:start.index(top)] if cols[k]==c}
            oldabove = {k for k in start[:start.index(top)] if oldcol[k]==oldcol[top]}
            prev = start[0]
            vals = Counter(n=1,moves=len(ops),column=c,triangle_holes=27-c,
                           pair_handle_holes=sum(not(ps[top].opaque>>j&1) for j in hs[:c+1]),
                           generic_holes=(gm&~ps[top].opaque).bit_count(),
                           old_mismatch=(start_display^target).bit_count(),visible=len(startvis))
            # Exact number of blockers that must move before the first possible move of D.
            blockers = [sum(ps[k].opaque>>j&1 for k in start[:start.index(top)]) for j in range(64) if ps[top].opaque>>j&1]
            vals['expose_D_lower'] = min(blockers)
            vals['prev_covers_D'] = prev != top and not(ps[top].opaque & ~ps[prev].opaque)
            # An endpoint lower bound allowing all papers to move regardless of visibility.
            rank = {k:i for i,k in enumerate(start)}
            tails = []
            for k in order:
                x = rank[k]
                p = bisect_left(tails,x)
                if p==len(tails): tails.append(x)
                else: tails[p]=x
            vals['endpoint_moves_lower'] = 192-len(tails)
            vals['repeat_moves'] = len(ops)-len({k for k,_ in ops})
            # Same counterfactual as the old hole audit: put D on top and remove prev.
            cf = [top]+[k for k in start if k not in (top,prev)]
            cf_display,_ = shown(ps,cf)
            wrong = cf_display^target
            vals['cf_triangle_wrong'] = sum(wrong>>j&1 for j in hs[c+1:])
            vals['cf_pair_handle_wrong'] = sum((wrong>>j&1) and not(ps[top].opaque>>j&1) for j in hs[:c+1])
            cur = list(start)
            curdisp = start_display
            for step,(k,d) in enumerate(ops):
                role = 'lift' if k==top else 'prev' if k==prev else 'gen' if k<6 else 'dig' if k in above else 'fix'
                oldrole = 'lift' if k==top else 'prev' if k==prev else 'gen' if k<6 else 'dig' if k in oldabove else 'fix'
                vals[role] += 1
                oldacc[oldrole] += 1
                _,vis = shown(ps,cur)
                assert k in vis, (seed,r,step,k)
                cur.remove(k)
                cur.insert(d,k)
                newdisp,_ = shown(ps,cur)
                improved = ((curdisp^target)&~(newdisp^target)).bit_count()
                worsened = ((newdisp^target)&~(curdisp^target)).bit_count()
                oc = opgroups[role]
                oc['n'] += 1
                oc['fix_bits'] += improved
                oc['break_bits'] += worsened
                oc['no_display_change'] += curdisp==newdisp
                oc['fix_4_or_more'] += improved>=4
                oc['net_positive'] += improved>worsened
                curdisp = newdisp
            assert cur==order
            vals['prev_moved'] = any(k==prev for k,_ in ops)
            groups['all'].update(vals)
            groups[kind].update(vals)
            groups[f'{kind}_cols_{c//4*4:02d}_{c//4*4+3:02d}'].update(vals)
            acc.update(vals)
            if seed==lo and r<12:
                detail.append(dict(seed=seed,request=r,item=inp.requests[r],paper=top,kind=kind,**vals))
        n = inp.r
        totals.append({k:(v/n if k not in ('handle_rank_errors','paper_column_errors','static_uniform_depth','static_weighted_depth_lower') else v) for k,v in acc.items()})
        old_totals.append({k:v/n for k,v in oldacc.items()})
    summary = {k:mean_se([row.get(k,0) for row in totals]) for k in totals[0]}
    return dict(run=RUN.name,seeds=[lo,hi],seed_mean_and_se=summary,
                old_classification_mean={k:sum(x.get(k,0) for x in old_totals)/len(old_totals) for k in old_totals[0]},
                groups={k:{x:v/a['n'] for x,v in a.items()}|{'n':a['n']} for k,a in groups.items()},
                operations={k:{x:v/a['n'] for x,v in a.items()}|{'n':a['n']} for k,a in opgroups.items()},
                seed_rows=totals,examples=detail)


if __name__=='__main__':
    lo,hi = map(int,sys.argv[1:3])
    res = audit(lo,hi)
    dst = Path(__file__).parent/f'audit_{lo}_{hi}.json'
    dst.write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in res.items() if k not in ('seed_rows','examples')},ensure_ascii=False,indent=2))
