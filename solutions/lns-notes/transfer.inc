// ==== Large neighborhood: transfer finished perforations ====

// Preserve only genuine old perforations, expressed in physical window space.
// Natural pair holes and holes below the old column are not inherited. A new
// pair takes the intersection of its old papers' perforations; every hole is
// clipped to a naturally opaque handle strictly above its new anchor.
DesignState lns_transfer_perforations(const DesignState& raw,const DesignState& parent) {
    auto result=raw;
    std::array<std::vector<int>,K> old_members,new_members;
    for(int t=0;t<P;++t){old_members[parent.ded[t]].push_back(t);new_members[raw.ded[t]].push_back(t);}
    std::array<int,64> inverse{};for(int w=0;w<64;++w)inverse[raw.permutation[w]]=w;
    std::array<u64,P> extra{};
    for(int k=0;k<K;++k)if(!old_members[k].empty()){
        const auto& ts=old_members[k];const int c=parent.columns[k];u64 natural=0;
        for(int j=0;j<=c;++j)natural|=1ULL<<parent.handle[j];
        if(ts.size()==2)natural&=~(parent.A[ts[0]]^parent.A[ts[1]]);
        u64 transformed=0;
        for(u64 bits=natural&~parent.papers[k].opaque;bits;bits&=bits-1){const int w=__builtin_ctzll(bits);transformed|=1ULL<<inverse[parent.permutation[w]];}
        for(int t:ts)extra[t]=transformed;
    }
    int count=0;
    for(int k=0;k<K;++k)if(!new_members[k].empty()){
        const auto& ts=new_members[k];const int c=raw.columns[k];u64 keep=extra[ts[0]],prior=0;
        if(ts.size()==2)keep&=extra[ts[1]];
        for(int j=0;j<c;++j)prior|=1ULL<<raw.handle[j];
        keep&=prior&raw.papers[k].opaque;count+=__builtin_popcountll(keep);
        result.papers[k].opaque&=~keep;result.papers[k].black&=result.papers[k].opaque;
        assert(result.papers[k].opaque>>raw.handle[c]&1);
    }
    std::cerr<<"lns_transferred_holes = "<<count<<'\n';return result;
}
