#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <queue>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

// Compare the submission's forward-BFS cache with the research model's
// independently written reverse multi-source Dijkstra, for every state.
#define main submission_main
#include "main.cpp"
#undef main
namespace reference_model {
#define main reference_main
#include "../chatgpt-block-mdp/probe.cpp"
#undef main
}
int main(int argc, char** argv) {
    assert(argc == 2);
    std::ifstream f(argv[1]);
    int groups; f >> groups; assert(f && groups > 0);
    Solver::FreeJointCache cache(groups);
    cache.fixed_misses = 100000;
    double max_error = 0;
    int checked = 0;
    for (int i = 0; i < groups; i++) {
        int g; std::array<int, 6> m{}, b{}; std::array<double, 27> demand{};
        f >> g; for (int& x : m) f >> x; for (int& x : b) f >> x;
        for (double& x : demand) { f >> x; x /= 256; }
        assert(f);
        reference_model::Model reference(m, b, demand);
        auto want = reference.bellman(std::vector<double>(720));
        for (int z = 0; z < 27; z++) {
            int v = z, need = 0, target = 0;
            for (int j = 0; j < 3; j++) {
                int c = v % 3; v /= 3;
                if (c) { need |= 1 << j; target |= (c - 1) << j; }
            }
            cache.probability[g][need][target] = demand[z];
        }
        std::array<unsigned, 6> mask{}, color{};
        for (int k = 0; k < 6; k++) { mask[k] = m[k]; color[k] = b[k]; }
        int type = 0, power = 1;
        for (int c = 1; c < 3; c++) for (int b = 0; b < 2; b++) for (int j = 0; j < c; j++) {
            int k = 2 * c + b;
            type += (mask[k] >> j & 1 ? int(color[k] >> j & 1) : 2) * power;
            power *= 3;
        }
        for (int s = 0; s < 720; s++) {
            assert(Solver::FreeJointCache::rank(cache.permutations[s]) == s);
            double actual = cache.query(g, type, s, mask, color);
            double expected = want[s] * reference.used;
            double error = std::abs(actual - expected);
            max_error = std::max(max_error, error);
            assert(error < 1e-6);
            assert(cache.query(g, type, s, mask, color) == actual);
            checked++;
        }
    }
    std::cout << std::setprecision(12) << "checked_states=" << checked
              << " max_abs_error=" << max_error << " cache_hits=" << cache.hits
              << " bfs_states=" << cache.states << "\n";
}
