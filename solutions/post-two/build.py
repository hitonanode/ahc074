from pathlib import Path
p=Path(__file__).resolve().parent;s=(p.parent/'future-interval/main.cpp').read_text()
a=s.index('    static inline double future_strength=0');b=s.index('    std::vector<std::pair<int, int>> process(int u) {',a)
s=s[:a]+'''    static constexpr int kPostCandidates=2;
    long long post_alternate=0,post_candidate_calls=0,post_secondary_saved=0;
'''+s[b:]
s=s.replace('            if(!future_enabled)return;\n','')
s=s.replace('future_candidates.size()==2','future_candidates.size()==kPostCandidates').replace('future_candidates.size()>2','future_candidates.size()>kPostCandidates')
s=s.replace('future_enabled&&future_candidates.size()>1&&future_candidates.back().cost-future_candidates.front().cost<=future_gate','future_candidates.size()>1')
s=s.replace('-(future_strength>0?future_strength*future_correction():0.)','')
s=s.replace('        auto chosen_path=post_optimize(st0,std::move(best_ops),u);','        auto chosen_path=post_optimize(st0,std::move(best_ops),u);post_candidate_calls++;\n        const int original_length=chosen_path.size();')
s=s.replace('restore(candidate.state);canonicalize();auto path=post_optimize(st0,candidate.path,u);','restore(candidate.state);canonicalize();auto path=post_optimize(st0,candidate.path,u);post_candidate_calls++;')
s=s.replace('restore(chosen);future_changes+=changed;','restore(chosen);post_alternate+=changed;')
s=s.replace('        return chosen_path;','        post_secondary_saved+=original_length-int(chosen_path.size());\n        return chosen_path;')
needle='    std::cerr << "end_sec = " << elapsed_sec()'
if needle in s:s=s.replace(needle,'    std::cerr << "post_alternate = " << solver.post_alternate << "\\npost_candidate_calls = " << solver.post_candidate_calls << "\\npost_secondary_saved = " << solver.post_secondary_saved << \'\\n\';\n'+needle)
else:
 needle='    std::cerr << "self_wrong = "'
 assert needle in s
 s=s.replace(needle,'    std::cerr << "post_alternate = " << solver.post_alternate << "\\npost_candidate_calls = " << solver.post_candidate_calls << "\\npost_secondary_saved = " << solver.post_secondary_saved << \'\\n\';\n'+needle)
(p/'main.cpp').write_text(s)
