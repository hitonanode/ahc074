from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
s=B
pos='    // The same when some column is not covered (its arrays passed): in every covered column,'
assert s.count(pos)==1
code=r'''    // A partial-coverage case formerly rescanned and ranked every covered column
    // on each next-cost miss. Cache each column's exact paper sequence instead.
    // Paper IDs (not only MDP types) are needed for the original one-step weights.
    struct PartialMdpEntry {
        u64 lo=0,hi=0;
        int length=-1;
        double one=0;
        float value=0;
    };
    mutable std::array<std::array<PartialMdpEntry,16>,64> partial_mdp_cache;
    mutable long long partial_mdp_hits=0,partial_mdp_misses=0;
    double colmdp_next_partial(const uint8_t* key,int count,
                            const std::array<bool,K>& extra,
                            const std::array<bool,128>& available,
                            const std::array<int,128>& first,const std::array<int,64>& rank,
                            const std::array<std::array<double,2>,64>& covered)const {
        std::array<u64,64> low{},high{};
        std::array<int,64> size{};
        for(int i=0;i<count;) {
            const int c=next_paper[key[i]].color>>1;
            if(!colmdp[c].ok) {
                do{++i;}while(i<count && (next_paper[key[i]].color>>1)==c);
                continue;
            }
            int n=size[c];u64 lo=low[c],hi=high[c];
            do {
                if(n<8)lo|=u64(key[i])<<(8*n);else hi|=u64(key[i])<<(8*(n-8));
                ++n;++i;
            }while(i<count && (next_paper[key[i]].color>>1)==c);
            size[c]=n;low[c]=lo;high[c]=hi;
        }
        double term=0;
        for(int c=0;c<H;++c) {
            if(!colmdp[c].ok)continue;
            const int n=size[c];const u64 lo=low[c],hi=high[c];
            const u64 h=(lo^(hi<<17|hi>>47)^u64(n))*0x9e3779b97f4a7c15ULL;
            auto& memo=partial_mdp_cache[c][(h^(h>>32))&15];
            if(memo.length!=n || memo.lo!=lo || memo.hi!=hi) {
                ++partial_mdp_misses;
                const auto& mdp=colmdp[c];
                auto at=[&](int i){return int((i<8?lo>>(8*i):hi>>(8*(i-8)))&255);};
                double one=0;
                for(int depth=0;depth<n;++depth)
                    one+=adaptive_weights[at(depth)]*depth/P;
                int r=0,sequence_rank=0;
                for(int i=n-1;i>=0;--i) {
                    const int t=colmdp_type[at(i)];r+=mdp.radix[t];sequence_rank+=mdp.before[r][t];
                }
                memo={lo,hi,n,one,mdp.F[mdp.offset[r]+sequence_rank]};
            } else ++partial_mdp_hits;
            double one_step=memo.one;
            for(int color=0;color<2;++color) {
                int fixes=available[2*c+color]?0:first[2*c+color];
                if(fixes<0)fixes=rank[c];
                one_step+=(adaptive_holes[c][color]-kCoverStrength*covered[c][color])*fixes;
            }
            term+=colmdp_next_weight[c]*memo.value-colmdp_next_drop*one_step;
        }
#ifdef PARTIAL_MDP_CHECK
        const double reference=colmdp_next_term(extra,available,first,rank,covered);
        if(std::bit_cast<u64>(reference)!=std::bit_cast<u64>(term)) {
            std::cerr<<"PARTIAL_MDP_MISMATCH "<<std::hexfloat<<reference<<' '<<term<<'\n';std::abort();
        }
#else
        (void)extra;
#endif
        return term;
    }
'''
s=s.replace(pos,code+pos)
x='            cost += colmdp_next_term(extra, available, first, rank, covered);'
# Preserve the old reference function under NEXT_PREFIX_CHECK.
i=s.index('    __attribute__((target("avx2,popcnt"))) double adaptive_next_cost(')
a,b=s[:i],s[i:];assert b.count(x)==1
b=b.replace(x,'            cost += colmdp_next_partial(key.data(),in_place,extra,available,first,rank,covered);');s=a+b
x='    cf_report();';assert s.count(x)==1
s=s.replace(x,'''    std::cerr<<"partial_mdp_hits = "<<solver.partial_mdp_hits<<"\\npartial_mdp_misses = "<<solver.partial_mdp_misses<<'\\n';
'''+x)
for name,source,extra in [('dcomp-t11-partial-cache',s,''),('dcomp-t11-partial-check','#define PARTIAL_MDP_CHECK 1\n'+s,'全呼出しを元のpartial関数でも再計算し、doubleの全bitを照合する検証版。')]:
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(source)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n列MDPが全列を覆わないケースのnext_costだけを短縮する。covered列の在列紙ID列（最大15枚）を正確な2語のkeyで持ち、元の紙順で足したone-step項とMDP値を列ごとの16枠に保存する。hole項と列間の加算順は変えない。キーの全体を検査し、hash衝突は値を共有しない。'+extra+'\n\npartial_mdp_hits/missesは列cacheの回数。予算・両コンパイラの探索設定・既存ログ・実験スイッチ・profiler・段の目印・DesignStoreを保持する。時計による切替なし。\n')
