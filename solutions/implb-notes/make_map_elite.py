from pathlib import Path
root=Path(__file__).resolve().parents[2]
s=(root/'solutions/dcomp-combo-dual30/main.cpp').read_text()
def replace(old,new):
 global s
 assert s.count(old)==1,(old[:80],s.count(old))
 s=s.replace(old,new)
replace('//   Helper tables: dedicated papers inside the generic layer (Interleave)', '//   Alternate map: matching and column repair\n//   Helper tables: dedicated papers inside the generic layer (Interleave)')
replace('struct WindowStats {', '''// Snapshots use original physical-window coordinates, independently of the returned map.
struct MapEliteSnapshot {
    int pool_id=0,G=0;
    double cost=0,gap=0;
    u64 generic=0,pol=0;
    std::array<int,64> which{};
    std::array<std::pair<int,int>,15> edge{};
};
std::vector<MapEliteSnapshot> map_elite_snapshots;
bool map_elite_enabled() {
#ifdef LOCAL_BENCH
    if(const char* p=std::getenv("MAP_ELITE"))return std::atoi(p)!=0;
#endif
    return true;
}

struct WindowStats {''')
replace('    constexpr int kCutoff = 26;', '    map_elite_snapshots.clear();\n    constexpr int kCutoff = 26;')
replace('    stats.gobj_after = cur;', '''    stats.gobj_after = cur;
    if(map_elite_enabled()) {
        u64 final_generic=0;
        for(u64 x:mask)final_generic|=x;
        for(int i=0;i<int(elites.size());++i) {
            const auto& e=elites[i];
            if(!e.ready || e.generic==final_generic)continue;
            MapEliteSnapshot snapshot;
            snapshot.pool_id=i;snapshot.G=g;snapshot.cost=e.cost;snapshot.gap=e.cost-cur;
            snapshot.which.fill(-1);
            for(int q=0;q<ne;++q)snapshot.edge[q]=ep[q];
            for(int w=0;w<64;++w)if(e.generic>>w&1) {
                const int physical=permutation[w];
                snapshot.generic|=u64(1)<<physical;
                snapshot.pol|=((e.pol>>w)&1)<<physical;
                snapshot.which[physical]=e.which[w];
            }
            map_elite_snapshots.push_back(snapshot);
        }
    }''')
lns=(root/'solutions/lns-star-study/main.cpp').read_text()
repair=lns[lns.index('// ==== Large neighborhood: matching and column repair ===='):lns.index('// Shuffle only the selected comparison groups')]
repair=repair.replace('Large neighborhood: matching and column repair','Alternate map: matching and column repair').replace('LnsMatching','MapMatching').replace('LnsRepairStats','MapRepairStats').replace('lns_new_pairs','map_new_pairs').replace('lns_repair','repair_map_elite')
repair=repair.replace('MapRepairStats& stats,u64 salt)', 'const std::vector<bool>& changed_columns,MapRepairStats& stats,u64 salt)')
repair=repair.replace('d->handle=old.handle;d->rng.x=old.rng.x^salt;', '// New internal handles are G+c; retained physical handles keep column c.\n    d->rng.x=old.rng.x^salt;')
repair=repair.replace('for(const auto& u:old.unit)if(u.b>=0 && (!d->ok[u.a][u.b]||!d->valid(u,u.c))){\n        ++stats.broken;free[u.a]=free[u.b]=true;\n    }', '''for(const auto& u:old.unit) {
        const bool broken=u.b>=0 && (!d->ok[u.a][u.b]||!d->valid(u,u.c));
        stats.broken+=broken;
        if(changed_columns[u.c] || broken) {
            free[u.a]=true;
            if(u.b>=0)free[u.b]=true;
        }
    }''')
