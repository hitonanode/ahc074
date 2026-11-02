#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

using u64 = std::uint64_t;
constexpr u64 diagonal = 0x8040201008040201ULL;
u64 low(int n) { return n == 64 ? ~u64(0) : (1ULL << n) - 1; }
u64 close(u64 r, int m) {
    for (int k = 0; k < m; k++) r |= ((r >> k) & 0x0101010101010101ULL) * ((r >> (8 * k)) & 255);
    return r;
}
int pc(u64 x) { return __builtin_popcountll(x); }

struct Mapping {
    int m, g;
    std::vector<std::pair<int, int>> edges;
    std::vector<int> windows, color;
    std::array<std::array<u64, 256>, 256> rel{};
    std::array<std::array<u64, 4>, 256> adj{};
    std::vector<u64> A;
    Mapping(int m_, int g_, const std::vector<u64>& a, std::mt19937_64& rng) : m(m_), g(g_), A(a) {
        std::vector<std::pair<int, int>> pairs;
        for (int x = 0; x < m; x++) for (int y = x + 1; y < m; y++) pairs.emplace_back(x, y);
        assert(g >= int(pairs.size()));
        std::shuffle(pairs.begin(), pairs.end(), rng);
        windows.resize(64);
        std::iota(windows.begin(), windows.end(), 0);
        std::shuffle(windows.begin(), windows.end(), rng);
        color.resize(g);
        for (int j = 0; j < g; j++) {
            edges.push_back(pairs[j % pairs.size()]);
            color[j] = rng() & 1;
        }
    }
    u64 generic_mask() const {
        u64 x = 0;
        for (int j = 0; j < g; j++) x |= 1ULL << windows[j];
        return x;
    }
    void rebuild() {
        for (auto& row : adj) row.fill(0);
        for (int a = 0; a < 256; a++) for (int b = a + 1; b < 256; b++) {
            u64 ra = 0, rb = 0, d = A[a] ^ A[b];
            for (int j = 0; j < g; j++) if (d >> windows[j] & 1) {
                auto [x, y] = edges[j];
                if (int(A[a] >> windows[j] & 1) != color[j]) std::swap(x, y);
                ra |= 1ULL << (8 * x + y);
                rb |= 1ULL << (8 * y + x);
            }
            rel[a][b] = ra;
            rel[b][a] = rb;
            if (!(close(ra, m) & diagonal)) {
                adj[a][b / 64] |= 1ULL << (b % 64);
                adj[b][a / 64] |= 1ULL << (a % 64);
            }
        }
    }
    struct Triple { int a, b, c, holes, generic; };
    std::vector<Triple> triples() const {
        std::vector<Triple> out;
        const u64 gm = generic_mask();
        for (int a = 0; a < 256; a++) for (int b = a + 1; b < 256; b++) {
            if (!(adj[a][b / 64] >> (b % 64) & 1)) continue;
            for (int w = b / 64; w < 4; w++) {
                u64 choices = adj[a][w] & adj[b][w];
                if (w == b / 64) choices &= ~low(b % 64 + 1);
                for (u64 z = choices; z; z &= z - 1) {
                    int c = w * 64 + __builtin_ctzll(z);
                    if (close(rel[a][b] | rel[a][c], m) & diagonal) continue;
                    if (close(rel[b][a] | rel[b][c], m) & diagonal) continue;
                    if (close(rel[c][a] | rel[c][b], m) & diagonal) continue;
                    const u64 d = (A[a] ^ A[b]) | (A[a] ^ A[c]);
                    if (!(~d & ~gm)) continue;
                    out.push_back({a, b, c, pc(d), pc(d & gm)});
                }
            }
        }
        return out;
    }
    // The exact least legal moves from a permutation to a partial order, using
    // the same kept-subsequence criterion as Comparator::plan in astra-search4.
    int moves(u64 closure, const std::array<int, 8>& order) const {
        unsigned reach[8]{}, conflict[8]{};
        for (int a = 0; a < m; a++) reach[a] = (closure >> (8 * a)) & 255;
        for (int i = 0; i < m; i++) for (int j = 0; j < i; j++)
            if (reach[order[i]] >> order[j] & 1) {
                conflict[order[i]] |= 1U << order[j];
                conflict[order[j]] |= 1U << order[i];
            }
        unsigned char valid[256]{};
        valid[0] = 1;
        const unsigned bottom = 1U << order[m - 1];
        int best = 0;
        for (unsigned mask = 1; mask < (1U << m); mask++) {
            unsigned rest = mask & (mask - 1);
            int a = __builtin_ctz(mask);
            valid[mask] = valid[rest] && !(rest & conflict[a]);
            if (!valid[mask] || pc(mask) <= best) continue;
            bool legal = mask & bottom;
            for (int b = 0; b < m && !legal; b++)
                if (!((mask | bottom) >> b & 1) && !(reach[b] & (mask | bottom))) legal = true;
            if (legal) best = pc(mask);
        }
        return m - best;
    }
    double mean_moves(const Triple& t, std::mt19937_64& rng, int samples = 128) const {
        const u64 closed[] = {close(rel[t.a][t.b] | rel[t.a][t.c], m),
                              close(rel[t.b][t.a] | rel[t.b][t.c], m),
                              close(rel[t.c][t.a] | rel[t.c][t.b], m)};
        long long sum = 0;
        std::array<int, 8> order{};
        for (int z = 0; z < samples; z++) {
            std::iota(order.begin(), order.end(), 0);
            std::shuffle(order.begin(), order.begin() + m, rng);
            for (u64 r : closed) sum += moves(r, order);
        }
        return double(sum) / (3 * samples);
    }
    double pair_mean_moves(int a, int b, std::mt19937_64& rng, int samples = 128) const {
        const u64 closed[] = {close(rel[a][b], m), close(rel[b][a], m)};
        long long sum = 0;
        std::array<int, 8> order{};
        for (int z = 0; z < samples; z++) {
            std::iota(order.begin(), order.end(), 0);
            std::shuffle(order.begin(), order.begin() + m, rng);
            for (u64 r : closed) sum += moves(r, order);
        }
        return double(sum) / (2 * samples);
    }
    // A diagnostic co-design search, not a contest-time solver. The pool is the
    // nearest 2048 triples (by the union of their differences). A smooth penalty
    // counts vertices belonging to directed cycles in all three required graphs.
    // It gives a direction even when no complete triple is feasible initially.
    void adapt(int steps, std::mt19937_64& rng) {
        if (steps <= 0) return;
        std::vector<Triple> pool;
        u64 gm = generic_mask();
        for (int a = 0; a < 256; a++) for (int b = a + 1; b < 256; b++)
            for (int c = b + 1; c < 256; c++) {
                u64 d = (A[a] ^ A[b]) | (A[a] ^ A[c]);
                int n = pc(d);
                if (n <= 40) pool.push_back({a, b, c, n, pc(d & gm)});
            }
        std::sort(pool.begin(), pool.end(), [](const auto& a, const auto& b) {
            return std::array<int, 5>{a.holes, a.holes - a.generic, a.a, a.b, a.c} <
                   std::array<int, 5>{b.holes, b.holes - b.generic, b.a, b.b, b.c};
        });
        if (pool.size() > 2048) pool.resize(2048);
        std::array<std::array<bool, 256>, 256> needed{};
        std::vector<std::pair<int, int>> pair_pool;
        for (const auto& t : pool) for (auto [a, b] : {std::pair{t.a, t.b}, std::pair{t.a, t.c}, std::pair{t.b, t.c}})
            if (!needed[a][b]) needed[a][b] = true, pair_pool.emplace_back(a, b);
        auto rebuild_pool = [&]() {
            for (auto [a, b] : pair_pool) {
                u64 ra = 0, rb = 0, d = A[a] ^ A[b];
                for (int j = 0; j < g; j++) if (d >> windows[j] & 1) {
                    auto [x, y] = edges[j];
                    if (int(A[a] >> windows[j] & 1) != color[j]) std::swap(x, y);
                    ra |= 1ULL << (8 * x + y);
                    rb |= 1ULL << (8 * y + x);
                }
                rel[a][b] = ra;
                rel[b][a] = rb;
            }
        };
        std::array<double, 25> value{};
        for (int k = 0; k <= 24; k++) value[k] = std::exp(-0.55 * k);
        auto score = [&]() {
            double raw = 0;
            std::array<std::vector<int>, 25> by_cycle;
            for (int i = 0; i < int(pool.size()); i++) {
                const auto& t = pool[i];
                int cyclic = pc(close(rel[t.a][t.b] | rel[t.a][t.c], m) & diagonal)
                           + pc(close(rel[t.b][t.a] | rel[t.b][t.c], m) & diagonal)
                           + pc(close(rel[t.c][t.a] | rel[t.c][t.b], m) & diagonal);
                raw += value[cyclic];
                by_cycle[cyclic].push_back(i);
            }
            if (std::getenv("TRIPLE_SUM_OBJECTIVE")) return raw;
            // Counting all compatible triples alone overfits many combinations
            // around the same few products. Price only a disjoint packing, with
            // a tiny smooth residual to distinguish otherwise flat candidates.
            std::array<bool, 256> used{};
            int count = 0;
            double sum = 0;
            for (int k = 0; k <= 24; k++) for (int i : by_cycle[k]) {
                const auto& t = pool[i];
                if (used[t.a] || used[t.b] || used[t.c] || count >= (64 + m) / 2) continue;
                used[t.a] = used[t.b] = used[t.c] = true;
                count++;
                sum += value[k];
            }
            return sum + 0.005 * raw;
        };
        double current = score(), best = current;
        const double initial = current;
        auto best_edges = edges;
        auto best_windows = windows;
        auto best_color = color;
        int accepted = 0;
        for (int it = 0; it < steps; it++) {
            auto old_edges = edges;
            auto old_windows = windows;
            auto old_color = color;
            int kind = rng() % 4, a = rng() % g;
            if (kind == 0) {
                std::swap(windows[a], windows[g + rng() % (64 - g)]);
                color[a] ^= rng() & 1;
            } else if (kind == 1) color[a] ^= 1;
            else if (kind == 2) std::swap(windows[a], windows[rng() % g]);
            else {
                int copies = 0;
                for (auto e : edges) copies += e == edges[a];
                if (copies <= 1) continue;
                int x = rng() % m, y = rng() % (m - 1);
                if (y >= x) y++;
                if (x > y) std::swap(x, y);
                edges[a] = {x, y};
                color[a] ^= rng() & 1;
            }
            rebuild_pool();
            double candidate = score();
            const double temp = 0.25 * std::pow(0.02, double(it) / std::max(1, steps - 1));
            const double uniform = (rng() >> 11) * 0x1.0p-53;
            if (candidate >= current || uniform < std::exp((candidate - current) / temp)) {
                current = candidate;
                accepted++;
                if (current > best) {
                    best = current;
                    best_edges = edges;
                    best_windows = windows;
                    best_color = color;
                }
            } else {
                edges = std::move(old_edges);
                windows = std::move(old_windows);
                color = std::move(old_color);
            }
        }
        edges = std::move(best_edges);
        windows = std::move(best_windows);
        color = std::move(best_color);
        rebuild();
        std::cerr << "adaptive_pool = " << pool.size() << "\nadaptive_before = " << initial
                  << "\nadaptive_after = " << best << "\nadaptive_accepted = " << accepted << '\n';
    }
};

