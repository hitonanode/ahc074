"""V16 の特徴量を、設計 7 通り × seed 0〜999（restart7）と、分岐 4 本を強制した設計 × seed 0〜499（branch4）について出す。

restart7: deval-model/data/<variant>.npz の設計の path・注文列 8 本のスコア・ラベル別の手数を使う。
branch4: deval-vselect/experiments.jsonl の trainbranch0..3（clean4 の候補 i を強制した run）と、その replay。
出力: restart7.npz、branch4.npz（X は 142 特徴、Y は注文列 8 本の 1 注文あたりの手数）。
"""
from pathlib import Path
import json, subprocess, sys, hashlib
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODEL = HERE.parent / 'deval-model'
RUNS = Path('/home/sato/ahc074/runs')
ORDER = ['base', 'DESIGN_SEED_1', 'DESIGN_SEED_2', 'DESIGN_SEED_3', 'DSEED_A_1', 'DSEED_A_2', 'DSEED_A_3']
sys.dont_write_bytecode = True
sys.path.insert(0, str(MODEL))
from prepare import state_file  # seed と design run から保存した設計の path

def features(paths):
    out = subprocess.run([str(HERE / 'features_v16'), '16'], input=('\n'.join(map(str, paths)) + '\n').encode(),
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float64).reshape(len(paths), -1)

def names():
    import re
    src = (HERE / 'value_v16.hpp').read_text()
    return [m[0] for m in re.findall(r'\{"([^"]+)",([^}]+)\}', src)]

def restart7():
    d = [np.load(MODEL / 'data' / f'{v}.npz', allow_pickle=True) for v in ORDER]
    seeds = d[0]['seeds']
    paths = [p for s in range(len(seeds)) for p in (x['paths'][s] for x in d)]
    X = features(paths).reshape(len(seeds), len(ORDER), -1)
    np.savez_compressed(HERE / 'restart7.npz', X=X, Y=np.stack([x['scores'] for x in d], 1),
                        L=np.stack([x['list_labels'] for x in d], 1), label_names=d[0]['label_names'],
                        B=np.stack([x['baselines'] for x in d], 1), baseline_names=d[0]['baseline_names'],
                        seeds=seeds, tags=np.array(ORDER), names=np.array(names()))

def branch4():
    ex = {json.loads(l)['tag']: json.loads(l) for l in open(HERE.parent / 'deval-vselect/experiments.jsonl') if l.strip()}
    runs = [ex[f'trainbranch{i}'] for i in range(4)]
    res = [{int(c['seed']): c['order_scores'] for c in json.load(open(RUNS / r['replay'] / 'result.json'))['cases']} for r in runs]
    seeds = sorted(set.intersection(*[set(x) for x in res]))
    paths = [state_file(r['design'], s) for s in seeds for r in runs]
    X = features(paths).reshape(len(seeds), 4, -1)
    Y = np.array([[res[i][s] for i in range(4)] for s in seeds], float) / 1024
    np.savez_compressed(HERE / 'branch4.npz', X=X, Y=Y, seeds=np.array(seeds), names=np.array(names()))

if __name__ == '__main__':
    restart7(); branch4(); print('done')
