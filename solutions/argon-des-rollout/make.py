from pathlib import Path
here=Path(__file__).resolve().parent
s=(here.parent/'argon-des-perf-latew105/main.cpp').read_text()
helper=r'''    // ==== Request processing: final-candidate rollouts ====

    inline static bool d5_worker_active = false;
    inline static long long d5_requests = 0, d5_multi = 0, d5_candidates = 0, d5_selected = 0;
    inline static long long d5_light_trials = 0, d5_light_invalid = 0, d5_static_better = 0;
    inline static double d5_sec = 0, d5_gain = 0, d5_now_delta = 0, d5_next_moves_gain = 0;
    inline static double d5_next_phi_gain = 0, d5_sd_sum = 0, d5_samples95_sum = 0;
    inline static std::array<long long, 6> d5_gate_cases{};
    inline static std::array<double, 6> d5_gate_gain{};

    // Measurement oracle: all 255 possible next targets, or a fixed random subset.
    // The worker has its own mutable planner state; only the selected existing legal path is used.
    template<class Candidate>
    void d5_rollout_select(int u, const std::vector<Candidate>& archive, Moves& chosen
                           OP_TAG(, std::vector<uint8_t>& chosen_tags)) {
        ++d5_requests;
        static const bool on = env_real("ARGON_D5_ON", 1) != 0;
        if (!on) return;
        const auto start = Clock::now();
        const State incumbent = save();
        const double static_cost = plan_cost(chosen.size());
        std::vector<Candidate> pool{{static_cost, incumbent, chosen OP_TAG(, chosen_tags)}};
        static const double gap = env_real("ARGON_D5_GAP", .5);
        for (const auto& c : archive) {
            if (c.cost > static_cost + gap) continue;
            d5_static_better += c.cost < static_cost - 1e-9;
            bool duplicate = false;
            for (const auto& old : pool) duplicate |= old.state.order == c.state.order;
            if (duplicate) continue;
            pool.push_back(c);
            if (pool.size() == 3) break;
        }
        d5_candidates += pool.size();
        if (pool.size() < 2) { d5_sec += scaled_since(start); return; }
        ++d5_multi;
        static std::unique_ptr<Solver> worker;
        if (!worker) worker = std::make_unique<Solver>(*this);
        worker->tail_cache_on = false;
        worker->beam_enabled = false;
        worker->check_vis = true;
        static const int samples = std::clamp(int(env_real("ARGON_D5_SAMPLES", 255)), 1, P-1);
        static const double phi_weight = env_real("ARGON_D5_PHI", 1);
        std::vector<int> next_targets;
        for (int v = 0; v < P; ++v) if (v != u) next_targets.push_back(v);
        if (samples < P-1) {
            std::mt19937_64 random(0x193aa57ULL + d5_requests);
            std::shuffle(next_targets.begin(), next_targets.end(), random);
            next_targets.resize(samples);
        }
        std::vector<std::vector<double>> next_value(pool.size(), std::vector<double>(samples));
        std::vector<double> forecast(pool.size()), next_moves(pool.size()), next_phi(pool.size());
        const std::array<PlanOpt, 3> options{{{1,1,true}, {3,4,true}, {1,5,true}}};
        for (int i = 0; i < int(pool.size()); ++i) {
            forecast[i] = pool[i].path.size();
            for (int q = 0; q < samples; ++q) {
                const int v = next_targets[q];
                double best = 1e100, moves = 0, phi = 0;
                for (const auto& opt : options) {
                    if (opt.ret_mode == 3 && (pool[i].state.top_d < 0 || ded[v] == pool[i].state.top_d)) continue;
                    worker->start_plan(pool[i].state);
                    worker->adaptive_request = v;
                    worker->placement_chains.clear();
                    worker->run_plan(v, opt);
                    ++d5_light_trials;
                    if (worker->invalid || worker->ops.size() > 2*K || worker->display() != A[v] || !worker->fillers_reachable()) {
                        ++d5_light_invalid;
                        continue;
                    }
                    const double n = worker->ops.size(), p = worker->plan_cost(n) - n;
                    const double value = n + phi_weight * p;
                    if (value < best) { best = value; moves = n; phi = p; }
                }
                assert(best < 1e99);
                next_value[i][q] = best;
                forecast[i] += best / samples;
                next_moves[i] += moves / samples;
                next_phi[i] += phi / samples;
            }
        }
        int best = 0;
        for (int i = 1; i < int(pool.size()); ++i) if (forecast[i] < forecast[best] - 1e-9) best = i;
        constexpr std::array<double,6> gates{{0,.02,.05,.1,.25,.5}};
        for (int g = 0; g < 6; ++g) {
            bool any = false;
            double selected = forecast[0];
            for (int i = 1; i < int(pool.size()); ++i) if (pool[i].cost <= static_cost + gates[g] + 1e-12) {
                any = true; selected = std::min(selected, forecast[i]);
            }
            d5_gate_cases[g] += any;
            d5_gate_gain[g] += forecast[0] - selected;
        }
        if (best) {
            ++d5_selected;
            const double gain = forecast[0] - forecast[best];
            d5_gain += gain;
            d5_now_delta += double(pool[best].path.size()) - pool[0].path.size();
            d5_next_moves_gain += next_moves[0] - next_moves[best];
            d5_next_phi_gain += next_phi[0] - next_phi[best];
            double mean = 0, square = 0;
            for (int q = 0; q < samples; ++q) mean += (next_value[0][q] - next_value[best][q]) / samples;
            for (int q = 0; q < samples; ++q) {
                const double x = next_value[0][q] - next_value[best][q] - mean;
                square += x*x;
            }
            const double variance = square / std::max(1,samples-1);
            d5_sd_sum += std::sqrt(variance);
            d5_samples95_sum += 255 * 3.8416 * variance / (255*gain*gain + 3.8416*variance + 1e-100);
            restore(pool[best].state);
            chosen = std::move(pool[best].path);
            OP_TAG(chosen_tags = std::move(pool[best].tags);)
        }
        d5_sec += scaled_since(start);
    }

'''
marker='    // ==== Request processing (process) ===='
assert s.count(marker)==1
s=s.replace('//   Request processing (process)', '//   Request processing: final-candidate rollouts\n//   Request processing (process)')
s=s.replace(marker,helper+marker)
needle='        FutureCandidate weighted_raw{};'
collector=r'''        std::vector<FutureCandidate> d5_archive;
        auto d5_record = [&](double cost, const Moves& path OP_TAG(, const std::vector<uint8_t>& tags)) {
            if (d5_worker_active) return;
            for (auto& c : d5_archive) if (c.state.order == order) {
                if (cost < c.cost) c = {cost, save(), path OP_TAG(, tags)};
                std::stable_sort(d5_archive.begin(), d5_archive.end(), [](const auto& a, const auto& b) { return a.cost < b.cost; });
                return;
            }
            d5_archive.push_back({cost, save(), path OP_TAG(, tags)});
            std::stable_sort(d5_archive.begin(), d5_archive.end(), [](const auto& a, const auto& b) { return a.cost < b.cost; });
            if (d5_archive.size() > 6) d5_archive.pop_back();
        };
'''
s=s.replace(needle,collector+needle)
start=s.index('    Moves process(int u) {');end=s.index('// ==== Emergency design',start)
part=s[start:end]
part=part.replace('        post_candidate_calls++;\n        const int original_length', '        d5_record(plan_cost(chosen_path.size()), chosen_path OP_TAG(, best_tags));\n        post_candidate_calls++;\n        const int original_length')
part=part.replace('                double next = plan_cost(path.size());','                d5_record(plan_cost(path.size()), path OP_TAG(, tags));\n                double next = plan_cost(path.size());')
part=part.replace('const double value = plan_cost(path.size());','const double value = plan_cost(path.size());\n                    d5_record(value, path OP_TAG(, tags));')
part=part.replace('        post_secondary_saved += original_length - int(chosen_path.size());','''        if (!d5_worker_active) d5_rollout_select(u, d5_archive, chosen_path OP_TAG(, best_tags));
        post_secondary_saved += original_length - int(chosen_path.size());''')
