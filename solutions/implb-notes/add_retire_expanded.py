from pathlib import Path
p=Path('solutions/d30b-req-stack/main.cpp');s=p.read_text()
a='    static constexpr int kPostCandidates = 6;'
b=a+'''
    static bool expanded_pass_on() {
#ifdef LOCAL_BENCH
        static const bool on=[] {
            const char* p=std::getenv("D30B_EXPANDED_PASS");
            return p && std::atoi(p)!=0;
        }();
        return on;
#else
        return false;
#endif
    }'''
assert s.count(a)==1;s=s.replace(a,b)
a='''            // Keep separate ordinary and expanded collectors, in the same insertion order.
            if (neutral_enabled && search_config().post_candidates > 2)'''
b='''            // The expanded collector and its pass are disabled together.
            // LOCAL_BENCH can restore them for a paired comparison.
            if (expanded_pass_on() && neutral_enabled && search_config().post_candidates > 2)'''
assert s.count(a)==1;s=s.replace(a,b)
p.write_text(s)
