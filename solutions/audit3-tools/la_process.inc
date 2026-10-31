    // ---- lookahead experiment (audit3): process() split into the plan options, the plan search
    // (candidates with their end states) and the choice.
    std::vector<PlanOpt> build_opts(int u) {
        int top0 = top_d;
        std::vector<PlanOpt> opts;
        bool has_free_filler = false;
        for (auto& f : fillers) has_free_filler |= f.pred < 0;
        bool prev_ok = top0 >= 0 && ded[u] >= 0 && ded[u] != top0 && prev_filler;
        std::vector<int> frets = {1};
        if (kFretRule && has_free_filler) frets.push_back(0);
        for (int rm = 1; rm <= (prev_ok ? 3 : 2); rm++)
            for (int fm : {1, 2, 3, 4})
                for (int uf = 1; uf < 2; uf++)
                    for (int kp = 0; kp < ((top0 >= 0 && ded[u] == top0) ? 2 : 1); kp++)
                        for (int fr : (fm >= 3 ? frets : std::vector<int>{1}))
                            if ((fm == 2 && !has_free_filler) || (fm >= 3 && (!refill || fillers.empty())) || (fm == 4 && !keep_harmless))
                                continue;
                            else
                                opts.push_back(PlanOpt{rm, fm, uf == 1, kp == 1, fr});
        if (joint_on && ded[u] >= 0 && ded[u] != top0)
            for (int rm = 1; rm <= 2; rm++)
                for (int fr : frets) opts.push_back(PlanOpt{rm, 5, true, false, fr});
        if (prev_ok && kPrevStay)
            for (int fm : {1, 2, 3, 4})
                for (int fr : (fm >= 3 ? frets : std::vector<int>{1}))
                    if (!((fm == 2 && !has_free_filler) || (fm >= 3 && (!refill || fillers.empty())) || (fm == 4 && !keep_harmless)))
                        opts.push_back(PlanOpt{4, fm, true, false, fr});
        return opts;
    }
    struct Cand {
        double cost;
        std::vector<std::pair<int, int>> ops;
        State st;
        PlanOpt opt;
        bool pool_lift;
    };
    // All valid plans of request u from the current state (restored afterwards).
    std::vector<Cand> plan_cands(int u) {
        const State st0 = save();
        auto opts = build_opts(u);
        std::vector<Cand> res;
        bool cv = check_vis;
        check_vis = true;
        for (const PlanOpt& o : opts) {
            restore(st0);
            ops.clear();
            invalid = false;
            run_plan(u, o);
            if (invalid || display() != A[u]) continue;
            if (!fillers_reachable()) continue;
            if (kMergeDouble) merge_double_moves(st0.order, ops);
            double cost = ops.size() + kFillerCharge * fillers.size() + kTopValue * tops_penalty();
            res.push_back({cost, ops, save(), o, o.fret_mode == 5 && last_pool_lift});
        }
        check_vis = cv;
        restore(st0);
        return res;
    }
    double best_cost_of(int u) {
        auto cs = plan_cands(u);
        double b = 1e18;
        for (auto& c : cs) b = std::min(b, c.cost);
        return b;
    }
    const double kLaMargin = env_double("LA_MARGIN", -1);  // < 0: no lookahead
    const int kLaN = env_int("LA_N", 255);                 // next targets evaluated (255 = all)
    const double kLaPhi = env_double("LA_PHI", 1.0);       // 1: next cost includes its Phi
    std::mt19937_64 la_rng{777};
    long long stat_la_req = 0, stat_la_changed = 0;
    double stat_la_gain = 0, stat_la_cands = 0;
    std::vector<std::pair<int, int>> process(int u) {
        const State st0 = save();
        int top0 = top_d;
        auto cands = plan_cands(u);
        if (cands.empty()) {
            restore(st0);
            ops.clear();
            run_plan(u, PlanOpt{});
            return ops;
        }
        int bi = 0;
        for (int i = 1; i < (int)cands.size(); i++)
            if (cands[i].cost < cands[bi].cost) bi = i;
        if (kLaMargin >= 0) {
            // distinct end states within the margin
            std::vector<int> pick;
            for (int i = 0; i < (int)cands.size(); i++) {
                if (cands[i].cost > cands[bi].cost + kLaMargin) continue;
                bool dup = false;
                for (int j : pick)
                    if (cands[j].st.order == cands[i].st.order && cands[j].st.top_d == cands[i].st.top_d &&
                        cands[j].st.fillers.size() == cands[i].st.fillers.size())
                        dup = true;
                if (!dup) pick.push_back(i);
            }
            if (pick.size() > 1) {
                std::vector<int> nxt;
                for (int v = 0; v < P; v++) if (v != u) nxt.push_back(v);
                if (kLaN < (int)nxt.size()) {
                    std::shuffle(nxt.begin(), nxt.end(), la_rng);
                    nxt.resize(kLaN);
                }
                double bv = 1e18;
                int bj = bi;
                double v_bi = 0;
                for (int i : pick) {
                    restore(cands[i].st);
                    double s = 0;
                    for (int v : nxt) {
                        auto cs = plan_cands(v);
                        double b = 1e18, bm = 0;
                        for (auto& c : cs)
                            if (c.cost < b) b = c.cost, bm = c.ops.size();
                        s += kLaPhi > 0.5 ? b : bm;
                    }
                    double val = cands[i].ops.size() + s / nxt.size();
                    if (i == bi) v_bi = val;
                    if (val < bv - 1e-9) bv = val, bj = i;
                }
                stat_la_req++;
                stat_la_cands += pick.size();
                if (bj != bi) {
                    stat_la_changed++, stat_la_gain += v_bi - bv;
                    if (std::getenv("LA_LOG")) {
                        auto& a = cands[bi];
                        auto& b = cands[bj];
                        restore(a.st);
                        double ta = tops_penalty();
                        restore(b.st);
                        double tb = tops_penalty();
                        std::cerr << "LACH base(" << a.opt.ret_mode << "," << a.opt.fret_mode << "," << a.opt.keep << "," << a.opt.fret_ret
                                  << ") ops " << a.ops.size() << " fill " << a.st.fillers.size() << " tops " << ta << " cost " << a.cost
                                  << " | la(" << b.opt.ret_mode << "," << b.opt.fret_mode << "," << b.opt.keep << "," << b.opt.fret_ret
                                  << ") ops " << b.ops.size() << " fill " << b.st.fillers.size() << " tops " << tb << " cost " << b.cost
                                  << " | gain " << v_bi - bv << " dl " << (cands[bj].cost - cands[bi].cost) << '\n';
                    }
                }
                bi = bj;
            }
        }
        restore(cands[bi].st);
        ops = cands[bi].ops;
        const PlanOpt& best_opt = cands[bi].opt;
        stat_stay += best_opt.ret_mode == 4;
        stat_fret_rule += best_opt.fret_ret == 0;
        stat_kept += best_opt.keep && top0 >= 0 && ded[u] == top0;
        stat_prev_fill += best_opt.ret_mode == 3;
        stat_refill += best_opt.fret_mode == 3;
        stat_joint += best_opt.fret_mode == 5;
        stat_pool_lift += cands[bi].pool_lift;
        stat_fill += fillers.size();
        return ops;
    }
};
