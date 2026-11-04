from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'eject-single-window/main.cpp').read_text()
s=s.replace('    static constexpr bool byte_links=true;','    static inline bool state_cache_enabled=true;\n    static constexpr bool byte_links=true;')
needle='        auto evaluate = [&](const std::vector<Edit>& trial) {\n            if(post_link_filter){\n                auto next=initial_next,prev=initial_prev;'
assert s.count(needle)==1
s=s.replace(needle,'''        struct ScoreCacheEntry {
            u64 hash=0; bool valid=false;
            std::array<Link,K+1> links;
            double charge=0,next_cost=0;
        };
        std::unique_ptr<ScoreCacheEntry[]> score_cache;
        if(state_cache_enabled)score_cache.reset(new ScoreCacheEntry[64]);
        auto evaluate = [&](const std::vector<Edit>& trial) {
            std::array<Link,K+1> final_links;
            u64 trial_hash=0;unsigned cache_slot=0;int trial_count=0;
            if(post_link_filter){
                final_links=initial_next;auto&next=final_links;auto prev=initial_prev;''')
a=s.index('        auto evaluate = [&](const std::vector<Edit>& trial) {');b=s.index('        auto delete_singles =',a)
t=s[a:b]
t=t.replace('                    if(prev[k]==a)continue;\n                    next[prev[k]]=next[k];','                    if(prev[k]==a)continue;\n                    trial_count++;\n                    next[prev[k]]=next[k];',1)
t=t.replace('                if(view!=A[u])return false;\n            }','''                if(view!=A[u])return false;
                if(state_cache_enabled) {
                    const auto* bytes=reinterpret_cast<const unsigned char*>(final_links.data());
                    constexpr size_t size=sizeof(Link)*(K+1);
                    trial_hash=0x517cc1b727220a95ULL;
                    for(size_t offset=0;offset<size;offset+=8) {
                        u64 word=0;std::memcpy(&word,bytes+offset,std::min(size_t(8),size-offset));
                        trial_hash=(trial_hash^word)*0x9e3779b97f4a7c15ULL;
                    }
                    trial_hash^=trial_hash>>31;cache_slot=unsigned(trial_hash)&63;
                    const auto& cached=score_cache[cache_slot];
                    if(cached.valid&&cached.hash==trial_hash&&cached.links==final_links&&
                       trial_count+cached.charge+cached.next_cost+1e-8>=best_score)return false;
                }
            }''',1)
t=t.replace('            const double value = score(path.size());','''            const double charge=filler_charge(),next_cost=kEndWeight*adaptive_next_cost();
            const double value=path.size()+charge+next_cost;
            if(state_cache_enabled&&post_link_filter) {
                auto& cached=score_cache[cache_slot];cached.valid=true;cached.hash=trial_hash;
                cached.links=final_links;cached.charge=charge;cached.next_cost=next_cost;
                assert(int(path.size())==trial_count);
            }''')
s=s[:a]+t+s[b:]
(p/'main.cpp').write_text(s)
(p/'saved.hpp').write_text((p.parent/'eject-small-error/saved.hpp').read_text())
