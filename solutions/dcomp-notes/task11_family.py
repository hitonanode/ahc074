from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
def rep(s,a,b):assert s.count(a)==1,(a[:100],s.count(a));return s.replace(a,b)
def write(name,s,desc):
 d=R/'solutions'/name;assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n'+desc+'\n\n設計は9候補のまま。予算は両コンパイラ共通の固定回数。既存ログ・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計による切替は使わない。\n')
for mode in ['delete','merge']:
 s=B
 a='''        auto record_future = [&](double cost) {
            // Keep separate ordinary and expanded collectors, in the same insertion order.'''
 act='''            auto screened=ops;OP_TAG(auto screened_tags=op_tags;)
'''
 if mode=='delete':act+='''            canonicalize();
            screened=post_optimize(st0,std::move(screened),u OP_TAG(,screened_tags),false,true);
'''
 else:act+='''            merge_double_moves(st0,screened OP_TAG(,screened_tags));
'''
 s=rep(s,a,'''        auto record_future = [&](double cost) {
            // Repair before different insertion depths are collapsed into one moved-paper family.
            const auto raw_state=save();const auto raw_ops=ops;OP_TAG(const auto raw_tags=op_tags;)
'''+act+'''            ops=std::move(screened);OP_TAG(op_tags=std::move(screened_tags);)
            cost=plan_cost(ops.size());
            // Keep separate ordinary and expanded collectors, in the same insertion order.''')
 s=rep(s,'''            collect_future(future_candidates, kPostCandidates, cost);
        };''','''            collect_future(future_candidates, kPostCandidates, cost);
            restore(raw_state);ops=raw_ops;OP_TAG(op_tags=raw_tags;)
        };''')
 write('dcomp-t11-family-'+mode,s,'raw計画をsame_familyでまとめる前に、'+('単純削除を既存post_optimizeのdelete_onlyで行い、修復後の移動紙列・終状態・費用で候補を集める。' if mode=='delete' else '同じ紙の二重移動を、同じ終状態へ達する合法な一回移動にまとめる。')+'計画生成側へは元の状態・操作列を返し、生成順を保つ。')
# Compare neutral rewrites from a second completed seed, sharing the six proposal slots.
for gap in [.3,.75]:
 s=B
 s=rep(s,'        std::vector<FutureCandidate> future_candidates, expanded_candidates, edited_candidates;','        std::vector<FutureCandidate> future_candidates, expanded_candidates, edited_candidates, neutral_seeds;')
 s=rep(s,'''        const auto ordinary_eject_start = neutral_enabled && search_config().alternate ? order : std::array<uint8_t, K>{};''','''        const auto ordinary_eject_start = neutral_enabled && search_config().alternate ? order : std::array<uint8_t, K>{};''')
 s=rep(s,'''        if (cache_plans && chosen_cache >= 0) {
            plan_cache[chosen_cache].edited''','''        neutral_seeds.push_back({plan_cost(chosen_path.size()),save(),chosen_path OP_TAG(,best_tags)});
        if (cache_plans && chosen_cache >= 0) {
            plan_cache[chosen_cache].edited''')
 s=rep(s,'''                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), 2);
                    ns_plan_calls++;''','''                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), 2);
                    neutral_seeds.push_back({plan_cost(path.size()),save(),path OP_TAG(,tags)});
                    ns_plan_calls++;''')
 s=rep(s,'''                const auto parent_path = chosen_path;
                const double parent_value''','''                const auto parent_path = chosen_path;
                const auto parent_order=order;
                const double parent_value''')
 x='''                auto proposals = std::move(neutral_candidates);
                neutral_candidates.clear();'''
 s=rep(s,x,'''                if(round==1) {
                    std::stable_sort(neutral_seeds.begin(),neutral_seeds.end(),by_cost);
                    for(const auto& second:neutral_seeds) {
                        if(second.state.order==parent_order || second.cost>parent_value+'''+str(gap)+''')continue;
                        restore(second.state);auto second_path=second.path;OP_TAG(auto second_tags=second.tags;)
                        neutral_collect=true;
                        second_path=post_optimize(st0,std::move(second_path),u OP_TAG(,second_tags),true);
                        neutral_collect=false;
                        const double second_value=plan_cost(second_path.size());
                        note(second_path OP_TAG(,second_tags),second_value);
                        if(second_value<incumbent_value-1e-9) {
                            incumbent_value=second_value;incumbent=save();chosen_path=std::move(second_path);
                            OP_TAG(best_tags=std::move(second_tags);)
                        }
                        restore(incumbent);break;
                    }
                }
'''+x)
 write('dcomp-t11-neutral-seed'+str(gap).replace('.',''),s,f'第一中立探索の最初の2→2生成を、完成済みALT計画のうち元の親と異なる最良計画からも行う（元の親費用からgap {gap}以内）。生成した候補は元の6枠を共用し、重複signatureをまとめてから本修復する。追加する親は最大1個。')
