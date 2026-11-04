from pathlib import Path

root=Path(__file__).resolve().parent
source=(root.parent/"as6-canon/main.cpp").read_text()
source=source.replace("    // Adaptive columns: a paper moved out",r'''
    // A product can use either of two printed templates. Tables are specific
    // to the chosen template, since its generic holes and usable helpers differ.
    std::vector<std::vector<int>> choices;
    std::vector<std::vector<std::vector<int>>> choice_sat;
    std::vector<std::vector<double>> choice_bias;
    std::vector<std::vector<std::pair<int,int>>> paper_targets;
    std::array<std::shared_ptr<Interleave>,2> choice_helpers;
    long long choice_requests=0, choice_alternative=0;
    void init_choices(double limit=1e9) {
        if(choices.empty()){choices.resize(P);for(int u=0;u<P;u++)choices[u]={ded[u]};}
        comparator.build_tables();
        choice_sat.resize(P);choice_bias.resize(P);paper_targets.assign(K,{});sat.assign(P,{});future.assign(comparator.perms.size(),0.0);
        int targets=0;
        for(int u=0;u<P;u++){
            choice_sat[u].resize(choices[u].size());
            choice_bias[u].resize(choices[u].size());
            bool has=false;
            for(int v=0;v<int(choices[u].size());v++){
                paper_targets[choices[u][v]].emplace_back(u,v);
                choice_bias[u][v]=.4*__builtin_popcountll(hmask&~paper[choices[u][v]].opaque);
                u64 gh=gmask&~paper[choices[u][v]].opaque;
                if(!gh)continue;
                has=true;choice_sat[u][v]=comparator.satisfying(A[u],gh);
                assert(!choice_sat[u][v].empty());
            }
            sat[u]=choice_sat[u][0];ded[u]=choices[u][0];
            if(!has)continue;targets++;
            for(int s=0;s<int(future.size());s++){
                double value=0;
                for(const auto& goals:choice_sat[u]){
                    int d=0;if(!goals.empty()){d=255;for(int t:goals)d=std::min(d,comparator.distance(s,t));}
                    value+=double(d)/choices[u].size();
                }
                future[s]+=value;
            }
        }
        for(int u=0;u<P;u++)for(int v=0;v<int(choices[u].size());v++)if(!choice_sat[u][v].empty()){
            double sum=0;for(int s=0;s<int(future.size());s++){int d=255;for(int t:choice_sat[u][v])d=std::min(d,comparator.distance(s,t));sum+=d;}
            choice_bias[u][v]+=sum/future.size();
        }
        if(targets)for(auto& f:future)f/=targets;
        for(int v=0;v<2;v++){
            std::vector<int> selected(P);bool needed=v==0;
            for(int u=0;u<P;u++){selected[u]=choices[u][std::min(v,int(choices[u].size())-1)];needed|=choices[u].size()>1;}
            if(!needed){choice_helpers[v]=choice_helpers[0];continue;}
            choice_helpers[v]=std::make_shared<Interleave>();
            choice_helpers[v]->init(comparator,paper,A,selected,col_of,gmask,hmask,limit);
        }
        interleave=choice_helpers[0];adaptive_initialized=false;init_adaptive();
    }

    // The marginal value of a copy decreases once the other copy is cheaper.
    // This replaces a fixed half-frequency when choosing a return position.
    double choice_rank_price(int k,int rank,const std::array<int,K>& other_rank) const {
        if(paper_targets.empty())return adaptive_weights[k]*rank;
        double cost=0;
        for(auto[u,v]:paper_targets[k]){
            double best=rank+choice_bias[u][v];
            for(int w=0;w<int(choices[u].size());w++)if(w!=v)
                best=std::min(best,other_rank[choices[u][w]]+choice_bias[u][w]);
            cost+=best-choice_bias[u][v];
        }
        return cost;
    }

    // Adaptive columns: a paper moved out''')
old='''            int d = ded[u];
            if (d < 0) continue;
            adaptive_weights[d] += 1.0;
            for (int c = 0; c < H; c++)
                if (!(paper[d].opaque >> handle[c] & 1)) adaptive_holes[c][A[u] >> handle[c] & 1] += 1.0 / P;'''
