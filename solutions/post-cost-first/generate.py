from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'eject-single-window/main.cpp').read_text().replace('    static constexpr bool byte_links=true;','    static inline bool early_state_cost=true;\n    static constexpr bool byte_links=true;')
a=s.index('        auto evaluate = [&](const std::vector<Edit>& trial) {');b=s.index('        auto delete_singles =',a)
t=s[a:b].replace('            if(post_link_filter){','            State priced_state;double priced_value=0;int trial_count=0;\n            if(post_link_filter){',1)
t=t.replace('                    if(prev[k]==a)continue;\n                    next[prev[k]]=next[k];','                    if(prev[k]==a)continue;\n                    trial_count++;\n                    next[prev[k]]=next[k];',1)
t=t.replace('                if(view!=A[u])return false;','''                if(view!=A[u])return false;
                if(early_state_cost) {
                    restore(seed);order.clear();for(int k=next[root];k!=root;k=next[k])order.push_back(k);
                    canonicalize();if(!fillers_reachable())return false;
                    priced_value=score(trial_count);if(priced_value+1e-8>=best_score)return false;
                    priced_state=save();
                }''',1)
old='''            restore(seed);
            order = std::move(ord);
            canonicalize();
            if (!fillers_reachable()) return false;
            const double value = score(path.size());'''
assert t.count(old)==1
t=t.replace(old,'''            double value=0;
            if(early_state_cost&&post_link_filter) {
                assert(int(path.size())==trial_count);assert(ord==priced_state.order);
                restore(priced_state);value=priced_value;
            } else {
                restore(seed);order=std::move(ord);canonicalize();
                if(!fillers_reachable())return false;value=score(path.size());
            }''')
s=s[:a]+t+s[b:];(p/'main.cpp').write_text(s)
(p/'saved.hpp').write_text((p.parent/'post-state-cache/saved.hpp').read_text())
(p/'probe.cpp').write_text((p.parent/'post-state-cache/probe.cpp').read_text().replace('state_cache_enabled','early_state_cost'))
(p/'run.py').write_text((p.parent/'post-state-cache/run.py').read_text().replace('range(1920,1952)','range(1952,1984)').replace('/tmp/ahc074-post-state-cache','/tmp/ahc074-post-cost-first'))
