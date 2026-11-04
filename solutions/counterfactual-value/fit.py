from pathlib import Path
import json,math,statistics
p=Path(__file__).resolve().parent
rows=[]
for f in sorted((p/'models').glob('[0-9]*.json')):
 try:r=json.loads(f.read_text())
 except ValueError:continue
 rows.append(r)
F=8;prior=[1,1,1,.6,.6,.25,-.25,0]
def solve(a,b):
 a=[x[:]+[y]for x,y in zip(a,b)];n=len(a)
 for k in range(n):
  j=max(range(k,n),key=lambda j:abs(a[j][k]));a[j],a[k]=a[k],a[j];assert abs(a[k][k])>1e-12
  pivot=a[k][k];a[k]=[v/pivot for v in a[k]]
  for i in range(n):
   if i==k:continue
   c=a[i][k];a[i]=[v-c*w for v,w in zip(a[i],a[k])]
 return [r[-1]for r in a]
def fit(cases,ridge=.01,constrained=False):
 records=[r for c in cases for r in c];n=len(records)
 A=[[sum(r['x'][i]*r['x'][j]for r in records)/n for j in range(F)]for i in range(F)]
 b=[sum(r['x'][i]*r['target']for r in records)/n for i in range(F)]
 scale=[math.sqrt(max(1e-12,A[i][i]))for i in range(F)]
 matrix=[[A[i][j]/(scale[i]*scale[j])+(ridge if i==j else 0)for j in range(F)]for i in range(F)]
 rhs=[b[i]/scale[i]+ridge*prior[i]*scale[i]for i in range(F)]
 if not constrained:return [w/s for w,s in zip(solve(matrix,rhs),scale)]
 free=list(range(2,F));rhs2=[rhs[i]-sum(matrix[i][j]*prior[j]*scale[j]for j in range(2))for i in free]
 small=[[matrix[i][j]for j in free]for i in free];theta=prior[:]
 for i,w in zip(free,solve(small,rhs2)):theta[i]=w/scale[i]
 return theta
def loss(cases,w):
 records=[r for c in cases for r in c];return statistics.mean((r['target']-sum(x*v for x,v in zip(r['x'],w)))**2 for r in records)
result=[]
for ridge in [.001,.01,.1]:
 theta=fit(rows,ridge);jack=[fit(rows[:i]+rows[i+1:],ridge)for i in range(len(rows))]
 se=[math.sqrt((len(rows)-1)/len(rows)*sum((v[k]-statistics.mean(t[k]for t in jack))**2 for v in jack))for k in range(F)]
 before=[loss([c],prior)for c in rows];after=[loss([c],w)for c,w in zip(rows,jack)]
 r={'cases':len(rows),'samples':sum(map(len,rows)),'ridge':ridge,'weights':theta,'se':se,'test_mse_prior':statistics.mean(before),'test_mse_fit':statistics.mean(after)};result.append(r);print(r)
(p/'fits.json').write_text(json.dumps(result,indent=2))

theta=fit(rows,.01,True);jack=[fit(rows[:i]+rows[i+1:],.01,True)for i in range(len(rows))]
se=[math.sqrt((len(rows)-1)/len(rows)*sum((v[k]-statistics.mean(t[k]for t in jack))**2 for v in jack))for k in range(F)]
r={'cases':len(rows),'samples':sum(map(len,rows)),'ridge':.01,'weights':theta,'se':se,'test_mse_prior':statistics.mean(loss([c],prior)for c in rows),'test_mse_fit':statistics.mean(loss([c],w)for c,w in zip(rows,jack))}
print('FIXED RANK',r);(p/'constrained-fit.json').write_text(json.dumps(r,indent=2))
