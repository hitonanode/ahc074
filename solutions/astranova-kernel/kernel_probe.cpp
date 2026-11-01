#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <utility>
#include <vector>

using U64 = std::uint64_t;
constexpr int G = 36;
struct Function { unsigned opaque, black; };
struct Pair { int u, v, full; U64 diff, target; };
struct Choice { double cost; int pair, na, nb; };
struct Evaluation { double cost = 0; int compatible = 0; std::vector<Choice> matching; };

struct Kernel {
    int m, witness, states, words, need;
    bool priority, mixed;
    std::string name;
    std::vector<Function> functions;
    std::vector<std::vector<int>> compact;
    std::vector<std::array<std::vector<U64>, 2>> truth;
    std::array<int, G> labels{};
    std::array<int, 64> windows{};
    std::vector<Pair> pairs;
    std::mt19937_64 rng;

    Kernel(std::string n, int count, bool prio, bool mix, const std::vector<U64>& a, U64 seed)
        : m(count), priority(prio), mixed(mix), name(std::move(n)), rng(seed) {
        need = 64 + m;
        if (priority) {
            // The earliest paper of each opposite-color pair determines its sign. The order of
            // these first occurrences determines every union-of-pairs column. There are exactly
            // 2^(m/2) (m/2)! such signatures; each has the same number of physical permutations.
            int h = m / 2;
            std::vector<int> p(h);
            std::iota(p.begin(), p.end(), 0);
            do {
                for (int z = 0; z < (1 << h); ++z) {
                    std::vector<int> o;
                    for (int j : p) o.push_back(2 * j + (z >> j & 1));
                    for (int j : p) o.push_back(2 * j + 1 - (z >> j & 1));
                    compact.push_back(o);
                }
            } while (std::next_permutation(p.begin(), p.end()));
            for (int j = 0; j < h; ++j) functions.push_back({3U << (2 * j), 1U << (2 * j)});
            witness = h;
            for (int mask = 1; mask < (1 << h); ++mask) {
                std::vector<int> ids;
                unsigned opq = 0;
                for (int j = 0; j < h; ++j) if (mask >> j & 1) ids.push_back(j), opq |= 3U << (2 * j);
                for (int z = 0; z < (1 << ids.size()); ++z) {
                    unsigned black = 0;
                    for (int j = 0; j < int(ids.size()); ++j) black |= 1U << (2 * ids[j] + (z >> j & 1));
                    functions.push_back({opq, black});
                }
            }
        } else {
            std::vector<int> o(m);
            std::iota(o.begin(), o.end(), 0);
            do { compact.push_back(o); } while (std::next_permutation(o.begin(), o.end()));
            for (int x = 0; x < m; ++x) for (int y = x + 1; y < m; ++y)
                functions.push_back({(1U << x) | (1U << y), 1U << x});
            witness = int(functions.size());
            for (int i = 0; i < witness; ++i) functions.push_back({functions[i].opaque, functions[i].opaque ^ functions[i].black});
            if (mixed) for (unsigned mask = 0; mask < (1U << m); ++mask) if (std::popcount(mask) == 4)
                for (unsigned b = mask; b; b = (b - 1) & mask) if (std::popcount(b) == 2)
                    functions.push_back({mask, b});
        }
        states = int(compact.size()); words = (states + 63) / 64;
        truth.resize(functions.size());
        for (int f = 0; f < int(functions.size()); ++f) {
            for (auto& v : truth[f]) v.assign(words, 0);
            for (int s = 0; s < states; ++s) {
                int c = 0;
                for (int k : compact[s]) if (functions[f].opaque >> k & 1) { c = functions[f].black >> k & 1; break; }
                truth[f][c][s >> 6] |= U64(1) << (s & 63);
            }
        }
        for (int j = 0; j < G; ++j) labels[j] = j < witness ? j : int(rng() % functions.size());
        std::iota(windows.begin(), windows.end(), 0);
        // Use the same physical window initialization for every kernel family on this case.
        std::mt19937_64 wrng(seed ^ 0x123abcdefULL);
        std::shuffle(windows.begin(), windows.end(), wrng);
        for (int u = 0; u < 256; ++u) for (int v = 0; v < u; ++v) {
            U64 d = a[u] ^ a[v];
            if (std::popcount(d) <= 26) pairs.push_back({u, v, std::popcount(d), d, a[u]});
        }
    }

