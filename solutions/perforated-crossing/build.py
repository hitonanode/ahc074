from pathlib import Path
p=Path(__file__).resolve().parent
s=Path('solutions/perforated-screen/perforate.hpp').read_text()
s=s.replace('    int trial_paper=-1;', '    int trial_paper=-1;\n    static inline bool crossing_cache=true, skip_equal=true;\n    std::vector<u64> cache_opacity;\n    long long equal_queries=0;')
s=s.replace('''        for(int c=0;c<H;c++)q.avoid[c]=(used[H]>>c&1)?solve_edges(edges,c):q.value;''','''        if(!crossing_cache)for(int c=0;c<H;c++)q.avoid[c]=(used[H]>>c&1)?solve_edges(edges,c):q.value;
        else{
            // A path which does not use a donor ending at c either takes the
            // zero-cost c -> c+1 step, or crosses it with an interval ending later.
            for(int c=0;c<H;c++)q.avoid[c]=q.forward[c]+q.backward[c+1];
            for(int lo=0;lo<H;lo++){
                double best=-1e9;
                for(int c=H-2;c>=lo;c--){
                    best=std::max(best,edges[c+1][lo]+q.backward[c+2]);
                    q.avoid[c]=std::max(q.avoid[c],q.forward[lo]+best);
                }
            }
#ifdef VERIFY_CROSSING
            for(int c=0;c<H;c++)assert(std::abs(q.avoid[c]-solve_edges(edges,c))<1e-7);
#endif
        }''')
s=s.replace('cache_heads=choose_heads();cache.resize(P*overlap_samples);', 'cache_heads=choose_heads();cache_opacity=opacity;cache.resize(P*overlap_samples);')
s=s.replace('''        double sum=0;
        for(int u=0;u<P;u++)for(int sample=0;sample<overlap_samples;sample++){
            int i=u*overlap_samples+sample;const auto&q=cache[i];''','''        std::vector<bool> same(P);
        if(skip_equal&&changed.size()==1){
            int c=changed[0];
            for(int u=0;u<P;u++){
                if(s.ded[u]==trial_paper)continue;
                u64 holes=low_bits(H)&~opacity[s.ded[u]];
                auto signature=[&](int k,const std::vector<u64>& opq){
                    u64 mask=opq[k]&holes,wrong=mask&(colors[k]^target[u]);
                    int lo=wrong?64-__builtin_clzll(wrong):0;
                    u64 cover=mask&~low_bits(lo)&low_bits(c+1);
                    if(__builtin_popcountll(cover)<2)return std::pair<u64,int>{0,0};
                    return std::pair<u64,int>{cover,lo};
                };
                same[u]=true;
                for(int b=0;b<2;b++)same[u]=same[u]&&(signature(heads[c][b],opacity)==signature(cache_heads[c][b],cache_opacity));
            }
        }
        double sum=0;
        for(int u=0;u<P;u++)for(int sample=0;sample<overlap_samples;sample++){
            int i=u*overlap_samples+sample;const auto&q=cache[i];
            if(same[u]){sum+=q.value;equal_queries++;continue;}''')
s=s.replace('''#ifdef VERIFY_FAST_PERFORATION
                assert(std::abs(next-full_profit())<1e-7);''','''#ifdef VERIFY_FAST_PERFORATION
                if(viable)assert(std::abs(next-full_profit())<1e-7);''')
(p/'perforate.hpp').write_text(s)
s=Path('solutions/perforated-batch/probe.cpp').read_text()
s=s.replace('for(int setting=0;setting<6;setting++)', 'for(int setting=0;setting<4;setting++)')
a=s.index('Perforation::overlap_samples=16;');b=s.index('  double model=',a)
s=s[:a]+'''Perforation::overlap_samples=16;Perforation::screen_weight=1;Perforation::crossing_cache=setting>=2;Perforation::skip_equal=setting==3;Perforation design(s);double original=design.hole_cost-design.profit;
  if(setting)design.run(.5,1,false);
'''+s[b:]
s=s.replace('<<design.holes()<<', '<<design.holes()<<",\\\"fast_queries\\\":"<<design.fast_queries<<",\\\"full_queries\\\":"<<design.full_queries<<",\\\"equal_queries\\\":"<<design.equal_queries<<')
(p/'probe.cpp').write_text(s)
r=Path('solutions/perforated-screen/run.py').read_text().replace('ahc074-perforated-screen','ahc074-perforated-crossing').replace('20261103-220920_post-prune','20261103-230624_post-repair')
(p/'run.py').write_text(r)
(p/'README.md').write_text('''# 区間DPの除外費用を横切る区間から計算\n\n改良元: solutions/perforated-screen。注文処理は solutions/post-repair。\n\n穴追加の評価で、ある列の補助紙を使わない最良費用を列ごとにDPし直す代わりに、その列を0手で通過する経路と、後ろまで横切る区間の最大値から一括で求める。前向き・後ろ向きDPを使い、二次時間で全列の除外費用を計算する。\n\nさらに、変更前後で有効な被覆位置と最浅の差し込み位置が同じ商品では、全ての先頭色標本の利益が同じなので前の値を再利用する。VERIFY_CROSSINGで全列の再DP、VERIFY_FAST_PERFORATIONで各候補の全DPと照合する。\n\n研究用。候補や目的は元の全1穴変更・16標本・利益係数0.5と同じ。固定乱数の模擬注文を使い、隠された注文列は読まない。CLOCK_SCALEを適用する。\n''')
