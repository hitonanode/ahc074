from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'eject-tight/main.cpp').read_text()
s=s.replace('static inline int mid_filter=0;', '''static inline int triple_mode=0;
    long long triple_trials=0,triple_accepts=0,pure_accepts=0;
    static inline int mid_filter=0;''')
old='''            for(int j=int(base_edits.size())-1;j>=1;j--)for(int i=j-1;i>=0;i--){
                int pi=base_edits[i].paper,pj=base_edits[j].paper;'''
new='''            std::vector<std::array<int,3>> deletions;
            for(int j=int(base_edits.size())-1;j>=1;j--)for(int i=j-1;i>=0;i--)deletions.push_back({i,j,-1});
            if(triple_mode>=2)for(int k=int(base_edits.size())-1;k>=2;k--)for(int j=k-1;j>=1;j--)for(int i=j-1;i>=0;i--){
                if(triple_mode==3&&!initial_extra[base_edits[i].paper]&&!initial_extra[base_edits[j].paper]&&!initial_extra[base_edits[k].paper])continue;
                deletions.push_back({i,j,k});
            }
            for(auto[i,j,third]:deletions){
                int pi=base_edits[i].paper,pj=base_edits[j].paper;'''
assert s.count(old)==1;s=s.replace(old,new)
old='auto trial=base_edits;trial.erase(trial.begin()+j);trial.erase(trial.begin()+i);'
new='auto trial=base_edits;if(third>=0)trial.erase(trial.begin()+third);trial.erase(trial.begin()+j);trial.erase(trial.begin()+i);'
assert s.count(old)==1;s=s.replace(old,new)
old='''                if(__builtin_popcountll(shown^A[u])<2)continue;
                for(int k:candidates){'''
new='''                if(triple_mode&&shown==A[u]){if(evaluate(trial)){pure_accepts++;mid_accepts++;}}
                if(__builtin_popcountll(shown^A[u])<2)continue;
                for(int k:candidates){'''
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace('''auto next=trial;next.insert(next.begin()+t,{k,a});mid_trials++;
                            if(evaluate(next)){
                                mid_accepts++;mid_inside+=t<length;''','''auto next=trial;next.insert(next.begin()+t,{k,a});mid_trials++;triple_trials+=third>=0;
                            if(evaluate(next)){
                                mid_accepts++;triple_accepts+=third>=0;mid_inside+=t<length;''')
(p/'main.cpp').write_text(s)