int main(int argc, char** argv) {
    if (argc < 5) return 1;
    const int m = std::atoi(argv[1]), g = std::atoi(argv[2]), maps = std::atoi(argv[3]);
    assert(m >= 2 && m <= 8 && g < 64);
    for (int file = 4; file < argc; file++) {
        std::ifstream in(argv[file]);
        int n, k, p, r;
        in >> n >> k >> p >> r;
        assert(n == 64 && p == 256);
        std::vector<u64> A(p);
        for (u64& a : A) {
            std::string s;
            in >> s;
            assert(s.size() == 64);
            for (int j = 0; j < 64; j++) if (s[j] == '1') a |= 1ULL << j;
        }
        std::mt19937_64 rng(0x8549e7ac51ULL);
        for (int map = 0; map < maps; map++) {
            Mapping x(m, g, A, rng);
            x.rebuild();
            const int adapt = std::getenv("TRIPLE_STEPS") ? std::atoi(std::getenv("TRIPLE_STEPS")) : 0;
            x.adapt(adapt, rng);
            int pairs = 0, close_pairs = 0;
            for (int a = 0; a < 256; a++) for (int b = a + 1; b < 256; b++)
                if (x.adj[a][b / 64] >> (b % 64) & 1) pairs++, close_pairs += pc(A[a] ^ A[b]) <= 26;
            auto ts = x.triples();
            std::sort(ts.begin(), ts.end(), [](const auto& a, const auto& b) {
                return std::array<int, 4>{a.holes, a.holes - a.generic, a.a, a.b} <
                       std::array<int, 4>{b.holes, b.holes - b.generic, b.a, b.b};
            });
            int close_triples = 0, disjoint = 0, sum_holes = 0, sum_generic = 0;
            double sum_moves = 0;
            std::array<bool, 256> used{};
            for (auto t : ts) {
                close_triples += t.holes <= 40;
                if (used[t.a] || used[t.b] || used[t.c] || disjoint >= (64 + m) / 2) continue;
                used[t.a] = used[t.b] = used[t.c] = true;
                disjoint++;
                sum_holes += t.holes;
                sum_generic += t.generic;
                sum_moves += x.mean_moves(t, rng);
            }
            struct Pair { int a, b, holes, generic, key; };
            std::vector<Pair> ps;
            const u64 gm = x.generic_mask();
            for (int a = 0; a < 256; a++) for (int b = a + 1; b < 256; b++)
                if (x.adj[a][b / 64] >> (b % 64) & 1) {
                    const u64 d = A[a] ^ A[b];
                    const int all = pc(d), gh = pc(d & gm);
                    ps.push_back({a, b, all, gh, 65 * (all - gh) + 30 * gh + 4 * all});
                }
            std::sort(ps.begin(), ps.end(), [](const auto& a, const auto& b) {
                return std::array<int, 3>{a.key, a.a, a.b} < std::array<int, 3>{b.key, b.a, b.b};
            });
            double pair_holes[2]{}, pair_generic[2]{}, pair_moves[2]{};
            int pair_count[2]{};
            // Keep pair-cost sampling from changing the next mapping's RNG.
            // This preserves the earlier random-counts experiment exactly.
            auto pair_rng = rng;
            for (int mode = 0; mode < 2; mode++) {
                auto taken = mode ? used : std::array<bool, 256>{};
                const int need = 64 + m - (mode ? 2 * disjoint : 0);
                for (auto p : ps) {
                    if (taken[p.a] || taken[p.b] || pair_count[mode] >= need) continue;
                    taken[p.a] = taken[p.b] = true;
                    pair_count[mode]++;
                    pair_holes[mode] += p.holes;
                    pair_generic[mode] += p.generic;
                    pair_moves[mode] += x.pair_mean_moves(p.a, p.b, pair_rng);
                }
                if (pair_count[mode]) {
                    pair_holes[mode] /= pair_count[mode];
                    pair_generic[mode] /= pair_count[mode];
                    pair_moves[mode] /= pair_count[mode];
                }
            }
            std::cout << "{\"file\":\"" << argv[file] << "\",\"m\":" << m << ",\"g\":" << g
                      << ",\"map\":" << map << ",\"adaptive_steps\":" << adapt
                      << ",\"objective\":\"" << (std::getenv("TRIPLE_SUM_OBJECTIVE") ? "sum" : "packing") << "\""
                      << ",\"pairs\":" << pairs << ",\"close_pairs\":" << close_pairs
                      << ",\"triples\":" << ts.size() << ",\"close_triples\":" << close_triples
                      << ",\"min_holes\":" << (ts.empty() ? -1 : ts.front().holes)
                      << ",\"greedy_disjoint\":" << disjoint
                      << ",\"selected_mean_holes\":" << (disjoint ? double(sum_holes) / disjoint : 0)
                      << ",\"selected_mean_generic_holes\":" << (disjoint ? double(sum_generic) / disjoint : 0)
                      << ",\"selected_mean_generic_moves\":" << (disjoint ? sum_moves / disjoint : 0)
                      << ",\"pairs_only_count\":" << pair_count[0]
                      << ",\"pairs_only_holes\":" << pair_holes[0]
                      << ",\"pairs_only_generic_holes\":" << pair_generic[0]
                      << ",\"pairs_only_generic_moves\":" << pair_moves[0]
                      << ",\"mixture_pair_count\":" << pair_count[1]
                      << ",\"mixture_pair_holes\":" << pair_holes[1]
                      << ",\"mixture_pair_generic_holes\":" << pair_generic[1]
                      << ",\"mixture_pair_generic_moves\":" << pair_moves[1] << "}\n";
        }
    }
    return 0;
}
