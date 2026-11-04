from pathlib import Path
import json,math,statistics
p=Path(__file__).resolve().parent
rows=[json.loads(f.read_text())for f in sorted((p/'models').glob('[0-9]*.json'))if f.read_text().rstrip().endswith('}')]
F=8;prior=[1,1,1,.6,.6,.25,-.25,0]
def solve(a,b):
 a=[x[:]+[y]for x,y in zip(a,b)]
 for k in range(len(a)):
  j=max(range(k,len(a)),key=lambda j:abs(a[j][k]));a[j],a[k]=a[k],a[j]
  assert abs(a[k][k])>1e-12
  pivot=a[k][k];a[k]=[v/pivot for v in a[k]]
  for i in range(len(a)):
   if i==k:continue
   c=a[i][k];a[i]=[v-c*w for v,w in zip(a[i],a[k])]
 return [r[-1]for r in a]
def fit(rows,h,ridge,constrained=False):
 records=[r['horizons'][h]for r in rows];n=sum(r['n']for r in records)
 A=[sum(r['A'][i]for r in records)/n for i in range(F*F)];b=[sum(r['b'][i]for r in records)/n for i in range(F)]
 var=[sum(r['cov'][i*F+i]for r in records)/n for i in range(F)];scale=[math.sqrt(max(1e-12,v))for v in var]
 matrix=[[A[i*F+j]/(scale[i]*scale[j])+(ridge if i==j else 0)for j in range(F)]for i in range(F)]
 rhs=[b[i]/scale[i]+ridge*prior[i]*scale[i]for i in range(F)]
 if not constrained:return [w/s for w,s in zip(solve(matrix,rhs),scale)]
 free=list(range(2,F));rhs2=[rhs[i]-sum(matrix[i][j]*prior[j]*scale[j]for j in range(2))for i in free]
 small=[[matrix[i][j]for j in free]for i in free];theta=prior[:]
 for i,w in zip(free,solve(small,rhs2)):theta[i]=w/scale[i]
 return theta
results=[]
for h in range(4):
 for ridge in [.001,.01,.1]:
  theta=fit(rows,h,ridge);jack=[fit(rows[:i]+rows[i+1:],h,ridge)for i in range(len(rows))]
  se=[math.sqrt((len(rows)-1)/len(rows)*sum((v[k]-statistics.mean(t[k]for t in jack))**2 for v in jack))for k in range(F)]
  r={'cases':len(rows),'horizon':[1,4,16,64][h],'ridge':ridge,'weights':theta,'se':se};results.append(r)
  print(r)
(p/'fits.json').write_text(json.dumps(results,indent=2))

constrained=[]
for h in range(4):
 theta=fit(rows,h,.01,True);jack=[fit(rows[:i]+rows[i+1:],h,.01,True)for i in range(len(rows))]
 se=[math.sqrt((len(rows)-1)/len(rows)*sum((v[k]-statistics.mean(t[k]for t in jack))**2 for v in jack))for k in range(F)]
 r={'cases':len(rows),'horizon':[1,4,16,64][h],'ridge':.01,'weights':theta,'se':se};constrained.append(r);print('FIXED RANK',r)
(p/'constrained-fits.json').write_text(json.dumps(constrained,indent=2))
