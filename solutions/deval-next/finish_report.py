from pathlib import Path
import sys,subprocess,json,os,time
P=Path(__file__).resolve().parent;root=P.parents[1];z=json.loads((P/'final-runs.json').read_text());name=z['choice']['name'];D=root/'solutions'/name;env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1');lock=['flock','-x','/home/sato/ahc074/runs/.lock']
with (D/'final-metrics.log').open('w') as f:subprocess.run(lock+[sys.executable,str(P/'final_metrics.py'),name,'--normal']+z['normal_runs']+['--replay',z['replay_run']],stdout=f,stderr=subprocess.STDOUT,env=env,check=True)
judge='/tmp/claude-1000/-home-sato-ahc074--claude-worktrees-esw-fixiter-improvement-55c629/c9c38a4d-6d47-4694-ada6-fce91018e02d/scratchpad/deval/judge_model.py'
with (D/'judge-model.log').open('w') as f:subprocess.run(lock+[sys.executable,judge]+z['normal_runs'],stdout=f,stderr=subprocess.STDOUT,env=env,check=True)
while not (D/'builds.json').exists():time.sleep(2)
builds=json.loads((D/'builds.json').read_text());assert len(builds)==2 and all(x['returncode']==0 for x in builds)
subprocess.run([sys.executable,str(P/'report_tables.py')],env=env,check=True)
subprocess.run([sys.executable,str(P/'render_report.py'),name],env=env,check=True)
print(json.dumps({'solver':name,'report':str(D/'REPORT.md')}),flush=True)
