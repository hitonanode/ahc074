"""Read the completed fixed-design diagnostic runs, holding runs/.lock."""
import json,statistics,math,re
from pathlib import Path
here=Path(__file__).resolve().parent;root=Path('/home/sato/ahc074/runs')
names=[re.search(r'run-id: (\S+)',(here/('column-'+suffix+'500.log')).read_text())[1]for suffix in ['base','whole']]
rows=[json.loads((root/n/'metrics.json').read_text())['cases']for n in names]
seeds=set(rows[0])&set(rows[1]);assert len(seeds)==500
actual=[(rows[1][s]['score']-rows[0][s]['score'])/1024 for s in seeds]
def stats(x):return dict(mean=statistics.mean(x),se=statistics.stdev(x)/math.sqrt(len(x)),min=min(x),max=max(x))
out=dict(runs=names,n=len(seeds),metrics={})
for k in ['d2_column_average','d2_column_rate','d2_column_holes','d2_column_weights','colmdp_columns','colmdp_full_states','colmdp_sequences']:
 a,b=[[r[s]['stderr'][k]for s in seeds]for r in rows];delta=[y-x for x,y in zip(a,b)]
 out['metrics'][k]=dict(base=stats(a),candidate=stats(b),delta=stats(delta),corr=statistics.correlation(delta,actual) if statistics.pstdev(delta) else 0)
originals=['20261106-062233_argon-des-perf-rematch-v2','20261106-062412_argon-des-perf-whole']
out['scores_identical']=[]
for r,n in zip(rows,originals):
 old=json.loads((root/n/'metrics.json').read_text())['cases']
 out['scores_identical'].append(sum(r[s]['score']==old[s]['score']for s in seeds))
(here/'column-diagnosis.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
