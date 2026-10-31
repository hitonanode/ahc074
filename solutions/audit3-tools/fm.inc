    // ---- first-move analysis (audit3): every legal first move (visible paper x every depth) followed
    // by the plan search, against the plan search alone. The bookkeeping (top_d, fillers) is repaired
    // after the free move: a dedicated paper that leaves its column (or the lifted paper, or a filler
    // that does not land on its column's top or bottom) becomes a filler whose level is the column of
    // the first paper in place below it.
    int first_in_place_below(int pos) const {
        for (int i = pos + 1; i < K; i++) {
            int k = order[i];
            if (col_of[k] >= 0 && in_column(k, col_of[k])) return col_of[k];
        }
        return H;
    }
    // Returns false when the move is illegal or the state cannot be described.
    bool free_move(int k, int d, int u) {
        if (k == ded[u]) return false;
        if (!visible(k)) return false;
        int i0 = index_of(k);
        if (i0 == d) return false;
        if (block_of[k] >= 0) {
            order.erase(order.begin() + i0);
            order.insert(order.begin() + d, k);
            return true;
        }
        if (col_of[k] < 0) return false;
        int c = col_of[k];
        bool was_top = k == top_d;
        int fidx = -1;
        for (int i = 0; i < (int)fillers.size(); i++) if (fillers[i].paper == k) fidx = i;
        int pred = -1;
        bool in_place = !was_top && fidx < 0;
        if (was_top) pred = top_pred;
        if (fidx >= 0) pred = fillers[fidx].pred;
        int ctop = column_top(c), cbot = column_bottom(c);
        if (in_place && k != ctop) {
            // cyclic predecessor: the paper in place of column c just above k
            int prev = -1;
            for (int x : order) {
                if (x == k) break;
                if (in_column(x, c)) prev = x;
            }
            pred = prev;
        }
        // apply
        order.erase(order.begin() + i0);
        order.insert(order.begin() + d, k);
        if (was_top) top_d = -1, top_pred = -1;
        if (fidx >= 0) fillers.erase(fillers.begin() + fidx);
        // classify the new place
        int below = d + 1 < K ? order[d + 1] : -1, above = d > 0 ? order[d - 1] : -1;
        if (in_place) {
            if (k == ctop && above == cbot) return true;  // a dig
            // left its column: a filler
        } else {
            // back in its column: just above its top (free paper) or just below its bottom, or
            // just below its predecessor
            int nt = column_top(c), nb = column_bottom(c);
            if (pred < 0 && ((below == nt && nt >= 0) || (above == nb && nb >= 0))) return true;
            if (pred >= 0 && above == pred && in_column(pred, c)) return true;
        }
        int lvl = first_in_place_below(d);
        if (lvl > c) return false;  // buried below its own column: shows nowhere
        Filler f{k, pred};
        f.lvl = lvl;
        f.hi = c;
        fillers.push_back(f);
        return true;
    }
    const int kFm = env_int("FM", 0);           // analyse every kFm-th request (0: off)
    long long fm_req = 0, fm_better = 0;
    double fm_gain = 0;
    std::vector<std::pair<int, int>> process_fm(int u, int r) {
        auto res = process(u);
        return res;
    }
    void analyse_first_moves(int u, int r) {
        const State st0 = save();
        auto cands = plan_cands(u);
        double base = 1e18;
        for (auto& c : cands) base = std::min(base, c.cost);
        if (base > 1e17) return;
        double best = base;
        int bk = -1, bd = -1;
        std::vector<int> ord0 = order;
        for (int k : ord0) {
            if (!visible(k)) continue;
            for (int d = 0; d < K; d++) {
                restore(st0);
                if (!free_move(k, d, u)) continue;
                auto cs = plan_cands(u);
                double b = 1e18;
                for (auto& c : cs) b = std::min(b, c.cost);
                if (1 + b < best - 1e-9) best = 1 + b, bk = k, bd = d;
            }
        }
        restore(st0);
        static const int kShow = env_int("FM_SHOW", -1);
        if (r == kShow) {
            auto pr = [&](const char* tag, const Cand& c) {
                std::cerr << tag << " opt(" << c.opt.ret_mode << "," << c.opt.fret_mode << "," << c.opt.keep << "," << c.opt.fret_ret << ") cost " << c.cost << " ops";
                for (auto [k, d] : c.ops) std::cerr << ' ' << k << '>' << d;
                std::cerr << " fillers";
                for (auto& f : c.st.fillers) std::cerr << ' ' << f.paper << '[' << f.lvl << ',' << f.hi << ']';
                std::cerr << '\n';
            };
            int bi = 0;
            for (int i = 1; i < (int)cands.size(); i++) if (cands[i].cost < cands[bi].cost) bi = i;
            pr("BASE", cands[bi]);
            std::cerr << "SHOW top_d " << top_d << " fillers";
            for (auto& f : fillers) std::cerr << ' ' << f.paper << '[' << f.lvl << ',' << f.hi << "] pred " << f.pred;
            std::cerr << "\nSHOW order";
            for (int i = 0; i < 40; i++) std::cerr << ' ' << order[i];
            std::cerr << '\n';
            if (bk >= 0) {
                free_move(bk, bd, u);
                std::cerr << "FIRST " << bk << '>' << bd << " fillers";
                for (auto& f : fillers) std::cerr << ' ' << f.paper << '[' << f.lvl << ',' << f.hi << "] pred " << f.pred;
                std::cerr << '\n';
                auto cs = plan_cands(u);
                int bj = 0;
                for (int i = 1; i < (int)cs.size(); i++) if (cs[i].cost < cs[bj].cost) bj = i;
                pr("ALT", cs[bj]);
                restore(st0);
            }
        }
        fm_req++;
        if (bk >= 0) {
            fm_better++;
            fm_gain += base - best;
            // describe the move
            int i0 = index_of(bk);
            std::string cls = block_of[bk] >= 0 ? "generic" : bk == top_d ? "x0" : is_filler(bk) ? "filler" : "column";
            int c = col_of[bk];
            int depth = -1;
            if (cls == "column") depth = depth_in_column(bk);
            std::cerr << "FM r " << r << " u " << u << " base " << base << " best " << best << " paper " << bk << " " << cls
                      << " col " << c << " depth " << depth << " from " << i0 << " to " << bd << " lvl_to " << first_in_place_below(bd)
                      << " Dcol " << col_of[ded[u]] << '\n';
        }
    }
