// Exact finite-kernel probe, not a reactive solution and not a contest-score evaluator.
#include <algorithm>
#include <array>
#include <bit>
#include <cassert>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

using U64 = std::uint64_t;
struct Paper { U64 opaque = 0, black = 0; };
constexpr int P = 256;

struct Graph {
    int n;
    std::vector<std::array<int, 7>> order;
    std::vector<std::vector<int>> incoming, outgoing;
    long long edges = 0, visible_sum = 0;
    static int rank(const std::array<int, 7>& a, int n) {
        static constexpr int fact[] = {1, 1, 2, 6, 24, 120, 720, 5040};
        int r = 0;
        for (int i = 0; i < n; ++i) {
            int smaller = 0;
            for (int j = i + 1; j < n; ++j) smaller += a[j] < a[i];
            r += smaller * fact[n - i - 1];
        }
        return r;
    }
    Graph(const std::vector<Paper>& papers, int count) : n(count) {
        std::array<int, 7> a{};
        std::iota(a.begin(), a.begin() + n, 0);
        do { order.push_back(a); } while (std::next_permutation(a.begin(), a.begin() + n));
        incoming.resize(order.size()); outgoing.resize(order.size());
        for (int s = 0; s < int(order.size()); ++s) {
            U64 covered = 0;
            int resident_pos = n;
            if (n == 7) resident_pos = std::find(order[s].begin(), order[s].end(), 6) - order[s].begin();
            for (int pos = 0; pos < n; ++pos) {
                const int k = order[s][pos];
                const bool visible = bool(papers[k].opaque & ~covered);
                covered |= papers[k].opaque;
                // Complete comparator witnesses make this independent of core labels and colors.
                const bool rule = n == 6 ? pos < 5 : (k == 6 || (pos < resident_pos && pos < 5));
                assert(visible == rule);
                if (!visible) continue;
                ++visible_sum;
                for (int dest = 0; dest < n; ++dest) if (dest != pos) {
                    auto next = order[s];
                    if (dest < pos) for (int j = pos; j > dest; --j) next[j] = next[j - 1];
                    else for (int j = pos; j < dest; ++j) next[j] = next[j + 1];
                    next[dest] = k;
                    outgoing[s].push_back(rank(next, n));
                }
            }
            auto& out = outgoing[s];
            std::sort(out.begin(), out.end()); out.erase(std::unique(out.begin(), out.end()), out.end());
            edges += out.size();
            for (int t : out) incoming[t].push_back(s);
        }
    }
    std::vector<U64> display(const std::vector<Paper>& paper, U64 gm) const {
        std::vector<U64> result(order.size());
        for (int s = 0; s < int(order.size()); ++s) {
            U64 covered = 0;
            for (int i = 0; i < n; ++i) {
                const auto& p = paper[order[s][i]];
                result[s] |= p.black & ~covered & gm;
                covered |= p.opaque;
            }
        }
        return result;
    }
    double mean_to(const std::vector<U64>& display, U64 target, U64 holes, int resident_pos = -1) const {
        const int ns = order.size();
        std::vector<int> dist(ns, -1), queue(ns);
        int head = 0, tail = 0;
        for (int s = 0; s < ns; ++s) if (!((display[s] ^ target) & holes)) dist[s] = 0, queue[tail++] = s;
        assert(tail > 0);
        while (head < tail) {
            const int s = queue[head++];
            for (int from : incoming[s]) if (dist[from] < 0) dist[from] = dist[s] + 1, queue[tail++] = from;
        }
        assert(tail == ns);
        if (resident_pos < 0) return double(std::accumulate(dist.begin(), dist.end(), 0LL)) / ns;
        assert(n == 7 && resident_pos < 7);
        long long total = 0; int count = 0;
        for (int s = 0; s < ns; ++s) if (order[s][resident_pos] == 6) total += dist[s], ++count;
        assert(count == 720);
        return double(total) / count;
    }
    void report(int case_id) const {
        int diameter = 0;
        long long total = 0;
        const int sources = n == 7 ? 7 : 1, ns = order.size();
        for (int pos = 0; pos < sources; ++pos) {
            std::array<int, 7> a{};
            std::iota(a.begin(), a.end(), 0);
            if (n == 7) { for (int j = 6; j > pos; --j) a[j] = a[j - 1]; a[pos] = 6; }
            std::vector<int> dist(ns, -1), queue(ns);
            int head = 0, tail = 1;
            queue[0] = rank(a, n); dist[queue[0]] = 0;
            while (head < tail) {
                int s = queue[head++];
                for (int t : outgoing[s]) if (dist[t] < 0) dist[t] = dist[s] + 1, queue[tail++] = t;
            }
            assert(tail == ns);
            diameter = std::max(diameter, *std::max_element(dist.begin(), dist.end()));
            total += std::accumulate(dist.begin(), dist.end(), 0LL);
        }
        std::cout << "case=" << case_id << " papers=" << n << " states=" << ns << " edges=" << edges
                  << " mean_visible=" << double(visible_sum) / ns << " canonical_sources=" << sources
                  << " canonical_entries=" << sources * ns << " directed_diameter=" << diameter
                  << " all_pair_mean_distance=" << double(total) / (sources * ns) << '\n';
    }
};

