// ==== Finished generic layout ====

// Keep the finished dedicated papers and handles. Optimize the six generic
// patterns against their actual paired targets, preserving every pair's DAG.
void improve_generic_layout(DesignState& state,int iterations) {
    if(state.M!=6)return;
    const double start=elapsed_sec();
    const WindowRelations relations(PosetSums::get());
    std::array<std::pair<int,int>,15> pairs;
    int id[6][6]{};
    for(int a=0,e=0;a<6;++a)for(int b=a+1;b<6;++b,++e)pairs[e]={a,b},id[a][b]=e;
    std::vector<int> edge(state.G),pol=state.polarity;
    std::array<int,15> counts{};
    for(int j=0;j<state.G;++j){edge[j]=id[state.edge[j].first][state.edge[j].second];++counts[edge[j]];}
    std::array<int,K> first;first.fill(-1);
    std::vector<std::pair<u64,u64>> targets;
    for(int u=0;u<P;++u) {
        const int k=state.ded[u];
        if(first[k]<0)first[k]=u;
        else targets.push_back({state.A[first[k]],(state.A[first[k]]^state.A[u])&low_bits(state.G)});
    }
    auto evaluate=[&]() {
        int value=0;
        for(auto [color,holes]:targets) {
            uint32_t r=0;
            for(u64 z=holes;z;z&=z-1) {
                const int j=__builtin_ctzll(z);
                r|=1U<<(edge[j]+16*(int(color>>j&1)!=pol[j]));
            }
            const int v=relations.cost(r);
            if(!v)return 1000000000;
            value+=v-1;
        }
        return value;
    };
    XorShift random{0x39d375ec852ab91ULL};
    const int initial=evaluate();int current=initial,best=initial,accepted=0,improved=0;
    auto best_edge=edge,best_pol=pol;
    for(int it=0;it<iterations;++it) {
        const int j=random.below(state.G),k=random.below(state.G),mode=random.below(3);
        const int ej=edge[j],ek=edge[k],pj=pol[j],pk=pol[k];
        if(mode==0)pol[j]^=1;
        else if(mode==1){if(j==k)continue;std::swap(edge[j],edge[k]);std::swap(pol[j],pol[k]);}
        else {
            if(counts[ej]<=1)continue;
            --counts[ej];edge[j]=random.below(15);++counts[edge[j]];pol[j]=random.below(2);
        }
        const int next=evaluate();
        if(next<=current) {
            current=next;++accepted;
            if(next<best){best=next;best_edge=edge;best_pol=pol;++improved;}
        } else {
            if(mode==2){--counts[edge[j]];++counts[ej];}
            edge[j]=ej;edge[k]=ek;pol[j]=pj;pol[k]=pk;
        }
    }
    Comparator comp;comp.M=state.M;comp.G=state.G;comp.edge=state.edge;comp.polarity=best_pol;
    for(int j=0;j<state.G;++j)comp.edge[j]=pairs[best_edge[j]];
    comp.rebuild();assert(comp.complete);
    state.edge=comp.edge;state.polarity=comp.polarity;
    for(int k=0;k<state.M;++k)state.papers[k]={comp.opq[k],comp.black[k]};
    std::cerr<<"gref_initial = "<<double(initial)/(720*P)<<"\ngref_final = "<<double(best)/(720*P)
             <<"\ngref_accepts = "<<accepted<<"\ngref_improvements = "<<improved
             <<"\ngref_sec = "<<elapsed_sec()-start<<'\n';
}

