    // ---- insertion analysis (audit4): the bookkeeping (top_d, fillers with their levels and
    // predecessors) is rebuilt from the physical order alone (describe), so that any sequence of
    // moves can be evaluated. A column keeps its cyclic order (a4cyc, captured after the design) in
    // every plan of the solution: the papers in place of a column form a rotation of its cycle with
    // the papers out removed.
    std::vector<std::vector<int>> a4cyc;  // per column, the cycle (top to bottom at the start)
    std::vector<int> a4cpos;              // position of a dedicated paper in its cycle
    void a4_init_cycles() {
        a4cyc.assign(H, {});
        a4cpos.assign(K, -1);
        for (int k : order)
            if (col_of[k] >= 0) {
                a4cpos[k] = a4cyc[col_of[k]].size();
                a4cyc[col_of[k]].push_back(k);
            }
    }
    // Rebuilds the state of `ord`: walking up from the bottom, a column paper of column c <= cur
    // (cur = column of the nearest paper in place below) is in place, one of a column > cur is out
    // (a filler of level cur), and every column paper above a generic paper is out. A run that is
    // not a cyclic subsequence of its column loses its top paper (a filler of level c taken from
    // below the top); if still not cyclic, the state is rejected.
    bool describe(const std::vector<int>& ord, State& st) const {
        st.order = ord;
        st.top_d = -1;
        st.top_pred = -1;
        st.fillers.clear();
        static std::vector<char> inpl;
        static std::vector<int> lv;
        static std::vector<std::vector<int>> run;
        inpl.assign(K, 0);
        lv.assign(K, -1);
        run.assign(H, {});
        int cur = H;
        bool gen_seen = false;
        for (int i = K - 1; i >= 0; i--) {
            int k = ord[i], c = col_of[k];
            if (c < 0) {
                if (block_of[k] >= 0) gen_seen = true;
                continue;
            }
            if (!gen_seen && c <= cur) {
                cur = c;
                run[c].push_back(k);  // bottom to top
                inpl[k] = 1;
            } else {
                lv[k] = gen_seen ? 0 : cur;
                if (lv[k] > c) lv[k] = c;  // (cannot show anywhere; rejected by the visibility checks)
            }
        }
        // a paper of column c out of place inside the run of c (between two of its papers) is hidden
        for (int c = 0; c < H; c++) {
            auto& r = run[c];
            int n = a4cyc[c].size();
            auto cyclic = [&](int skip_top) {
                int m = (int)r.size() - skip_top;
                if (m <= 1) return true;
                long tot = 0;
                // r is bottom to top: r[m-1] is the top (when skip_top = 0)
                for (int t = m - 1; t > 0; t--) tot += ((a4cpos[r[t - 1]] - a4cpos[r[t]]) % n + n) % n;
                tot += ((a4cpos[r[m - 1]] - a4cpos[r[0]]) % n + n) % n;
                return tot == n;
            };
            if (cyclic(0)) continue;
            if (!cyclic(1)) return false;
            int k = r.back();
            r.pop_back();
            inpl[k] = 0;
            lv[k] = c;
        }
        auto pred_of = [&](int x) {
            int c = col_of[x], n = a4cyc[c].size();
            if (run[c].empty()) return -1;
            int bottom = run[c][0];
            for (int t = 1; t < n; t++) {
                int p = a4cyc[c][((a4cpos[x] - t) % n + n) % n];
                if (inpl[p]) return p == bottom ? -1 : p;
            }
            return -1;
        };
        for (int i = 0; i < K; i++) {
            int k = ord[i];
            if (col_of[k] < 0 || inpl[k]) continue;
            if (i == 0) {
                st.top_d = k;
                st.top_pred = pred_of(k);
                continue;
            }
            Filler f{k, pred_of(k)};
            f.lvl = lv[k];
            f.hi = col_of[k];
            st.fillers.push_back(f);
        }
        return true;
    }
    // Validation of describe against the bookkeeping of the solution (end of every request).
    long long dsc_req = 0, dsc_bad = 0, dsc_pred = 0;
    void check_describe() {
        if (a4cyc.empty()) return;
        State s;
        dsc_req++;
        if (!describe(order, s)) {
            dsc_bad++;
            return;
        }
        bool ok = s.top_d == top_d && s.fillers.size() == fillers.size();
        bool pred_ok = s.top_pred == top_pred;
        if (ok)
            for (auto& f : fillers) {
                bool found = false;
                for (auto& g : s.fillers)
                    if (g.paper == f.paper) {
                        found = g.lvl == f.lvl;
                        if (g.pred != f.pred) pred_ok = false;
                    }
                if (!found) ok = false;
            }
        if (!ok) {
            dsc_bad++;
            static int shown = 0;
            if (shown++ < 5) {
                std::cerr << "DSC mismatch top " << top_d << "/" << s.top_d << " fillers";
                for (auto& f : fillers) std::cerr << ' ' << f.paper << '[' << f.lvl << ']';
                std::cerr << " | ";
                for (auto& f : s.fillers) std::cerr << ' ' << f.paper << '[' << f.lvl << ']';
                std::cerr << '\n';
            }
        }
        dsc_pred += !pred_ok;
        if (!pred_ok && std::getenv("DSC_SHOWP")) {
            static int shownp = 0;
            if (shownp++ < 8) {
                std::cerr << "DSCP top " << top_d << " pred " << top_pred << "/" << s.top_pred << " fillers";
                for (auto& f : fillers) std::cerr << ' ' << f.paper << '[' << f.lvl << "] p " << f.pred;
                std::cerr << " | ";
                for (auto& f : s.fillers) std::cerr << ' ' << f.paper << '[' << f.lvl << "] p " << f.pred;
                std::cerr << '\n';
            }
        }
    }
    // For the best plan of request u: after each prefix of its moves (i moves), every legal move
    // (visible paper x every depth) followed by the plan search from the rebuilt state; also the
    // plan search alone from the prefix. Prints INS lines for the gains.
    long long ins_req = 0, ins_better = 0, ins_restart_better = 0, ins_evals = 0;
    double ins_gain = 0;
    const int kInsMaxPrefix = env_int("INS_MAXP", 64);
    std::string paper_class(int k, const State& s) const {
        if (block_of[k] >= 0) return k == base_paper ? "base" : "flip";
        if (k == s.top_d) return "top";
        for (auto& f : s.fillers) if (f.paper == k) return "filler" + std::to_string(f.lvl) + "-" + std::to_string(f.hi);
        return "col" + std::to_string(col_of[k]);
    }
    double ins_dm = 0;
    std::tuple<double, int, int> best_of(int u) {
        auto cs = plan_cands(u);
        double b = 1e18;
        int m = 0, f = 0;
        for (auto& c : cs)
            if (c.cost < b) b = c.cost, m = c.ops.size(), f = c.st.fillers.size();
        return {b, m, f};
    }
    // PLAN_DBG=r: every plan option of request r with its outcome.
    void debug_plans(int u) {
        const State st0 = save();
        auto opts = build_opts(u);
        bool cv = check_vis;
        check_vis = true;
        for (const PlanOpt& o : opts) {
            restore(st0);
            ops.clear();
            invalid = false;
            run_plan(u, o);
            bool disp = display() == A[u];
            bool reach = fillers_reachable();
            std::cerr << "PDBG opt(" << o.ret_mode << "," << o.fret_mode << "," << o.keep << "," << o.fret_ret << ") invalid " << invalid
                      << " disp " << disp << " reach " << reach << " n " << ops.size() << " fill " << fillers.size() << " ops";
            for (auto [k, d] : ops) std::cerr << ' ' << k << '>' << d;
            std::cerr << " fillers";
            for (auto& f : fillers) std::cerr << ' ' << f.paper << '[' << f.lvl << ',' << f.hi << ']';
            std::cerr << '\n';
        }
        check_vis = cv;
        restore(st0);
    }