s=s[:start]+part+s[end:]
stats=r'''    std::cerr << "d5_requests = " << solver.d5_requests << "\nd5_multi = " << solver.d5_multi
              << "\nd5_candidates = " << solver.d5_candidates << "\nd5_selected = " << solver.d5_selected
              << "\nd5_light_trials = " << solver.d5_light_trials << "\nd5_light_invalid = " << solver.d5_light_invalid
              << "\nd5_static_better = " << solver.d5_static_better
              << "\nd5_sec = " << solver.d5_sec << "\nd5_gain = " << solver.d5_gain / R
              << "\nd5_now_delta = " << solver.d5_now_delta / R
              << "\nd5_next_moves_gain = " << solver.d5_next_moves_gain / R
              << "\nd5_next_phi_gain = " << solver.d5_next_phi_gain / R
              << "\nd5_selected_sd = " << solver.d5_sd_sum / std::max(1LL,solver.d5_selected)
              << "\nd5_samples95 = " << solver.d5_samples95_sum / std::max(1LL,solver.d5_selected) << '\n';
    for (int g = 0; g < 6; ++g)
        std::cerr << "d5_gate" << g << "_cases = " << solver.d5_gate_cases[g]
                  << "\nd5_gate" << g << "_gain = " << solver.d5_gate_gain[g] / R << '\n';
'''
s=s.replace('    // ==== main: statistics ====','    // ==== main: statistics ====\n'+stats)
(here/'main.cpp').write_text(s)