// Packed direct enumeration. It uses displayed colors, not order-constraint closures.
struct Truth {
    int ns, words;
    std::array<std::array<std::vector<U64>, 2>, 64> bit;
    Truth(const std::vector<U64>& display, U64 gm) : ns(display.size()), words((ns + 63) / 64) {
        for (U64 x = gm; x; x &= x - 1) {
            const int j = std::countr_zero(x);
            for (auto& v : bit[j]) v.assign(words, 0);
            for (int s = 0; s < ns; ++s) bit[j][display[s] >> j & 1][s >> 6] |= U64(1) << (s & 63);
        }
    }
    bool exists(U64 target, U64 holes) const {
        std::array<U64, 79> active{};
        for (int w = 0; w < words; ++w) active[w] = ~U64(0);
        if (ns % 64) active[words - 1] = (U64(1) << (ns % 64)) - 1;
        for (; holes; holes &= holes - 1) {
            const int j = std::countr_zero(holes);
            const auto& mask = bit[j][target >> j & 1];
            U64 any = 0;
            for (int w = 0; w < words; ++w) any |= active[w] &= mask[w];
            if (!any) return false;
        }
        return true;
    }
};

struct Pair {
    int u, v, full, hd;
    U64 gh;
    bool core;
    double mean = 0, proxy = 0;
};
struct Match { int h0 = -1, eligible = 0; std::vector<int> pair; double proxy = 0, hd = 0; };
Match match(const std::vector<Pair>& pairs, const std::vector<int>& sorted, const std::vector<U64>& A,
            int h0, int owner, int need) {
    Match m; m.h0 = h0;
    std::array<bool, P> used{};
    if (owner >= 0) used[owner] = true;
    for (int q : sorted) {
        const auto& p = pairs[q];
        if (p.u == owner || p.v == owner || (h0 >= 0 && ((A[p.u] ^ A[p.v]) >> h0 & 1))) continue;
        ++m.eligible;
        if (int(m.pair.size()) == need || used[p.u] || used[p.v]) continue;
        used[p.u] = used[p.v] = true;
        m.pair.push_back(q); m.proxy += p.proxy; m.hd += p.hd;
    }
    return m;
}

