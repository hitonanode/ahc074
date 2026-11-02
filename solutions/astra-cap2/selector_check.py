"""Small exhaustive checks for fixed selectors and D interleaving."""
from itertools import product,permutations
import json
from pathlib import Path
r=Path(__file__).resolve().parent
selectors=[]
for n in range(1,5):
 for color in range(1<<n):
  ok=set()
  for p in range(1<<n):
   states={(p&~((1<<t)-1))|(color&((1<<t)-1)) for t in range(n+1)}
   ok.update((a,b) for a in states for b in states)
  selectors.append({'caps':n,'color':color,'legal_ordered_pairs':len(ok),'total_pairs':1<<(2*n),'rate':len(ok)/(1<<(2*n))})
# The three pairwise-comparison windows of 3 generic papers. Enumerate every
# possible D print, all 24 orders, all target pairs. A D cannot serve an
# incompatible pair, even if it prints a different color at each window.
edges=[(0,1),(0,2),(1,2)]
def generic(order):
 pos={v:i for i,v in enumerate(order)}
 return tuple(int(pos[a]<pos[b]) for a,b in edges)
reachable={generic(o) for o in permutations(range(3))}
contradictions=0;checks=0
for d in product([-1,0,1],repeat=3):
 outputs=set()
 for order in permutations(range(4)):
  row=[]
  for j,(a,b) in enumerate(edges):
   for k in order:
    color=d[j] if k==3 else 1 if k==a else 0 if k==b else -1
    if color!=-1:row.append(color);break
  outputs.add(tuple(row))
 for x in product([0,1],repeat=3):
  y=tuple(1-v for v in x)
  if x not in reachable:
   checks+=1;contradictions+=x in outputs and y in outputs
res={'selector_counts':selectors,'triangle_d_prints':27,'triangle_total_orders_per_print':24,'incompatible_pair_print_checks':checks,'counterexamples_to_comparator_obstruction':contradictions}
(r/'results/selector-check.json').write_text(json.dumps(res,indent=2)+'\n')
print(json.dumps(res,indent=2))
assert contradictions==0