new='''            const auto options=choices.empty()?std::vector<int>{ded[u]}:choices[u];
            for(int d:options){
                if(d<0)continue;
                adaptive_weights[d]+=1.0/options.size();
                for(int c=0;c<H;c++)if(!(paper[d].opaque>>handle[c]&1))
                    adaptive_holes[c][A[u]>>handle[c]&1]+=1.0/(P*options.size());
            }'''
assert old in source
source=source.replace(old,new,1)
source=source.replace('''        std::vector<int> rank(H, 0);
        std::vector<std::array<int, 2>> first(H);''','''        std::vector<int> rank(H, 0);
        std::array<int,K> paper_rank{};
        std::vector<std::array<int, 2>> first(H);''',1)
source=source.replace('''            cost += adaptive_weights[k] * rank[c] / P;
            rank[c]++;''','''            paper_rank[k]=rank[c];
            if(choices.empty())cost+=adaptive_weights[k]*rank[c]/P;
            rank[c]++;''',1)
source=source.replace('''        for (int c = 0; c < H; c++)
            for (int color = 0; color < 2; color++) {
                int fixes = available[c][color] ? 0 : first[c][color];''','''        if(!choices.empty())for(int u=0;u<P;u++){
            double best=1e100,bias=1e100;
            for(int v=0;v<int(choices[u].size());v++){
                best=std::min(best,paper_rank[choices[u][v]]+choice_bias[u][v]);
                bias=std::min(bias,choice_bias[u][v]);
            }
            cost+=(best-bias)/P;
        }
        for (int c = 0; c < H; c++)
            for (int color = 0; color < 2; color++) {
                int fixes = available[c][color] ? 0 : first[c][color];''',1)
source=source.replace('''        std::vector<double> suffix(n + 1, 0.0);
        std::array<int, 2> first = {n, n};''','''        std::array<int,K> other_rank{};std::vector<int> count(H);
        if(!choices.empty())for(int k:order)if(col_of[k]>=0&&k!=top_d&&!is_filler(k))other_rank[k]=count[col_of[k]]++;
        std::vector<double> suffix(n + 1, 0.0);
        std::array<int, 2> first = {n, n};''',1)
source=source.replace('''            suffix[i] = suffix[i + 1] + adaptive_weights[v[i]];''','''            suffix[i]=suffix[i+1]+choice_rank_price(v[i],i+1,other_rank)-choice_rank_price(v[i],i,other_rank);''',1)
source=source.replace('''            double rank = adaptive_weights[x] * i + suffix[i];''','''            double rank=choice_rank_price(x,i,other_rank)+suffix[i];''',1)
old='''    std::vector<std::pair<int, int>> process(int u) {
        init_adaptive();'''
new=r'''    std::vector<std::pair<int,int>> process(int u) {
        if(choices.empty())return process_one(u);
        const auto before=save();State best_state;
        std::vector<std::pair<int,int>> best_ops;
        double best=1e100;int best_v=0;
        for(int v=0;v<int(choices[u].size());v++){
            restore(before);ded[u]=choices[u][v];sat[u]=choice_sat[u][v];interleave=choice_helpers[v];
            auto path=process_one(u);
            if(display()!=A[u]||path.size()>2*K)continue;
            double cost=path.size()+kFillerCharge*fillers.size()+kEndWeight*adaptive_next_cost();
            if(cost<best){best=cost;best_v=v;best_ops=std::move(path);best_state=save();}
        }
        if(best>1e90){restore(before);ded[u]=choices[u][0];sat[u]=choice_sat[u][0];interleave=choice_helpers[0];return process_one(u);}
        restore(best_state);ded[u]=choices[u][best_v];sat[u]=choice_sat[u][best_v];interleave=choice_helpers[best_v];
        choice_requests+=choices[u].size()>1;choice_alternative+=best_v>0;
        return best_ops;
    }
    std::vector<std::pair<int, int>> process_one(int u) {
        init_adaptive();'''
assert old in source
source=source.replace(old,new,1)
(root/"main.cpp").write_text(source)