#ifdef TOGGLE_PROBE
    // TOGGLE=1: before every request, the best plan cost with the audit4 options off and on from the
    // same state (the game follows the options given by the environment).
    long long tg_req = 0, tg_better = 0, tg_worse = 0;
    double tg_gain = 0, tg_dm = 0;
    void analyse_toggle(int u, int r) {
        bool pb = kPredBottom, gf = kGenFix;
        kPredBottom = false, kGenFix = false;
        auto [b0, m0, f0] = best_of(u);
        kPredBottom = true, kGenFix = true;
        auto [b1, m1, f1] = best_of(u);
        kPredBottom = pb, kGenFix = gf;
        tg_req++;
        if (b1 < b0 - 1e-9) tg_better++;
        if (b1 > b0 + 1e-9) tg_worse++;
        tg_gain += b0 - b1;
        tg_dm += m0 - m1;
        if (std::getenv("TOGGLE_LOG") && std::abs(b1 - b0) > 1e-9)
            std::cerr << "TG r " << r << " off " << b0 << " (" << m0 << "," << f0 << ") on " << b1 << " (" << m1 << "," << f1 << ")\n";
    }
#endif
    void analyse_insert(int u, int r) {
        const State st0 = save();
        auto cands = plan_cands(u);
        if (cands.empty()) return;
        int bi = 0;
        for (int i = 1; i < (int)cands.size(); i++) if (cands[i].cost < cands[bi].cost) bi = i;
        const double base = cands[bi].cost;
        const auto base_ops = cands[bi].ops;
        double best = base;
        int best_m = cands[bi].ops.size(), best_f = cands[bi].st.fillers.size();
        const int base_m = best_m, base_f = best_f;
        std::string best_desc;
        std::vector<int> ord = st0.order;
        bool restart_better = false;
        State best_state;
        int best_i = -1;
        int n = base_ops.size();
        for (int i = 0; i < n && i <= kInsMaxPrefix; i++) {
            State si;
            if (describe(ord, si)) {
                if (i > 0) {
                    restore(si);
                    auto [b, bm, bf] = best_of(u);
                    if (i + b < base - 1e-9) restart_better = true;
                    if (i + b < best - 1e-9) {
                        best = i + b;
                        best_state = si, best_i = i;
                        best_m = i + bm, best_f = bf;
                        best_desc = "restart i " + std::to_string(i);
                    }
                }
                std::vector<int> ks;
                restore(si);
                for (int k : ord) if (visible(k)) ks.push_back(k);
                for (int k : ks) {
                    int i0 = std::find(ord.begin(), ord.end(), k) - ord.begin();
                    for (int d = 0; d < K; d++) {
                        if (d == i0) continue;
                        std::vector<int> o2 = ord;
                        o2.erase(o2.begin() + i0);
                        o2.insert(o2.begin() + d, k);
                        State s2;
                        if (!describe(o2, s2)) continue;
                        // only the moved paper may change between in place and out
                        bool same = true;
                        auto out_in = [](const State& s, int x) {
                            if (s.top_d == x) return true;
                            for (auto& f : s.fillers) if (f.paper == x) return true;
                            return false;
                        };
                        if (s2.top_d >= 0 && s2.top_d != k && !out_in(si, s2.top_d)) same = false;
                        for (auto& f : s2.fillers) if (f.paper != k && !out_in(si, f.paper)) same = false;
                        if (si.top_d >= 0 && si.top_d != k && !out_in(s2, si.top_d)) same = false;
                        for (auto& f : si.fillers) if (f.paper != k && !out_in(s2, f.paper)) same = false;
                        if (!same) continue;
                        restore(s2);
                        if (out_in(s2, k) && s2.top_d != k && !visible(k)) continue;  // a hidden filler
                        ins_evals++;
                        auto [b, bm, bf] = best_of(u);
                        if (i + 1 + b < best - 1e-9) {
                            best = i + 1 + b;
                            best_state = s2, best_i = i;
                            best_m = i + 1 + bm, best_f = bf;
                            std::string from = paper_class(k, si);
                            std::string to = paper_class(k, s2);
                            best_desc = "i " + std::to_string(i) + " paper " + std::to_string(k) + " " + from + " -> " + to +
                                        " pos " + std::to_string(i0) + ">" + std::to_string(d) + " next_base_op " +
                                        std::to_string(base_ops[i].first) + ">" + std::to_string(base_ops[i].second);
                        }
                    }
                }
            }
            // apply base op i
            auto [k, d] = base_ops[i];
            ord.erase(std::find(ord.begin(), ord.end(), k));
            ord.insert(ord.begin() + d, k);
        }
        restore(st0);
        static const int kInsShow = env_int("INS_SHOW", -1);
        if (r == kInsShow) {
            auto pr_state = [&](const char* tag, const State& s) {
                std::cerr << tag << " top_d " << s.top_d << " pred " << s.top_pred << " fillers";
                for (auto& f : s.fillers) std::cerr << ' ' << f.paper << '[' << f.lvl << ',' << f.hi << "]p" << f.pred;
                std::cerr << "\n" << tag << " order";
                for (int i = 0; i < 48; i++) std::cerr << ' ' << s.order[i];
                std::cerr << '\n';
            };
            auto pr = [&](const char* tag, const Cand& c) {
                std::cerr << tag << " opt(" << c.opt.ret_mode << "," << c.opt.fret_mode << "," << c.opt.keep << "," << c.opt.fret_ret << ") cost " << c.cost << " ops";
                for (auto [k, d] : c.ops) std::cerr << ' ' << k << '>' << d;
                std::cerr << " fillers";
                for (auto& f : c.st.fillers) std::cerr << ' ' << f.paper << '[' << f.lvl << ',' << f.hi << ']';
                std::cerr << '\n';
            };
            pr_state("S0", st0);
            {
                State d0;
                if (describe(st0.order, d0)) pr_state("D0", d0);
            }
            pr("BASE", cands[bi]);
            std::cerr << "SHOWHEAD Dcol " << col_of[ded[u]] << " D " << ded[u] << '\n';
            if (best_i >= 0) {
                std::cerr << "VAR i " << best_i << " " << best_desc << '\n';
                pr_state("S1", best_state);
                restore(best_state);
                auto cs = plan_cands(u);
                int bj = 0;
                for (int i = 1; i < (int)cs.size(); i++) if (cs[i].cost < cs[bj].cost) bj = i;
                pr("ALT", cs[bj]);
                restore(st0);
            }
        }
        ins_req++;
        ins_restart_better += restart_better;
        if (best < base - 1e-9) {
            ins_better++;
            ins_gain += base - best;
            std::cerr << "INS r " << r << " u " << u << " Dcol " << col_of[ded[u]] << " n " << n << " base " << base << " best " << best
                      << " gain " << base - best << " moves " << base_m << ">" << best_m << " fill " << base_f << ">" << best_f
                      << " opt(" << cands[bi].opt.ret_mode << "," << cands[bi].opt.fret_mode << "," << cands[bi].opt.keep << "," << cands[bi].opt.fret_ret
                      << ") | " << best_desc << '\n';
            ins_dm += base_m - best_m;
        }
    }
    // INS2=n (audit4): two insertions by a beam. Level 1 is the insertion analysis above (every
    // prefix of the best plan, every legal move, then the plan search); the INS2_B best results
    // become full plans (prefix + move + their best plan) and each is searched again the same way.
    // Prints IN2 lines with the base cost, the best single insertion and the best double one.
    struct InsCand {
        double cost;
        std::vector<std::pair<int, int>> pre;  // moves before the plan search (prefix + inserted move)
        State st;
        std::string desc;
    };
    std::vector<InsCand> ins_level(int u, const State& st0, const std::vector<std::pair<int, int>>& plan, int B) {
        std::vector<InsCand> top;
        auto offer = [&](double c, const std::vector<std::pair<int, int>>& pre, const State& s, const std::string& d) {
            if ((int)top.size() == B && c >= top.back().cost - 1e-9) return;
            top.push_back({c, pre, s, d});
            std::sort(top.begin(), top.end(), [](const InsCand& a, const InsCand& b) { return a.cost < b.cost; });
            if ((int)top.size() > B) top.pop_back();
        };
        std::vector<int> ord = st0.order;
        std::vector<std::pair<int, int>> pre;
        int n = plan.size();
        for (int i = 0; i < n; i++) {
            State si;
            if (describe(ord, si)) {
                if (i > 0) {
                    restore(si);
                    auto [b, bm, bf] = best_of(u);
                    if (b < 1e17) offer(i + b, pre, si, "restart i " + std::to_string(i));
                }
                std::vector<int> ks;
                restore(si);
                for (int k : ord) if (visible(k)) ks.push_back(k);
                auto out_in = [](const State& s, int x) {
                    if (s.top_d == x) return true;
                    for (auto& f : s.fillers) if (f.paper == x) return true;
                    return false;
                };
                for (int k : ks) {
                    int i0 = std::find(ord.begin(), ord.end(), k) - ord.begin();
                    for (int d = 0; d < K; d++) {
                        if (d == i0) continue;
                        std::vector<int> o2 = ord;
                        o2.erase(o2.begin() + i0);
                        o2.insert(o2.begin() + d, k);
                        State s2;
                        if (!describe(o2, s2)) continue;
                        bool same = true;
                        if (s2.top_d >= 0 && s2.top_d != k && !out_in(si, s2.top_d)) same = false;
                        for (auto& f : s2.fillers) if (f.paper != k && !out_in(si, f.paper)) same = false;
                        if (si.top_d >= 0 && si.top_d != k && !out_in(s2, si.top_d)) same = false;
                        for (auto& f : si.fillers) if (f.paper != k && !out_in(s2, f.paper)) same = false;
                        if (!same) continue;
                        restore(s2);
                        if (out_in(s2, k) && s2.top_d != k && !visible(k)) continue;
                        auto [b, bm, bf] = best_of(u);
                        if (b > 1e17) continue;
                        auto p2 = pre;
                        p2.push_back({k, d});
                        offer(i + 1 + b, p2, s2,
                              "i " + std::to_string(i) + " paper " + std::to_string(k) + " " + paper_class(k, si) + " -> " +
                                  paper_class(k, s2) + " pos " + std::to_string(i0) + ">" + std::to_string(d));
                    }
                }
            }
            auto [k, d] = plan[i];
            ord.erase(std::find(ord.begin(), ord.end(), k));
            ord.insert(ord.begin() + d, k);
            pre.push_back(plan[i]);
        }
        restore(st0);
        return top;
    }
    long long in2_req = 0, in2_better1 = 0, in2_better2 = 0;
    double in2_gain1 = 0, in2_gain2 = 0;
    void analyse_insert2(int u, int r) {
        const State st0 = save();
        auto cands = plan_cands(u);
        if (cands.empty()) return;
        int bi = 0;
        for (int i = 1; i < (int)cands.size(); i++) if (cands[i].cost < cands[bi].cost) bi = i;
        const double base = cands[bi].cost;
        static const int kB = env_int("INS2_B", 8);
        auto l1 = ins_level(u, st0, cands[bi].ops, kB);
        double best1 = base, best2 = base;
        std::string d1, d2;
        if (!l1.empty() && l1[0].cost < best1 - 1e-9) best1 = l1[0].cost, d1 = l1[0].desc;
        best2 = best1, d2 = d1;
        for (auto& c : l1) {
            // the full plan of this candidate: its moves so far and its best plan
            restore(c.st);
            auto cs = plan_cands(u);
            if (cs.empty()) continue;
            int bj = 0;
            for (int i = 1; i < (int)cs.size(); i++) if (cs[i].cost < cs[bj].cost) bj = i;
            auto plan = c.pre;
            for (auto& m : cs[bj].ops) plan.push_back(m);
            restore(st0);
            auto l2 = ins_level(u, st0, plan, 1);
            if (!l2.empty() && l2[0].cost < best2 - 1e-9) best2 = l2[0].cost, d2 = c.desc + " ; " + l2[0].desc;
        }
        restore(st0);
        in2_req++;
        in2_better1 += best1 < base - 1e-9;
        in2_better2 += best2 < best1 - 1e-9;
        in2_gain1 += base - best1;
        in2_gain2 += best1 - best2;
        if (best2 < base - 1e-9)
            std::cerr << "IN2 r " << r << " u " << u << " base " << base << " best1 " << best1 << " best2 " << best2 << " | " << d1
                      << " || " << d2 << '\n';
    }
