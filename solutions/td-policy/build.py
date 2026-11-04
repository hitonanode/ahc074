from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'tight-thirty-eight/main.cpp').read_text()
s=s.replace('    void init_adaptive() {  // (once)','    static inline std::array<double,8> value_weights{1,1,1,.6,.6,.25,-.25,0};\n    void init_adaptive() {  // (once)')
old='        add_filler_demand(FILL_DEMAND_WEIGHT);\n        init_stay_value();'
new='        const auto direct_weights=adaptive_weights;\n        add_filler_demand(FILL_DEMAND_WEIGHT);\n        if(value_weights[0]!=1||value_weights[1]!=1)for(int k=0;k<K;k++)adaptive_weights[k]=value_weights[0]*direct_weights[k]+value_weights[1]*(adaptive_weights[k]-direct_weights[k]);\n        if(value_weights[2]!=1)for(auto&v:adaptive_holes)for(auto&x:v)x*=value_weights[2];\n        stay_strength=value_weights[5];cover_strength=-value_weights[6];\n        init_stay_value();'
assert s.count(old)==1;s=s.replace(old,new)
old='        double charge=.6*fillers.size();\n        if(stay_strength)for(auto f:fillers)if(below_generic(f.paper))charge+=stay_strength*(.4-stay_table[f.paper][f.lvl].probability);'
new='        const double n=fillers.size();\n        double charge=value_weights[4]*n+value_weights[7]*n*(n-1)/2;\n        if(stay_strength||value_weights[3]!=value_weights[4])for(auto f:fillers)if(below_generic(f.paper))charge+=value_weights[3]-value_weights[4]+stay_strength*(.4-stay_table[f.paper][f.lvl].probability);'
assert s.count(old)==1;s=s.replace(old,new)
(p/'main.cpp').write_text(s)
