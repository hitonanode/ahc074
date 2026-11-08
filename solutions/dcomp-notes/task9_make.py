"""Task9 exact-output design optimizations. Task8 sources are read-only."""
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[2]
BASE=(ROOT/'solutions/dcomp-nine/main.cpp').read_text()
assert hashlib.sha256(BASE.encode()).hexdigest()=='2969698026bbdb76c0d345d921480068edf14bad3480c6e15fd6dc1a476b8169'
def sub(s,a,b):
 assert s.count(a)==1,(s.count(a),a[:80]);return s.replace(a,b)
def write(name,s,desc):
 p=ROOT/'solutions'/name;p.mkdir(exist_ok=True)
 (p/'main.cpp').write_text(s)
 (p/'README.md').write_text('改良元: solutions/dcomp-nine\n\n'+desc+'\n\n探索の乱数列、固定反復数、候補数9、受理規則、V、注文処理を保持する。近似演算やfast-mathなし。CLOCK_SCALE、@paper/@ops、DesignStore、段の目印、実験スイッチとプロファイラを保ち、時間不足の切替は加えない。\n')
# Each new count is a small integer, exactly representable in float. Evaluate
# one 8-handle group before preparing the next, rather than keeping 2*NR deltas
# alive across all NR evaluations. The q polynomial and reduction are verbatim.
helper='''        // Column moves affect only one interval. Fuse construction of its
        // integer deltas with q evaluation, retaining the original FMA/division
        // and lane-reduction order while shortening SIMD temporary lifetimes.
        template<int sy>
        ANNEAL_TARGET __attribute__((always_inline)) float eval_column(
                u64 mx,u64 hx,u64 my,u64 hy,float kx,float ky,u64 dirty,
                __m256* N0,__m256* N1,__m256* Q) const {
            AF_SCOPE(eval_holes,4096);
            const __m256 zero=_mm256_setzero_ps(),one=_mm256_set1_ps(1.f);
            const __m256 vx=_mm256_set1_ps(kx),vy=_mm256_set1_ps(ky);
            __m256 dif[NR];
            _Pragma("GCC unroll 5") for(int r=0;r<NR;++r) {
                if(r==NR-1 && !((dirty>>(8*r))&255)) {
                    N0[r]=_mm256_load_ps(n0+8*r);N1[r]=_mm256_load_ps(n1+8*r);
                    Q[r]=_mm256_load_ps(hq+8*r);dif[r]=zero;continue;
                }
                __m256 a=_mm256_fmadd_ps(_mm256_load_ps(bit_lanes(((mx&~hx)>>(8*r))&255)),vx,zero);
                __m256 b=_mm256_fmadd_ps(_mm256_load_ps(bit_lanes(((mx&hx)>>(8*r))&255)),vx,zero);
                if constexpr(sy!=0) {
                    a=_mm256_fmadd_ps(_mm256_load_ps(bit_lanes(((my&~hy)>>(8*r))&255)),vy,a);
                    b=_mm256_fmadd_ps(_mm256_load_ps(bit_lanes(((my&hy)>>(8*r))&255)),vy,b);
                }
                N0[r]=_mm256_add_ps(_mm256_load_ps(n0+8*r),a);
                N1[r]=_mm256_add_ps(_mm256_load_ps(n1+8*r),b);
                const __m256 reset_count=_mm256_load_ps(reset+8*r);
                const __m256 s=_mm256_max_ps(_mm256_add_ps(_mm256_add_ps(N0[r],N1[r]),reset_count),one);
                const __m256 numerator=_mm256_fmadd_ps(_mm256_mul_ps(_mm256_set1_ps(.5f),reset_count),
                    _mm256_min_ps(N0[r],N1[r]),_mm256_mul_ps(N0[r],N1[r]));
                Q[r]=_mm256_div_ps(numerator,s);
                dif[r]=_mm256_sub_ps(Q[r],_mm256_load_ps(hq+8*r));
            }
            __m256 acc=_mm256_add_ps(_mm256_add_ps(dif[0],dif[1]),_mm256_add_ps(dif[2],dif[3]));
            if constexpr(NR==5)acc=_mm256_add_ps(acc,dif[4]);
            return hsum(acc);
        }
'''
s=sub(BASE,'        // Units x, y moved between the columns P = ox.c',helper+'        // Units x, y moved between the columns P = ox.c')
a='''            __m256 d0[NR], d1[NR];
            _Pragma("GCC unroll 5") for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            const u64 interval = low_bits(P + 1) ^ low_bits(Q + 1);
            const int sign = Q > P ? -1 : 1;
            const u64 hx = D.hb[ox.a], dx = px ? hx ^ D.hb[ox.b] : 0;
            const u64 mx = interval & ~dx;
            add_bits(d1, mx & hx, float(sign * wx));
            add_bits(d0, mx & ~hx, float(sign * wx));
            if (sy) {
                const u64 hy = D.hb[oy.a], dy = py ? hy ^ D.hb[oy.b] : 0;
                const u64 my = interval & ~dy;
                add_bits(d1, my & hy, float(-sy * sign * wy));
                add_bits(d0, my & ~hy, float(-sy * sign * wy));
            }
            __m256 N0[NR], N1[NR], Qv[NR];
            const float dq = eval_holes(d0, d1, N0, N1, Qv, interval);'''
