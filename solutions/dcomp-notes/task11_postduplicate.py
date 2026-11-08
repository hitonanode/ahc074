from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
def rep(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:80])
 s=s.replace(a,b)
rep('    Moves post_optimize(const State& initial,', '''    struct PostSeen {
        State state; Moves path;
        OP_TAG(std::vector<uint8_t> tags;)
        bool eject,only,collect;
    };
    std::vector<PostSeen> post_seen;
    long long post_duplicate_calls=0,post_profile_calls=0;
    double post_duplicate_sec=0,post_profile_sec=0;
    Moves post_optimize(const State& initial,''')
rep('''        if (input_ops.empty()) return input_ops;
        const auto& cfg = search_config();''','''        if (input_ops.empty()) return input_ops;
        bool duplicate=false;
        for(const auto& old:post_seen) {
            if(old.eject!=eject || old.only!=delete_only || old.collect!=neutral_collect || old.path!=input_ops)continue;
            if(old.state.order!=order || old.state.top_d!=top_d || !same_fillers(old.state.fillers,fillers))continue;
            OP_TAG(if(old.tags!=tags)continue;)
            duplicate=true;break;
        }
        if(!duplicate)post_seen.push_back({save(),input_ops OP_TAG(,tags),eject,delete_only,neutral_collect});
        ++post_profile_calls;post_duplicate_calls+=duplicate;
        const double profile_tick=elapsed_sec();
        const auto& cfg = search_config();''')
rep('''        OP_TAG(tags = std::move(best_tags);)
        return best_ops;''','''        OP_TAG(tags = std::move(best_tags);)
        const double profile_time=elapsed_sec()-profile_tick;
        post_profile_sec+=profile_time;if(duplicate)post_duplicate_sec+=profile_time;
        return best_ops;''')
rep('''        post_context.ready = false;  // all post-processing in this call replays the same st0''','''        post_seen.clear();
        post_context.ready = false;  // all post-processing in this call replays the same st0''')
rep('    cf_report();','''    std::cerr<<"post_duplicate_calls = "<<solver.post_duplicate_calls<<"\\npost_profile_calls = "<<solver.post_profile_calls
        <<"\\npost_duplicate_sec = "<<solver.post_duplicate_sec<<"\\npost_profile_sec = "<<solver.post_profile_sec<<'\\n';
    cf_report();''')
d=R/'solutions/dcomp-t11-postdup-prof';assert not d.exists();d.mkdir()
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\n要求内で同じstate、操作列、ラベル、post_optimizeモードを再評価する回数と時間を測る。計算は省略せず、出力は変えない。時計は既存のscaled elapsed_secを使い、探索には使わない。ログ・trace・profiler・実験スイッチ・段・DesignStoreを保持する。\n')
