struct Perforation {
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
        rebuild();
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
    double total_profit()const{
        std::vector<std::array<double,2>> best(H);
        for(int k=7;k<K;k++){
            int c=columns[k],b=colors[k]>>c&1;
            if(frequency[k]==max_frequency[c][b])best[c][b]=std::max(best[c][b],utility[k]);
        }
        double sum=0;for(int c=0;c<H;c++)for(int b=0;b<2;b++)sum+=probability[c][b]*best[c][b];
        return sum;
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
        profit=total_profit();
    }
    void run(double weight,int passes,bool only_heads){
        std::mt19937_64 rng(0xc9a513a1ULL);
        for(int pass=0;pass<passes;pass++){
            rebuild();std::vector<std::pair<int,int>> candidates;
            for(int k=7;k<K;k++){
                int c=columns[k],b=colors[k]>>c&1;
                if(only_heads&&frequency[k]!=max_frequency[c][b])continue;
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
                double old_cost=cost(c);opacity[k]^=bit;
                for(int u:owners[k])counts[c][target[u]>>c&1]+=remove?1:-1;
                const double delta=cost(c)-old_cost;
                utility[k]=0;for(int u=0;u<P;u++)utility[k]+=gains[k][u]=gain(u,k);
                for(int y=7;y<K;y++)if(y!=k)for(int u:owners[k])utility[y]+=gains[y][u]=gain(u,y);
                double next=total_profit();
                if(delta-weight*(next-profit)<-1e-9){hole_cost+=delta;profit=next;accepted++;}
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
