from pathlib import Path
p=Path(__file__).parent
s=Path('solutions/argon-des-perf-latew105/main.cpp').read_text()
def sub(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:90]);s=s.replace(a,b,1)
sub('''    static const SearchConfig& search_config() {
        static const SearchConfig config;
        return config;
    }''','''    inline static const SearchConfig* budget_override = nullptr;
    static const SearchConfig& search_config() {
        static const SearchConfig config;
        return budget_override ? *budget_override : config;
    }
    struct BudgetFeatures { int raw, ordinary, holes, generic, depth, fillers, alternatives; double gap, first_gain; };
    inline static BudgetFeatures budget_features{};''')
sub('''        const int top0 = top_d, d = ded[u];''','''        const int top0 = top_d, d = ded[u];
        budget_features = {};
        budget_features.fillers = fillers.size();
        if (d >= 0) {
            budget_features.holes = __builtin_popcountll(hmask & ~paper[d].opaque);
            budget_features.generic = __builtin_popcountll(gmask & ~paper[d].opaque);
            budget_features.depth = in_column(d, col_of[d]) ? depth_in_column(d) : 0;
        }''')
sub('''        check_vis = false;
        restore(best_state);''','''        budget_features.raw = best_ops.size();
        budget_features.alternatives = future_candidates.size();
        budget_features.gap = future_candidates.size() > 1 ? future_candidates[1].cost - future_candidates[0].cost : 0;
        check_vis = false;
        restore(best_state);''')
sub('''            const auto baseline_path = chosen_path;''','''            const auto baseline_path = chosen_path;
            budget_features.ordinary = chosen_path.size();''')
sub('''                if (incumbent_value >= parent_value - 1e-9 || parent_value - incumbent_value < cfg.repeat_min) break;''','''                if (round == 1) budget_features.first_gain = parent_value - incumbent_value;
                if (incumbent_value >= parent_value - 1e-9 || parent_value - incumbent_value < cfg.repeat_min) break;''')
sub('''    double req_sec = 0;  // time spent planning the requests (without waiting for them)
    for (int r = 0; r < R; r++) {''','''    double req_sec = 0;  // time spent planning the requests (without waiting for them)
    Solver::SearchConfig budget_light = Solver::search_config();
    budget_light.delete_only = true;
    Solver::SearchConfig budget_short = budget_light;
    budget_short.rounds = 1;
    Solver::SearchConfig budget_heavy = Solver::search_config();
    budget_heavy.rounds = 4;
    budget_heavy.post_candidates = 8;
    budget_heavy.plan_shortlist = 0;
    budget_heavy.plan_limit = 2;
    budget_heavy.triples = true;
    budget_heavy.interior = 4;
    budget_heavy.refine_best = 1;
    const std::array<const Solver::SearchConfig*,3> budget_configs = {&budget_light,&budget_short,&budget_heavy};
    std::array<double,3> budget_sec{}, budget_gain{}, budget_moves{};
    std::array<long long,3> budget_invalid{};
    double budget_base_sec = 0;
    OP_TAG(std::string budget_log;)
    for (int r = 0; r < R; r++) {''')
sub('''        const double t_req = elapsed_sec();
        auto moves = solver.process(u);
        req_sec += elapsed_sec() - t_req;''','''        const auto initial = solver.save();
        const double t_req = elapsed_sec();
        auto moves = solver.process(u);
        const double baseline_sec = elapsed_sec()-t_req;
        budget_base_sec += baseline_sec;
        const auto winner = solver.save();
        [[maybe_unused]] const auto features = Solver::budget_features;
        const double baseline_value = solver.plan_cost(moves.size());
        OP_TAG(const auto winner_tags = solver.op_tags;
               const auto trace_size = solver.heavy_log.size();
               const int query_counter = solver.request_counter;)
        for (int mode=0; mode<3; ++mode) {
            solver.restore(initial);
            Solver::budget_override = budget_configs[mode];
            const double began = elapsed_sec();
            const auto alternate = solver.process(u);
            const double seconds = elapsed_sec()-began;
            const bool valid = solver.display()==state.A[u] && solver.fillers_reachable();
            const double value = valid ? solver.plan_cost(alternate.size()) : baseline_value;
            budget_invalid[mode] += !valid;
            budget_sec[mode] += seconds;
            budget_gain[mode] += baseline_value-value;
            budget_moves[mode] += int(moves.size())-int(alternate.size());
            OP_TAG(
                budget_log += "#budget " + std::to_string(r) + ' ' + std::to_string(mode)
                    + ' ' + std::to_string(features.raw) + ' ' + std::to_string(features.ordinary)
                    + ' ' + std::to_string(features.holes) + ' ' + std::to_string(features.generic)
                    + ' ' + std::to_string(features.depth) + ' ' + std::to_string(features.fillers)
                    + ' ' + std::to_string(features.alternatives) + ' ' + Solver::trace_value(features.gap)
                    + ' ' + Solver::trace_value(features.first_gain)
                    + ' ' + std::to_string(moves.size()) + ' ' + std::to_string(alternate.size())
                    + ' ' + Solver::trace_value(baseline_value-value)
                    + ' ' + Solver::trace_value(baseline_sec) + ' ' + Solver::trace_value(seconds)
                    + ' ' + std::to_string(valid) + '\\n';
                solver.heavy_log.resize(trace_size);
                solver.request_counter = query_counter;
            )
        }
        Solver::budget_override = nullptr;
        solver.restore(winner);
        OP_TAG(solver.op_tags = winner_tags;)
        req_sec += elapsed_sec() - t_req;''')
sub('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
    std::cerr << "budget_base_sec = " << budget_base_sec << '\\n';
    for (int mode=0;mode<3;++mode) {
        std::cerr << "budget_" << mode << "_sec = " << budget_sec[mode] << '\\n'
                  << "budget_" << mode << "_gain = " << budget_gain[mode] << '\\n'
                  << "budget_" << mode << "_moves = " << budget_moves[mode] << '\\n'
                  << "budget_" << mode << "_invalid = " << budget_invalid[mode] << '\\n';
    }
    OP_TAG(std::cerr << budget_log;)
''')
(p/'main.cpp').write_text(s)
