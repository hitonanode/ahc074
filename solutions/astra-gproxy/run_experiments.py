"""固定回数の研究・模擬。子プロセス最大12個、全ての出力をこの下に保存する。"""
import argparse
import concurrent.futures as cf
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
INPUT = Path('/home/sato/ahc074/tools/in')
BASE = dict(MAP_ITERS='380000', GOPT_STEPS='110000', ANNEAL_ITERS='19000000',
            CLIMB_ITERS='65000', SIM_SEQS='4')

p = argparse.ArgumentParser()
p.add_argument('binary')
p.add_argument('name')
p.add_argument('--from-seed', type=int, default=24)
p.add_argument('--to-seed', type=int, default=88)
p.add_argument('--maps', type=int, default=1)
p.add_argument('--map-start', type=int, default=0)
p.add_argument('--jobs', type=int, default=12)
p.add_argument('--research', action='store_true')
p.add_argument('--env', nargs='*', default=[])
args = p.parse_args()
assert 1 <= args.jobs <= 12
dest = HERE / 'data' / args.name
dest.mkdir(parents=True, exist_ok=True)
extra = dict(x.split('=', 1) for x in args.env)
if args.research:
    extra.update(DUMP_MAP='1', RESEARCH_ONLY='1')
env = dict(os.environ, **BASE)
env.update(extra)
(dest / 'config.json').write_text(json.dumps(dict(binary=args.binary, args=vars(args),
                                                env=dict(BASE, **extra)), indent=2))

def run(t):
    seed, ms = t
    path = dest / f'{seed:04d}-{ms:02d}.json'
    if path.exists():
        return json.loads(path.read_text())
    start = time.monotonic()
    with (INPUT / f'{seed:04d}.txt').open() as f:
        r = subprocess.run([str(Path(args.binary).resolve())], stdin=f,
                           capture_output=True, text=True, env=dict(env, MAP_SEED=str(ms)), timeout=120)
    st = {}
    for l in r.stderr.splitlines():
        if ' = ' in l:
            k, v = l.split(' = ', 1)
            try:
                st[k] = float(v)
            except ValueError:
                pass
    raw = {}
    for l in r.stdout.splitlines():
        vs = l.split()
        if vs and vs[0] in ('A','MASK','POL','HM','SELECT','VALID','HANDLE','UNIT'):
            raw[vs[0]] = list(map(int, vs[1:]))
    out = dict(seed=seed, map_seed=ms, stats=st, raw=raw, elapsed=time.monotonic()-start,
               returncode=r.returncode)
    if r.returncode != 0 or 'model_cost' not in st or (not args.research and 'sim_moves' not in st):
        out.update(stderr=r.stderr, stdout=r.stdout)
        path.write_text(json.dumps(out))
        raise RuntimeError(f'failed {seed} {ms}: {r.stderr[-1000:]}')
    path.write_text(json.dumps(out))
    return out

tasks = [(s,m) for s in range(args.from_seed,args.to_seed)
         for m in range(args.map_start,args.map_start+args.maps)]
start = time.monotonic()
with cf.ThreadPoolExecutor(args.jobs) as ex, (dest / 'summary.tsv').open('w') as f:
    for i, r in enumerate(ex.map(run,tasks),1):
        s = r['stats']
        f.write(f"{r['seed']}\t{r['map_seed']}\t{s.get('sim_moves',0)}\t{s['model_cost']}\t{s.get('sim_wrong',0)}\n")
        f.flush()
        if i % 24 == 0 or i == len(tasks):
            print(f'{args.name}: {i}/{len(tasks)}, {time.monotonic()-start:.1f}s',flush=True)
