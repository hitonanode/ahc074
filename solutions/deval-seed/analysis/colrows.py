"""全 seed の設計の列ごとに、特徴量と実際の fix / dig（--orders の全注文列の平均）を 1 行ずつ CSV に出す。
使い方: python3 colrows.py RUN OUT.csv [SEED_FROM SEED_TO]"""
import sys, json, csv, collections
from pathlib import Path
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import colfix
ROOT = Path('/home/sato/ahc074/runs')
run, outp = sys.argv[1], sys.argv[2]
s0, s1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, 10 ** 9)
d = json.load(open(ROOT / run / 'result.json'))
rows = []
for c in d['cases']:
    seed = int(c['seed'])
    if not (s0 <= seed < s1) or any(x <= 0 for x in c['order_scores']): continue
    n = len(c['order_scores'])
    st = colfix.load_design(run, seed)
    G, H = st['G'], st['H']; A = st['A']; cols = st['columns']; ded = st['ded']; handle = st['handle']; papers = st['papers']
    hb = [sum(((a >> handle[k]) & 1) << k for k in range(H)) for a in A]
    tgt = collections.defaultdict(list)
    for u in range(256): tgt[ded[u]].append(u)
    nc = [0] * H; nt = [0] * H; n1 = [0] * H; hn = [[0, 0] for _ in range(H)]
    deeper = [[0, 0] for _ in range(H)]  # papers of deeper columns opaque at the handle, by printed color
    for k in range(len(cols)):
        cc = cols[k]
        if cc < 0: continue
        ts = tgt[k]
        nc[cc] += 1; nt[cc] += len(ts); n1[cc] += hb[ts[0]] >> cc & 1
        dd = (hb[ts[0]] ^ hb[ts[1]]) if len(ts) == 2 else 0
        holes = (((1 << H) - 1) & ~((1 << (cc + 1)) - 1)) | dd
        for j in range(H):
            if holes >> j & 1:
                for t in ts: hn[j][hb[t] >> j & 1] += 1
        op, bl = papers[2 * k], papers[2 * k + 1]
        for j in range(cc):
            w = handle[j]
            if op >> w & 1: deeper[j][bl >> w & 1] += 1
    fix = [0.0] * H; dig = [0.0] * H
    for j in range(n):
        a = colfix.analyze(run, seed, j, verbose=False)
        fix = [x + y / n for x, y in zip(fix, a['fix'])]; dig = [x + y / n for x, y in zip(dig, a['dig'])]
    for cc in range(H):
        x, y = hn[cc]; reset = 2.0 * nt[cc]
        h = 4 * 0.38 * (x * y + 0.5 * reset * min(x, y)) / max(1.0, x + y + reset) / 256
        rows.append(dict(seed=seed, c=cc, H=H, nc=nc[cc], nt=nt[cc], n1=n1[cc], x=x, y=y, reset=reset, hcost=h,
                         deep0=deeper[cc][0], deep1=deeper[cc][1], fix=fix[cc], dig=dig[cc], nseq=n))
with open(outp, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(len(rows), 'rows')
