// ==== Large neighborhood: matching and column repair ====

// Edmonds' cardinality augmentation, seeded with the cheap greedy matching.
// Fixed vertices have no adjacency, so augmenting paths cannot disturb them.
struct LnsRepairStats {
    int broken=0,free_targets=0,released_pairs=0,new_pairs=0,expanded=0;
    double map_before=0,map_after=0;
    int lost_max=0,lost_accepted=0,lost_tracked=0;
    int graph_added=0,graph_removed=0,window_changes=0;
    std::vector<std::pair<int,int>> map_pairs;
    std::vector<std::pair<int,int>> preferred_pairs;
    int preferred_valid=0,preferred_used=0;
};
int lns_new_pairs(const Design& a,const Design& old) {
    int n=0;
    for(const auto& u:a.unit)if(u.b>=0){const auto& v=old.unit[old.owner[u.a]];n+=!((v.a==u.a&&v.b==u.b)||(v.a==u.b&&v.b==u.a));}
    return n;
}
std::unique_ptr<Design> lns_repair(const Design& old,const std::vector<u64>& A,const Comparator& comp,
                                 LnsRepairStats& stats,u64 salt,const std::array<bool,256>& released) {
    auto d=std::make_unique<Design>(A,comp.M,comp.G);
    d->handle=old.handle;d->rng.x=old.rng.x^salt;
    for(int a=0;a<256;++a){d->hb[a]=0;for(int c=0;c<d->H;++c)d->hb[a]|=((A[a]>>d->handle[c])&1)<<c;}
    for(int a=0;a<256;++a)for(int b=a+1;b<256;++b){
        const auto reach=comp.closure(A[a],A[a]^A[b]);bool ok=true;u64 packed=0;
        for(int i=0;i<comp.M;++i){ok&=!(reach[i]>>i&1);packed|=u64(reach[i])<<(8*i);}
        if(!ok)continue;
        d->ok[a][b]=d->ok[b][a]=1;d->partners[a].push_back(b);d->partners[b].push_back(a);
        d->gcost[a][b]=d->gcost[b][a]=PosetSums::get().both_of(packed)/1440.0;
    }
    for(int a=0;a<256;++a)for(int b=a+1;b<256;++b){
        stats.graph_added+=d->ok[a][b]&&!old.ok[a][b];stats.graph_removed+=old.ok[a][b]&&!d->ok[a][b];
    }
    std::array<bool,256> free=released;
    for(auto [a,b]:stats.preferred_pairs)if(d->ok[a][b]){
        ++stats.preferred_valid;
        const auto& x=old.unit[old.owner[a]];const auto& y=old.unit[old.owner[b]];
        free[x.a]=free[y.a]=true;if(x.b>=0)free[x.b]=true;if(y.b>=0)free[y.b]=true;
    }
    for(const auto& u:old.unit)if(u.b>=0 && (!d->ok[u.a][u.b]||!d->valid(u,u.c))){
        ++stats.broken;free[u.a]=free[u.b]=true;
    }
    // A single enters the region only through an edge to an affected product.
    for(const auto& u:old.unit)if(u.b<0)
        for(int b:d->partners[u.a])if(free[b]){free[u.a]=true;break;}
    const int release=std::max(0,env_int("LNS_RELEASE"));
    std::vector<int> optional;
    for(int x=0;x<old.U;++x)if(old.unit[x].b>=0&&!free[old.unit[x].a])optional.push_back(x);
    for(int i=int(optional.size())-1;i>0;--i)std::swap(optional[i],optional[d->rng.below(i+1)]);
    for(int i=0;i<std::min(release,int(optional.size()));++i){const auto& u=old.unit[optional[i]];free[u.a]=free[u.b]=true;}
    struct Edge{double w;int a,b;};std::vector<Edge> edges;
    for(int a=0;a<256;++a)for(int b:d->partners[a])if(a<b)
        edges.push_back({.65*Design::pc(d->hb[a]^d->hb[b])+2*d->gcost[a][b]+.04*Design::pc(A[a]^A[b]),a,b});
    std::sort(edges.begin(),edges.end(),[](const Edge&a,const Edge&b){return std::tie(a.w,a.a,a.b)<std::tie(b.w,b.a,b.b);});
    if(!stats.preferred_pairs.empty()){
        for(auto& e:edges)if(std::find(stats.preferred_pairs.begin(),stats.preferred_pairs.end(),std::pair<int,int>{e.a,e.b})!=stats.preferred_pairs.end())e.w-=1000;
        std::stable_sort(edges.begin(),edges.end(),[](const Edge&a,const Edge&b){return a.w<b.w;});
    }
    LnsMatching match;bool repaired=false;
    if(env_int("LNS_USE_MAP_MATCH") && int(stats.map_pairs.size())==d->need){
        for(auto [a,b]:stats.map_pairs){assert(d->ok[a][b]);match.mate[a]=b;match.mate[b]=a;}
        for(int a=0;a<256;++a){const auto& u=old.unit[old.owner[a]];const int b=u.b<0?-1:(u.a==a?u.b:u.a);
            if(match.mate[a]!=b){free[a]=true;if(b>=0)free[b]=true;}
        }
        repaired=true;
    }
    for(int pass=0;pass<2 && !repaired;++pass){
        match=LnsMatching();int count=0;
        for(const auto& u:old.unit)if(u.b>=0&&!free[u.a]){match.mate[u.a]=u.b;match.mate[u.b]=u.a;++count;}
        for(const auto& e:edges)if(free[e.a]&&free[e.b]){
            match.g[e.a].push_back(e.b);match.g[e.b].push_back(e.a);
            if(count<d->need&&match.mate[e.a]<0&&match.mate[e.b]<0){match.mate[e.a]=e.b;match.mate[e.b]=e.a;++count;}
        }
        for(int a=0;a<256&&count<d->need;++a)if(free[a]&&match.mate[a]<0)count+=match.augment(a);
        if(count==d->need){repaired=true;break;}
        // A repair may enlarge its product region; it never rejects a window
        // proposal merely because many of the old pairs were destroyed.
        free.fill(true);++stats.expanded;
    }
    if(!repaired)return {};
    for(auto [a,b]:stats.preferred_pairs)stats.preferred_used+=match.mate[a]==b;
    stats.free_targets=std::count(free.begin(),free.end(),true);
    for(const auto& u:old.unit)if(u.b>=0&&free[u.a])++stats.released_pairs;
    std::vector<Design::Unit> pending;
    for(int a=0;a<256;++a){
        int b=match.mate[a];if(b>=0&&a>b)continue;
        Design::Unit u{a,b,-1};
        const auto& before=old.unit[old.owner[a]];
        bool keep=!free[a];
        if(env_int("LNS_KEEP_COLUMNS")) {
            keep=(b<0?before.b<0:((before.a==a&&before.b==b)||(before.a==b&&before.b==a)))&&d->valid(u,before.c);
            // A replaced physical handle releases its entire column.
            for(int t=0;t<256&&keep;++t)if(((old.hb[t]^d->hb[t])>>before.c)&1)keep=false;
        }
        if(keep){u.c=before.c;d->unit.push_back(u);}
        else pending.push_back(u);
    }
    d->cur=0;d->cval.assign(d->H,100000.0);d->cur=100000.0*d->H;
    for(const auto& u:d->unit)d->update(u,1);
    auto install=[&](int i,int c){auto u=pending[i];u.c=c;d->unit.push_back(u);d->update(u,1);pending.erase(pending.begin()+i);};
    // Restore both anchor colors before filling released column slots.
    for(int c=0;c<d->H;++c)for(int v=0;v<2;++v){
        if(v?d->n1[c]>0:d->nc[c]-d->n1[c]>0)continue;
        int best=-1;double cost=1e100;
        for(int i=0;i<int(pending.size());++i)if(d->valid(pending[i],c)&&d->color(pending[i],c)==v){
            const auto& u=pending[i];double q=1000*(u.b>=0)+std::abs(old.unit[old.owner[u.a]].c-c);
            if(q<cost){cost=q;best=i;}
        }
        if(best<0)return {};
        install(best,c);
    }
    std::stable_sort(pending.begin(),pending.end(),[](const auto&a,const auto&b){return (a.b>=0)>(b.b>=0);});
    while(!pending.empty()){
        const auto u=pending.front();int best=-1;double cost=1e100;
        for(int c=0;c<d->H;++c)if(d->valid(u,c)){
            const int w=d->weight(u),v=d->color(u,c);
            double q=d->colcost_of(d->nc[c]+1,d->nt[c]+w,d->n1[c]+v,d->pairOne[c]+(u.b>=0)*v)-d->colcost(c);
            q+=.55*w*(d->H-1-c)+1.5*std::max(0,d->nc[c]+1-old.nc[c]);
            q+=.15*std::abs(c-old.unit[old.owner[u.a]].c);
            if(q<cost){cost=q;best=c;}
        }
        if(best<0)return {};
        install(0,best);
    }
    if(int(d->unit.size())!=d->U)return {};
    std::array<int,256> visits{};int pairs=0;
    for(const auto& u:d->unit){++visits[u.a];assert(d->valid(u,u.c));if(u.b>=0){++visits[u.b];++pairs;assert(d->ok[u.a][u.b]);}}
    assert(pairs==d->need);for(int n:visits)assert(n==1);
    d->refresh_reset();stats.new_pairs=lns_new_pairs(*d,old);return d;
}