    Evaluation evaluate() const {
        Evaluation e;
        std::vector<Choice> choices;
        for (int p = 0; p < int(pairs.size()); ++p) {
            const auto& q = pairs[p];
            std::array<U64, 12> aa{}, bb{};
            for (int w = 0; w < words; ++w) aa[w] = bb[w] = ~U64(0);
            if (states % 64) aa[words - 1] = bb[words - 1] = (U64(1) << (states % 64)) - 1;
            int gd = 0;
            bool valid = true;
            for (int j = 0; j < G; ++j) if (q.diff >> windows[j] & 1) {
                ++gd;
                const int c = q.target >> windows[j] & 1, f = labels[j];
                U64 any_a = 0, any_b = 0;
                for (int w = 0; w < words; ++w) {
                    any_a |= aa[w] &= truth[f][c][w];
                    any_b |= bb[w] &= truth[f][1 - c][w];
                }
                if (!any_a || !any_b) { valid = false; break; }
            }
            if (!valid) continue;
            int na = 0, nb = 0;
            for (int w = 0; w < words; ++w) na += std::popcount(aa[w]), nb += std::popcount(bb[w]);
            const double info = 0.5 * (std::sqrt(std::log2(double(states) / na)) + std::sqrt(std::log2(double(states) / nb)));
            const double cost = 0.65 * (q.full - gd) + 2.0 * info + 0.04 * q.full;
            choices.push_back({cost, p, na, nb});
        }
        e.compatible = int(choices.size());
        std::sort(choices.begin(), choices.end(), [](const Choice& a, const Choice& b) {
            return a.cost != b.cost ? a.cost < b.cost : a.pair < b.pair;
        });
        std::array<bool, 256> used{};
        for (const auto& c : choices) {
            const Pair& p = pairs[c.pair];
            if (used[p.u] || used[p.v]) continue;
            used[p.u] = used[p.v] = true;
            e.matching.push_back(c); e.cost += c.cost;
            if (int(e.matching.size()) == need) break;
        }
        e.cost = e.cost / need + 20.0 * (need - int(e.matching.size()));
        return e;
    }

    Evaluation optimize(int steps) {
        Evaluation cur = evaluate(), best = cur;
        auto best_labels = labels; auto best_windows = windows;
        for (int it = 0; it < steps; ++it) {
            const int j = rng() % G;
            const int kind = rng() % 10;
            int k = -1, old = labels[j];
            if (kind < 5) { k = rng() % 64; std::swap(windows[j], windows[k]); }
            else if (kind < 7 || j < witness) {
                const auto f = functions[old];
                for (int l = 0; l < int(functions.size()); ++l)
                    if (functions[l].opaque == f.opaque && functions[l].black == (f.opaque ^ f.black)) { labels[j] = l; break; }
            } else labels[j] = rng() % functions.size();
            Evaluation next = evaluate();
            const double temp = 0.20 * std::pow(0.001 / 0.20, double(it) / std::max(1, steps));
            const double u = double(rng() >> 11) * 0x1.0p-53;
            if (next.cost <= cur.cost || u < std::exp((cur.cost - next.cost) / temp)) {
                cur = next;
                if (cur.cost < best.cost) { best = cur; best_labels = labels; best_windows = windows; }
            } else { if (k >= 0) std::swap(windows[j], windows[k]); labels[j] = old; }
        }
        labels = best_labels; windows = best_windows;
        return evaluate();
    }

