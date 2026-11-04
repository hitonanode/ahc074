from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'perforated-eight/main.cpp').read_text()
s=s.replace('static inline int post_rewrite_mode=5;', 'static inline bool mid_possible=true;\n    static inline bool mid_fast=true;\n    static inline int mid_eject_mode=2;\n    std::array<double,64> relation_gain{};std::array<long long,64> relation_count{};\n    std::array<double,125> eject_gain{};std::array<long long,125> eject_count{};\n    long long mid_pairs=0,mid_trials=0,mid_accepts=0,mid_inside=0;\n    static inline int post_rewrite_mode=5;')
anchor='        post_saved += int(input_ops.size()) - int(best_ops.size());'
assert s.count(anchor)==1
s=s.replace(anchor,(p/'eject.inc').read_text()+'\n'+anchor)
s=s.replace('static inline bool mid_possible=true;', 'static inline int mid_filter=0;\n    static inline bool mid_once=true;\n    static inline bool mid_possible=true;')
s=s.replace('                                                   int u) {', '                                                   int u,bool only_eject=false) {',1)
a=s.index('        for (int pass = 0; pass < 3; pass++)',s.index('std::vector<std::pair<int, int>> post_optimize'))
b=s.index('        if(mid_eject_mode&&edits.size()>=2){',a)
s=s[:a]+'        if(!only_eject){\n'+s[a:b]+'        }\n'+s[b:]
s=s.replace('if(mid_eject_mode&&edits.size()>=2)', 'if(mid_eject_mode&&(only_eject||!mid_once)&&edits.size()>=2)')
needle='        post_secondary_saved+=original_length-int(chosen_path.size());'
s=s.replace(needle, '        if(mid_eject_mode&&mid_once)chosen_path=post_optimize(st0,std::move(chosen_path),u,true);\n'+needle)
(p/'main.cpp').write_text(s)
