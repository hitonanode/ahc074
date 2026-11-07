"""Retain only q vectors across the acceptance test; rebuild counts on acceptance."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
pos=s.index('        // Units x, y moved between the columns')
code='''        // Rejected column proposals need only their q change. Retain four
        // Q vectors, and reconstruct the exact integer count increments after
        // acceptance instead of keeping eight count vectors alive as well.
        ANNEAL_TARGET __attribute__((always_inline)) void column_deltas(
                int r,u64 x0,u64 x1,u64 y0,u64 y1,float wx,float wy,__m256& d0,__m256& d1) const {
            const int shift=8*r;
            const auto vx=_mm256_set1_ps(wx),vy=_mm256_set1_ps(wy),zero=_mm256_setzero_ps();
            d0=_mm256_fmadd_ps(_mm256_load_ps(bit_lanes((x0>>shift)&255)),vx,zero);
            d1=_mm256_fmadd_ps(_mm256_load_ps(bit_lanes((x1>>shift)&255)),vx,zero);
            if(wy!=0) {
                d0=_mm256_fmadd_ps(_mm256_load_ps(bit_lanes((y0>>shift)&255)),vy,d0);
                d1=_mm256_fmadd_ps(_mm256_load_ps(bit_lanes((y1>>shift)&255)),vy,d1);
            }
        }
        ANNEAL_TARGET __attribute__((always_inline)) float column_q(
                u64 x0,u64 x1,u64 y0,u64 y1,float wx,float wy,u64 dirty,__m256* Q) const {
            __m256 dif[NR];
            _Pragma("GCC unroll 5") for(int r=0;r<NR;++r) {
                if(r==NR-1&&!((dirty>>(8*r))&255)) {
                    Q[r]=_mm256_load_ps(hq+8*r);dif[r]=_mm256_setzero_ps();continue;
                }
                __m256 d0,d1;column_deltas(r,x0,x1,y0,y1,wx,wy,d0,d1);
                const auto a=_mm256_add_ps(_mm256_load_ps(n0+8*r),d0);
                const auto b=_mm256_add_ps(_mm256_load_ps(n1+8*r),d1);
                const auto t=_mm256_load_ps(reset+8*r);
                const auto den=_mm256_max_ps(_mm256_add_ps(_mm256_add_ps(a,b),t),_mm256_set1_ps(1.f));
                const auto num=_mm256_fmadd_ps(_mm256_mul_ps(_mm256_set1_ps(.5f),t),_mm256_min_ps(a,b),_mm256_mul_ps(a,b));
                Q[r]=_mm256_div_ps(num,den);
                dif[r]=_mm256_sub_ps(Q[r],_mm256_load_ps(hq+8*r));
            }
            auto acc=_mm256_add_ps(_mm256_add_ps(dif[0],dif[1]),_mm256_add_ps(dif[2],dif[3]));
            if constexpr(NR==5)acc=_mm256_add_ps(acc,dif[4]);
            return hsum(acc);
        }
        ANNEAL_TARGET __attribute__((always_inline)) void commit_column_q(
                u64 x0,u64 x1,u64 y0,u64 y1,float wx,float wy,const __m256* Q) {
            _Pragma("GCC unroll 5") for(int r=0;r<NR;++r) {
                __m256 d0,d1;column_deltas(r,x0,x1,y0,y1,wx,wy,d0,d1);
                _mm256_store_ps(n0+8*r,_mm256_add_ps(_mm256_load_ps(n0+8*r),d0));
                _mm256_store_ps(n1+8*r,_mm256_add_ps(_mm256_load_ps(n1+8*r),d1));
                _mm256_store_ps(hq+8*r,Q[r]);
            }
        }
'''
s=s[:pos]+code+s[pos:]
start=s.index('            __m256 d0[NR], d1[NR];',s.index('ANNEAL_TARGET void column_move('))
end=s.index('            const double delta =',start)
s=s[:start]+'''            const u64 interval=low_bits(P+1)^low_bits(Q+1);
            const int sign=Q>P?-1:1;
            const u64 hx=D.hb[ox.a],dx=px?hx^D.hb[ox.b]:0,mx=interval&~dx;
            const u64 hy=sy?D.hb[oy.a]:0,dy=sy&&py?hy^D.hb[oy.b]:0,my=sy?interval&~dy:0;
            const u64 x0=mx&~hx,x1=mx&hx,y0=my&~hy,y1=my&hy;
            const float xweight=float(sign*wx),yweight=float(-sy*sign*wy);
            __m256 Qv[NR];
            const float dq=column_q(x0,x1,y0,y1,xweight,yweight,interval,Qv);
'''+s[end:]
start=s.index('ANNEAL_TARGET void column_move(');end=s.index('ANNEAL_TARGET void target_move(',start)
b=s[start:end].replace('            commit_holes(N0, N1, Qv);','            commit_column_q(x0,x1,y0,y1,xweight,yweight,Qv);',1)
s=s[:start]+b+s[end:]
d=ROOT/'solutions/deval-recompute';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-recompute

改良元: solutions/deval-vbranch-o3。

焼きなましの列移動で、採否判定をまたいで保持するSIMD値を穴費用Qだけにする。穴数の変更は同じ整数のFMAで採用時に再計算する。棄却が多い処理でレジスタへの負担を減らす。qの除算・差分集計と乱数の順序、探索予算、時間ガードは変えない。
''')
print(d,len(s.encode()))