    // Exact physical state graph. Every edge first checks visibility, including mixed 4-paper
    // columns. Reverse BFS gives distances TO a target set, rather than the reverse directed metric.
    void report_exact(int seed, const Evaluation& e) const {
        std::vector<std::vector<int>> permutations;
        std::vector<int> o(m);
        std::iota(o.begin(), o.end(), 0);
        do { permutations.push_back(o); } while (std::next_permutation(o.begin(), o.end()));
        const int ns = permutations.size();
        std::vector<int> factorial(m + 1, 1);
        for (int j = 1; j <= m; ++j) factorial[j] = factorial[j - 1] * j;
        auto rank = [&](const std::vector<int>& p) {
            int s = 0;
            for (int i = 0; i < m; ++i) {
                int smaller = 0;
                for (int j = i + 1; j < m; ++j) smaller += p[j] < p[i];
                s += smaller * factorial[m - i - 1];
            }
            return s;
        };
        std::vector<U64> opaque(m), black(m), display(ns);
        for (int j = 0; j < G; ++j) for (int k = 0; k < m; ++k) {
            const Function& f = functions[labels[j]];
            if (f.opaque >> k & 1) opaque[k] |= U64(1) << windows[j];
            if (f.black >> k & 1) black[k] |= U64(1) << windows[j];
        }
        std::vector<std::vector<int>> incoming(ns);
        double mean_visible = 0;
        for (int s = 0; s < ns; ++s) {
            U64 covered = 0;
            for (int pos = 0; pos < m; ++pos) {
                int k = permutations[s][pos];
                U64 vis = opaque[k] & ~covered;
                display[s] |= black[k] & vis; covered |= opaque[k];
                if (!vis) continue;
                ++mean_visible;
                for (int dest = 0; dest < m; ++dest) if (dest != pos) {
                    auto p = permutations[s];
                    p.erase(p.begin() + pos); p.insert(p.begin() + dest, k);
                    incoming[rank(p)].push_back(s);
                }
            }
        }
        U64 gmask = 0;
        for (int j = 0; j < G; ++j) gmask |= U64(1) << windows[j];
        std::vector<int> queue(ns), dist(ns);
        double moves = 0, holes = 0, sat = 0;
        for (const auto& choice : e.matching) {
            const Pair& p = pairs[choice.pair];
            holes += std::popcount(p.diff & ~gmask);
            for (int side = 0; side < 2; ++side) {
                U64 target = side ? p.target ^ p.diff : p.target;
                std::fill(dist.begin(), dist.end(), -1);
                int qb = 0, qe = 0;
                for (int s = 0; s < ns; ++s) if (!((display[s] ^ target) & p.diff & gmask)) {
                    dist[s] = 0; queue[qe++] = s;
                }
                sat += double(qe) / ns;
                while (qb < qe) {
                    int s = queue[qb++];
                    for (int from : incoming[s]) if (dist[from] < 0) { dist[from] = dist[s] + 1; queue[qe++] = from; }
                }
                if (qe != ns) { std::cerr << "Disconnected state graph or unrepresentable goal\n"; std::exit(2); }
                moves += double(std::accumulate(dist.begin(), dist.end(), 0LL)) / ns;
            }
        }
        const int matched = e.matching.size();
        int four = 0, more = 0;
        for (int f : labels) { four += std::popcount(functions[f].opaque) == 4; more += std::popcount(functions[f].opaque) > 4; }
        std::cout << seed << ',' << name << ',' << m << ',' << G << ',' << states << ',' << e.compatible
                  << ',' << pairs.size() << ',' << matched << ',' << need << ',' << e.cost << ','
                  << (matched ? holes / matched : 0) << ',' << (matched ? moves / (2 * matched) : 0) << ','
                  << (matched ? sat / (2 * matched) : 0) << ',' << mean_visible / ns << ',' << four << ',' << more << '\n' << std::flush;
    }
};

int main(int argc, char** argv) {
    const std::string directory = argc > 1 ? argv[1] : "tools/in";
    const int begin = argc > 2 ? std::stoi(argv[2]) : 0;
    const int end = argc > 3 ? std::stoi(argv[3]) : 8;
    const int steps = argc > 4 ? std::stoi(argv[4]) : 2000;
    std::cout << "seed,kernel,papers,generic_windows,compact_states,compatible_pairs,close_pairs,matched_pairs,needed_pairs,proxy_objective,mean_handle_differences,exact_mean_moves,mean_satisfying_fraction,mean_visible_papers,four_opaque_windows,more_opaque_windows\n" << std::setprecision(10);
    for (int seed = begin; seed < end; ++seed) {
        std::string filename = std::to_string(seed);
        while (filename.size() < 4) filename = "0" + filename;
        std::ifstream input(directory + "/" + filename + ".txt");
        int n, k, p, r;
        if (!(input >> n >> k >> p >> r) || n != 64 || p != 256) { std::cerr << "Bad input seed " << seed << '\n'; return 1; }
        std::vector<U64> a(256);
        for (auto& v : a) {
            std::string s; input >> s;
            for (int j = 0; j < 64; ++j) if (s[j] == '1') v |= U64(1) << j;
        }
        // Deliberately do not read the request sequence.
        for (int family = 0; family < 4; ++family) {
            const std::string names[] = {"pair6", "mixed6", "priority6", "priority8"};
            Kernel kernel(names[family], family == 3 ? 8 : 6, family >= 2, family == 1, a, 0x718243ULL + seed);
            auto result = kernel.optimize(steps);
            kernel.report_exact(seed, result);
        }
    }
}
