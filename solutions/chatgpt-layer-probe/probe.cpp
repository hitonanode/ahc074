#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using U64 = std::uint64_t;

struct Sheet {
    U64 opaque = 0, black = 0;
};

struct Placement {
    // Display of the complete generic order; windows covered above the shared sheet.
    U64 display = 0, above = 0;
    bool operator<(const Placement& b) const {
        return std::pair(above, display) < std::pair(b.above, b.display);
    }
    bool operator==(const Placement& b) const = default;
};

U64 pattern(const std::string& s) {
    U64 x = 0;
    for (int j = 0; j < int(s.size()); ++j) if (s[j] == '1') x |= U64(1) << j;
    return x;
}

// Each generic window compares exactly two opposite-colored sheets.
bool ordinary_pair(U64 a, U64 b, U64 mask,
                   const std::array<std::pair<int, int>, 64>& edge, int m) {
    std::array<unsigned, 8> reach{};
    U64 d = (a ^ b) & mask;
    while (d) {
        const int j = std::countr_zero(d);
        d &= d - 1;
        auto [zero, one] = edge[j];
        if ((a >> j) & 1) reach[one] |= 1U << zero;
        else reach[zero] |= 1U << one;
    }
    for (int k = 0; k < m; ++k)
        for (int i = 0; i < m; ++i)
            if ((reach[i] >> k) & 1) reach[i] |= reach[k];
    for (int i = 0; i < m; ++i) if ((reach[i] >> i) & 1) return false;
    return true;
}

bool extended_pair(U64 a, U64 b, U64 mask,
                   const std::vector<Placement>& pa,
                   const std::vector<Placement>& pb) {
    const U64 d = (a ^ b) & mask;
    for (const Placement& x : pa) {
        const U64 wrong_a = (a ^ x.display) & mask;
        for (const Placement& y : pb) {
            const U64 wrong_b = (b ^ y.display) & mask;
            if (wrong_a & d & ~y.above) continue;
            if (wrong_b & d & ~x.above) continue;

            // A constructive check of the criterion: print exactly the cells
            // where a generic-only display would be wrong, using the target
            // for which the shared paper is visible there.
            const U64 opaque = wrong_a | wrong_b;
            const U64 black = (a & wrong_a) | (b & wrong_b);
            const U64 visible_a = opaque & ~x.above;
            const U64 visible_b = opaque & ~y.above;
            const U64 result_a = (x.display & ~visible_a) | (black & visible_a);
            const U64 result_b = (y.display & ~visible_b) | (black & visible_b);
            if (((result_a ^ a) | (result_b ^ b)) & mask)
                throw std::runtime_error("internal witness validation failed");
            return true;
        }
    }
    return false;
}

int main(int argc, char** argv) {
    try {
        if (argc < 3 || argc > 4) {
            std::cerr << "usage: layer-probe INPUT SOLVER_OUTPUT [GENERIC_SHEETS=6]\n";
            return 2;
        }
        const int m = argc == 4 ? std::stoi(argv[3]) : 6;
        if (m < 2 || m > 8) throw std::runtime_error("generic sheet count must be 2..8");
        std::ifstream in(argv[1]), out(argv[2]);
        int n, k, p, r;
        if (!(in >> n >> k >> p >> r) || n != 64 || k < m)
            throw std::runtime_error("invalid input header");
        std::vector<U64> targets(p);
        std::string row;
        for (U64& x : targets) {
            if (!(in >> row) || int(row.size()) != n)
                throw std::runtime_error("invalid target");
            x = pattern(row);
        }
        std::vector<Sheet> generic(m);
        U64 mask = 0;
        for (Sheet& s : generic) {
            if (!(out >> row) || int(row.size()) != n)
                throw std::runtime_error("invalid design output");
            for (int j = 0; j < n; ++j) {
                if (row[j] != '.') s.opaque |= U64(1) << j;
                if (row[j] == '1') s.black |= U64(1) << j;
            }
            mask |= s.opaque;
        }
        std::array<std::pair<int, int>, 64> edge;
        for (int j = 0; j < n; ++j) {
            edge[j] = {-1, -1};
            if (!((mask >> j) & 1)) continue;
            int count = 0;
            for (int x = 0; x < m; ++x) if ((generic[x].opaque >> j) & 1) {
                ++count;
                if ((generic[x].black >> j) & 1) edge[j].second = x;
                else edge[j].first = x;
            }
            if (count != 2 || edge[j].first < 0 || edge[j].second < 0)
                throw std::runtime_error("generic layer is not a two-color comparator");
        }
        std::vector<std::vector<Placement>> candidates(p);
        std::vector<int> order(m);
        std::iota(order.begin(), order.end(), 0);
        do {
            U64 display = 0, covered = 0;
            std::array<U64, 9> prefix{};
            for (int d = 0; d < m; ++d) {
                const Sheet& s = generic[order[d]];
                display |= s.black & ~covered;
                covered |= s.opaque;
                prefix[d + 1] = covered;
            }
            for (int u = 0; u < p; ++u) {
                const U64 wrong = (display ^ targets[u]) & mask;
                for (int d = 1; d <= m; ++d) {
                    if (wrong & prefix[d]) break;
                    candidates[u].push_back({display, prefix[d]});
                }
            }
        } while (std::next_permutation(order.begin(), order.end()));
        std::vector<int> eligible;
        for (int u = 0; u < p; ++u) {
            auto& c = candidates[u];
            std::sort(c.begin(), c.end());
            c.erase(std::unique(c.begin(), c.end()), c.end());
            if (!c.empty()) eligible.push_back(u);
        }
        int ordinary = 0, ordinary_close = 0;
        int extra = 0, extra_close = 0, checked = 0;
        for (int u = 0; u < p; ++u) for (int v = u + 1; v < p; ++v) {
            const bool close = std::popcount(targets[u] ^ targets[v]) <= 26;
            if (ordinary_pair(targets[u], targets[v], mask, edge, m)) {
                ++ordinary;
                ordinary_close += close;
            } else if (!candidates[u].empty() && !candidates[v].empty()) {
                ++checked;
                if (extended_pair(targets[u], targets[v], mask, candidates[u], candidates[v])) {
                    ++extra;
                    extra_close += close;
                }
            }
        }
        std::cout << "generic_windows,eligible_targets,ordinary_pairs,ordinary_close_pairs,"
                     "checked_extra_candidates,extra_pairs,extra_close_pairs\n";
        std::cout << std::popcount(mask) << ',' << eligible.size() << ',' << ordinary << ','
                  << ordinary_close << ',' << checked << ',' << extra << ',' << extra_close << '\n';
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
