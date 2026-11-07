"""Writes a research copy of a tie-corrected solver (default solutions/legal-tie-fix) that logs open-loop rollout
data at its final choice, with that solver itself as the rollout policy (policy iteration of the near-tie
correction).

At every ROLL_EVERY-th real request, the candidates of tie_choice (the plan_cost choice first, then the kept
plans within ROLL_GAP / 100 of its plan_cost, the policy's own choice always included, at most ROLL_CAP) are
rolled out on ROLL_S common sampled sequences of ROLL_H requests (this policy, a wrong display costs 2K, plus
the terminal plan_cost(0)), and logged as `#rollmat r u n chosen` + per candidate `#rc` (source, moves,
plan_cost, costs) and `#rf` (features, the layout of solutions/legal-roll). The output is the policy's (the
copies run with in_rollout set and do not log).

Usage: python make_roll2.py OUT_DIR [--base solutions/legal-tie-fix/main.cpp] [--every 12] [--s 24] [--h 5]
"""
import argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rep(src, old, new, count=1):
    n = src.count(old)
    assert n == count, (n, old[:90])
    return src.replace(old, new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--base", default=str(HERE.parent / "legal-tie-fix" / "main.cpp"))
    ap.add_argument("--every", type=int, default=12)
    ap.add_argument("--s", type=int, default=24)
    ap.add_argument("--h", type=int, default=5)
    ap.add_argument("--cap", type=int, default=5)
    ap.add_argument("--gap", type=int, default=30)
    args = ap.parse_args()
    src = Path(args.base).read_text()
    src = rep(src, '''// ==== Common: constants, clock, random numbers ====
''', f'''// ==== Common: constants, clock, random numbers ====

#ifndef LOCAL_BENCH
#error "this is a research build (solutions/legal-roll/make_roll2.py): compile with -DLOCAL_BENCH"
#endif
#ifndef ROLL_EVERY
#define ROLL_EVERY {args.every}   // log at every ROLL_EVERY-th real request
#endif
#ifndef ROLL_S
#define ROLL_S {args.s}       // sampled future sequences, common to the candidates
#endif
#ifndef ROLL_H
#define ROLL_H {args.h}        // requests per sequence
#endif
#ifndef ROLL_CAP
#define ROLL_CAP {args.cap}      // candidates logged per decision
#endif
#ifndef ROLL_GAP
#define ROLL_GAP {args.gap}     // candidates within ROLL_GAP / 100 of the plan_cost choice
#endif
''')
    section = r'''    // ==== Research: open-loop rollout data at the final choice (make_roll2.py) ====

    bool in_rollout = false, roll_now = false;
    long long real_requests = 0;
    std::string roll_log;
    // The mean cost of this policy over the sequences from state s (a wrong display costs 2K), plus the
    // terminal plan_cost(0); the cost of every sequence in `each`.
    void rollout_costs(const State& s, const std::vector<std::vector<int>>& seqs, std::vector<double>& each) {
        for (const auto& seq : seqs) {
            Solver sim = *this;
            sim.in_rollout = true;
            sim.roll_now = false;
            sim.roll_log.clear();
            sim.restore(s);
            long long moves = 0;
            for (int t : seq) {
                moves += sim.process(t).size();
                if (sim.display() != A[t]) moves += 2 * K;
            }
            each.push_back(moves + sim.plan_cost(0));
        }
    }
    // the `#rf` features of the current state (the layout of solutions/legal-roll's state_features, the move
    // labels counted from `tags`)
    std::string roll_features(const Moves& path OP_TAG(, const std::vector<uint8_t>& tags)) {
        GenericSplit split;
        split_generic(split);
        const double fc = filler_charge(split), nc = adaptive_next_cost(split), gb = generic_bias();
        int nfb = 0, lvl = 0;
        double wf = 0, stay = 0;
        for (auto f : fillers) {
            nfb += split.below(f.paper);
            wf += adaptive_weights[f.paper];
            if (split.below(f.paper)) stay += stay_table[f.paper][f.lvl].probability;
            lvl += f.lvl;
        }
        const double wt = top_d >= 0 ? adaptive_weights[top_d] : 0;
        std::array<int, 64> head;
        head.fill(-1);
        std::array<bool, K> extra{};
        if (top_d >= 0) extra[top_d] = true;
        for (auto f : fillers) extra[f.paper] = true;
        for (int k : order)
            if (col_of[k] >= 0 && !extra[k] && head[col_of[k]] < 0) head[col_of[k]] = paper[k].black >> handle[col_of[k]] & 1;
        double other = 0;
        for (int c = 0; c < H; c++)
            if (head[c] >= 0) other += adaptive_holes[c][1 - head[c]];
        std::array<int, kOpLabels> lab{};
        OP_TAG(for (auto t : tags) if (t < kOpLabels) lab[t]++;)
        int genmv = 0;
        for (auto [k, d] : path) genmv += k < M;
        // the next-cost components: the 1-step digs (dsum) and the handle fixes (hsum) as adaptive_next_cost
        // adds them; the rest of nc is the column MDP term
        double dsum = 0, hsum = 0;
        {
            std::array<int, 64> rank{};
            std::array<int, 128> first;
            std::array<bool, 128> available{};
            if (top_d >= 0 && column_color[top_d] >= 0) available[column_color[top_d]] = true;
            for (const auto& f : fillers)
                if (column_color[f.paper] >= 0) available[column_color[f.paper]] = true;
            std::fill(first.begin(), first.begin() + 2 * H, -1);
            for (int k : order) {
                if (col_of[k] < 0 || extra[k]) continue;
                const int c = col_of[k], color = column_color[k];
                if (first[color] < 0) first[color] = rank[c];
                dsum += adaptive_weights[k] * rank[c] / P;
                rank[c]++;
            }
            std::array<std::array<double, 2>, 64> covered{};
            for (auto f : fillers)
                if (split.below(f.paper)) {
                    const auto& v = stay_table[f.paper][f.lvl];
                    for (int c = 0; c < H; c++) {
                        const int color = h_blk[f.paper] >> c & 1;
                        covered[c][color] = std::max(covered[c][color], v.cover[c]);
                    }
                }
            for (int c = 0; c < H; c++)
                for (int color = 0; color < 2; color++) {
                    int fixes = available[2 * c + color] ? 0 : first[2 * c + color];
                    if (fixes < 0) fixes = rank[c];
                    hsum += (adaptive_holes[c][color] - kCoverStrength * covered[c][color]) * fixes;
                }
        }
        char b[128];
        std::snprintf(b, sizeof b, "#rf %.4f %.4f %.4f %d %d %.1f %.1f %.5f", fc, nc, gb, int(fillers.size()), nfb, wt, wf, other);
        std::string s = b;
        for (int i = 0; i < kOpLabels; i++) s += ' ' + std::to_string(lab[i]);
        std::snprintf(b, sizeof b, " %.5f %d %d %.5f %.5f %.5f", stay, genmv, lvl, dsum, hsum, nc - dsum - hsum);
        s += b;
        return s;
    }
    // Logs the decision: the plan_cost choice (index 0), the kept plans within ROLL_GAP, the policy's choice
    // `chosen` (-1: the plan_cost choice) always included.
    void roll_decision(int u, const State& c0, const Moves& path0 OP_TAG(, const std::vector<uint8_t>& tags0),
                       double v0, int chosen) {
        std::vector<int> idx;
        for (int i = 0; i < int(tie_pool.size()); i++)
            if (tie_pool[i].state.order != c0.order && tie_pool[i].value - v0 < ROLL_GAP / 100.0) idx.push_back(i);
        std::stable_sort(idx.begin(), idx.end(), [&](int a, int b) { return tie_pool[a].value < tie_pool[b].value; });
        if (int(idx.size()) > ROLL_CAP - 1) {
            std::vector<int> keep(idx.begin(), idx.begin() + (ROLL_CAP - 1));
            if (chosen >= 0 && std::find(keep.begin(), keep.end(), chosen) == keep.end()) keep.back() = chosen;
            idx = keep;
        }
        if (idx.empty()) return;
        std::mt19937_64 rr(0x9E3779B97F4A7C15ULL + 1000003ULL * uint64_t(real_requests));
        std::vector<std::vector<int>> seqs(ROLL_S, std::vector<int>(ROLL_H));
        for (auto& seq : seqs) {
            int prev = u;
            for (int& t : seq) {
                t = int(rr() % (P - 1));
                if (t >= prev) t++;
                prev = t;
            }
        }
        int ch = 0;
        for (int j = 0; j < int(idx.size()); j++)
            if (idx[j] == chosen) ch = j + 1;
        char b[96];
        std::snprintf(b, sizeof b, "#rollmat %lld %d %d %d\n", real_requests - 1, u, int(idx.size()) + 1, ch);
        roll_log += b;
        auto one = [&](const State& s, const Moves& p OP_TAG(, const std::vector<uint8_t>& t), double value, int source) {
            std::vector<double> each;
            rollout_costs(s, seqs, each);
            std::snprintf(b, sizeof b, "#rc %d %d %.3f", source, int(p.size()), value);
            roll_log += b;
            for (double x : each) {
                std::snprintf(b, sizeof b, " %.2f", x);
                roll_log += b;
            }
            roll_log += '\n';
            restore(s);
            roll_log += roll_features(p OP_TAG(, t)) + '\n';
        };
        one(c0, path0 OP_TAG(, tags0), v0, 0);
        for (int i : idx) one(tie_pool[i].state, tie_pool[i].path OP_TAG(, tie_pool[i].tags), tie_pool[i].value, 1);
    }

    // ==== Near-tie correction of the final choice (tie_choice) ====
'''
    src = rep(src, '''    // ==== Near-tie correction of the final choice (tie_choice) ====
''', section)
    # the decision log inside tie_choice: before returning in each branch
    src = rep(src, '''        tie_decisions++;
        if (best < 0) {
            restore(c0);
            return path;
        }''', '''        tie_decisions++;
        if (roll_now) {
            roll_decision(u, c0, path OP_TAG(, tags), v0, best);
            roll_now = false;
        }
        if (best < 0) {
            restore(c0);
            return path;
        }''')
    src = rep(src, '''        tie_pool.clear();
        tie_pooling = true;''', '''        tie_pool.clear();
        tie_pooling = true;
        roll_now = false;
        if (!in_rollout) roll_now = real_requests++ % ROLL_EVERY == 0;''')
    src = rep(src, '''    std::cerr << "tie_decisions = " << solver.tie_decisions''', '''    std::cerr << solver.roll_log;
    std::cerr << "tie_decisions = " << solver.tie_decisions''')
    src = rep(src, '''//   Near-tie correction of the final choice (tie_choice)
''', '''//   Research: open-loop rollout data at the final choice (make_roll2.py)
//   Near-tie correction of the final choice (tie_choice)
''')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "main.cpp").write_text(src)
    print(f"wrote {out / 'main.cpp'} from {args.base}")


if __name__ == "__main__":
    main()