int main(int argc, char** argv) {
    if (argc != 7) { std::cerr << "Usage: probe INPUT_DIR REFERENCE_OUTPUT_DIR BEGIN END RESULTS_CSV HANDLES_CSV\n"; return 1; }
    std::ofstream results(argv[5]), handles(argv[6]);
    if (!results || !handles) return 2;
    results << std::setprecision(10) << "case,template,owner,h0,needed,matched,eligible_pairs,mean_Hdiff,mean_core6,mean_resident7,kernel_delta,mean_resident7_bottom,kernel_delta_bottom,same_template_feasibility_checks,new_feasible_pairs,lost_feasible_pairs\n";
    handles << std::setprecision(10) << "case,owner,h0,needed,matched,eligible_pairs,mean_Hdiff,proxy_sum\n";
    for (int id = std::stoi(argv[3]); id < std::stoi(argv[4]); ++id) {
        std::string name = std::to_string(id); while (name.size() < 4) name = "0" + name;
        std::ifstream input(std::string(argv[1]) + "/" + name + ".txt"), output(std::string(argv[2]) + "/" + name + ".txt");
        int n, k, p, r;
        if (!(input >> n >> k >> p >> r) || n != 64 || k != 192 || p != P) return 3;
        std::vector<U64> A(P);
        for (auto& a : A) {
            std::string row; input >> row; if (row.size() != 64) return 4;
            for (int j = 0; j < 64; ++j) { if (row[j] != '0' && row[j] != '1') return 4; if (row[j] == '1') a |= U64(1) << j; }
        } // Do not read any future request.
        std::vector<Paper> papers(7);
        for (int x = 0; x < 192; ++x) {
            std::string row; output >> row; if (row.size() != 64) return 5;
            for (int j = 0; j < 64; ++j) if (x < 6) {
                if (row[j] != '.') papers[x].opaque |= U64(1) << j;
                if (row[j] == '1') papers[x].black |= U64(1) << j;
            }
        } // Do not read the saved operation sequence.
        U64 gm = 0; for (int x = 0; x < 6; ++x) gm |= papers[x].opaque;
        assert(std::popcount(gm) == 36);
        std::array<std::array<bool, 6>, 6> witness{};
        for (U64 bits = gm; bits; bits &= bits - 1) {
            const int j = std::countr_zero(bits); int a = -1, b = -1, count = 0;
            for (int x = 0; x < 6; ++x) if (papers[x].opaque >> j & 1) {
                ++count; ((papers[x].black >> j & 1) ? a : b) = x;
            }
            assert(count == 2 && a >= 0 && b >= 0); witness[a][b] = witness[b][a] = true;
        }
        for (int a = 0; a < 6; ++a) for (int b = a + 1; b < 6; ++b) assert(witness[a][b]);
        std::vector<int> H; for (int j = 0; j < 64; ++j) if (!(gm >> j & 1)) H.push_back(j);
        papers[6] = {gm | (U64(1) << H[0]), 0};
        Graph core(papers, 6), resident(papers, 7);
        core.report(id); resident.report(id);
        const auto core_display = core.display(papers, gm);
        const Truth core_truth(core_display, gm);
        std::vector<Pair> pairs;
        for (int u = 0; u < P; ++u) for (int v = u + 1; v < P; ++v) {
            const U64 diff = A[u] ^ A[v]; const int full = std::popcount(diff);
            if (full > 26) continue;
            Pair q{u, v, full, std::popcount(diff & ~gm), diff & gm, core_truth.exists(A[u], diff & gm)};
            assert(q.core == core_truth.exists(A[v], q.gh));
            if (q.core) {
                q.mean = (core.mean_to(core_display, A[u], q.gh) + core.mean_to(core_display, A[v], q.gh)) * 0.5;
                q.proxy = 0.65 * q.hd + 2 * q.mean + 0.04 * q.full;
            }
            pairs.push_back(q);
        }
        std::vector<int> sorted;
        for (int q = 0; q < int(pairs.size()); ++q) if (pairs[q].core) sorted.push_back(q);
        std::sort(sorted.begin(), sorted.end(), [&](int a, int b) { return pairs[a].proxy != pairs[b].proxy ? pairs[a].proxy < pairs[b].proxy : a < b; });
        const auto unrestricted = match(pairs, sorted, A, -1, -1, 70);
        double unmean = 0; for (int q : unrestricted.pair) unmean += pairs[q].mean;
        const double uncount = unrestricted.pair.size();
        results << id << ",core6_unrestricted,-1,-1,70," << uncount << ',' << unrestricted.eligible << ','
                << unrestricted.hd / std::max(1.0, uncount) << ',' << unmean / std::max(1.0, uncount) << ','
                << unmean / std::max(1.0, uncount) << ",0," << unmean / std::max(1.0, uncount) << ",0,0,0,0\n";
        const std::array<std::string, 4> templates{"white", "black", "target0", "target128"};
        for (int t = 0; t < 4; ++t) {
            const int owner = t == 2 ? 0 : t == 3 ? 128 : -1, need = owner < 0 ? 71 : 70;
            const U64 black = t == 0 ? 0 : t == 1 ? gm : A[owner] & gm;
            Match best;
            double best_key = 1e100;
            for (int h : H) {
                auto m = match(pairs, sorted, A, h, owner, need);
                const double key = 1000.0 * (need - int(m.pair.size())) + m.proxy;
                if (t != 1) handles << id << ',' << owner << ',' << h << ',' << need << ',' << m.pair.size() << ',' << m.eligible << ','
                                   << m.hd / std::max(1.0, double(m.pair.size())) << ',' << m.proxy << '\n';
                if (key < best_key) best_key = key, best = std::move(m);
            }
            papers[6].black = black;
            const auto display = resident.display(papers, gm);
            const Truth truth(display, gm);
            int gained = 0, lost = 0;
            for (const auto& q : pairs) {
                const bool possible = truth.exists(A[q.u], q.gh) && truth.exists(A[q.v], q.gh);
                gained += possible && !q.core; lost += q.core && !possible;
            }
            assert(gained == 0 && lost == 0);
            double mean6 = 0, mean7 = 0, mean7bottom = 0;
            for (int q : best.pair) {
                const auto& a = pairs[q]; mean6 += a.mean;
                mean7 += (resident.mean_to(display, A[a.u], a.gh) + resident.mean_to(display, A[a.v], a.gh)) * 0.5;
                const double bottom = (resident.mean_to(display, A[a.u], a.gh, 6) + resident.mean_to(display, A[a.v], a.gh, 6)) * 0.5;
                assert(bottom <= a.mean + 1e-10); // Ignoring the resident reproduces every six-paper path.
                mean7bottom += bottom;
            }
            const double count = std::max(1.0, double(best.pair.size()));
            results << id << ',' << templates[t] << ',' << owner << ',' << best.h0 << ',' << need << ',' << best.pair.size() << ','
                    << best.eligible << ',' << best.hd / count << ',' << mean6 / count << ',' << mean7 / count << ','
                    << (mean7 - mean6) / count << ',' << mean7bottom / count << ',' << (mean7bottom - mean6) / count << ','
                    << pairs.size() << ',' << gained << ',' << lost << '\n' << std::flush;
        }
    }
}
