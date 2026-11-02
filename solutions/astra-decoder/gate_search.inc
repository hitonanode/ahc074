// Atomic 2--4-window gate search. Partial nodes only guide the beam; a complete
// candidate is accepted using freshly computed exact prices and a fresh matching.
// One comparator window for each of the fifteen sheet pairs is protected, so
// all distances use exactly the same legal directed graph as the six-sheet base.
struct AtomicGateSearch {
    using Bits=Comparator::StateBits;
    using GBits=std::array<u64,10>;
    struct Gate{unsigned o,b;};
    struct Pair{int u,v;u64 d;double fixed;};
    struct Eval{double value=1e9;std::vector<int> selected;std::vector<double>prices;};
    Comparator&c;const std::vector<u64>&A;std::vector<Gate>gates;
    std::vector<std::array<Bits,2>>truth;std::vector<GBits>one;
    std::vector<Pair>pairs;std::vector<int>movable;
    std::array<int,64>state{};u64 protected_mask=0;
    XorShift rng{0x92fa415db453eULL};long long full_evals=0,gate_trials=0;
    int accepted=0,multi_accepted=0;bool comparisons_only=false;
    AtomicGateSearch(Comparator&comp,const std::vector<u64>&a,bool only):c(comp),A(a),comparisons_only(only){
        c.build_tables();c.rebuild_truth();c.nonlinear=true;
        for(unsigned o=1;o<64;o++)for(unsigned b=(o-1)&o;b;b=(b-1)&o)
            if(!only||__builtin_popcount(o)==2)gates.push_back({o,b});
        one.resize(720);truth.resize(gates.size());
        for(int g=0;g<int(gates.size());g++)for(int s=0;s<720;s++){
            int color=0;for(int k:c.perms[s])if(gates[g].o>>k&1){color=gates[g].b>>k&1;break;}
            truth[g][color][s>>6]|=1ULL<<(s&63);if(color)one[s][g>>6]|=1ULL<<(g&63);
        }
        bool seen[6][6]{};
        for(int j=0;j<c.G;j++){
            auto[x,y]=c.edge[j];if(x>y)std::swap(x,y);
            if(!seen[x][y])seen[x][y]=true,protected_mask|=1ULL<<j;else movable.push_back(j);
            unsigned o=(1U<<x)|(1U<<y),b=0;
            for(int k=0;k<6;k++)if(c.black[k]>>j&1)b|=1U<<k;
            for(int g=0;g<int(gates.size());g++)if(gates[g].o==o&&gates[g].b==b)state[j]=g;
        }
        // All product pairs, as in Design::initialize, including distance > 26.
        for(int u=0;u<256;u++)for(int v=u+1;v<256;v++){
            u64 d=A[u]^A[v];pairs.push_back({u,v,d,.65*__builtin_popcountll(d>>c.G)+.04*__builtin_popcountll(d)});
        }
    }
    void set(int j,int g){
        state[j]=g;u64 bit=1ULL<<j;
        for(int k=0;k<6;k++){c.opq[k]=(c.opq[k]&~bit)|(u64(gates[g].o>>k&1)<<j);c.black[k]=(c.black[k]&~bit)|(u64(gates[g].b>>k&1)<<j);}
        c.truth[j]=truth[g];
    }
    void restore(const std::array<int,64>&s){for(int j:movable)set(j,s[j]);}
    Eval evaluate(u64 active){
        ++full_evals;Eval result;result.prices.assign(pairs.size(),-1);
        struct E{double price;int i;};std::vector<E>es;
        for(int i=0;i<int(pairs.size());i++){
            auto&e=pairs[i];auto x=c.goal_bits(A[e.u],e.d&active),y=c.goal_bits(A[e.v],e.d&active);
            if(!Comparator::any(x)||!Comparator::any(y))continue;
            double cost=e.fixed+c.exact_goal_mean(x)+c.exact_goal_mean(y);
            result.prices[i]=cost;es.push_back({cost,i});
        }
        std::sort(es.begin(),es.end(),[](auto&a,auto&b){return a.price<b.price||(a.price==b.price&&a.i<b.i);});
        std::array<bool,256>used{};double sum=0;
        for(auto e:es){auto&p=pairs[e.i];if(used[p.u]||used[p.v])continue;used[p.u]=used[p.v]=true;result.selected.push_back(e.i);sum+=e.price;if(result.selected.size()==71)break;}
        if(result.selected.size()<71){
            std::array<std::vector<std::pair<int,int>>,256>partners;
            for(auto e:es){auto&p=pairs[e.i];partners[p.u].push_back({p.v,e.i});partners[p.v].push_back({p.u,e.i});}
            while(result.selected.size()<71){
                double best=1e100;int bx=-1,bi=-1,bj=-1,bu=-1,bv=-1;
                for(int x=0;x<int(result.selected.size());x++){
                    int old=result.selected[x];auto&p=pairs[old];
                    for(auto[u,i]:partners[p.u])if(!used[u])for(auto[v,j]:partners[p.v])if(!used[v]&&u!=v){
                        double add=result.prices[i]+result.prices[j]-result.prices[old];
                        if(add<best){best=add;bx=x;bi=i;bj=j;bu=u;bv=v;}
                    }
                }
                if(bx<0)return result;
                used[bu]=used[bv]=true;sum+=best;result.selected[bx]=bi;result.selected.push_back(bj);
            }
        }
        result.value=sum/71;return result;
    }
    std::vector<int> choose_windows(int t){
        c.rebuild_truth();
        std::vector<int>hard;
        for(int i=0;i<int(pairs.size());i++){auto&e=pairs[i];if(__builtin_popcountll(e.d)<=26&&!c.compatible(A[e.u],A[e.v]))hard.push_back(i);}
        std::sort(hard.begin(),hard.end(),[&](int i,int j){return pairs[i].fixed<pairs[j].fixed;});
        for(int attempt=0;attempt<24&&!hard.empty();attempt++){
            auto&e=pairs[hard[rng.mod(std::min<int>(400,hard.size()))]];
            std::vector<u64>bad[2];
            for(int z=0;z<2;z++){
                u64 target=A[z?e.v:e.u];
                for(u64 disp:c.actual_display){u64 b=(disp^target)&e.d&low_bits(c.G);if(!(b&protected_mask)&&__builtin_popcountll(b)<=4)bad[z].push_back(b);}
                std::sort(bad[z].begin(),bad[z].end(),[](u64 a,u64 b){int x=__builtin_popcountll(a),y=__builtin_popcountll(b);return x<y||(x==y&&a<b);});
                bad[z].erase(std::unique(bad[z].begin(),bad[z].end()),bad[z].end());if(bad[z].size()>32)bad[z].resize(32);
            }
            std::vector<u64>unions;
            for(u64 x:bad[0])for(u64 y:bad[1])if(__builtin_popcountll(x|y)<=4)unions.push_back(x|y);
            if(unions.empty())continue;
            std::sort(unions.begin(),unions.end(),[](u64 a,u64 b){int x=__builtin_popcountll(a),y=__builtin_popcountll(b);return x<y||(x==y&&a<b);});
            u64 chosen=unions[rng.mod(std::min<int>(8,unions.size()))];
            std::vector<int>ws;for(;chosen;chosen&=chosen-1)ws.push_back(__builtin_ctzll(chosen));
            while(ws.size()<2){int j=movable[rng.mod(movable.size())];if(std::find(ws.begin(),ws.end(),j)==ws.end())ws.push_back(j);}
            if(t%3==2)while(ws.size()<4){int j=movable[rng.mod(movable.size())];if(std::find(ws.begin(),ws.end(),j)==ws.end())ws.push_back(j);}
            return ws;
        }
        std::vector<int>ws;while(ws.size()<unsigned(2+t%3)){int j=movable[rng.mod(movable.size())];if(std::find(ws.begin(),ws.end(),j)==ws.end())ws.push_back(j);}return ws;
    }
    void run(int iterations){
        const u64 gm=low_bits(c.G);auto initial_state=state;Eval current=evaluate(gm);const double before=current.value;
        struct Node{std::array<int,64>s;Eval e;};
        for(int t=0;t<iterations;t++){
            const auto saved=state;auto windows=choose_windows(t);u64 removed=0;for(int j:windows)removed|=1ULL<<j;
            std::vector<Node>beam;beam.push_back({state,evaluate(gm&~removed)});
            for(int j:windows){
                removed&=~(1ULL<<j);std::vector<Node>next;
                for(auto&node:beam){
                    restore(node.s);
                    std::vector<GBits>allowed(pairs.size());std::vector<int>eligible;
                    for(int i=0;i<int(pairs.size());i++){
                        auto&e=pairs[i];if(node.e.prices[i]<0)continue;
                        auto x=c.goal_bits(A[e.u],e.d&gm&~removed&~(1ULL<<j));auto y=c.goal_bits(A[e.v],e.d&gm&~removed&~(1ULL<<j));
                        if(!Comparator::any(x)||!Comparator::any(y))continue;eligible.push_back(i);
                        if(!(e.d>>j&1)){allowed[i].fill(~0ULL);continue;}
                        GBits can[2]{};Bits side[2]={x,y};
                        for(int z=0;z<2;z++){int color=(A[z?e.v:e.u]>>j)&1;for(int w=0;w<12;w++)for(u64 b=side[z][w];b;b&=b-1){int s=w*64+__builtin_ctzll(b);for(int k=0;k<10;k++)can[z][k]|=color?one[s][k]:~one[s][k];}}
                        for(int k=0;k<10;k++)allowed[i][k]=can[0][k]&can[1][k];
                    }
                    std::sort(eligible.begin(),eligible.end(),[&](int a,int b){return node.e.prices[a]<node.e.prices[b];});
                    std::vector<std::pair<double,int>>ranked;
                    for(int g=0;g<int(gates.size());g++){
                        ++gate_trials;std::array<bool,256>used{};int n=0;double sum=0;
                        for(int i:eligible){auto&e=pairs[i];if(used[e.u]||used[e.v]||!(allowed[i][g>>6]>>(g&63)&1))continue;used[e.u]=used[e.v]=true;sum+=node.e.prices[i];if(++n==71)break;}
                        ranked.push_back({sum/71+10*(71-n),g});
                    }
                    std::sort(ranked.begin(),ranked.end());
                    std::vector<int>shortlist{saved[j]};for(int k=0;k<std::min<int>(8,ranked.size());k++)shortlist.push_back(ranked[k].second);
                    // Preserve nonlinear diversity in the beam, even when the best
                    // partial comparator is a little cheaper. Complete acceptance
                    // remains by exact cost; no surrogate is reported as an outcome.
                    int extra=0;for(auto[z,g]:ranked)if(__builtin_popcount(gates[g].o)>2&&extra++<2)shortlist.push_back(g);
                    std::sort(shortlist.begin(),shortlist.end());shortlist.erase(std::unique(shortlist.begin(),shortlist.end()),shortlist.end());
                    for(int g:shortlist){set(j,g);auto ev=evaluate(gm&~removed);next.push_back({state,std::move(ev)});}
                }
                std::sort(next.begin(),next.end(),[](auto&a,auto&b){return a.e.value<b.e.value;});
                beam.clear();for(auto&node:next){bool duplicate=false;for(auto&b:beam)duplicate|=b.s==node.s;if(!duplicate)beam.push_back(std::move(node));if(beam.size()==4)break;}
            }
            if(!beam.empty()&&beam[0].e.value<current.value-1e-9){
                restore(beam[0].s);current=std::move(beam[0].e);int changes=0;for(int j:windows)changes+=saved[j]!=state[j];++accepted;multi_accepted+=changes>=2;
            }else restore(saved);
        }
        c.rebuild_truth();int nonlinear=0;for(int j=0;j<c.G;j++)nonlinear+=__builtin_popcount(gates[state[j]].o)>2;
        std::cerr<<"decoder_obj_before = "<<before<<"\ndecoder_obj_after = "<<current.value<<"\ndecoder_full_evals = "<<full_evals<<"\ndecoder_gate_trials = "<<gate_trials<<"\ndecoder_accepted = "<<accepted<<"\ndecoder_multi_accepted = "<<multi_accepted<<"\ndecoder_nonlinear = "<<nonlinear<<'\n';
    }
};
