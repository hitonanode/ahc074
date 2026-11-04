from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'tight-thirty-eight/main.cpp').read_text()
s=s.replace('    double filler_charge()const{','    double filler_charge()const{\n        if(terminal_cost)return 0;')
s=s.replace('    double adaptive_next_cost() const {','    double adaptive_next_cost() const {\n        if(terminal_cost)return 0;')
needle='''            double value = rank / P + adaptive_holes[c][0] * fc[0] + adaptive_holes[c][1] * fc[1];'''
assert s.count(needle)==1;s=s.replace(needle,needle+'\n            if(terminal_cost)value=0;')
s=s.replace('if (mode == 1 && i == 0 && n) value += kTopPenalty;', 'if (!terminal_cost && mode == 1 && i == 0 && n) value += kTopPenalty;')
needle='''    std::vector<std::pair<int, int>> process(int u) {'''
replacement='''    bool last_request=false,terminal_cost=false;
    long long terminal_saved=0;
    std::vector<std::pair<int,int>> process(int u){
        if(!last_request)return process_core(u);
        const auto initial=save();auto original=process_core(u);const auto result=save();
        // There is no next order after the final display. Explore the same
        // planner with zero residual cost and keep only a strictly shorter plan.
        restore(initial);terminal_cost=true;auto alternate=process_core(u);terminal_cost=false;
        if(alternate.size()<original.size()&&display()==A[u]){terminal_saved+=original.size()-alternate.size();return alternate;}
        restore(result);return original;
    }
    std::vector<std::pair<int, int>> process_core(int u) {'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
(p/'main.cpp').write_text(s)
