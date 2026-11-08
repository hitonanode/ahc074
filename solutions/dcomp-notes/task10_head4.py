from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-donor4/main.cpp').read_text()
a='    std::vector<int> active_heads;  // beta != 0, in the original unit-index order'
b=a+'''
    struct alignas(32) HeadBlock {
        std::array<u64,4> cover,bits,below;
        std::array<double,4> weight;
        std::array<int,4> column;
        int size;
    };
    std::vector<HeadBlock> head_blocks;'''
assert s.count(a)==1;s=s.replace(a,b)
a=s.index('    double target(int t,const Design::Unit& u,int slot=-1) const {');b=s.index('    // Recomputes everything',a)
s=s[:a]+'''    __attribute__((target("avx2"))) double target(int t,const Design::Unit& u,int slot=-1) const {
        AF_SCOPE(head_target,256);
        double sum=0;
        const u64 dx=(u.b>=0?d.hb[u.a]^d.hb[u.b]:0)|extra_holes(slot);
        const u64 holes=~low_bits(u.c+1)|dx;
        const auto hv=_mm256_set1_epi64x(holes),tv=_mm256_set1_epi64x(d.hb[t]);
        for(const auto& block:head_blocks) {
            const auto range=_mm256_and_si256(hv,_mm256_load_si256((const __m256i*)block.cover.data()));
            auto wrong=_mm256_and_si256(range,_mm256_xor_si256(tv,_mm256_load_si256((const __m256i*)block.bits.data())));
            wrong=_mm256_or_si256(wrong,_mm256_srli_epi64(wrong,1));
            wrong=_mm256_or_si256(wrong,_mm256_srli_epi64(wrong,2));
            wrong=_mm256_or_si256(wrong,_mm256_srli_epi64(wrong,4));
            wrong=_mm256_or_si256(wrong,_mm256_srli_epi64(wrong,8));
            wrong=_mm256_or_si256(wrong,_mm256_srli_epi64(wrong,16));
            wrong=_mm256_or_si256(wrong,_mm256_srli_epi64(wrong,32));
            alignas(32) u64 covered[4];
            _mm256_store_si256((__m256i*)covered,_mm256_andnot_si256(wrong,_mm256_and_si256(range,
                _mm256_load_si256((const __m256i*)block.below.data()))));
            for(int lane=0;lane<block.size;++lane)if(block.column[lane]!=u.c)
                sum+=block.weight[lane]*Design::covered_gain(covered[lane],[&](int j){return q[t][j];});
        }
        return sum;
    }
'''+s[b:]
a='''        for (int y = 0; y < d.U; ++y) if (beta[y]) active_heads.push_back(y);
        return last_value = sum;'''
b='''        for (int y = 0; y < d.U; ++y) if (beta[y]) active_heads.push_back(y);
        head_blocks.resize((active_heads.size()+3)/4);
        for(int bi=0;bi<int(head_blocks.size());++bi) {
            auto& block=head_blocks[bi];block={};block.size=std::min(4,int(active_heads.size())-4*bi);
            for(int lane=0;lane<block.size;++lane) {
                const int y=active_heads[4*bi+lane];block.cover[lane]=unit_cover[y];block.bits[lane]=unit_bits[y];
                block.column[lane]=unit_column[y];block.below[lane]=low_bits(unit_column[y]);block.weight[lane]=beta[y];
            }
        }
        return last_value = sum;'''
assert s.count(a)==1;s=s.replace(a,b)
p=r/'solutions/dcomp-head4';assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: solutions/dcomp-donor4\n\nrematchのtarget評価でも修復可能集合だけを4 headずつAVX2で計算する。headの整数マスクを元のactive_heads順に連続配置し、gatherを省く。確率多項式、重み、sumの順は元のまま。head更新と同時にblockを再構築する。予算・乱数・ログ・実験スイッチ・DesignStoreを維持、時間fallbackなし。\n')
