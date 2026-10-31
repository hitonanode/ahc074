// Offline (not a solution): dumps f(C, X) = expected moves of the hub8 group policy to show X on the
// care windows C, from the stationary state distribution under pair-like needs (see need_cost.cpp).
// Output: a C++ table (x 1000, rounded) for each group type, indexed [C * 2^g + X].
#define main hub_main
#include "main.cpp"
#undef main

int main(int argc, char** argv) {
    double p = argc > 1 ? std::atof(argv[1]) : 0.3;
    double q = argc > 2 ? std::atof(argv[2]) : 0.24;
    long long samples = argc > 3 ? std::atoll(argv[3]) : 20000000;
    std::vector<std::vector<std::string>> types = {kGroup6, kGroup5, kGroup4};
    const char* names[] = {"kF6_7", "kF5_6", "kF4_6"};
    std::mt19937_64 rng(1);
    for (int ti = 0; ti < 3; ti++) {
        GroupMDP mdp;
        mdp.build(types[ti]);
        int g = mdp.g, T = 1 << g;
        std::vector<double> sum(T * T, 0), cnt(T * T, 0);
        int st = 0;
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
        }
        // Cells never sampled (large C): fall back to 0.45 per hole.
        std::printf("const std::uint16_t %s[%d] = {", names[ti], T * T);
        for (int i = 0; i < T * T; i++) {
            int C = i / T, X = i % T;
            double v = 0;
            if ((X & ~C) == 0 && C) v = cnt[i] >= 20 ? sum[i] / cnt[i] : 0.45 * __builtin_popcount(C);
            if (i % 32 == 0) std::printf("\n    ");
            std::printf("%ld,", std::lround(v * 1000));
        }
        std::printf("\n};\n");
        int few = 0;
        for (int i = 0; i < T * T; i++) {
            int C = i / T, X = i % T;
            if ((X & ~C) == 0 && C && cnt[i] < 200) few++;
        }
        std::fprintf(stderr, "%s: cells with < 200 samples: %d\n", names[ti], few);
    }
}
