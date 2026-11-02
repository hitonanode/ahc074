    // The exact existing planner supplies both current candidates and rollout policy.
    // Only small stack states are restored: immutable design/tables are shared in this solver.
    struct EndPlan {
        State state;
        std::vector<std::pair<int, int>> path;
        double value = 0;
    };
    bool collecting = false;
    std::vector<EndPlan> endplans;
    int oracle_samples = 0, oracle_step = 0;
    double terminal_weight = 1.0;
    long long oracle_calls = 0, oracle_candidates = 0, oracle_changed = 0, oracle_bad = 0;
    void collect_plan() {
        if (!collecting) return;
        // Canonicalization is part of the real transition. Restore records afterwards so that
        // collecting does not change normal plan generation or its tie breaking.
        const auto original = save();
        canonicalize();
        if (fillers_reachable()) {
            const auto st = save();
            bool found = false;
            for (auto& p : endplans) {
                if (p.state.order == st.order && p.state.top_d == st.top_d && same_fillers(p.state.fillers, st.fillers)) {
                    if (ops.size() < p.path.size()) p.path = ops;
                    found = true;
                    break;
                }
            }
            if (!found) endplans.push_back({st, ops, 0});
        }
        restore(original);
    }
    // No actual future request is passed here. Sample without replacement from the 255 other
    // targets, using common draws for all candidates. With 255 this is the complete expectation.
    std::vector<int> next_targets(int u) const {
        std::vector<int> v;
        for (int t = 0; t < P; t++) if (t != u) v.push_back(t);
        XorShift r{0x9e3779b97f4a7c15ULL ^ (u64(oracle_step + 1) * 1000003) ^ u64(u * 9176)};
        for (int i = P - 2; i > 0; i--) std::swap(v[i], v[r.below(i + 1)]);
        v.resize(std::min(oracle_samples, P - 1));
        return v;
    }
    double rollout_value(const EndPlan& p, const std::vector<int>& targets) {
        double sum = 0;
        for (int v : targets) {
            restore(p.state);
            auto path = base_process(v);
            oracle_calls++;
            if (display() != A[v]) {
                oracle_bad++;
                return 1e10;
            }
            sum += path.size() + terminal_weight * (adaptive_next_cost() + kFillerCharge * fillers.size());
        }
        return p.path.size() + sum / targets.size();
    }
    std::vector<std::pair<int, int>> process(int u) {
        if (oracle_samples <= 0) return base_process(u);
        endplans.clear();
        collecting = true;
        auto base = base_process(u);
        const auto base_state = save();
        ops = base;
        collect_plan();
        collecting = false;
        oracle_candidates += endplans.size();
        const auto targets = next_targets(u);
        // Put the baseline first to preserve it in exact ties.
        for (int i = 0; i < int(endplans.size()); i++)
            if (endplans[i].state.order == base_state.order && endplans[i].path.size() == base.size()) {
                std::swap(endplans[0], endplans[i]);
                break;
            }
        int best = 0;
        double bv = 1e100;
        if (endplans.size() > 1) {
            for (int i = 0; i < int(endplans.size()); i++) {
                const double value = rollout_value(endplans[i], targets);
                endplans[i].value = value;
                if (value < bv - 1e-9) bv = value, best = i;
            }
        }
        oracle_changed += endplans[best].state.order != base_state.order;
        restore(endplans[best].state);
        adaptive_request = u;
        check_vis = false;
        invalid = false;
        oracle_step++;
        return endplans[best].path;
    }

    // Mutually exclusive move accounting on the final, legally replayed path. Fillers dug for
    // are included in repair digs; moving an old filler (return or reuse) is counted separately.
    struct Counts {
        long long total=0, generic=0, lift=0, old_top=0, old_filler=0, dig_d=0, filler=0, fix=0;
        long long wrong=0, illegal=0, filler_state=0;
    };
    void account(const State& initial, const std::vector<std::pair<int,int>>& path, int u, Counts& c) const {
        std::vector<int> ord = initial.order;
        bool lifted = false;
        std::array<bool,K> oldf{}, newf{};
        for (auto f : initial.fillers) oldf[f.paper] = true;
        for (auto f : fillers) newf[f.paper] = true;
        const int d = ded[u];
        for (int j=0; j<int(path.size()); j++) {
            auto [k, dest] = path[j];
            const int pos = std::find(ord.begin(), ord.end(), k) - ord.begin();
            u64 cov = 0;
            for (int i=0;i<pos;i++) cov |= paper[ord[i]].opaque;
            c.illegal += !(paper[k].opaque & ~cov) || dest < 0 || dest >= K;
            c.total++;
            bool final_move=true;
            for(int t=j+1;t<int(path.size());t++) if(path[t].first==k) final_move=false;
            if(k<M || k==kCapPaper) c.generic++;
            else if(k==d && dest<=1) c.lift++, lifted=true;
            else if(k==initial.top_d) c.old_top++;
            else if(oldf[k]) c.old_filler++;
            else if(newf[k] && final_move) c.filler++;
            else if(!lifted && col_of[k]==col_of[d]) c.dig_d++;
            else c.fix++;
            ord.erase(ord.begin()+pos);
            ord.insert(ord.begin()+dest,k);
        }
        c.illegal += ord != order;
        c.wrong += display() != A[u];
        c.filler_state += fillers.size();
    }
