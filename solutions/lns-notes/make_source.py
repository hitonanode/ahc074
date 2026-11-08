from pathlib import Path
root=Path(__file__).resolve().parents[2]
here=Path(__file__).resolve().parent
s=(root/'solutions/deval-helper-wide/main.cpp').read_text()
def replace(a,b):
    global s
    assert s.count(a)==1,(a[:80],s.count(a))
    s=s.replace(a,b)
replace('struct WindowStats {',(here/'matching.inc').read_text()+(here/'map_extra.inc').read_text()+'\nstruct WindowStats {')
replace('const int as_elite = std::getenv("AS_ELITE") ? env_int("AS_ELITE") : 1;', 'const int as_elite = lns_map.active ? 0 : std::getenv("AS_ELITE") ? env_int("AS_ELITE") : 1;')
replace('    int climb_steps = 0;\n};\nWindowStats assign_windows', '    int climb_steps = 0;\n    double gobj_initial=0;\n    int lost_max=0,lost_accepted=0,lost_tracked=0;\n    std::vector<std::pair<int,int>> matched_pairs;\n};\nWindowStats assign_windows')
replace('    const int np = pairs.n, np8 = pairs.n8;', '    const int np = pairs.n, np8 = pairs.n8;\n    std::vector<int> lns_old_ids;int lns_last_lost=0;\n    if(lns_map.active){\n        std::array<int,256> ref;ref.fill(-1);\n        for(auto [a,b]:lns_map.old_pairs){if(a>b)std::swap(a,b);ref[a]=b;}\n        for(int p=0;p<np;++p)if(ref[pairs.u[p]]==pairs.v[p])lns_old_ids.push_back(p);\n        stats.lost_tracked=lns_old_ids.size();\n    }')
replace('        return double(total) / (need * 3600) + (need - matched) * 10.0;', '        lns_last_lost=0;for(int p:lns_old_ids)lns_last_lost+=!rel[p];\n        stats.lost_max=std::max(stats.lost_max,lns_last_lost);\n        return double(total) / (need * 3600) + (need - matched) * 10.0;')
replace('    double cur = matching_cost(pairs.rel.data(), hm), best = cur;', '    double cur = matching_cost(pairs.rel.data(), hm), best = cur;\n    stats.gobj_initial=cur;')
replace('        apply_move(mv);\n        cur = candidate;', '        apply_move(mv);\n        stats.lost_accepted=std::max(stats.lost_accepted,lns_last_lost);\n        cur = candidate;')
replace('XorShift rng{0x71eb2566be932e31ULL};','XorShift rng{0x71eb2566be932e31ULL ^ lns_map.salt};')
replace('    auto propose = [&](Move& mv) {\n','    auto propose = [&](Move& mv) {\n'+(here/'map_propose.inc').read_text())
replace('            if (mv.transfer >= 0) {\n                counts[mv.ea]--;','            if(lns_map.active && mv.a!=mv.b)std::swap(which[mv.a],which[mv.b]);\n            if (mv.transfer >= 0) {\n                counts[mv.ea]--;')
replace('auto temp = [&] { return 0.05 * std::pow(0.00125 / 0.05, progress); };','auto temp = [&] { const double t=lns_map.active?lns_map.temperature:.05; return t * std::pow(0.00125 / t, progress); };')
replace('// ==== Helper tables: dedicated papers inside the generic layer (Interleave) ====',(here/'repair.inc').read_text()+'\n// ==== Helper tables: dedicated papers inside the generic layer (Interleave) ====')
replace('//   Helper tables: dedicated papers inside the generic layer (Interleave)','//   Large neighborhood: matching and column repair\n//   Helper tables: dedicated papers inside the generic layer (Interleave)')
replace('#include <cstdio>', '#include <cstdio>\n#include <filesystem>')
replace('// ==== Design iteration counts ====',(here/'transfer.inc').read_text()+(here/'dump.inc').read_text()+'\n// ==== Design iteration counts ====')
replace('    std::unique_ptr<Design> best_assignment;', '    std::unique_ptr<Design> best_assignment;\n    DesignState last_candidate;')
replace('        if(v<best){best=v;', '        last_candidate=candidate;\n#ifdef LOCAL_BENCH\n        lns_dump_design(candidate,originalA,id,v);\n#endif\n        if(v<best){best=v;')
replace('    constexpr int kCutoff = 26;', '    const int kCutoff = lns_map.active ? int(env_real("LNS_CUTOFF",26)) : 26;')
replace('    std::vector<int> selected, candidate_selected;', '    std::vector<int> selected, candidate_selected;\n    const bool exact_repair=lns_map.active&&env_int("LNS_MAP_EXACT");\n    const double missing_penalty=lns_map.active?env_real("LNS_MISSING",10.):10.;\n    std::vector<int> lns_pair_id(exact_repair?65536:0,-1),lns_pair_key(exact_repair?np:0);\n    if(exact_repair)for(int p=0;p<np;++p)lns_pair_id[256*pairs.u[p]+pairs.v[p]]=p;')
replace('            assert(key < (1 << 17));', '            assert(key < (1 << 17));\n            if(exact_repair)lns_pair_key[p]=key;')
replace('        candidate_selected.resize(matched);', '        candidate_selected.resize(matched);\n        if(exact_repair && matched<need){\n            LnsMatching repair;\n            for(int p:candidate_selected){int a=pairs.u[p],b=pairs.v[p];repair.mate[a]=b;repair.mate[b]=a;}\n            for(int i=0;i<size;++i){const u64 x=sorted[i];int a=int(x>>8)&255,b=int(x)&255;repair.g[a].push_back(b);repair.g[b].push_back(a);}\n            for(int a=0;a<256&&matched<need;++a)if(repair.mate[a]<0)matched+=repair.augment(a);\n            candidate_selected.clear();total=0;\n            for(int a=0;a<256;++a)if(repair.mate[a]>a){int p=lns_pair_id[256*a+repair.mate[a]];assert(p>=0);candidate_selected.push_back(p);total+=lns_pair_key[p];}\n            assert(int(candidate_selected.size())==matched);\n        }')
replace('(need - matched) * 10.0;', '(need - matched) * missing_penalty;')
replace('    auto matching_cost = [&](const int* rel, u64 handle_mask)', '    std::vector<int> preferred_ids;\n    const double preferred_weight=env_real("LNS_PREFERRED_WEIGHT",.15);\n    for(auto [a,b]:lns_map.preferred_pairs)for(int p=0;p<np;++p)if(pairs.u[p]==a&&pairs.v[p]==b)preferred_ids.push_back(p);\n    auto matching_cost = [&](const int* rel, u64 handle_mask)')
replace('        return double(total) / (need * 3600) + (need - matched) * missing_penalty;', '        double preferred_bonus=0;for(int p:preferred_ids)preferred_bonus+=rel[p]!=0;\n        return double(total) / (need * 3600) + (need - matched) * missing_penalty - preferred_weight*preferred_bonus;')
replace('    stats.gobj_initial=cur;', '    stats.gobj_initial=cur;\n    auto best_selected=candidate_selected;')
replace('            best_order = order;\n        }\n    };', '            best_order = order;\n            best_selected=selected;\n        }\n    };')
replace('    stats.gobj_before = cur;', '    stats.gobj_before = cur;\n    best_selected=selected;')
replace('    stats.gobj_after = cur;', '    stats.gobj_after = cur;\n    if(lns_map.active)for(int p:best_selected)stats.matched_pairs.emplace_back(pairs.u[p],pairs.v[p]);')
replace('    const double missing_penalty=', '    const double soft_penalty=lns_map.active?env_real("LNS_SOFT_PENALTY",0.):0.;\n    const double missing_penalty=')
replace('        const int size = nvalid;', '        const int size = soft_penalty>0?np:nvalid;')
replace('            const int p = valid[i];\n            const int key = 1800 *', '            const int p = soft_penalty>0?i:valid[i];\n            int key = 1800 *')
replace('            // hd <= 26, full144 <= 144*26, rel <= 4380: the key fits 17 bits.', '''            if(soft_penalty>0 && !rel[p]){
                const uint32_t dir=(rel==nrel.data()?ndir[p]:pairs.dir[p]);
                const int violations=std::max(1,__builtin_popcount(dir&(dir>>16)&0x7fff));
                key=std::min(131071,1800*__builtin_popcountll(pairs.diff[p]&handle_mask)+5*4380+full144[p]+int(3600*soft_penalty*violations));
            }
            // hd <= 26, full144 <= 144*26, rel <= 4380: the key fits 17 bits.''')
