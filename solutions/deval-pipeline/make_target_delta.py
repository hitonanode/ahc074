from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
b=(R/'solutions/deval-ordered8/main.cpp').read_text()
start=b.index('        ANNEAL_TARGET void target_move(');end=b.index('        ANNEAL_TARGET void mutate(',start)
t=b[start:end]
old='''                const u64 hs = D.holes(u);
                _Pragma("GCC unroll 2") for (int t : {u.a, u.b}) {
                    if (t < 0) continue;
                    add_bits(d1, hs & D.hb[t], float(sgn));
                    add_bits(d0, hs & ~D.hb[t], float(sgn));
                }'''
assert old in t
t=t.replace(old,'',1)
pos=t.index('            const __m128i costs')
code='''            // At a pair difference, its two targets contribute one hole of
            // each color. Below both columns the exchanged targets cancel.
            // Every intermediate is a small exact integer, as in the original
            // four-unit SIMD additions; eval_holes retains its rounding order.
            auto pair_holes=[&](const Unit& u) {
                return u.b<0?u64(0):(D.hb[u.a]^D.hb[u.b])&low_bits(u.c+1);
            };
            __m256 common[NR];
            _Pragma("GCC unroll 5") for(int r=0;r<NR;++r)common[r]=_mm256_setzero_ps();
            add_bits(common,pair_holes(ox),-1.f);
            add_bits(common,pair_holes(nx),1.f);
            add_bits(common,pair_holes(oy),-1.f);
            add_bits(common,pair_holes(ny),1.f);
            const int old_target=ox.a!=nx.a?ox.a:ox.b;
            const int new_target=ox.a!=nx.a?nx.a:nx.b;
            const u64 from=D.hb[old_target],to=D.hb[new_target];
            const u64 range=low_bits(cx+1)^low_bits(cy+1);
            const u64 more=(to&~from)&range,less=(from&~to)&range;
            const __m256 sign=_mm256_set1_ps(cx<cy?1.f:-1.f);
            _Pragma("GCC unroll 5") for(int r=0;r<NR;++r) {
                const __m256 diff=_mm256_mul_ps(sign,_mm256_sub_ps(
                    _mm256_load_ps(bit_lanes((more>>(8*r))&255)),
                    _mm256_load_ps(bit_lanes((less>>(8*r))&255))));
                d0[r]=_mm256_sub_ps(common[r],diff);
                d1[r]=_mm256_add_ps(common[r],diff);
            }
'''
t=t[:pos]+code+t[pos:]
t=t.replace('eval_holes(d0, d1, N0, N1, Qv);','eval_holes(d0, d1, N0, N1, Qv,low_bits(std::max(cx,cy)+1));',1)
s=b[:start]+t+b[end:]
p=R/'solutions/deval-target-delta';p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: `solutions/deval-ordered8`。\n\n焼きなましの2目標交換で、穴需要の差分を4枚分の再加算から、ペア差分の穴と2列間の色需要だけに整理する。両列より深い需要は交換前後で相殺する。小さい整数の加減算で同じSIMD差分を作り、費用の除算・加算・受理判定と乱数列は維持する。探索回数と全候補、時計の規則は同じ。\n')
print(p.name,len(s.encode()))
