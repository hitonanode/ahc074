#!/usr/bin/env python3
"""Generate public-only designs and independent training scores. No held-out query is read."""
import argparse, concurrent.futures, hashlib, json, os, random, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'));import replay

def run(cmd,inp,env,log,timeout=300):
    start=time.monotonic();p=subprocess.run(cmd,input=inp,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=timeout)
    Path(str(log)+'.stdout').write_bytes(p.stdout);Path(str(log)+'.stderr').write_bytes(p.stderr)
    if p.returncode:raise RuntimeError(f'{cmd} failed: '+p.stderr.decode(errors='replace')[-2000:])
    return p,time.monotonic()-start

def prepare(seed,root,driver,lib,train_count):
    start=time.monotonic();out=root/str(seed);out.mkdir(parents=True,exist_ok=True)
    # Read exactly the public prefix, not the held-out request suffix.
    with open(ROOT/'tools/in'/f'{seed:04}.txt') as f:public=''.join(f.readline() for _ in range(257)).encode()
    assert len(public.split())==260
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',JOINT_FORCE_BFS='1',
         MAP_ITERS='12000',GOPT_STEPS='3000',ANNEAL_ITERS='6000000',CLIMB_ITERS='30000')
    env.update(JOINT_STAGE='base',JOINT_OUTPUT=str(out/'base.design'))
    _,base_sec=run([driver],public,env,out/'base-export')
    popt=os.environ.copy();popt.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    p,search_sec=run([sys.executable,str(HERE/'pool.py'),str(out/'base.design'),'--out',str(out/'pool'),'--lib',lib],b'',popt,out/'search')
    candidates=['base.design','pair-only.final']+[f'linear-{i}.final' for i in range(8)]+[f'nonlinear-{i}.final' for i in range(4)]
    refit_times={}
    for name in candidates[1:]:
        stem=name.removesuffix('.final');env.update(JOINT_STAGE='refit',JOINT_INPUT=str(out/'pool'/f'{stem}.design'),
                        JOINT_MATCH=str(out/'pool'/f'{stem}.match'),JOINT_OUTPUT=str(out/name))
        _,refit_times[name]=run([driver],public,env,out/(stem+'-refit'))
    # Independent training sequences depend on a separate seed, not on held-out orders.
    inputs=[];train_manifest=[]
    for q in range(train_count):
        rng=random.Random(0xC067F1+1009*seed+7919*q);prev=-1;requests=[]
        for r in range(1024):
            x=rng.randrange(256 if prev<0 else 255)
            if prev>=0 and x>=prev:x+=1
            requests.append(x);prev=x
        text=public+''.join(f'{u}\n' for u in requests).encode();inputs.append(text)
        train_manifest.append(dict(seed=0xC067F1+1009*seed+7919*q,sha256=hashlib.sha256(text).hexdigest()))
    scores={};training_results={};train_sec=0.0
    tester=str(ROOT/'tools/target/release/tester')
    for name in candidates:
        vals=[];evidence=[]
        for q,inp in enumerate(inputs):
            env.update(JOINT_STAGE='play',JOINT_INPUT=str(out/name))
            p,elapsed=run([tester,driver],inp,env,out/(name+f'-train-{q}'))
            train_sec+=elapsed
            # Full independent replay catches any invalid move; the tester sees future orders,
            # but the submitted program receives only one order at a time.
            game=replay.replay(replay.parse_input(inp.decode()),replay.parse_output(replay.parse_input(inp.decode()),p.stdout.decode()))
            assert game.error is None and game.game.mistakes==0
            scorelines=[x for x in p.stderr.decode().splitlines() if x.startswith('Score = ')]
            assert len(scorelines)==1 and int(scorelines[0].split('=')[1])==game.score
            vals.append(game.score)
            evidence.append(dict(score=game.score,stdout_sha256=hashlib.sha256(p.stdout).hexdigest(),stderr_sha256=hashlib.sha256(p.stderr).hexdigest(),verified_moves=game.game.moves,requests=game.game.completed))
        scores[name]=vals;training_results[name]=evidence
    common=candidates[:2];linear=common+[f'linear-{i}.final' for i in range(8)]
    mixed=common+[f'linear-{i}.final' for i in range(4)]+[f'nonlinear-{i}.final' for i in range(4)]
    def best(group):return min(group,key=lambda n:(sum(scores[n]),candidates.index(n)))
    selection={'linear-selected.final':best(linear),'mixed-selected.final':best(mixed),
               'union-selected.final':best(candidates)}
    for target,source in selection.items():(out/target).write_bytes((out/source).read_bytes())
    manifest=dict(seed=seed,public_sha256=hashlib.sha256(public).hexdigest(),training=train_manifest,
                   training_scores=scores,training_results=training_results,selection=selection,base_seconds=base_sec,search_seconds=search_sec,
                   refit_seconds=refit_times,training_seconds=train_sec,total_seconds=time.monotonic()-start,
                   candidate_hashes={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in candidates},
                   controls={k:env[k] for k in ['MAP_ITERS','GOPT_STEPS','ANNEAL_ITERS','CLIMB_ITERS','JOINT_FORCE_BFS']})
    (out/'preparation.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return dict(seed=seed,seconds=manifest['total_seconds'],selection=selection)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seeds',required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--driver',default='/mnt/data/joint_driver');p.add_argument('--lib',default='/mnt/data/libjoint.so')
    p.add_argument('--threads',type=int,default=4);p.add_argument('--train-sequences',type=int,default=2)
    a=p.parse_args();lo,hi=map(int,a.seeds.split('-'));a.out.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.threads) as ex:
        fs={ex.submit(prepare,s,a.out.resolve(),a.driver,a.lib,a.train_sequences):s for s in range(lo,hi)}
        for f in concurrent.futures.as_completed(fs):print(json.dumps(f.result()),flush=True)
if __name__=='__main__':main()