// Choose mutually disjoint, short new product pairs whose comparison constraints
// outside the destroyed region are already acyclic. Their compatibility steers
// window repair, but only a completed design can enter the retained incumbent.
void lns_prefer_pairs(const Design& old,const std::vector<u64>& A,const Comparator& comp,XorShift& rng){
    const int count=std::max(0,env_int("LNS_PREFERRED_PAIRS"));if(!count)return;
    struct Option{double cost;int a,b;};std::vector<Option> options;
    u64 handles=kActiveWindows&~low_bits(comp.G);
    for(int a=0;a<256;++a)for(int b=a+1;b<256;++b){
        if(old.ok[a][b])continue;
        const u64 diff=A[a]^A[b];if(Design::pc(diff)>26||!(diff&lns_map.windows))continue;
        const auto reach=comp.closure(A[a],diff&~lns_map.windows);bool ok=true;u64 packed=0;
        for(int i=0;i<comp.M;++i){ok&=!(reach[i]>>i&1);packed|=u64(reach[i])<<(8*i);}
        if(!ok)continue;
        const double cost=.5*Design::pc(diff&handles)+.04*Design::pc(diff)+PosetSums::get().both_of(packed)/720.;
        options.push_back({cost+double(rng.next()%1000000)/1000000.,a,b});
    }
    std::sort(options.begin(),options.end(),[](const Option&a,const Option&b){return std::tie(a.cost,a.a,a.b)<std::tie(b.cost,b.a,b.b);});
    std::array<bool,256> used{};
    for(const auto& x:options)if(!used[x.a]&&!used[x.b]){
        used[x.a]=used[x.b]=true;lns_map.preferred_pairs.emplace_back(x.a,x.b);
        if(int(lns_map.preferred_pairs.size())==count)break;
    }
}

