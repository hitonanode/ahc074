    std::shared_ptr<FrontModel> front;
    std::vector<int> front_papers, front_index;
    bool front_member(int k) const { return k >= 0 && !front_index.empty() && front_index[k] >= 0; }
    void init_front(double seconds = 1e9) {
        front_index.assign(K, -1);
        for (int k = 0; k < K; ++k) if (col_of[k] >= 0 && col_of[k] < 2) {
            front_index[k] = front_papers.size(); front_papers.push_back(k);
        }
        std::vector<int> op, black;
        for (int k : front_papers) { op.push_back(h_opq[k] & 3); black.push_back(h_blk[k] & 3); }
        std::vector<FrontModel::Event> events;
        for (int u = 0; u < P; ++u) {
            int k = front_index[ded[u]], mask = (~h_opq[ded[u]]) & 3;
            if (k >= 0 || mask) events.push_back({k, mask, int(handle_bits(A[u]) & 3), 1});
        }
        auto begin = std::chrono::steady_clock::now();
        front = std::make_shared<FrontModel>(op, black, events);
        double built = CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() - begin).count();
        front->solve(500, 1e-6, std::max(0.0, seconds - built));
    }
    struct FrontState { int variant = 0, state = 0, offset = 0, open = 3; bool valid = true; };
    FrontState front_state(int excluded = -2) const {
        FrontState result;
        if (excluded == -2) excluded = front_member(top_d) ? top_d : -1;
        int local = excluded >= 0 ? front_index[excluded] : -1;
        result.variant = local + 1;
        std::vector<int> sequence;
        bool started = false, ended = false;
        for (int i = 0; i < K; i++) {
            int k = order[i];
            if (k == excluded) continue;
            if (front_member(k)) {
                if (ended || is_filler(k)) result.valid = false;
                if (!started) { started = true; result.offset = i; }
                sequence.push_back(front_index[k]);
            } else if (started) {
                ended = true;
                if (k < M) result.valid = false;
            } else {
                result.open &= ~int(h_opq[k]);
            }
        }
        if (int(sequence.size()) != front->variants[result.variant].n) result.valid = false;
        if (result.valid) result.state = front->variants[result.variant].rank(sequence);
        result.open &= 3;
        return result;
    }
    bool front_invariant() const {
        if (!front) return true;
        for (auto f : fillers) if (front_member(f.paper) || f.lvl == 1) return false;
        auto s = front_state();
        return s.valid && s.offset > generic_bottom();
    }
    double front_bias() const {
        auto s = front_state();
        return s.valid ? front->variants[s.variant].bias[s.state] : 1e12;
    }
    // Follow a table inside the contiguous component. Each stored move is legal
    // through an uncovered front window; the ordinary move check verifies it again.
    void front_path(FrontState s, const FrontModel::Path& path) {
        const auto& v = front->variants[s.variant];
        if (!s.valid || path.value[s.state] >= FrontModel::infinity / 2) { invalid = true; return; }
        for (int steps = 0; path.action[s.state] >= 0; ++steps) {
            if (steps >= 2 * K) { invalid = true; return; }
            int a = path.action[s.state], from = a / v.n, to = a % v.n;
            int k = front_papers[v.permutations[s.state][from]];
            move(k, s.offset + to);
            if (invalid) return;
            s.state = v.next[(size_t(s.state) * v.n + from) * v.n + to];
        }
    }
    void front_fix(int u, int required) {
        auto s = front_state();
        if (!s.valid) { invalid = true; return; }
        required &= s.open;
        const int goal = FrontModel::code(required, handle_bits(A[u]) & 3);
        front_path(s, front->variants[s.variant].fix[s.open][goal]);
    }
    void front_access(int d) {
        auto s = front_state();
        if (!s.valid || s.variant) { invalid = true; return; }
        front_path(s, front->access[s.open][front_index[d]][handle_bits(A[adaptive_request]) & 3]);
    }
    void front_return(int x, int u) {
        auto s = front_state(x);
        if (!s.valid) { invalid = true; return; }
        const int local = front_index[x], desired = u >= 0 ? handle_bits(A[u]) & 3 : 0;
        const int target = u >= 0 ? ded[u] : -1;
        double best = 1e100; int gap = 0;
        for (int pos = 0; pos < front->count; ++pos) {
            int full = front->inserted[local][s.state][pos];
            double value;
            if (target < 0) value = front->h[full];
            else if (front_member(target)) value = front->access[s.open][front_index[target]][desired].value[full];
            else {
                int needed = s.open & ~int(h_opq[target]);
                value = front->variants[0].fix[s.open][FrontModel::code(needed, desired)].value[full];
            }
            if (value < best) { best = value; gap = pos; }
        }
        if (best >= FrontModel::infinity / 2) { invalid = true; return; }
        const auto& seq = front->variants[s.variant].permutations[s.state];
        if (x == top_d) top_d = -1;
        drop_filler(x);
        if (gap < int(seq.size())) {
            int to = index_of(front_papers[seq[gap]]), from = index_of(x);
            move(x, to - (from < to));
        } else move_after(x, front_papers[seq.back()]);
    }
