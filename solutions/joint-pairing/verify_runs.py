#!/usr/bin/env python3
"""Independently replay every recorded test operation and verify immutable hashes."""
import argparse,concurrent.futures,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import replay

def verify(job):
    run,c,designs=job;s=c['seed'];source=c.get('source_seed',s)
    inp=ROOT/'tools'/'in'/f'{s:04}.txt';out=run/'out'/f'{s:04}.txt';err=run/'err'/f'{s:04}.txt'
    for p,k in [(inp,'input_sha256'),(out,'stdout_sha256'),(err,'stderr_sha256'),(designs/str(source)/c['arm'],'design_sha256')]:
        assert hashlib.sha256(p.read_bytes()).hexdigest()==c[k],(run.name,s,k)
    text=out.read_text();i=replay.parse_input(inp.read_text());r=replay.replay(i,replay.parse_output(i,text),check=True)
    assert r.error is None and r.game.completed==1024 and r.game.mistakes==0 and r.score==c['score'],(run.name,s,r.error)
    return r.game.moves

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--designs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    jobs=[];runs=[]
    for name in ['evaluation-6001-6033.json','evaluation-6001-6009.json','evaluation-6200-6424.json']:
        for run in json.loads((a.designs/name).read_text())['runs']:
            runs.append(run);d=ROOT/'runs'/run
            jobs.extend((d,c,a.designs) for c in json.loads((d/'result.json').read_text())['cases'])
    start=time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as p:totals=list(p.map(verify,jobs,chunksize=8))
    training=0
    for seed in range(6001,6033):
        root=a.designs/str(seed);j=json.loads((root/'preparation.json').read_text())
        for arm,records in j['training_results'].items():
            for q,record in enumerate(records):
                # Training was visibility-replayed before preparation.json was saved.
                prefix=root/f'{arm}-train-{q}'
                for ext,k in [('stdout','stdout_sha256'),('stderr','stderr_sha256')]:
                    assert hashlib.sha256(Path(str(prefix)+'.'+ext).read_bytes()).hexdigest()==record[k],(seed,arm,q,k)
                training+=1
    result=dict(status='passed',test_runs=len(jobs),orders=len(jobs)*1024,moves=sum(totals),errors=0,
                input_design_stdout_stderr_hashes='all matched',training_hashes_checked=training,
                training_full_replay='performed by prepare.py before selection',seconds=time.monotonic()-start,runs=runs)
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