// Shuffle only the selected comparison groups and a fixed number of handles.
// The map repair can flip, exchange and transfer any window inside this region.
void lns_destroy(std::vector<u64>& A,Comparator& comp,std::vector<int>& permutation,
                 XorShift& rng,int step) {
    lns_map=LnsMapConfig();lns_map.active=true;lns_map.salt=rng.next();
    lns_map.temperature=env_real("LNS_MAP_TEMP",.12);
    if(env_int("LNS_CUT")) {
        std::vector<int> codes={1,2,4,8,16,31};
        for(int k=1;k<32;++k)if(std::find(codes.begin(),codes.end(),k)==codes.end())codes.push_back(k);
        const int code=codes[step%codes.size()];
        int index=0;for(int a=0;a<comp.M;++a)for(int b=a+1;b<comp.M;++b,++index)
            if(((code>>a)^(code>>b))&1)lns_map.groups.push_back(index);
        for(int w=0;w<comp.G;++w){auto [a,b]=comp.edge[w];if(((code>>a)^(code>>b))&1){comp.polarity[w]^=1;lns_map.windows|=1ULL<<w;}}
        comp.rebuild();return;
    }
    const int sheet=step%comp.M;
    std::vector<std::pair<int,int>> groups;
    for(int a=0;a<comp.M;++a)for(int b=a+1;b<comp.M;++b)if(a==sheet||b==sheet)groups.push_back({a,b});
    for(int i=int(groups.size())-1;i>0;--i)std::swap(groups[i],groups[rng.below(i+1)]);
    const int ng=std::min(int(groups.size()),std::max(1,int(env_real("LNS_GROUPS",5))));groups.resize(ng);
    std::vector<int> slots;
    for(int j=0;j<comp.G;++j)if(std::find(groups.begin(),groups.end(),comp.edge[j])!=groups.end())slots.push_back(j);
    const int generic=int(slots.size());
    std::vector<int> hs(63-comp.G);std::iota(hs.begin(),hs.end(),comp.G);
    for(int i=int(hs.size())-1;i>0;--i)std::swap(hs[i],hs[rng.below(i+1)]);
    const int nh=std::min(int(hs.size()),std::max(0,int(env_real("LNS_HANDLES",4))));
    slots.insert(slots.end(),hs.begin(),hs.begin()+nh);
    for(int j:slots)lns_map.windows|=1ULL<<j;
    int index=0;for(int a=0;a<comp.M;++a)for(int b=a+1;b<comp.M;++b,++index)
        if(std::find(groups.begin(),groups.end(),std::pair<int,int>{a,b})!=groups.end())lns_map.groups.push_back(index);
    const int kick=int(env_real("LNS_KICK",-1));
    auto src=slots;
    if(kick<0){for(int i=int(src.size())-1;i>0;--i)std::swap(src[i],src[rng.below(i+1)]);}
    else for(int k=0;k<kick;++k){int a=rng.below(src.size()),b=rng.below(src.size());std::swap(src[a],src[b]);}
    const auto oldp=permutation;
    for(int i=0;i<int(slots.size());++i)permutation[slots[i]]=oldp[src[i]];
    for(u64& a:A){u64 old=a;a&=~lns_map.windows;for(int i=0;i<int(slots.size());++i)a|=((old>>src[i])&1)<<slots[i];}
    if(kick<0)for(int i=0;i<generic;++i)comp.polarity[slots[i]]=rng.next()&1;
    else for(int k=0;k<kick;++k)comp.polarity[slots[rng.below(generic)]]^=1;
    comp.rebuild();
}
