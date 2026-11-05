from pathlib import Path
import sys
sys.path.insert(0,'solutions/argon-req-oldfull-v2')
from build_seedcore import add_seed_core
p=Path(__file__).parent
s=add_seed_core(Path('solutions/argon-req-helperkeep/main.cpp').read_text())
def sub(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:90]);s=s.replace(a,b,1)
sub('''    struct ProcessSeed {''','''    struct HelperProbe { long long trials, valid, same, better, saved; double gain, sec; };
    inline static std::array<std::array<HelperProbe,4>,3> helper_probe{};
    inline static std::array<double,4> helper_probe_best{};
    struct ProcessSeed {''')
sub('''        FutureCandidate weighted_raw{};''','''        std::vector<FutureCandidate> kept_helpers;
        FutureCandidate weighted_raw{};''')
sub('''            try_helpers(u, st0, [&](double cost) {
                record_future(cost);
                if (cost < best) {
                    ++helper_keep_better; helper_keep_gain += best - cost;
                    best = cost; best_ops = ops; OP_TAG(best_tags = op_tags;)
                    best_state = save(); used = true;
                }
            }, true);''','''            try_helpers(u, st0, [&](double cost) {
                collect_future(kept_helpers, size_t(-1), cost);
                if (cost < best) { ++helper_keep_better; helper_keep_gain += best-cost; }
            }, true);''')
sub('''            if (chosen_path != baseline_path) {''','''            if (!seed && !kept_helpers.empty()) {
                const auto incumbent = save();
                const double value = plan_cost(chosen_path.size());
                std::array<double,4> gains{};
                const std::array<double,4> gates = {0,.5,1,1e30};
                for (const auto& raw : kept_helpers) {
                    const auto* cached = find_cached_plan(raw);
                    const auto& c = cached ? cached->edited : raw;
                    const int stage = cached ? (cached->complete ? 2 : 1) : 0;
                    const ProcessSeed candidate{c.state,c.path OP_TAG(,c.tags),stage};
                    restore(st0);
                    bool ok = false;
                    const double began = elapsed_sec();
                    const auto path = process(u,&candidate,&ok);
                    const double seconds = elapsed_sec()-began;
                    const bool valid = ok && display()==A[u] && fillers_reachable();
                    const double next = valid ? plan_cost(path.size()) : value;
                    for (int g=0;g<4;++g) if (c.cost <= value+gates[g]) {
                        auto& q=helper_probe[stage][g];
                        ++q.trials;q.valid+=valid;q.same+=order==incumbent.order;q.sec+=seconds;
                        if (valid && next<value-1e-9) {
                            ++q.better;q.gain+=value-next;
                            q.saved+=int(chosen_path.size())-int(path.size());
                            gains[g]=std::max(gains[g],value-next);
                        }
                    }
                    restore(incumbent);
                }
                for(int g=0;g<4;++g) helper_probe_best[g]+=gains[g];
                restore(incumbent);
            }
            if (chosen_path != baseline_path) {''')
sub('''    // ==== main: statistics ====
''','''    // ==== main: statistics ====
    for(int g=0;g<4;++g) std::cerr << "helper_probe_best_" << g << " = " << solver.helper_probe_best[g] << '\\n';
    for(int st=0;st<3;++st) for(int g=0;g<4;++g) {
        const auto& q=solver.helper_probe[st][g];
        const std::string prefix="helper_probe_"+std::to_string(st)+'_'+std::to_string(g)+'_';
        std::cerr << prefix << "trials = " << q.trials << '\\n'
                  << prefix << "valid = " << q.valid << '\\n'
                  << prefix << "same = " << q.same << '\\n'
                  << prefix << "better = " << q.better << '\\n'
                  << prefix << "saved = " << q.saved << '\\n'
                  << prefix << "gain = " << q.gain << '\\n'
                  << prefix << "sec = " << q.sec << '\\n';
    }
''')
(p/'main.cpp').write_text(s)
