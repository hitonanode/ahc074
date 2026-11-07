"""clean4 の 4 分岐の各候補を強制した replay（trainbranch0..3）から、分岐集合の中での V の選択の効率を測る。リポジトリの最上位で実行する。"""
import json, math
import numpy as np
R = '/home/sato/ahc074/runs/'
ex = {json.loads(l)['tag']: json.loads(l) for l in open('solutions/deval-vselect/experiments.jsonl') if l.strip()}
def load(run):
    d = json.load(open(R + run + '/result.json'))
    return {int(c['seed']): np.array(c['order_scores'], float) for c in d['cases'] if c.get('order_scores') and min(c['order_scores']) > 0}
base = load('20261107-015743_deval-seed')
cand = [load(ex[f'trainbranch{i}']['replay']) for i in range(4)]
pick = load(ex['clean4']['replay'])
seeds = sorted(set(base) & set(pick) & set.intersection(*[set(c) for c in cand]))
C = np.array([[c[s] for c in cand] for s in seeds]) / 1024  # seed x cand x list, moves/order
B = np.array([base[s] for s in seeds]) / 1024
P = np.array([pick[s] for s in seeds]) / 1024
# which candidate did V pick? match on all 8 lists
match = np.array([[np.allclose(P[i], C[i, j]) for j in range(4)] for i in range(len(seeds))])
print('n', len(seeds), 'V pick identified', match.any(1).mean(), 'pick counts', match.argmax(1)[match.any(1)].tolist().count(0), [int((match.argmax(1)==j)[match.any(1)].sum()) for j in range(4)])
def pct(x, b): return 100 * np.log(x / b)
L17 = slice(1, 8)
m = C[:, :, L17].mean(2); bm = B[:, L17].mean(1)
print('each candidate vs base (L1-7 %):', [f'{pct(m[:, j], bm).mean():+.3f}' for j in range(4)])
print('random branch vs base: %+.3f' % pct(m.mean(1), bm).mean())
vp = P[:, L17].mean(1)
print('V pick vs base: %+.3f ± %.3f' % (pct(vp, bm).mean(), pct(vp, bm).std(ddof=1) / math.sqrt(len(seeds))))
# oracle: pick by lists 0-3, measure on 4-7
A = slice(0, 4); Bq = slice(4, 8)
o = C[np.arange(len(seeds)), C[:, :, A].mean(2).argmin(1)][:, Bq].mean(1)
bq = B[:, Bq].mean(1); vq = P[:, Bq].mean(1); rq = C[:, :, Bq].mean(2).mean(1)
print('lists 4-7: oracle(0-3) %+.3f  V %+.3f  random %+.3f  (vs base)' % (pct(o, bq).mean(), pct(vq, bq).mean(), pct(rq, bq).mean()))
# true within-set SD, noise corrected: var of 8-list means minus noise var / 8
dev = C - C.mean(1, keepdims=True)           # seed x cand x list
mean8 = dev.mean(2)                          # true + noise/8
noise = (dev - mean8[:, :, None]).var(2, ddof=1).mean() * 4 / 3  # per-list noise var (correct for centring over 4 cands)
tot = (mean8 ** 2).sum(1).mean() / 3
true_var = tot - noise / 8
print('within-set SD of 8-list mean %.4f, noise SD per list %.4f, true SD %.4f moves/order' % (math.sqrt(tot), math.sqrt(noise), math.sqrt(max(true_var, 0))))
print('perfect selector expected gain vs random ~ %.4f moves/order (%.3f%%)' % (1.029 * math.sqrt(max(true_var, 0)), 100 * 1.029 * math.sqrt(max(true_var, 0)) / C.mean()))
