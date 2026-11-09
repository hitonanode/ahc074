from pathlib import Path
p=Path('solutions/d30b-req-stack/main.cpp');s=Path('solutions/dcomp-combo-dual30/main.cpp').read_text()
a='    static constexpr int kPostCandidates = 6;'
b=a+'''
    static bool share_collector_enabled() {
#ifdef LOCAL_BENCH
        static const bool on=[] {
            const char* p=std::getenv("D30B_SHARE_COLLECTOR");
            return !p || std::atoi(p)!=0;
        }();
        return on;
#else
        return true;
#endif
    }'''
assert s.count(a)==1;s=s.replace(a,b)
a='        std::vector<FutureCandidate> future_candidates, expanded_candidates, edited_candidates, neutral_seeds;'
b=a+'''
        // Equal-width collectors receive precisely the same stream and tie order.
        const bool share_expanded=share_collector_enabled() && neutral_enabled &&
                                  search_config().post_candidates==kPostCandidates;'''
assert s.count(a)==1;s=s.replace(a,b)
a='''            // Keep separate ordinary and expanded collectors, in the same insertion order.
            if (neutral_enabled && search_config().post_candidates > 2)'''
b='''            // Different configured widths still require separate collectors.
            if (!share_expanded && neutral_enabled && search_config().post_candidates > 2)'''
assert s.count(a)==1;s=s.replace(a,b)
a='''        check_vis = false;
        restore(best_state);
        canonicalize();'''
b='''        // Preserve the raw candidates BEFORE the ordinary post-pass moves their
        // tags/paths. The expanded pass itself, including all tie candidates, stays intact.
        if(share_expanded)expanded_candidates=future_candidates;
'''+a
assert s.count(a)==1;s=s.replace(a,b)
p.write_text(s)
