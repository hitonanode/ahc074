"""Fixed-budget compare-after-repair screens and ALT caps on alt1."""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
def rep(s,a,b):
    assert s.count(a)==1,(s.count(a),a[:80]);return s.replace(a,b)
def write(name,s,desc):
    d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
    (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n'+desc+'\n\n0–499の固定設計・4注文列で選別する。両コンパイラで固定予算は共通、時刻による切替なし。既存の環境変数、ログ・trace・profiler・DesignStore・段の目印と目次を維持する。\n')

x='''                        path = post_optimize(st0, std::move(path), u OP_TAG(, tags), false, true);
                        screened.push_back({plan_cost(path.size()), save(), std::move(path) OP_TAG(, std::move(tags))});'''
s=rep(B,x,'''                        path = post_optimize(st0, std::move(path), u OP_TAG(, tags), false, true);
                        // A longer plan may cross the shortlist threshold after one real repair.
                        if(path.size()>chosen_path.size())
                            path=post_optimize(st0,std::move(path),u OP_TAG(,tags),true);
                        screened.push_back({plan_cost(path.size()), save(), std::move(path) OP_TAG(, std::move(tags))});''')
write('dcomp-t11-exp-repair',s,'拡張候補の安い削除screenの後、現候補より長い計画だけ2→1修復を1回行う。修復後の長さと費用でshortlistへ進めるかを決める。')

for width in [8,12]:
    s=B
    s=rep(s,'            double cost;\n            State state;\n            Moves path;',
          '            double cost;\n            State state;\n            Moves path;') if False else s
    # Append a source index without changing existing aggregate initializers.
    x='''            OP_TAG(std::vector<uint8_t> tags;)  // the labels of path
        };
        FutureCandidate weighted_raw{};'''
    s=rep(s,x,'''            OP_TAG(std::vector<uint8_t> tags;)  // the labels of path
            int raw_index=-1;
        };
        std::vector<FutureCandidate> before_screen;
        FutureCandidate weighted_raw{};''')
    s=rep(s,'            collect_future(future_candidates, kPostCandidates, cost);',
          f'            collect_future(future_candidates, {width}, cost);')
    x='''        check_vis = false;
        restore(best_state);
        canonicalize();
        if (cache_plans) {'''
    s=rep(s,x,'''        check_vis = false;
        before_screen=future_candidates;
        for(int i=0;i<int(future_candidates.size());++i) {
            auto& c=future_candidates[i];c.raw_index=i;
            restore(c.state);canonicalize();
            c.path=post_optimize(st0,std::move(c.path),u OP_TAG(,c.tags),false,true);
            c.cost=plan_cost(c.path.size());c.state=save();
        }
        std::stable_sort(future_candidates.begin(),future_candidates.end(),by_cost);
        if(future_candidates.size()>kPostCandidates)future_candidates.resize(kPostCandidates);
        if(!future_candidates.empty()) {
            const auto& c=future_candidates.front();best=c.cost;best_state=c.state;best_ops=c.path;
            OP_TAG(best_tags=c.tags;)
        }
        restore(best_state);
        canonicalize();
        if (cache_plans) {''')
    s=rep(s,'            plan_cache.push_back({{best, best_state, best_ops OP_TAG(, best_tags)}, {}});',
          '            plan_cache.push_back({before_screen[future_candidates.front().raw_index], {}});')
    s=rep(s,'                if (cache_plans) plan_cache.push_back({candidate, {}});',
          '                if (cache_plans) plan_cache.push_back({before_screen[candidate.raw_index], {}});')
    write('dcomp-t11-prescreen'+str(width),s,f'通常の計画候補を一旦{width}個まで保持し、削除だけのpost_optimizeで修復してから費用順に4個へ絞る。元の計画とのcache対応を維持し、選ばれた4候補は元と同じ本編集・ALTへ進む。')

s=B
s=rep(s,'const char* s = search_env("NEUTRAL_WIDTH");','const char* s = search_env("NEUTRAL_POOL");')
s=rep(s,'return s ? std::max(1, std::atoi(s)) : 2;','return s ? std::max(1, std::atoi(s)) : 24;')
s=rep(s,'if(std::strcmp(name,"NEUTRAL_SLACK")==0)return ".35";',
      'if(std::strcmp(name,"NEUTRAL_SLACK")==0)return "1.5";')
x='''                [[maybe_unused]] int rank = 0;
                if (neutral_depth)'''
s=rep(s,x,'''                // Apply cheap real deletions before spending the six full edit slots.
                for(auto& c:proposals) {
                    restore(c.state);
                    c.path=post_optimize(st0,std::move(c.path),u OP_TAG(,c.tags),false,true);
                    c.state=save();c.value=plan_cost(c.path.size());
                }
                std::stable_sort(proposals.begin(),proposals.end(),[](const auto& a,const auto& b){
                    if(a.path.size()!=b.path.size())return a.path.size()<b.path.size();
                    return a.value<b.value;
                });
                static const int kept=std::max(1,SearchConfig::get("NEUTRAL_WIDTH",6));
                if(proposals.size()>size_t(kept))proposals.resize(kept);
                restore(incumbent);
                [[maybe_unused]] int rank = 0;
                if (neutral_depth)''')
write('dcomp-t11-neutral-screen',s,'neutral候補を費用slack1.5・最大24個まで保持し、削除だけの実修復を行ってから6個を本編集する。修復後の手数、費用で並べる。')

for cap in [1,2]:
    s=B
    s=rep(s,'                for (auto& c : edited_candidates) {',
          f'''                std::stable_sort(edited_candidates.begin(),edited_candidates.end(),by_cost);
                int alt_tried=0;
                for (auto& c : edited_candidates) {{''')
    s=rep(s,'                    if (c.state.order == ordinary_eject_start || c.cost > baseline_value + cfg.alternate_gap) continue;',
          f'''                    if (c.state.order == ordinary_eject_start || c.cost > baseline_value + cfg.alternate_gap) continue;
                    if(alt_tried=={cap})break;
                    ++alt_tried;''')
    write('dcomp-t11-altcap'+str(cap),s,f'各注文のALT候補を編集後費用で安定sortし、条件を満たす先頭{cap}個だけ修復する。時計を使わない固定件数上限でtailの費用と失う得点を測る。')
