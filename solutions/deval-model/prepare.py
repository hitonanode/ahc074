"""Read saved states and observed labels. Writes only beneath this directory.

Run under flock; inputs are completed rows of the upstream runs.tsv. Target labels
are training responses, never evaluator inputs. Reading test labels here does not
evaluate/tune a model; the fitting scripts explicitly isolate the seed split.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import sys
sys.dont_write_bytecode = True
import argparse
import collections
import concurrent.futures
import json
from pathlib import Path
import re
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/sato/ahc074')
DEFAULT_MANIFEST = Path('/tmp/claude-1000/-home-sato-ahc074--claude-worktrees-esw-fixiter-improvement-55c629/c9c38a4d-6d47-4694-ada6-fce91018e02d/scratchpad/deval/runs.tsv')
LABELS = ['dig', 'fix', 'gen', 'fret', 'lift', 'ret', 'repair', 'fill', 'relevel', 'fdig', 'reuse', 'help', 'hdig']
BASELINES = ['model_cost', 'model_col', 'model_hole', 'model_gc', 'd2_model_final', 'd2_filler_final']

def hash_barcode(path):
    lines = path.read_text().splitlines()
    h = 0xCBF29CE484222325
    for s in lines[1:257]:
        a = int(s[::-1], 2)
        for i in range(8):
            h = ((h ^ (a >> (i * 8) & 255)) * 0x100000001B3) & ((1 << 64) - 1)
    return f'{h:016x}'

def state_file(design_run, seed):
    return ROOT / 'runs' / design_run / 'design' / (hash_barcode(ROOT / 'tools/in' / f'{seed:04d}.txt') + '.txt')

def read_state(path):
    st = {}
    text = path.read_text()
    for line in text.splitlines():
        if line.startswith('stderr '): break
        f = line.split()
        if len(f) == 2: st[f[0]] = float(f[1]) if '.' in f[1] else int(f[1])
        elif len(f) >= 3: st[f[0]] = [int(x) for x in f[2:]]
    st['baselines'] = [float(re.search(r'^' + k + r' = ([-0-9.e+]+)', text, re.M)[1]) for k in BASELINES]
    return st

def one_case(task):
    variant, design_run, replay_run, case = task
    seed = int(case['seed'])
    scores = np.asarray(case['order_scores'], dtype=float)
    if len(scores) != 8 or np.any(scores <= 0):
        raise ValueError(f'{variant}/{seed}: bad scores {scores}')
    sf = state_file(design_run, seed)
    st = read_state(sf)
    target_counts = np.zeros(256, dtype=np.int32)
    target_labels = np.zeros((256, len(LABELS)), dtype=np.int32)
    list_labels = np.zeros((8, len(LABELS)), dtype=np.int32)
    index = {s:i for i,s in enumerate(LABELS)}
    unknown = collections.Counter()
    for j in range(8):
        inp = ROOT / ('tools/in' if j == 0 else f'runs/.orders/v1/{j}') / f'{seed:04d}.txt'
        orders = list(map(int, inp.read_text().splitlines()[257:]))
        assert len(orders) == 1024
        ep = ROOT / 'runs' / replay_run / ('err' if j == 0 else f'orders/{j}/err') / f'{seed:04d}.txt'
        seen = 0
        for line in ep.read_text().splitlines():
            if not line.startswith('@ops '): continue
            left, right = line.split('=', 1)
            r = int(left[5:])
            t = orders[r]
            target_counts[t] += 1
            seen += 1
            for tok in right.split():
                lab, _, n = tok.partition('*')
                n = int(n) if n else 1
                if lab not in index:
                    unknown[lab] += n
                    continue
                k = index[lab]
                target_labels[t,k] += n
                list_labels[j,k] += n
        assert seen == 1024, (ep, seen)
    if unknown: raise ValueError(unknown)
    # Scores also contain 384 E; require exact successful display on all lists.
    assert np.array_equal(list_labels.sum(axis=1), scores), (variant, seed, list_labels.sum(axis=1), scores)
    return seed, str(sf), st, scores/1024, target_counts, target_labels, list_labels/1024

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)
    p.add_argument('--jobs', type=int, default=12)
    p.add_argument('--variants', nargs='*')
    a = p.parse_args()
    cache = HERE / 'data'
    cache.mkdir(exist_ok=True)
    rows = [line.split() for line in a.manifest.read_text().splitlines() if line.strip() and line.strip() != 'done']
    for variant, drun, rrun in rows:
        tag = variant.replace('=', '_')
        if a.variants and variant not in a.variants: continue
        dest = cache / (tag + '.npz')
        if dest.exists(): continue
        print('reading', variant, drun, rrun, flush=True)
        cases = json.loads((ROOT/'runs'/rrun/'result.json').read_text())['cases']
        tasks = [(variant, drun, rrun, c) for c in cases if 0 <= int(c['seed']) < 1000]
        with concurrent.futures.ProcessPoolExecutor(max_workers=a.jobs) as ex:
            results = sorted(ex.map(one_case, tasks, chunksize=8), key=lambda x:x[0])
        seeds, paths, states, scores, counts, targets, labels = zip(*results)
        np.savez_compressed(dest, seeds=seeds, paths=paths, scores=scores, counts=counts,
                            target_labels=targets, list_labels=labels,
                            baselines=np.array([s['baselines'] for s in states]),
                            baseline_names=BASELINES, label_names=LABELS,
                            variant=variant, design_run=drun, replay_run=rrun)
        (cache/(tag+'.states.json')).write_text(json.dumps(states))
        print('saved', dest, len(seeds), 'cases; all label totals match scores', flush=True)
    (HERE/'runs.tsv').write_text(a.manifest.read_text())

if __name__ == '__main__': main()
