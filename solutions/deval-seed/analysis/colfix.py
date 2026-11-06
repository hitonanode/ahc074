"""設計の列ごとに、設計の見積り（列の深さ colcost、取っ手の色直し hcost）と、実際の手（dig, fix）を並べる。
使い方: python3 colfix.py RUN SEED [ORDER_J]   （RUN は --save-design か --design-from の run。設計は design/ から読む）
ORDER_J: --orders の j 本目（0 は元の注文列）。"""
import sys, collections, json
from pathlib import Path
sys.path.insert(0, '/home/sato/ahc074/scripts')
import replay
ROOT = Path('/home/sato/ahc074/runs')
def barcode_hash(input_path):
    lines = Path(input_path).read_text().split("\n")
    h = 0xCBF29CE484222325
    for s in lines[1:1 + int(lines[0].split()[2])]:
        a = int(s.strip()[::-1], 2)
        for byte in range(8):
            h = ((h ^ (a >> (8 * byte) & 255)) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"{h:016x}"
def load_design(run, seed):
    meta = json.load(open(ROOT / run / 'meta.json'))
    drun = meta.get('design_from') or run
    if isinstance(drun, dict): drun = drun.get('run')
    f = ROOT / drun / 'design' / f"{barcode_hash(f'/home/sato/ahc074/tools/in/{seed:04d}.txt')}.txt"
    st = {}
    for line in f.read_text().split('\n'):
        p = line.split()
        if len(p) >= 2 and p[0] in ('M', 'G', 'H'): st[p[0]] = int(p[1])
        elif len(p) >= 2 and p[0] in ('A', 'columns', 'ded', 'handle', 'papers', 'permutation'):
            st[p[0]] = [int(x) for x in p[2:2 + int(p[1])]]
    return st
def analyze(run, seed, j=0, verbose=True):
    st = load_design(run, seed)
    G, H = st['G'], st['H']
    A = st['A']; cols = st['columns']; ded = st['ded']
    handle = st['handle']
    hb = [sum(((a >> handle[c]) & 1) << c for c in range(H)) for a in A]  # bit c: color at the handle of column c
    tgt = collections.defaultdict(list)
    for u in range(256): tgt[ded[u]].append(u)
    units = [(k, tgt[k], cols[k]) for k in range(len(cols)) if cols[k] >= 0]
    nc = [0] * H; nt = [0] * H; n1 = [0] * H; hn = [[0, 0] for _ in range(H)]
    for k, ts, c in units:
        nc[c] += 1; nt[c] += len(ts); n1[c] += hb[ts[0]] >> c & 1
        d = (hb[ts[0]] ^ hb[ts[1]]) if len(ts) == 2 else 0
        holes = (((1 << H) - 1) & ~((1 << (c + 1)) - 1)) | d
        for jj in range(H):
            if holes >> jj & 1:
                for t in ts: hn[jj][hb[t] >> jj & 1] += 1
    w = 0.38
    def hcost(jj):
        x, y = hn[jj]; reset = 2.0 * nt[jj]
        return 4 * w * (x * y + 0.5 * reset * min(x, y)) / max(1.0, x + y + reset)
    def colcost(c):
        np_ = nt[c] - nc[c]
        return (nc[c] * (nc[c] - 1) + np_ * (np_ - 1)) * 0.5
    # real moves by the column of the moved paper
    rd = ROOT / run
    sub = '' if j == 0 else f'orders/{j}/'
    inp = replay.load_input(seed)
    if j:
        # the order list of sequence j is in runs/.orders; replay is only needed for the labels, so read out/err directly
        pass
    out_text = (rd / f'{sub}out' / f'{seed:04d}.txt').read_text()
    err_text = (rd / f'{sub}err' / f'{seed:04d}.txt').read_text()
    out = replay.parse_output(inp, out_text) if j == 0 else None
    ann = replay.parse_annotations(err_text, inp.k)
    lines = out_text.split('\n')[inp.k:]
    # parse the queries directly (count, then "k d" lines)
    q = []; i = 0
    while i < len(lines) and len(q) < 1024:
        if not lines[i].strip(): i += 1; continue
        n = int(lines[i]); ops = [tuple(map(int, lines[i + 1 + t].split())) for t in range(n)]; q.append(ops); i += 1 + n
    fix = [0] * H; dig = [0] * H
    for r, ops in enumerate(q):
        labs = ann.labels_of(r, len(ops))
        for (k, d), lab in zip(ops, labs):
            c = cols[k] if k >= 7 else -1
            if c < 0: continue
            if lab == 'fix': fix[c] += 1
            elif lab == 'dig': dig[c] += 1
    R = len(q)
    if verbose:
        print(f'{run} seed {seed} seq {j}: G={G} H={H}  real fix {sum(fix)/R:.3f} /order (model hole {sum(hcost(c) for c in range(H))/256:.3f}), real dig {sum(dig)/R:.3f} (model col {sum(colcost(c) for c in range(H))/256:.3f})')
        print('   c  units targets ones  holeT(x,y) reset | hcost/256  fix/order | colcost/256  dig/order')
        for c in range(H):
            print(f'  {c:2d} {nc[c]:5d} {nt[c]:6d} {n1[c]:5d}  {hn[c][0]:4d},{hn[c][1]:<4d} {2*nt[c]:5d} |   {hcost(c)/256:.4f}    {fix[c]/R:.4f} |   {colcost(c)/256:.4f}     {dig[c]/R:.4f}')
    return dict(fix=[x / R for x in fix], dig=[x / R for x in dig], hcost=[hcost(c) / 256 for c in range(H)], colcost=[colcost(c) / 256 for c in range(H)], nc=nc, nt=nt, n1=n1, hn=hn, H=H)
if __name__ == '__main__':
    analyze(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 0)
