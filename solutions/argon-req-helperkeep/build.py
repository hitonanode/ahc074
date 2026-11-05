from pathlib import Path
p=Path(__file__).parent
s=Path('solutions/argon-des-perf-latew105/main.cpp').read_text()
def sub(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:90]);s=s.replace(a,b,1)
sub('''    long long interleave_trials = 0, interleave_selected = 0;''','''    long long interleave_trials = 0, interleave_selected = 0;
    inline static long long helper_keep_calls = 0, helper_keep_ready = 0, helper_keep_papers = 0;
    inline static long long helper_keep_trials = 0, helper_keep_valid = 0, helper_keep_better = 0;
    inline static double helper_keep_gain = 0;''')
sub('''    void finish_handles(int u, int d, u64 hh) {
        for (auto& pk''','''    void finish_handles(int u, int d, u64 hh) {
        for (const auto& f : fillers) hh &= ~shown_by(f);
        for (auto& pk''')
sub('''    void try_helpers(int u, const State& st0, Keep keep) {''','''    void try_helpers(int u, const State& st0, Keep keep, bool keep_old = false) {''')
sub('''        const int d = ded[u];
        start_plan(st0);
        if (top_d >= 0) return_paper(top_d, u, 1);
        const auto olds = fillers;
        return_visible_fillers(olds, u, 1);
        if (invalid) return;
        if (order[0] != kCapPaper) return;''','''        const int d = ded[u];
        if (keep_old) {
            ++helper_keep_calls;
            if (st0.fillers.empty()) return;
        }
        start_plan(st0);
        if (top_d >= 0) return_paper(top_d, u, 1);
        const auto olds = fillers;
        u64 kept_coverage = 0;
        if (keep_old) {
            std::vector<Filler> placed;
            refill_or_return(u, olds, kept_coverage, placed);
            for (const auto& f : placed) fillers.push_back(f);
            if (fillers.empty()) return;
            // Helper insertion uses fixed offsets in a contiguous generic layer.
            // A harmless old filler may have stayed inside it: put it below the layer.
            for (const auto& f : placed) {
                OP_LABEL(kOpRelevel);
                move_to_level(f.paper, f.lvl, true, true);
            }
        } else return_visible_fillers(olds, u, 1);
        if (invalid) return;
        if (order[0] != kCapPaper) return;''')
sub('''        const State clean = save();
        const auto clean_ops = ops;''','''        if (keep_old) { ++helper_keep_ready; helper_keep_papers += fillers.size(); }
        const State clean = save();
        const auto clean_ops = ops;''')
sub('''        const auto fixes = fix_costs(u, ~paper[d].opaque & hmask);''','''        const auto fixes = fix_costs(u, ~paper[d].opaque & hmask & ~kept_coverage);''')
sub('''        for (const auto& h : interleave->helpers[u]) {
            const int dep = helper_depth[h.paper];''','''        for (const auto& h : interleave->helpers[u]) {
            if (keep_old && is_filler(h.paper)) continue;
            const int dep = helper_depth[h.paper];''')
sub('''        auto finish = [&]() {
            if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) return;
            keep(plan_cost(ops.size()));
        };''','''        auto finish = [&]() {
            helper_keep_trials += keep_old;
            if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) return;
            helper_keep_valid += keep_old;
            keep(plan_cost(ops.size()));
        };''')
sub('''            interleave_selected += used;
            if (used) source = 2;''','''            try_helpers(u, st0, [&](double cost) {
                record_future(cost);
                if (cost < best) {
                    ++helper_keep_better; helper_keep_gain += best - cost;
                    best = cost; best_ops = ops; OP_TAG(best_tags = op_tags;)
                    best_state = save(); used = true;
                }
            }, true);
            interleave_selected += used;
            if (used) source = 2;''')
sub('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
'''+''.join(f'    std::cerr << "helper_keep_{f} = " << solver.helper_keep_{f} << \'\\n\';\n' for f in ['calls','ready','papers','trials','valid','better','gain']))
(p/'main.cpp').write_text(s)
