"""Official-tester legality check on eight learned-decoder designs, then replay."""
import argparse,concurrent.futures as cf,json,os,pathlib,re,subprocess,sys,time
sys.dont_write_bytecode=True
D=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(D.parents[1]/'scripts'))
import replay
ap=argparse.ArgumentParser();ap.add_argument('--label',default='shared12');ap.add_argument('--binary',default='shared');ap.add_argument('--output',default='validation-shared');ap.add_argument('--workers',type=int,default=1);args=ap.parse_args()
rows=[json.loads(f.read_text()) for f in (D/'results'/args.label).glob('[0-9]*.json')]
rows.sort(key=lambda r:(-r['metrics']['decoder_nonlinear'],-r['metrics']['decoder_window_swaps'],r['seed']))
seeds=[r['seed'] for r in rows[:8]]
out=D/'results'/args.output;out.mkdir(exist_ok=True)
env=os.environ|dict(MAP_ITERS='400000',GOPT_STEPS='100000',ANNEAL_ITERS='20000000',CLIMB_ITERS='60000',MODEL_ONLY='0',DUMP_DESIGN='0',SIM_SEQS='0',GATE_TRIALS='128',GATE_WITNESSES='12')
(out/'meta.json').write_text(json.dumps({'binary':args.binary,'design_run':args.label,'seeds':seeds,'extra':{k:env[k] for k in ['MAP_ITERS','GOPT_STEPS','ANNEAL_ITERS','CLIMB_ITERS','GATE_TRIALS','GATE_WITNESSES']},'purpose':'legality only; selected designs, fixed work, not a timing or score comparison'},indent=2)+'\n')
def job(seed):
 t=time.monotonic()
 with open(f'/home/sato/ahc074/tools/in/{seed:04d}.txt','rb') as inp:
  r=subprocess.run(['/home/sato/ahc074/tools/target/release/tester',str(D/args.binary)],stdin=inp,env=env,capture_output=True,timeout=180)
 (out/f'{seed:04d}.out').write_bytes(r.stdout);(out/f'{seed:04d}.err').write_bytes(r.stderr)
 metrics={k:float(v) for k,v in re.findall(rb'(?m)^(\w+) = ([-+0-9.eE]+)$',r.stderr)};metrics={k.decode():v for k,v in metrics.items()}
 inp=replay.load_input(seed);parsed=replay.parse_output(inp,r.stdout.decode());game=replay.Game(inp,parsed.designs)
 wrong=0;moves=0
 for req,ops in enumerate(parsed.queries):
  for k,d in ops:game.move(k,d);moves+=1
  wrong+=not game.finish(req)
 result={'seed':seed,'returncode':r.returncode,'metrics':metrics,'replay_queries':len(parsed.queries),'replay_wrong':wrong,'replay_moves':moves,'replay_score':game.score(),'wall_sec':time.monotonic()-t}
 assert r.returncode==0 and metrics['Score']>0 and metrics['self_wrong']==0 and wrong==0 and len(parsed.queries)==1024 and game.score()==metrics['Score']
 (out/f'{seed:04d}.json').write_text(json.dumps(result,indent=2)+'\n');print('verified',seed,moves,flush=True);return result
with cf.ThreadPoolExecutor(max_workers=min(4,args.workers)) as pool:results=list(pool.map(job,seeds))
(out/'summary.json').write_text(json.dumps({'n':len(results),'WA':0,'wrong':0,'replayed_queries':sum(r['replay_queries'] for r in results),'replayed_moves':sum(r['replay_moves'] for r in results),'seeds':seeds},indent=2)+'\n')
