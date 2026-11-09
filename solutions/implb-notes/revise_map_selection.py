from pathlib import Path
p=Path('solutions/d30b-map-elite/main.cpp');s=p.read_text()
old='''    for(const auto& e:map_elite_snapshots)if(e.G==G) {
        const int swaps=Design::pc(e.generic^primary_generic);
        if(!alternate || std::make_tuple(e.cost,swaps,e.pool_id)<
            std::make_tuple(alternate->cost,Design::pc(alternate->generic^primary_generic),alternate->pool_id))alternate=&e;
    }'''
new='''    // A close map should preserve the shared prefix. Audit only its old units;
    // the full 32640-pair graph is still built for exactly one selected elite.
    bool repair_first=true;
#ifdef LOCAL_BENCH
    if(const char* p=std::getenv("MAP_ELITE_REPAIR_FIRST"))repair_first=std::atoi(p)!=0;
#endif
    int alt_released_estimate=0;
    auto released_estimate=[&](const MapEliteSnapshot& e) {
        u64 old_handles=0;
        std::vector<int> physical(prefix->H);
        std::vector<bool> changed(prefix->H,false);
        for(int c=0;c<prefix->H;++c)old_handles|=u64(1)<<(physical[c]=primary_permutation[prefix->handle[c]]);
        u64 added=kActiveWindows & ~e.generic & ~old_handles;
        for(int c=0;c<prefix->H;++c)if(e.generic>>physical[c]&1) {
            physical[c]=__builtin_ctzll(added);added&=added-1;changed[c]=true;
        }
        int released=0;
        for(const auto& u:prefix->unit) {
            bool compatible=true;
            if(u.b>=0 && !changed[u.c]) {
                std::array<unsigned,6> reach{};
                for(u64 z=(originalA[u.a]^originalA[u.b])&e.generic;z;z&=z-1) {
                    const int w=__builtin_ctzll(z);auto [x,y]=e.edge[e.which[w]];
                    if(int(originalA[u.a]>>w&1)!=int(e.pol>>w&1))std::swap(x,y);
                    reach[x]|=1U<<y;
                }
                for(int k=0;k<6;++k)for(int x=0;x<6;++x)if(reach[x]>>k&1)reach[x]|=reach[k];
                for(int x=0;x<6;++x)compatible&=!(reach[x]>>x&1);
                compatible&=!((originalA[u.a]^originalA[u.b])>>physical[u.c]&1);
            }
            if(changed[u.c] || !compatible)released+=1+(u.b>=0);
        }
        return released;
    };
    for(const auto& e:map_elite_snapshots)if(e.G==G) {
        const int swaps=Design::pc(e.generic^primary_generic);
        const int released=repair_first?released_estimate(e):0;
        // Within the measured close-map window, prioritize less destroyed work.
        // Outside it, retain the window-cost ordering.
        auto key=[&](const MapEliteSnapshot& q,int n) {
            return std::make_tuple(repair_first && q.gap>.02,
                repair_first && q.gap<=.02?double(n):q.cost,q.cost,
                Design::pc(q.generic^primary_generic),q.pool_id);
        };
        if(!alternate || key(e,released)<key(*alternate,alt_released_estimate)) {
            alternate=&e;alt_released_estimate=released;
        }
        (void)swaps;
    }'''
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace('std::cerr<<"map_alt_attempt = "<<alt_attempt', 'std::cerr<<"map_alt_released_estimate = "<<alt_released_estimate<<"\\nmap_alt_attempt = "<<alt_attempt')
p.write_text(s)
