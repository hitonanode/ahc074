#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

using u64 = std::uint64_t;
constexpr int G = 36;
constexpr u64 full = (u64(1) << G) - 1;
struct Layer {
    int m = 6;
    std::array<u64, 8> opaque{}, black{};
    bool possible(u64 target, u64 holes) const {
        unsigned used = 0;
        // A safe sheet may be moved to the front of any feasible order.
        // Peeling an arbitrary one therefore preserves existence exactly.
        while (holes) {
            bool found = false;
            for (int k = 0; k < m; ++k) {
                if ((used >> k & 1) || ((black[k] ^ target) & opaque[k] & holes)) continue;
                used |= 1U << k;
                holes &= ~opaque[k];
                found = true;
            }
            if (!found) return false;
        }
        return true;
    }
    bool both(u64 target, u64 holes) const {
        return possible(target, holes) && possible(target ^ holes, holes);
    }
};

struct StateGraph {
    int m;
    std::vector<std::array<int, 8>> orders;
    std::vector<u64> shows;
    std::vector<std::vector<int>> reverse;
    std::array<int, 9> factorial{};
    int rank(const std::array<int, 8>& p) const {
        int ans = 0;
        for (int a = 0; a < m; ++a) {
            int less = 0;
            for (int b = a + 1; b < m; ++b) less += p[b] < p[a];
            ans += less * factorial[m - 1 - a];
        }
        return ans;
    }
    explicit StateGraph(const Layer& layer): m(layer.m) {
        factorial[0] = 1;
        for (int i = 1; i <= 8; ++i) factorial[i] = factorial[i - 1] * i;
        std::array<int, 8> p{};
        std::iota(p.begin(), p.begin() + m, 0);
        do orders.push_back(p); while (std::next_permutation(p.begin(), p.begin() + m));
        const int n = orders.size();
        reverse.resize(n);
        shows.resize(n);
        long long edges = 0;
        for (int s = 0; s < n; ++s) {
            u64 covered = 0;
            for (int pos = 0; pos < m; ++pos) {
                const int k = orders[s][pos];
                const u64 exposed = layer.opaque[k] & ~covered;
                shows[s] |= exposed & layer.black[k];
                covered |= layer.opaque[k];
                if (!exposed) continue;
                for (int d = 0; d < m; ++d) {
                    if (pos == d) continue;
                    auto next = orders[s];
                    if (pos < d) std::rotate(next.begin() + pos, next.begin() + pos + 1, next.begin() + d + 1);
                    else std::rotate(next.begin() + d, next.begin() + pos, next.begin() + pos + 1);
                    // Forward move s -> to, stored as predecessor of to.
                    const int to = rank(next);
                    reverse[to].push_back(s);
                    ++edges;
                }
            }
        }
        std::cerr << "graph m=" << m << " states=" << n << " forward_edges=" << edges << '\n';
    }
    double mean_distance(u64 target, u64 holes, int* goal_count = nullptr) const {
        const int n = orders.size();
        std::vector<int> distance(n, -1), queue(n);
        int begin = 0, end = 0;
        for (int s = 0; s < n; ++s) if (((shows[s] ^ target) & holes) == 0) {
            distance[s] = 0;
            queue[end++] = s;
        }
        if (goal_count) *goal_count = end;
        if (!end) return -1;
        while (begin < end) {
            const int to = queue[begin++];
            for (int from : reverse[to]) if (distance[from] < 0) {
                distance[from] = distance[to] + 1;
                queue[end++] = from;
            }
        }
        if (end != n) { std::cerr << "unreachable state\n"; std::exit(2); }
        return std::accumulate(distance.begin(), distance.end(), 0.0) / n;
    }
};

u64 sample_holes(int h, std::mt19937_64& rng) {
    std::array<int, G> p{};
    std::iota(p.begin(), p.end(), 0);
    u64 result = 0;
    for (int i = 0; i < h; ++i) {
        const int j = i + rng() % (G - i);
        std::swap(p[i], p[j]);
        result |= u64(1) << p[i];
    }
    return result;
}

struct Moments {
    int n = 0;
    double sum = 0, squared = 0;
    void add(double x) { ++n; sum += x; squared += x * x; }
    double mean() const { return n ? sum / n : 0; }
    double se() const { return n > 1 ? std::sqrt(std::max(0.0, squared - sum * sum / n) / (n * (n - 1.0))) : 0; }
};

