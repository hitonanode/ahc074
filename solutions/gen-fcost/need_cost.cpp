// Offline analysis (not a solution): expected cost of partial needs (care C, value X) for the
// generic group types of hub8, under the stationary state distribution of the MDP policy when the
// needs come from pairs (C: each window independently with probability p, X uniform; an empty
// need with probability q for orders of single targets).
// Build: g++ -std=c++23 -O2 need_cost.cpp -o need_cost   (includes main.cpp of this directory)
#define main hub_main
#include "main.cpp"
#undef main

int main(int argc, char** argv) {
    double p = argc > 1 ? std::atof(argv[1]) : 0.3;
    double q = argc > 2 ? std::atof(argv[2]) : 0.24;
    long long samples = argc > 3 ? std::atoll(argv[3]) : 2000000;
    std::vector<std::vector<std::string>> types = {kGroup6, kGroup5, kGroup4};
    std::mt19937_64 rng(1);
    for (auto& pats : types) {
        GroupMDP mdp;
        mdp.build(pats);
        int g = mdp.g, T = 1 << g;
        std::vector<double> sum(T * T, 0), cnt(T * T, 0);
        std::vector<std::array<std::int8_t, 8>> perm = mdp.perm;
        int st = 0;
        double tot_moves = 0, tot_holes = 0;
        std::vector<double> by_c_moves(g + 1, 0), by_c_cnt(g + 1, 0);
        for (long long it = 0; it < samples; it++) {
            int C = 0;
            if ((rng() >> 11) * 0x1.0p-53 >= q)
                for (int b = 0; b < g; b++) if ((rng() >> 11) * 0x1.0p-53 < p) C |= 1 << b;
            int X = (int)(rng() & (T - 1)) & C;
            int moves = 0;
            if (C) {
                for (int step = 0; step < 64; step++) {
                    int e = mdp.next_edge(C, X, st);
                    if (e < 0) break;
                    st = mdp.adj_to[e];
                    moves++;
                }
            }
            sum[C * T + X] += moves;
            cnt[C * T + X] += 1;
            tot_moves += moves;
            tot_holes += __builtin_popcount(C);
            int c = __builtin_popcount(C);
            by_c_moves[c] += moves;
            by_c_cnt[c] += 1;
        }
        std::printf("group g=%d m=%d: moves/hole = %.4f\n", g, mdp.m, tot_moves / tot_holes);
        for (int c = 1; c <= g; c++)
            if (by_c_cnt[c] > 0) std::printf("  |C|=%d: %.4f per need (%.4f per hole)\n", c, by_c_moves[c] / by_c_cnt[c], by_c_moves[c] / by_c_cnt[c] / c);
        // Spread of the pair cost f(C,X) + f(C,~X) for each care size.
        for (int c = 1; c <= std::min(g, 4); c++) {
            std::vector<double> vals;
            for (int C = 1; C < T; C++) {
                if (__builtin_popcount(C) != c) continue;
                for (int X = C;; X = (X - 1) & C) {
                    int Y = C & ~X;
                    if (X < Y || (X == Y && false)) {
                        if (X == 0) break;
                        continue;
                    }
                    double a = cnt[C * T + X] ? sum[C * T + X] / cnt[C * T + X] : -1;
                    double b = cnt[C * T + Y] ? sum[C * T + Y] / cnt[C * T + Y] : -1;
                    if (a >= 0 && b >= 0) vals.push_back(a + b);
                    if (X == 0) break;
                }
            }
            std::sort(vals.begin(), vals.end());
            if (vals.empty()) continue;
            double mean = std::accumulate(vals.begin(), vals.end(), 0.0) / vals.size();
            std::printf("  pair cost |C|=%d: n=%zu min %.3f p10 %.3f median %.3f p90 %.3f max %.3f mean %.3f\n", c,
                        vals.size(), vals.front(), vals[vals.size() / 10], vals[vals.size() / 2],
                        vals[vals.size() * 9 / 10], vals.back(), mean);
        }
    }
}
