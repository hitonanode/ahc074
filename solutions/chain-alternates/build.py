from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'eject-tight/main.cpp').read_text()
s=s.replace('static constexpr int kPostCandidates=2;', 'static inline int chain_options=1;\n    static constexpr int kPostCandidates=2;')
s=s.replace('''        PlanOpt best_normal_opt;
        check_vis = true;''','''        PlanOpt best_normal_opt;
        struct NormalCandidate {double cost;PlanOpt option;std::vector<int> order;};
        std::vector<NormalCandidate> normal_candidates;
        check_vis = true;''')
old='''            if (o.fret_mode != 5 && cost < best_normal) best_normal = cost, best_normal_opt = o;'''
new='''            if (o.fret_mode != 5) {
                if(cost<best_normal)best_normal=cost,best_normal_opt=o;
                bool duplicate=false;
                for(auto&c:normal_candidates)if(c.order==order){if(cost<c.cost)c={cost,o,order};duplicate=true;break;}
                if(!duplicate)normal_candidates.push_back({cost,o,order});
            }'''
assert s.count(old)==1;s=s.replace(old,new)
old='''        if (best_normal < 1e17) {
            restore(st0);'''
new='''        std::stable_sort(normal_candidates.begin(),normal_candidates.end(),[](auto&a,auto&b){return a.cost<b.cost;});
        if(chain_options==1&&best_normal<1e17)normal_candidates={{best_normal,best_normal_opt,{}}};
        if(normal_candidates.size()>size_t(chain_options))normal_candidates.resize(chain_options);
        for(const auto&normal:normal_candidates) {
            restore(st0);'''
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace('run_plan(u, best_normal_opt);','run_plan(u, normal.option);')
(p/'main.cpp').write_text(s)