b=repair.index('    const int release=');e=repair.index('    struct Edge',b);repair=repair[:b]+repair[e:]
repair+='''// Rebuild coordinates once for the chosen different-set elite. Old physical
// handles that remain handles retain their columns, even after prefix handle swaps.
std::unique_ptr<Design> make_map_elite(const Design& old,const std::vector<u64>& originalA,
                                      const std::vector<int>& oldperm,const MapEliteSnapshot& e,
                                      Comparator& comp,std::vector<int>& permutation,
                                      MapRepairStats& stats,u64 salt) {
    if(e.G!=old.G)return {};
    const int H=old.H,G=old.G;
    std::vector<int> physical(H,-1),added;
    std::vector<bool> changed(H,false);
    u64 retained=0;
    for(int c=0;c<H;++c) {
        const int w=oldperm[old.handle[c]];
        if(!(e.generic>>w&1)){physical[c]=w;retained|=u64(1)<<w;}
        else changed[c]=true;
    }
    for(int w=0;w<63;++w)if(!((e.generic|retained)>>w&1))added.push_back(w);
    int ai=0;
    for(int c=0;c<H;++c)if(physical[c]<0)physical[c]=added.at(ai++);
    assert(ai==int(added.size()));
    permutation.clear();
    for(int w=0;w<63;++w)if(e.generic>>w&1)permutation.push_back(w);
    permutation.insert(permutation.end(),physical.begin(),physical.end());
    permutation.push_back(63);
    assert(permutation.size()==64);
    comp.M=191-old.U;comp.G=G;comp.edge.resize(G);comp.polarity.resize(G);
    for(int j=0;j<G;++j) {
        const int w=permutation[j];
        assert(e.which[w]>=0 && e.which[w]<15);
        comp.edge[j]=e.edge[e.which[w]];comp.polarity[j]=e.pol>>w&1;
    }
    comp.rebuild();
    std::vector<u64> A(256,0);
    for(int a=0;a<256;++a)for(int j=0;j<63;++j)A[a]|=((originalA[a]>>permutation[j])&1)<<j;
    auto result=repair_map_elite(old,A,comp,changed,stats,salt);
#ifdef LOCAL_BENCH
    if(result) {
        std::array<int,256> seen{};
        for(const auto& u:result->unit) {
            assert(result->valid(u,u.c));++seen[u.a];
            if(u.b>=0){assert(result->ok[u.a][u.b]);++seen[u.b];}
        }
        for(int n:seen)assert(n==1);
        for(int c=0;c<H;++c)assert(result->n1[c]>0 && result->n1[c]<result->nc[c]);
    }
#endif
    return result;
}

'''
replace('// ==== Helper tables: dedicated papers inside the generic layer (Interleave) ====',repair+'// ==== Helper tables: dedicated papers inside the generic layer (Interleave) ====')
replace('    std::unique_ptr<Design> best_assignment;', '''    std::unique_ptr<Design> best_assignment;
    const Comparator primary_comp=comp;
    const auto primary_permutation=permutation;
    bool branch_is_alt=false,best_is_alt=false;
    int alt_attempt=0,alt_success=0,alt_selected=0;
    double alt_v=0,alt_main_v=0,alt_gap=0;
    MapRepairStats alt_stats;
    const MapEliteSnapshot* alternate=nullptr;
    u64 primary_generic=0;
    for(int j=0;j<G;++j)primary_generic|=u64(1)<<permutation[j];
    for(const auto& e:map_elite_snapshots)if(e.G==G) {
        const int swaps=Design::pc(e.generic^primary_generic);
        if(!alternate || std::make_tuple(e.cost,swaps,e.pool_id)<
            std::make_tuple(alternate->cost,Design::pc(alternate->generic^primary_generic),alternate->pool_id))alternate=&e;
    }''')
replace('if(v<best){best=v;chosen=id;state=std::move(candidate);chosen_log=log.str();best_assignment=std::make_unique<Design>(*des);}', 'if(v<best){best=v;chosen=id;state=std::move(candidate);chosen_log=log.str();best_assignment=std::make_unique<Design>(*des);best_is_alt=branch_is_alt;}')
replace('''        des=std::make_unique<Design>(*prefix);
        if(i)des->rng.x^=u64(i)*0x9E3779B97F4A7C15ULL;''','''        comp=primary_comp;permutation=primary_permutation;branch_is_alt=false;
        if(i==3 && map_elite_enabled() && alternate) {
            ++alt_attempt;alt_gap=alternate->gap;alt_main_v=best;
            des=make_map_elite(*prefix,originalA,primary_permutation,*alternate,comp,permutation,alt_stats,
                              u64(i)*0x9E3779B97F4A7C15ULL);
            if(!des)continue;  // An infeasible alternate is not a completed candidate.
            ++alt_success;branch_is_alt=true;
        } else {
            des=std::make_unique<Design>(*prefix);
            if(i)des->rng.x^=u64(i)*0x9E3779B97F4A7C15ULL;
        }''')
replace('        complete(i,0);','''        const double v=complete(i,0);
        if(branch_is_alt){alt_v=v;alt_selected=best_is_alt;}''')
replace('''        des=std::make_unique<Design>(*best_assignment);
        des->rng.x^=u64(repeat)*0x9E3779B97F4A7C15ULL;''','''        des=std::make_unique<Design>(*best_assignment);
        comp.M=state.M;comp.G=state.G;comp.edge=state.edge;comp.polarity=state.polarity;comp.rebuild();
        permutation=state.permutation;branch_is_alt=best_is_alt;
        des->rng.x^=u64(repeat)*0x9E3779B97F4A7C15ULL;''')
replace('    if(!finished)state.emergency=true;', '''    std::cerr<<"map_alt_attempt = "<<alt_attempt<<"\\nmap_alt_success = "<<alt_success
             <<"\\nmap_alt_selected = "<<alt_selected<<"\\nmap_alt_final = "<<best_is_alt
             <<"\\nmap_alt_gap = "<<alt_gap<<"\\nmap_alt_v = "<<alt_v
             <<"\\nmap_alt_main_v = "<<alt_main_v<<"\\nmap_alt_broken = "<<alt_stats.broken
             <<"\\nmap_alt_free_targets = "<<alt_stats.free_targets<<"\\nmap_alt_new_pairs = "<<alt_stats.new_pairs
             <<"\\nmap_alt_expanded = "<<alt_stats.expanded<<'\\n';
    if(!finished)state.emergency=true;''')
(root/'solutions/d30b-map-elite/main.cpp').write_text(s)
