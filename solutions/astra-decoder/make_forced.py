from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'shared.cpp').read_text()
s=s.replace('''int accepted=0,multi_accepted=0,window_swaps=0;''','''int accepted=0,multi_accepted=0,window_swaps=0;
    int forced_pair=-1,pending_target=-1,forced_trials=0,forced_accepts=0;''')
s=s.replace('''        std::array<bool,256>used{};double sum=0;
        for(auto e:es)''','''        std::array<bool,256>used{};double sum=0;
        if(forced_pair>=0){
            if(result.prices[forced_pair]<0)return result;
            auto&e=pairs[forced_pair];used[e.u]=used[e.v]=true;
            sum=result.prices[forced_pair];result.selected.push_back(forced_pair);
        }
        for(auto e:es)''')
s=s.replace('''                    int old=result.selected[x];auto&p=pairs[old];''','''                    int old=result.selected[x];if(old==forced_pair)continue;auto&p=pairs[old];''')
s=s.replace('''    std::vector<int> choose_windows(int t){
        c.rebuild_truth();''','''    std::vector<int> choose_windows(int t){
        pending_target=-1;c.rebuild_truth();''')
s=s.replace('''            auto&e=pairs[hard[rng.mod(std::min<int>(400,hard.size()))]];''','''            int target_index=hard[rng.mod(std::min<int>(400,hard.size()))];auto&e=pairs[target_index];''')
s=s.replace('''            return ws;
        }
        std::vector<int>ws;''','''            pending_target=target_index;
            int width=env_int("GATE_GROUP");
            while(width>0 && ws.size()<unsigned(width)){int j=movable[rng.mod(movable.size())];if(std::find(ws.begin(),ws.end(),j)==ws.end())ws.push_back(j);}
            return ws;
        }
        std::vector<int>ws;''')
s=s.replace('''            const auto saved=state;auto windows=choose_windows(t);
            int swap_j''','''            const auto saved=state;auto windows=choose_windows(t);
            forced_pair=pending_target;forced_trials+=forced_pair>=0;
            int swap_j''')
s=s.replace('''                    for(int g=0;g<int(gates.size());g++){
                        ++gate_trials;''','''                    for(int g=0;g<int(gates.size());g++){
                        ++gate_trials;
                        if(forced_pair>=0 && !(allowed[forced_pair][g>>6]>>(g&63)&1))continue;''')
s=s.replace('''            if(!beam.empty()&&beam[0].e.value<current.value-1e-9){''','''            // The forced edge guides partial nodes only. Complete candidates
            // are re-priced and re-matched without the forcing constraint.
            int wanted=forced_pair;forced_pair=-1;
            for(auto&node:beam){restore(node.s);node.e=evaluate(gm);}
            std::sort(beam.begin(),beam.end(),[](auto&a,auto&b){return a.e.value<b.e.value;});
            if(!beam.empty()&&beam[0].e.value<current.value-1e-9){
                forced_accepts+=wanted>=0;''')
s=s.replace('''<<"\\ndecoder_window_swaps = "<<window_swaps''','''<<"\\ndecoder_forced_trials = "<<forced_trials<<"\\ndecoder_forced_accepts = "<<forced_accepts<<"\\ndecoder_window_swaps = "<<window_swaps''')
(p/'forced.cpp').write_text(s)