b='''            const u64 interval=low_bits(P+1)^low_bits(Q+1);
            const int sign=Q>P?-1:1;
            const u64 hx=D.hb[ox.a],dx=px?hx^D.hb[ox.b]:0,mx=interval&~dx;
            u64 hy=0,my=0;
            if constexpr(sy!=0) {hy=D.hb[oy.a];my=interval&~(py?hy^D.hb[oy.b]:0);}
            __m256 N0[NR],N1[NR],Qv[NR];
            const float dq=eval_column<sy>(mx,hx,my,hy,float(sign*wx),float(-sy*sign*wy),interval,N0,N1,Qv);'''
s=sub(s,a,b)
write('dcomp-nine-fused',s,'annealのcolumn_moveで、差分SIMD配列の構築と取っ手費用の評価を8列ずつ融合する。元の整数差分・FMA・除算・横方向加算順序を保ち、全列分の差分配列を同時に生存させない。')
# Retain q but postpone saving the cheap integer counts until an accepted move.
h=helper.replace('__m256* N0,__m256* N1,__m256* Q','__m256* Q')
h=h.replace('                    N0[r]=_mm256_load_ps(n0+8*r);N1[r]=_mm256_load_ps(n1+8*r);\n','')
h=h.replace('N0[r]=','const __m256 A=').replace('N1[r]=','const __m256 B=').replace('N0[r]','A').replace('N1[r]','B')
s2=sub(s,helper,h)
s2=sub(s2,'''            __m256 N0[NR],N1[NR],Qv[NR];
            const float dq=eval_column<sy>(mx,hx,my,hy,float(sign*wx),float(-sy*sign*wy),interval,N0,N1,Qv);''','''            __m256 Qv[NR];
            const float dq=eval_column<sy>(mx,hx,my,hy,float(sign*wx),float(-sy*sign*wy),interval,Qv);''')
a='''            commit_holes(N0, N1, Qv);
            cnc[P]'''
b='''            // Accepted trials repeat only their exact small-integer additions;
            // rejected trials never spill new N0/N1 arrays to the stack.
            const __m256 zero=_mm256_setzero_ps(),vx=_mm256_set1_ps(float(sign*wx)),vy=_mm256_set1_ps(float(-sy*sign*wy));
            _Pragma("GCC unroll 5") for(int r=0;r<NR;++r) {
                __m256 a=_mm256_fmadd_ps(_mm256_load_ps(bit_lanes(((mx&~hx)>>(8*r))&255)),vx,zero);
                __m256 b=_mm256_fmadd_ps(_mm256_load_ps(bit_lanes(((mx&hx)>>(8*r))&255)),vx,zero);
                if constexpr(sy!=0) {
                    a=_mm256_fmadd_ps(_mm256_load_ps(bit_lanes(((my&~hy)>>(8*r))&255)),vy,a);
                    b=_mm256_fmadd_ps(_mm256_load_ps(bit_lanes(((my&hy)>>(8*r))&255)),vy,b);
                }
                _mm256_store_ps(n0+8*r,_mm256_add_ps(_mm256_load_ps(n0+8*r),a));
                _mm256_store_ps(n1+8*r,_mm256_add_ps(_mm256_load_ps(n1+8*r),b));
                _mm256_store_ps(hq+8*r,Qv[r]);
            }
            cnc[P]'''
s2=sub(s2,a,b)
write('dcomp-nine-deferred',s2,'dcomp-nine-fusedに加え、column_moveで新しい穴数の保存を受理まで遅らせる。棄却時は新しいQだけ保持する。受理時には元と同じ小整数加算を再計算してn0/n1へ保存する。費用式と評価値は変えない。')
