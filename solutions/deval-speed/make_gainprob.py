from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
s=s.replace('return covered_gain(covered, [&](int j) { return 0.5 * (q[j + 1] - q[j]); });','return covered_gain(covered, [&](int j) { return q[j]; });',1)
a='''        for (int t = 0; t < 256; t++)
            for (int c = 0; c < H; c++) q[t][c + 1] = q[t][c] + 2 * color_probability[c][(hb[t] >> c & 1) ^ 1];'''
b=a+'''
        // Resolve the original rounded prefix differences once. Ascending
        // writes do not touch either input needed by any following difference.
        for(int t=0;t<256;++t)for(int c=0;c<H;++c)q[t][c]=0.5*(q[t][c+1]-q[t][c]);'''
assert a in s;s=s.replace(a,b,1)
a='''            for (int c = 0; c < d.H; c++) q[t][c + 1] = q[t][c] + 2 * prob[c][(d.hb[t] >> c & 1) ^ 1];'''
b=a+'''
            for(int c=0;c<d.H;++c)q[t][c]=0.5*(q[t][c+1]-q[t][c]);'''
assert a in s;s=s.replace(a,b,1)
s=s.replace('// probabilities of the heads for the target). The saving is the expected number of fixes, less 1','// probabilities of the heads for the target, resolved once before calls). The saving is the expected number of fixes, less 1',1)
d=ROOT/'solutions/deval-gainprob';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-gainprob

改良元: solutions/deval-vbranch-o3。

filler期待費用で繰り返していた累積確率の差分0.5*(q[j+1]-q[j])を、累積和を作った直後に1回だけ計算して保存する。元の累積和の丸めと差分の算術をそのまま通し、直接の確率値への置換はしない。列挙順・探索予算・時間ガードは同じ。
''')
print(len(s.encode()))
