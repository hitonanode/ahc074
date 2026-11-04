from pathlib import Path
p=Path(__file__).resolve().parent;s=(p.parent/'reset-head/main.cpp').read_text();code=(p/'value.inc').read_text()
needle='    std::vector<std::pair<int, int>> process(int u) {'
assert needle in s;s=s.replace(needle,code+'\n'+needle)
a=s.index(needle);b=s.index('\n};',a);proc=s[a:b]
needle='''        State best_state;
        PlanOpt best_normal_opt;'''
new='''        State best_state;
        struct FutureCandidate {double cost;State state;std::vector<std::pair<int,int>> path;};
        std::vector<FutureCandidate> future_candidates;
        auto record_future=[&](double cost){
            if(!future_enabled)return;
            if(future_candidates.size()==2&&cost>=future_candidates.back().cost)return;
            for(auto&candidate:future_candidates)if(candidate.state.order==order){
                if(cost<candidate.cost){candidate={cost,save(),ops};std::sort(future_candidates.begin(),future_candidates.end(),[](auto&a,auto&b){return a.cost<b.cost;});}
                return;
            }
            future_candidates.push_back({cost,save(),ops});
            std::sort(future_candidates.begin(),future_candidates.end(),[](auto&a,auto&b){return a.cost<b.cost;});
            if(future_candidates.size()>2)future_candidates.pop_back();
        };
        PlanOpt best_normal_opt;'''
assert needle in proc;proc=proc.replace(needle,new)
proc=proc.replace('            if (cost < best) best = cost, best_ops = ops, best_state = save();','            record_future(cost);\n            if (cost < best) best = cost, best_ops = ops, best_state = save();')
proc=proc.replace('                if (cost < best) best = cost, best_ops = ops, best_state = save(), source = 1;', '                record_future(cost);\n                if (cost < best) best = cost, best_ops = ops, best_state = save(), source = 1;')
proc=proc.replace('            try_helpers(u, st0, [&](double cost) {', '            try_helpers(u, st0, [&](double cost) {\n                record_future(cost);')
old='''        return post_optimize(st0, std::move(best_ops), u);'''
new='''        auto chosen_path=post_optimize(st0,std::move(best_ops),u);
        if(future_enabled&&future_candidates.size()>1&&future_candidates.back().cost-future_candidates.front().cost<=future_gate){
            auto chosen=save();const auto original_order=best_state.order;
            double value=chosen_path.size()+kFillerCharge*fillers.size()+kEndWeight*adaptive_next_cost()-(future_strength>0?future_strength*future_correction():0.);
            bool changed=false;
            for(auto&candidate:future_candidates){
                if(candidate.state.order==original_order)continue;
                restore(candidate.state);canonicalize();auto path=post_optimize(st0,candidate.path,u);
                double next=path.size()+kFillerCharge*fillers.size()+kEndWeight*adaptive_next_cost()-(future_strength>0?future_strength*future_correction():0.);
                if(next<value-1e-9){value=next;chosen=save();chosen_path=std::move(path);changed=true;}
            }
            restore(chosen);future_changes+=changed;
        }
        return chosen_path;'''
assert old in proc;proc=proc.replace(old,new)
s=s[:a]+proc+s[b:];(p/'main.cpp').write_text(s)