replace('    auto best_selected=candidate_selected;', '    auto best_selected=candidate_selected;\n    bool best_feasible=int(candidate_selected.size())==need;\n    for(int p:candidate_selected)best_feasible&=pairs.rel[p]!=0;')
replace('        if (cur < best - 1e-9) {\n            best = cur;', '''        bool feasible=true;
        if(soft_penalty>0){feasible=int(selected.size())==need;for(int p:selected)feasible&=pairs.rel[p]!=0;}
        if (soft_penalty>0 ? ((feasible&&!best_feasible)||((feasible||!best_feasible)&&cur<best-1e-9)) : cur < best - 1e-9) {
            best_feasible=feasible;
            best = cur;''')
replace('    bool best_feasible=int(candidate_selected.size())==need;', '''    const int minimum_changes=lns_map.active?env_int("LNS_MIN_WINDOWS"):0;
    auto window_distance=[&](){
        std::array<int,64> code{};int count=0;
        for(int e=0;e<ne;++e)for(u64 q=mask[e];q;q&=q-1){const int w=__builtin_ctzll(q);code[permutation[w]]=1+2*e+int(pol>>w&1);}
        for(int w=0;w<63;++w)count+=code[w]!=lns_map.origin_codes[w];return count;
    };
    bool best_feasible=int(candidate_selected.size())==need && (!minimum_changes||window_distance()>=minimum_changes);''')
replace('        if (soft_penalty>0 ? ((feasible&&!best_feasible)', '        if(minimum_changes)feasible&=window_distance()>=minimum_changes;\n        if (soft_penalty>0||minimum_changes ? ((feasible&&!best_feasible)')
replace('    deval_salt=std::max(0,env_int("DEVAL_SALT"));', '#ifdef LOCAL_BENCH\n    if(env_int("LNS_VERIFY_MATCH"))lns_verify_matching();\n#endif\n    deval_salt=std::max(0,env_int("DEVAL_SALT"));')
replace('//   Window assignment: candidate screens and tables', '//   Window assignment: regional matching\n//   Window assignment: candidate screens and tables')
replace('//   Design iteration counts', '//   Large neighborhood: transfer finished perforations\n//   Design iteration counts')
# Extra pipeline installed separately below.
if (here/'pipeline.inc').exists():
    replace('    if(!finished)state.emergency=true;',(here/'pipeline.inc').read_text().replace('        if(lns_mode==1 || lns_mode==6){',(here/'full_control.inc').read_text()+'        if(lns_mode==1 || lns_mode==6){')+'\n    if(!finished)state.emergency=true;')
replace('        if(!finished)first=v;','        std::cerr<<"@lns_candidate "<<id<<\' \'<<v<<\' \'<<des->cur/P<<\'\\n\';\n        if(!finished)first=v;')
(root/'solutions/lns-star/main.cpp').write_text(s)
