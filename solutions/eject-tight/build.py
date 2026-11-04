from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'post-packed-links/main.cpp').read_text()
s=s.replace('static inline int replay_mode=1;', 'static constexpr int replay_mode=1;')
s=s.replace('static inline bool byte_links=true;', 'static constexpr bool byte_links=true;')
old='''        auto record_future=[&](double cost){
            if(future_candidates.size()==kPostCandidates&&cost>=future_candidates.back().cost)return;
            for(auto&candidate:future_candidates)if(candidate.state.order==order){'''
new='''        // Different insertion depths of the same moved-paper sequence often
        // collapse to one result during post-processing. Spend the second slot
        // on a different sequence while keeping the cheaper family member.
        auto same_family=[](const auto&a,const auto&b){
            if(a.size()!=b.size())return false;
            for(int i=0;i<int(a.size());i++)if(a[i].first!=b[i].first)return false;
            return true;
        };
        auto record_future=[&](double cost){
            if(future_candidates.size()==kPostCandidates&&cost>=future_candidates.back().cost)return;
            for(auto&candidate:future_candidates)if(candidate.state.order==order||same_family(candidate.path,ops)){'''
assert s.count(old)==1
s=s.replace(old,new)
(p/'main.cpp').write_text(s)
