struct Perforation {
    static inline int overlap_samples=8;
    static inline bool freeze_heads=true, head_candidates=true;
    std::vector<std::array<int,2>> fixed_heads;
    static inline double screen_weight=1;
    int screened=0;
    int trial_paper=-1;
    static inline bool crossing_cache=true, skip_equal=true;
    std::vector<u64> cache_opacity;
    long long equal_queries=0;
    long long fast_queries=0,full_queries=0;
    struct QueryCache{std::array<double,26> forward{},backward{};std::array<double,25> avoid{};double value=0;};
    std::vector<QueryCache> cache;
    std::vector<std::array<int,2>> cache_heads;
    using Edges=std::array<std::array<double,26>,25>;
    std::vector<u64> samples;
    Solver& s;
    int H;
    std::vector<u64> opacity, allowed, colors, target;
    std::vector<int> frequency, columns;
    std::vector<std::vector<int>> owners;
    std::vector<std::array<int, 2>> counts, max_frequency;
    std::vector<int> demands;
    std::vector<std::array<double, 2>> probability;
    std::vector<std::vector<double>> gains, bad;
    std::vector<double> utility;
    int trials=0, accepted=0;
    double hole_cost=0, profit=0;

    explicit Perforation(Solver& solver):s(solver),H(s.H),opacity(s.h_opq),allowed(s.h_opq),colors(s.h_blk),target(P),frequency(K),columns(s.col_of),owners(K),counts(H),max_frequency(H),demands(H),probability(H),gains(K,std::vector<double>(P)),bad(P,std::vector<double>(H)),utility(K){
        for(int u=0;u<P;u++){
            int k=s.ded[u];owners[k].push_back(u);frequency[k]++;demands[columns[k]]++;target[u]=s.handle_bits(s.A[u]);
            for(int c=0;c<H;c++)if(!(opacity[k]>>c&1))counts[c][target[u]>>c&1]++;
        }
        for(int k=7;k<K;k++)max_frequency[columns[k]][colors[k]>>columns[k]&1]=std::max(max_frequency[columns[k]][colors[k]>>columns[k]&1],frequency[k]);
        rebuild();if(freeze_heads)fixed_heads=cache_heads;
    }
    double cost(int c)const{
        double x=counts[c][0],y=counts[c][1],r=2*demands[c];
        return 4*Design::kHoleWeight*(x*y+.5*r*std::min(x,y))/std::max(1.,x+y+r);
    }
    double gain(int u,int k)const{
        int c=columns[k];u64 mask=opacity[k]&~opacity[s.ded[u]];
        u64 wrong=mask&(colors[k]^target[u]);int level=wrong?64-__builtin_clzll(wrong):0;
        if(level>=c)return 0;
        u64 cover=mask&low_bits(c)&~low_bits(level);double p0=1,p1=0,expected=0;
        for(u64 bits=cover;bits;bits&=bits-1){int j=__builtin_ctzll(bits);double p=bad[u][j];expected+=p;p1=p1*(1-p)+p0*p;p0*=1-p;}
        return std::max(0.,expected-(1-p0)-.6*(1-p0-p1));
    }
    double separate_profit()const{
        if(!fixed_heads.empty()){
            double sum=0;for(int c=0;c<H;c++)for(int b=0;b<2;b++)sum+=probability[c][b]*utility[fixed_heads[c][b]];return sum;
        }
        std::vector<std::array<double,2>> best(H);
        for(int k=7;k<K;k++){
            int c=columns[k],b=colors[k]>>c&1;
            if(frequency[k]==max_frequency[c][b])best[c][b]=std::max(best[c][b],utility[k]);
        }
        double sum=0;for(int c=0;c<H;c++)for(int b=0;b<2;b++)sum+=probability[c][b]*best[c][b];
        return sum;
    }
    // Price a set of compatible, non-overlapping placements. Multiple
    // donors cannot all claim the same repaired handle as a saving.
    __attribute__((target("popcnt"))) double full_profit()const{
        if(overlap_samples==0)return separate_profit();
        auto heads=choose_heads();
        double sum=0;
        for(int u=0;u<P;u++){
            int own=s.ded[u];u64 holes=low_bits(H)&~opacity[own];
            std::array<std::array<u64,2>,25> ranges{};
            std::array<std::array<int,2>,25> levels{};
            for(int c=0;c<H;c++)for(int b=0;b<2;b++){
                int k=heads[c][b];assert(k>=0);u64 mask=opacity[k]&holes;
                u64 wrong=mask&(colors[k]^target[u]);ranges[c][b]=mask;
                levels[c][b]=wrong?64-__builtin_clzll(wrong):0;
            }
            for(int sample=0;sample<overlap_samples;sample++){
                u64 color=samples[u*overlap_samples+sample],wrong=(color^target[u])&holes;
                std::array<double,26> forward{};
                for(int c=0;c<H;c++){
                    forward[c+1]=forward[c];if(c==columns[own])continue;
                    for(int b=0;b<2;b++){
                        int lo=levels[c][b];u64 covered=wrong&ranges[c][b]&~low_bits(lo);
                        int number=__builtin_popcountll(covered);double price=1.6+(b!=int(color>>c&1));
                        if(number<=price)continue;
                        for(int start=lo;start<=c;start++){
                            forward[c+1]=std::max(forward[c+1],forward[start]+number-price);
                            number-=int(covered>>start&1);if(number<=price)break;
                        }
                    }
                }
                sum+=forward[H];
            }
        }
        return sum/overlap_samples;
    }
    std::vector<std::array<int,2>> choose_heads()const{
        if(!fixed_heads.empty())return fixed_heads;
        std::vector<std::array<int,2>> heads(H,std::array<int,2>{-1,-1});
        for(int k=7;k<K;k++){
            int c=columns[k],b=colors[k]>>c&1;
            if(frequency[k]==max_frequency[c][b]&&(heads[c][b]<0||utility[k]>utility[heads[c][b]]))heads[c][b]=k;
        }
        return heads;
    }
    __attribute__((target("popcnt"))) void edge_column(int u,u64 color,int c,const std::vector<std::array<int,2>>&heads,std::array<double,26>&edge)const{
        edge.fill(-1e9);int own=s.ded[u];if(c==columns[own])return;
        u64 holes=low_bits(H)&~opacity[own],bad_mask=(color^target[u])&holes;
        for(int b=0;b<2;b++){
            int k=heads[c][b];assert(k>=0);u64 mask=opacity[k]&holes;
            u64 wrong=mask&(colors[k]^target[u]);int lo=wrong?64-__builtin_clzll(wrong):0;
            if(lo>c)continue;
            u64 covered=bad_mask&mask&~low_bits(lo);
            int number=__builtin_popcountll(covered);double price=1.6+(b!=int(color>>c&1));
            for(int start=lo;start<=c&&number>price;start++){
                edge[start]=std::max(edge[start],number-price);
                number-=int(covered>>start&1);
            }
        }
    }
    Edges make_edges(int u,u64 color,const std::vector<std::array<int,2>>&heads)const{
        Edges edges;for(int c=0;c<H;c++)edge_column(u,color,c,heads,edges[c]);return edges;
    }
    double solve_edges(const Edges&edges,int skip=-1)const{
        std::array<double,26> dp{};
        for(int c=0;c<H;c++){
            dp[c+1]=dp[c];if(c==skip)continue;
            for(int lo=0;lo<=c;lo++)dp[c+1]=std::max(dp[c+1],dp[lo]+edges[c][lo]);
        }
        return dp[H];
    }
    QueryCache make_cache(const Edges&edges)const{
        QueryCache q;std::array<unsigned,26> used{};
        for(int c=0;c<H;c++){
            q.forward[c+1]=q.forward[c];used[c+1]=used[c];
            for(int lo=0;lo<=c;lo++){
                double v=q.forward[lo]+edges[c][lo];
                if(v>q.forward[c+1])q.forward[c+1]=v,used[c+1]=used[lo]|(1U<<c);
            }
        }
        q.value=q.forward[H];
        for(int lo=H-1;lo>=0;lo--){
            q.backward[lo]=q.backward[lo+1];
            for(int c=lo;c<H;c++)q.backward[lo]=std::max(q.backward[lo],edges[c][lo]+q.backward[c+1]);
        }
        if(!crossing_cache)for(int c=0;c<H;c++)q.avoid[c]=(used[H]>>c&1)?solve_edges(edges,c):q.value;
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
        }
        return q;
    }
    void refresh_cache(){
        cache_heads=choose_heads();cache_opacity=opacity;cache.resize(P*overlap_samples);
        for(int u=0;u<P;u++)for(int sample=0;sample<overlap_samples;sample++){
            int i=u*overlap_samples+sample;cache[i]=make_cache(make_edges(u,samples[i],cache_heads));
        }
    }
    double cached_profit()const{
        double sum=0;for(const auto&q:cache)sum+=q.value;return sum/overlap_samples;
    }
    double total_profit(){
        if(trial_paper<0)return cached_profit();
        auto heads=choose_heads();std::vector<int>changed;
        for(int c=0;c<H;c++)if(heads[c]!=cache_heads[c]||heads[c][0]==trial_paper||heads[c][1]==trial_paper)changed.push_back(c);
        std::vector<bool> same(P);
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
            if(same[u]){sum+=q.value;equal_queries++;continue;}
            if(s.ded[u]==trial_paper||changed.size()>1){sum+=solve_edges(make_edges(u,samples[i],heads));full_queries++;}
            else if(changed.empty())sum+=q.value;
            else{
                int c=changed[0];std::array<double,26>edge;edge_column(u,samples[i],c,heads,edge);
                double value=q.avoid[c];
                for(int lo=0;lo<=c;lo++)value=std::max(value,q.forward[lo]+edge[lo]+q.backward[c+1]);
                sum+=value;fast_queries++;
            }
        }
        return sum/overlap_samples;
    }

    void rebuild(){
        hole_cost=0;
        for(int c=0;c<H;c++){
            hole_cost+=cost(c);double x=counts[c][0],y=counts[c][1],r=2*demands[c],n=x+y+r;
            double p=n?(y+r*(y>x))/n:.5;probability[c]={1-p,p};
            for(int u=0;u<P;u++)bad[u][c]=probability[c][(target[u]>>c&1)^1];
        }
        std::fill(utility.begin(),utility.end(),0);
        for(int k=7;k<K;k++)for(int u=0;u<P;u++)utility[k]+=gains[k][u]=gain(u,k);
        std::mt19937_64 random(731000003);samples.assign(P*overlap_samples,0);
        for(auto&bits:samples)for(int c=0;c<H;c++)if((random()>>11)*0x1.0p-53<probability[c][1])bits|=1ULL<<c;
        refresh_cache();profit=cached_profit();
    }
    void run(double weight,int passes,bool only_heads){
        std::mt19937_64 rng(0xc9a513a1ULL);
        for(int pass=0;pass<passes;pass++){
            rebuild();std::vector<std::pair<int,int>> candidates;
            for(int k=7;k<K;k++){
                int c=columns[k],b=colors[k]>>c&1;
                if(only_heads&&frequency[k]!=max_frequency[c][b])continue;
                if(!fixed_heads.empty()&&head_candidates&&k!=fixed_heads[c][b])continue;
                for(u64 bits=allowed[k]&low_bits(c);bits;bits&=bits-1)candidates.push_back({k,__builtin_ctzll(bits)});
            }
            std::shuffle(candidates.begin(),candidates.end(),rng);
            for(auto[k,c]:candidates){
                trials++;const u64 bit=1ULL<<c;bool remove=opacity[k]&bit;
                auto old_utility=utility,old_row=gains[k];
                std::vector<std::array<double,2>> old_columns(K);
                for(int y=7;y<K;y++)if(y!=k)for(int q=0;q<int(owners[k].size());q++){
                    int u=owners[k][q];old_columns[y][q]=gains[y][u];utility[y]-=gains[y][u];
                }
                double old_cost=cost(c),old_separate=separate_profit();opacity[k]^=bit;
                for(int u:owners[k])counts[c][target[u]>>c&1]+=remove?1:-1;
                const double delta=cost(c)-old_cost;
                utility[k]=0;for(int u=0;u<P;u++)utility[k]+=gains[k][u]=gain(u,k);
                for(int y=7;y<K;y++)if(y!=k)for(int u:owners[k])utility[y]+=gains[y][u]=gain(u,y);
                bool viable=screen_weight==0||delta-screen_weight*(separate_profit()-old_separate)<-1e-9;
                screened+=!viable;trial_paper=k;double next=viable?total_profit():profit;trial_paper=-1;
#ifdef VERIFY_FAST_PERFORATION
                if(viable)assert(std::abs(next-full_profit())<1e-7);
#endif
                if(viable&&delta-weight*(next-profit)<-1e-9){hole_cost+=delta;profit=next;accepted++;refresh_cache();assert(std::abs(profit-cached_profit())<1e-7);}
                else{
                    opacity[k]^=bit;for(int u:owners[k])counts[c][target[u]>>c&1]+=remove?-1:1;
                    utility=std::move(old_utility);gains[k]=std::move(old_row);
                    for(int y=7;y<K;y++)if(y!=k)for(int q=0;q<int(owners[k].size());q++)gains[y][owners[k][q]]=old_columns[y][q];
                }
            }
#ifdef VERIFY_PERFORATION
            for(int k=7;k<K;k++)for(int u=0;u<P;u++)assert(std::abs(gains[k][u]-gain(u,k))<1e-9);
            double sum=0;for(int c=0;c<H;c++)sum+=cost(c);assert(std::abs(sum-hole_cost)<1e-6);
#endif
        }
    }
    void run_targeted(double weight,int passes,int max_holes){
        std::mt19937_64 rng(0xc9a513a1ULL);
        for(int pass=0;pass<passes;pass++){
            rebuild();std::vector<std::pair<int,u64>> candidates;
            for(int k=7;k<K;k++){
                int c=columns[k],b=colors[k]>>c&1;
                if(k!=fixed_heads[c][b])continue;
                // Erase precisely the wrong printed windows that prevent
                // this donor from covering one recipient above a level.
                // This crosses barriers that a one-hole descent cannot cross.
                for(int u=0;u<P;u++){
                    if(s.ded[u]==k)continue;
                    u64 wrong=(colors[k]^target[u])&opacity[k]&~opacity[s.ded[u]];
                    if(wrong>>c&1)continue;
                    for(int lo=0;lo<c;lo++){
                        u64 remove=wrong&~low_bits(lo)&low_bits(c);
                        int size=__builtin_popcountll(remove);
                        if(size>=2&&size<=max_holes)candidates.push_back({k,remove});
                    }
                }
            }
            std::sort(candidates.begin(),candidates.end());
            candidates.erase(std::unique(candidates.begin(),candidates.end()),candidates.end());
            std::shuffle(candidates.begin(),candidates.end(),rng);
            for(auto[k,bit]:candidates){
                bit&=opacity[k];if(__builtin_popcountll(bit)<2)continue;trials++;u64 removed=opacity[k]&bit;
                auto old_utility=utility,old_row=gains[k];
                std::vector<std::array<double,2>> old_columns(K);
                for(int y=7;y<K;y++)if(y!=k)for(int q=0;q<int(owners[k].size());q++){
                    int u=owners[k][q];old_columns[y][q]=gains[y][u];utility[y]-=gains[y][u];
                }
                double delta=0,old_separate=separate_profit();
                for(u64 bits=bit;bits;bits&=bits-1){int c=__builtin_ctzll(bits);delta-=cost(c);for(int u:owners[k])counts[c][target[u]>>c&1]+=(removed>>c&1)?1:-1;delta+=cost(c);}
                opacity[k]^=bit;
                utility[k]=0;for(int u=0;u<P;u++)utility[k]+=gains[k][u]=gain(u,k);
                for(int y=7;y<K;y++)if(y!=k)for(int u:owners[k])utility[y]+=gains[y][u]=gain(u,y);
                bool viable=screen_weight==0||delta-screen_weight*(separate_profit()-old_separate)<-1e-9;
                screened+=!viable;trial_paper=k;double next=viable?total_profit():profit;trial_paper=-1;
#ifdef VERIFY_FAST_PERFORATION
                if(viable)assert(std::abs(next-full_profit())<1e-7);
#endif
                if(viable&&delta-weight*(next-profit)<-1e-9){hole_cost+=delta;profit=next;accepted++;refresh_cache();assert(std::abs(profit-cached_profit())<1e-7);}
                else{
                    opacity[k]^=bit;for(u64 bits=bit;bits;bits&=bits-1){int c=__builtin_ctzll(bits);for(int u:owners[k])counts[c][target[u]>>c&1]+=(removed>>c&1)?-1:1;}
                    utility=std::move(old_utility);gains[k]=std::move(old_row);
                    for(int y=7;y<K;y++)if(y!=k)for(int q=0;q<int(owners[k].size());q++)gains[y][owners[k][q]]=old_columns[y][q];
                }
            }
#ifdef VERIFY_PERFORATION
            for(int k=7;k<K;k++)for(int u=0;u<P;u++)assert(std::abs(gains[k][u]-gain(u,k))<1e-9);
            double sum=0;for(int c=0;c<H;c++)sum+=cost(c);assert(std::abs(sum-hole_cost)<1e-6);
#endif
        }
    }
    int holes()const{int answer=0;for(int k=7;k<K;k++)answer+=__builtin_popcountll(allowed[k]&~opacity[k]);return answer;}
    void install(){
        for(int k=7;k<K;k++){
            for(int c=0;c<H;c++)if(!(opacity[k]>>c&1))s.paper[k].opaque&=~(1ULL<<s.handle[c]);
            s.paper[k].black&=s.paper[k].opaque;s.h_opq[k]=s.handle_bits(s.paper[k].opaque);s.h_blk[k]=s.handle_bits(s.paper[k].black);
        }
        s.adaptive_initialized=false;s.init_adaptive();
        s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();
    }
};
