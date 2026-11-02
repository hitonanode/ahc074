import collections, itertools, json, math, statistics
from pathlib import Path
D=Path(__file__).resolve().parent;data=D/'data'
def avg(x):return statistics.mean(x)
def se(x):return statistics.stdev(x)/math.sqrt(len(x)) if len(x)>1 else 0
records={n:[json.loads((data/f'{n}-{s:04d}.json').read_text()) for s in range(24,88)] for n in ['base','free230','free246','free260','free300','free340','free380']}
summary={}
for name,rs in records.items():
 delta=[r['metrics']['model_cost']-b['metrics']['model_cost'] for r,b in zip(rs,records['base'])]
 summary[name]={'n':len(rs),'mean':{k:avg([r['metrics'][k] for r in rs]) for k in ['model_cost','model_col','model_hole','model_gc','pair_gc_mean','pair_shallow_hd','pair_generic_hd','pair_full_hd','gobj_after','pairs_incompat']},'delta':avg(delta),'delta_se':se(delta),'wins_ties_losses':[sum(x<0 for x in delta),sum(x==0 for x in delta),sum(x>0 for x in delta)]}
(D/'model-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2),flush=True)
# For a comparator, reversing the order complements every generic bit. One side's
# optimum feedback set is therefore also a valid optimum for its paired side.
perms=list(itertools.permutations(range(6)))
allrows=[];byseed=[]
for record in records['free246']:
 seed=record['seed'];d=record['design'];A=d['A'];G=d['G'];edges=d['edges'];gm=(1<<G)-1
 displays=[]
 for order in perms:
  pos={x:i for i,x in enumerate(order)}
  displays.append(sum((pol if pos[a]<pos[b] else 1-pol)<<j for j,(a,b,pol) in enumerate(edges)))
 protected=0;seen=set()
 for j,(a,b,pol) in enumerate(edges):
  e=(min(a,b),max(a,b))
  if e not in seen:seen.add(e);protected|=1<<j
 selected=[]
 for a,b,c in d['units']:
  if b<0:continue
  diff=A[a]^A[b];hd=diff&gm
  bads=set((disp^A[a])&hd for disp in displays)
  fas=min(x.bit_count() for x in bads)
  mins=sorted(x for x in bads if x.bit_count()==fas)
  # Keep all inclusion-minimal sets (for exact common-window coverage).
  minimal=[]
  for x in sorted(bads,key=lambda x:(x.bit_count(),x)):
   if not any(y&x==y for y in minimal):minimal.append(x)
  cnt=collections.defaultdict(lambda:[0,0])
  for j,(x,y,pol) in enumerate(edges):
   if hd>>j&1:cnt[x,y][((A[a]>>j)&1)!=pol]+=1
  two=sum(min(v) for v in cnt.values())
  sh=sum((diff>>j)&1 for j in d['handles'][:c+1])
  row={'seed':seed,'a':a,'b':b,'col':c,'fas':fas,'two_cycle_lower':two,'generic_hd':hd.bit_count(),'full_hd':diff.bit_count(),'shallow_hd':sh,'min_sets':mins,'minimal_sets':minimal,'protected_rescuable':any(x&protected==0 for x in bads)}
  allrows.append(row);selected.append(row)
 # Exact fixed shared removal, up to 3 windows; no claim of executable cap scheme.
 common=[]
 for size in (1,2,3):
  best=(-1,())
  for js in itertools.combinations(range(G),size):
   mask=sum(1<<j for j in js)
   count=sum(r['fas']>0 and any(m&mask==m for m in r['minimal_sets']) for r in selected)
   if count>best[0]:best=(count,js)
  common.append({'size':size,'rescued':best[0],'windows_internal':best[1],'windows_original':[d['permutation'][j] for j in best[1]]})
 byseed.append({'seed':seed,'shared_removal':common})
 print('cycles finished',seed,flush=True)
(D/'pair-cycles.json').write_text(json.dumps({'pairs':allrows,'shared':byseed},separators=(',',':'))+'\n')
inc=[r for r in allrows if r['fas']]
cs={'n_cases':64,'n_pairs':len(allrows),'incompatible':len(inc),'fas_hist':dict(sorted(collections.Counter(r['fas'] for r in allrows).items())),'mean_fas_incompat':avg(r['fas'] for r in inc),'mean_generic_hd_incompat':avg(r['generic_hd'] for r in inc),'mean_shallow_hd_incompat':avg(r['shallow_hd'] for r in inc),'two_cycle_explains_optimum':sum(r['two_cycle_lower']==r['fas'] for r in inc),'mean_two_cycle_lower':avg(r['two_cycle_lower'] for r in inc),'protected_rescuable':sum(r['protected_rescuable'] for r in inc),'shared_removal_means':{str(n):avg(x['shared_removal'][n-1]['rescued'] for x in byseed) for n in (1,2,3)}}
(D/'cycle-summary.json').write_text(json.dumps(cs,indent=2)+'\n');print(json.dumps(cs,indent=2))
