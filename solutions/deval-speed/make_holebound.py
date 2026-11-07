from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
lo=s.index('        ANNEAL_TARGET void column_move(');hi=s.index('        // An exchange of targets between units',lo)
b=s[lo:hi]
# No extra random draw unless the mathematical lower bound is strictly positive.
old='''            __m256 d0[NR], d1[NR];
            _Pragma("GCC unroll 5") for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            const u64 interval = low_bits(P + 1) ^ low_bits(Q + 1);
            const int sign = Q > P ? -1 : 1;
            const u64 hx = D.hb[ox.a], dx = px ? hx ^ D.hb[ox.b] : 0;
            const u64 mx = interval & ~dx;'''
new='''            const u64 interval = low_bits(P + 1) ^ low_bits(Q + 1);
            const int sign = Q > P ? -1 : 1;
            const u64 hx = D.hb[ox.a], dx = px ? hx ^ D.hb[ox.b] : 0;
            const u64 mx = interval & ~dx;
            const u64 hy = D.hb[oy.a], dy = py ? hy ^ D.hb[oy.b] : 0;
            const u64 my = interval & ~dy;
            bool sampled=false;
            double threshold=0;
            if(delta_col40>0) {
                // q(a,b,r) is monotone and 1-Lipschitz in either count.
                // Only removed demands can lower it. The 0.001 margin exceeds
                // accumulated rounding error of all 40 float lanes by >10x.
                const int removed=(sign<0?wx*__builtin_popcountll(mx):0)
                                 +(sy*sign>0?wy*__builtin_popcountll(my):0);
                const double lower=delta_col40*(1.0/40)-kHoleScale*removed-.001;
                if(lower>0) {
                    threshold=temp*logs[D.rng.next()&16383];sampled=true;
                    if(lower>=threshold)return;
                }
            }
            __m256 d0[NR], d1[NR];
            _Pragma("GCC unroll 5") for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();'''
assert old in b
b=b.replace(old,new,1)
b=b.replace('''                const u64 hy = D.hb[oy.a], dy = py ? hy ^ D.hb[oy.b] : 0;
                const u64 my = interval & ~dy;
''','',1)
b=b.replace('            if (!accept(delta)) return;','            if (sampled ? delta>=threshold : !accept(delta)) return;',1)
s=s[:lo]+b+s[hi:]
d=ROOT/'solutions/deval-holebound';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-holebound

改良元: solutions/deval-vbranch-o3。

焼きなましの列移動で列費用が増すとき、穴費用の改善量を「除く需要数×1.52」で上から押さえる。目的値差の下界が正なら、本来必要な乱数を先に1回読み、その下界だけで棄却できる候補のSIMD除算を省く。qは各需要数について単調かつ1-Lipschitz。floatの丸めには0.001の余裕を取る。乱数の消費と採択条件を保ち、出力一致を確認する。探索予算と時間ガードは同じ。
''')
print(len(s.encode()))