int main(int argc, char** argv) {
    int samples = 200000, distance_pairs = 100;
    for (int i = 1; i + 1 < argc; i += 2) {
        if (std::string(argv[i]) == "--samples") samples = std::atoi(argv[i + 1]);
        else if (std::string(argv[i]) == "--distance-pairs") distance_pairs = std::atoi(argv[i + 1]);
    }
    std::mt19937_64 structure_rng(779879);
    std::vector<std::pair<int, int>> edges;
    for (int a = 0; a < 6; ++a) for (int b = a + 1; b < 6; ++b) edges.emplace_back(a, b);
    std::shuffle(edges.begin(), edges.end(), structure_rng);
    Layer base;
    u64 polarities = 0;
    std::array<int, 15> direction{};
    for (int& x : direction) x = structure_rng() & 1;
    u64 edge_random = 0;
    for (int j = 0; j < G; ++j) {
        const auto [a, b] = edges[j % 15];
        const int polarity = structure_rng() & 1;
        if (polarity) polarities |= u64(1) << j;
        base.opaque[a] |= u64(1) << j;
        base.opaque[b] |= u64(1) << j;
        base.black[polarity ? a : b] |= u64(1) << j;
        if (polarity ^ direction[j % 15]) edge_random |= u64(1) << j;
    }
    const std::array<std::string, 4> names{"zero", "random_window", "random_edge", "feasible_control"};
    const std::array<u64, 4> ys{0, structure_rng() & full, edge_random, polarities};
    std::array<Layer, 4> sentinels;
    for (int mode = 0; mode < 4; ++mode) {
        sentinels[mode] = base;
        sentinels[mode].m = 8;
        sentinels[mode].opaque[6] = sentinels[mode].opaque[7] = full;
        sentinels[mode].black[6] = ys[mode];
        sentinels[mode].black[7] = ys[mode] ^ full;
    }
    for (int h : {8, 10, 12, 14, 16, 18}) {
        std::mt19937_64 rng(9948371 + h);
        int bcount = 0;
        std::array<int, 4> scount{}, rescue{}, one_only{};
        for (int i = 0; i < samples; ++i) {
            const u64 holes = sample_holes(h, rng);
            const u64 target = rng() & holes;
            const bool ok = base.both(target, holes);
            bcount += ok;
            for (int mode = 0; mode < 4; ++mode) {
                const bool x = sentinels[mode].possible(target, holes);
                const bool y = sentinels[mode].possible(target ^ holes, holes);
                if (ok && !(x && y)) { std::cerr << "extension violated\n"; return 2; }
                scount[mode] += x && y;
                rescue[mode] += !ok && x && y;
                one_only[mode] += x != y;
            }
        }
        for (int mode = 0; mode < 4; ++mode)
            std::cout << "{\"kind\":\"compatibility\",\"model\":\"" << names[mode]
                      << "\",\"h\":" << h << ",\"samples\":" << samples << ",\"baseline_compatible\":" << bcount
                      << ",\"sentinel_compatible\":" << scount[mode] << ",\"rescued\":" << rescue[mode]
                      << ",\"one_side_only\":" << one_only[mode] << ",\"baseline_rate\":" << double(bcount) / samples
                      << ",\"sentinel_rate\":" << double(scount[mode]) / samples
                      << ",\"rescue_fraction_of_incompatible\":" << double(rescue[mode]) / (samples - bcount)
                      << "}" << std::endl;
    }
    if (distance_pairs <= 0) return 0;
    StateGraph bg(base);
    for (int mode = 0; mode < 3; ++mode) {
        StateGraph sg(sentinels[mode]);
        std::mt19937_64 rng(834658734 + mode);
        Moments all, common_s, common_b, new_s, common_diff, goals;
        int trials = 0;
        while (all.n < distance_pairs) {
            ++trials;
            const u64 holes = sample_holes(12, rng), target = rng() & holes;
            if (!sentinels[mode].both(target, holes)) continue;
            int goalx, goaly;
            const double ms = (sg.mean_distance(target, holes, &goalx) + sg.mean_distance(target ^ holes, holes, &goaly)) * 0.5;
            all.add(ms);
            goals.add((goalx + goaly) * 0.5);
            if (base.both(target, holes)) {
                const double mb = (bg.mean_distance(target, holes) + bg.mean_distance(target ^ holes, holes)) * 0.5;
                common_b.add(mb);
                common_s.add(ms);
                common_diff.add(ms - mb);
            } else new_s.add(ms);
        }
        std::cout << "{\"kind\":\"distance\",\"model\":\"" << names[mode] << "\",\"h\":12,\"pairs\":" << all.n
                  << ",\"trials\":" << trials << ",\"all_mean\":" << all.mean() << ",\"all_se\":" << all.se()
                  << ",\"common_count\":" << common_b.n << ",\"common_baseline_mean\":" << common_b.mean()
                  << ",\"common_sentinel_mean\":" << common_s.mean() << ",\"common_difference\":" << common_diff.mean()
                  << ",\"common_difference_se\":" << common_diff.se() << ",\"new_count\":" << new_s.n
                  << ",\"new_sentinel_mean\":" << new_s.mean() << ",\"mean_goal_states\":" << goals.mean() << "}" << std::endl;
    }
}
