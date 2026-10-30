// Hub6: solutions/hub5 whose annealing also moves balanced pairs of units between columns (column
// sizes change by 2) and swaps the handle windows of two columns.
// Hub5: solutions/hub4 + simulated annealing of the pairing and of the columns (anneal_units).
// Hub4: dedicated papers hidden under a generic layer, reached through "handle" windows; a dedicated
// paper serves one target or a pair of close targets.
//
// Windows are split into G (generic windows) and H handle windows h_0..h_{H-1}.
//   - Generic layer (top of the stack): G is cut into groups of 4-6 windows. Each group has 6-7
//     papers opaque only inside the group, with fixed local patterns (found offline by an exact
//     average-cost MDP search, see trial_log.md). Moves inside a group follow the optimal MDP policy
//     for a uniformly random target pattern, computed at startup by relative value iteration; a
//     policy is also computed for every partial target (only some windows of the group matter).
//     The layer always covers every G window.
//   - Dedicated papers, grouped into H "columns". A paper of column l is opaque on all G windows and
//     on h_0..h_l, and a hole on h_{l+1}..h_{H-1} (the "triangle"). A paper serves one target u
//     (colors of A_u), or a pair u, v of targets at Hamming distance <= dmax: then it is also a
//     hole where A_u and A_v differ (they must agree at h_l). Columns are stacked in order
//     0, 1, ..., H-1 below the generic layer, so the top paper of column l is visible exactly at
//     h_l, and every other cell of a dedicated paper is hidden.
// Request u with a dedicated paper D (column l):
//   set the generic groups on the holes of D inside G (partial-target policies), rotate column l
//   until D is its top ("dig": top paper to the bottom of its column, which only changes window
//   h_l), move D to the very top, then dig every column whose handle is a hole of D until its top
//   shows the color of A_u there.
// Request u without one: set every group of the generic layer, and every handle window by digging.
// Before the next request, D goes back to the bottom of its column. Rotations and this return keep
// the cyclic order of every column; columns alternate the colors at their handle as much as
// possible, so one dig usually flips the handle window.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

using u64 = std::uint64_t;

namespace {

constexpr int N = 64, K = 192, P = 256;

struct Paper {
    u64 opaque = 0, black = 0;
};

int env_int(const char* name, int def) {
    const char* s = std::getenv(name);
    return s ? std::atoi(s) : def;
}
double env_double(const char* name, double def) {
    const char* s = std::getenv(name);
    return s ? std::atof(s) : def;
}

// Exact average-cost MDP of one group: g windows, m papers with fixed local patterns, the target
// pattern uniformly random. States are the permutations of the m papers (top first).
struct GroupMDP {
    int g = 0, m = 0, S = 0;
    std::vector<int> op, bl;  // local masks, bit i = i-th window of the group
    std::vector<int> fact;
    std::vector<std::array<std::int8_t, 8>> perm;
    std::vector<int> disp;
    std::vector<int> adj_start, adj_to;
    std::vector<std::uint8_t> adj_paper, adj_pos;  // moved paper (local) and its new position
    std::vector<double> h;
    // fT[T][state] = min over paths to a state showing pattern T of (length + h[end]).
    std::vector<std::vector<float>> fT;

    int rank(const std::int8_t* p) const {
        int r = 0;
        unsigned used = 0;
        for (int i = 0; i < m; i++) {
            int c = __builtin_popcount(((1u << p[i]) - 1) & ~used);
            r += c * fact[m - 1 - i];
            used |= 1u << p[i];
        }
        return r;
    }

    void build(const std::vector<std::string>& pats) {
        m = pats.size();
        g = pats[0].size();
        for (auto& s : pats) {
            int o = 0, b = 0;
            for (int i = 0; i < g; i++) {
                if (s[i] != '.') o |= 1 << i;
                if (s[i] == '1') b |= 1 << i;
            }
            op.push_back(o);
            bl.push_back(b);
        }
        fact.assign(m + 1, 1);
        for (int i = 1; i <= m; i++) fact[i] = fact[i - 1] * i;
        S = fact[m];
        perm.resize(S);
        disp.resize(S);
        std::array<std::int8_t, 8> p{};
        std::iota(p.begin(), p.begin() + m, 0);
        // std::next_permutation enumerates in lexicographic order = rank order.
        int s = 0;
        do {
            perm[s] = p;
            int cov = 0, b = 0;
            for (int i = 0; i < m; i++) {
                b |= bl[p[i]] & ~cov;
                cov |= op[p[i]];
            }
            disp[s] = b;
            s++;
        } while (std::next_permutation(p.begin(), p.begin() + m));
        adj_start.assign(S + 1, 0);
        for (int st = 0; st < S; st++) {
            adj_start[st] = adj_to.size();
            const auto& q = perm[st];
            int cov = 0;
            for (int i = 0; i < m; i++) {
                bool vis = (op[q[i]] & ~cov) != 0;
                cov |= op[q[i]];
                if (!vis) continue;
                for (int np = 0; np < m; np++) {
                    if (np == i) continue;
                    std::array<std::int8_t, 8> r{};
                    int t = 0;
                    for (int j = 0; j < m; j++) if (j != i) r[t++] = q[j];
                    for (int j = m - 1; j > np; j--) r[j] = r[j - 1];
                    r[np] = q[i];
                    adj_to.push_back(rank(r.data()));
                    adj_paper.push_back(q[i]);
                    adj_pos.push_back(np);
                }
            }
        }
        adj_start[S] = adj_to.size();
        solve();
    }

    // f[s] = min over paths s -> s' with (disp(s') & care) == value of (length + h[s']), by a
    // multi-source search on the reversed graph (unit edges, sources sorted by h).
    void shortest(int care, int value, const std::vector<int>& rstart, const std::vector<int>& radj,
                  std::vector<double>& f, std::vector<std::pair<double, int>>& src,
                  std::vector<int>& queue, std::vector<char>& done) const {
        src.clear();
        for (int s = 0; s < S; s++) if ((disp[s] & care) == value) src.push_back({h[s], s});
        std::sort(src.begin(), src.end());
        std::fill(f.begin(), f.end(), 1e18);
        std::fill(done.begin(), done.end(), 0);
        for (auto& [v, s] : src) f[s] = v;
        size_t i1 = 0;
        int qh = 0, qt = 0;
        while (i1 < src.size() || qh < qt) {
            int u;
            if (qh < qt && (i1 >= src.size() || f[queue[qh]] < src[i1].first)) u = queue[qh++];
            else u = src[i1++].second;
            if (done[u]) continue;
            done[u] = 1;
            double nv = f[u] + 1;
            for (int e = rstart[u]; e < rstart[u + 1]; e++) {
                int w = radj[e];
                if (!done[w] && nv < f[w]) {
                    f[w] = nv;
                    queue[qt++] = w;
                }
            }
        }
    }

    void solve() {
        std::vector<int> rstart(S + 1, 0), radj(adj_to.size());
        for (int x : adj_to) rstart[x + 1]++;
        for (int s = 0; s < S; s++) rstart[s + 1] += rstart[s];
        std::vector<int> fill(rstart.begin(), rstart.end() - 1);
        for (int s = 0; s < S; s++)
            for (int e = adj_start[s]; e < adj_start[s + 1]; e++) radj[fill[adj_to[e]]++] = s;
        int T = 1 << g;
        h.assign(S, 0);
        std::vector<double> nh(S), f(S);
        std::vector<std::pair<double, int>> src;
        std::vector<int> queue(S + adj_to.size() + 1);
        std::vector<char> done(S);
        for (int it = 0; it < 300; it++) {
            std::fill(nh.begin(), nh.end(), 0.0);
            for (int t = 0; t < T; t++) {
                shortest(T - 1, t, rstart, radj, f, src, queue, done);
                for (int s = 0; s < S; s++) nh[s] += f[s] / T;
            }
            double mx = -1e18, mn = 1e18;
            for (int s = 0; s < S; s++) {
                mx = std::max(mx, nh[s] - h[s]);
                mn = std::min(mn, nh[s] - h[s]);
            }
            double base = nh[0];
            for (int s = 0; s < S; s++) h[s] = 0.5 * h[s] + 0.5 * (nh[s] - base);
            if (mx - mn < 1e-4) {
#ifdef PROFILE_MDP
                std::cerr << "vi_iters_g" << g << " = " << it << '\n';
#endif
                break;
            }
        }
        fT.assign(T, std::vector<float>(S));
        for (int t = 0; t < T; t++) {
            shortest(T - 1, t, rstart, radj, f, src, queue, done);
            for (int st = 0; st < S; st++) fT[t][st] = f[st];
        }
    }

    // Next edge from state st towards showing `value` on the windows of `care` (other windows
    // free), or -1 if st should stop. The states showing a partial pattern are the union of those
    // showing its completions, so its value is the minimum of fT over the completions.
    int next_edge(int care, int value, int st) const {
        int free = ((1 << g) - 1) & ~care;
        double best = ((disp[st] & care) == value) ? h[st] : 1e18;
        int best_e = -1;
        for (int e = adj_start[st]; e < adj_start[st + 1]; e++) {
            int to = adj_to[e];
            double v = 1e18;
            for (int x = free;; x = (x - 1) & free) {
                v = std::min(v, (double)fT[value | x][to]);
                if (x == 0) break;
            }
            if (v + 1 < best - 1e-6) {
                best = v + 1;
                best_e = e;
            }
        }
        return best_e;
    }
};

// Group structures found offline by an exact MDP local search (see trial_log.md).
// Expected moves per window for a uniformly random target: 4 windows / 6 papers 0.419,
// 5 windows / 6 papers 0.406, 6 windows / 7 papers 0.398.
const std::vector<std::string> kGroup4 = {"1110", "..0.", "...1", "0110", ".0..", ".100"};
const std::vector<std::string> kGroup5 = {"1..0.", "0.001", "01101", "00101", "0..00", "...1."};
const std::vector<std::string> kGroup6 = {"0...0.", "01..1.", "000110", "001110", "00.010", "1.....",
                                          "00..11"};

struct Group {
    int type = 0;              // index into Solver::mdps
    std::vector<int> windows;  // global windows, local bit i = windows[i]
    std::vector<int> papers;   // global ids of the local papers 0..m-1
};

struct Solver {
    std::vector<u64> A;
    int H = 0;
    std::vector<int> handle;
    u64 gmask = 0;
    std::vector<Paper> paper;
    std::vector<int> col_of;   // column of a dedicated paper, -1 otherwise
    std::vector<int> group_of; // group of a generic paper, -1 otherwise
    std::vector<int> local_of; // local index of a generic paper in its group
    std::vector<int> ded;      // ded[u] = dedicated paper of target u, -1 if none
    std::vector<Group> groups;
    std::vector<GroupMDP> mdps;  // [0] 6 windows, [1] 5 windows, [2] 4 windows
    std::vector<int> order;    // stack, top first
    int top_d = -1;            // dedicated paper lifted to the top, -1 if none
    std::vector<std::pair<int, int>> ops;
    long long stat_dig = 0, stat_tri = 0, stat_gcare_moves = 0, stat_gcare_windows = 0, stat_hholes = 0;

    explicit Solver(std::vector<u64> a) : A(std::move(a)) {}

    std::vector<std::string> design() {
        mdps.resize(3);
        mdps[0].build(kGroup6);
        mdps[1].build(kGroup5);
        mdps[2].build(kGroup4);
        H = env_int("HUB_H", 34);
        double slope = env_double("HUB_SLOPE", 1.0);
        std::mt19937_64 rng(12345);
        for (int l = 0; l < H; l++) handle.push_back(N - H + l);
        for (int j = 0; j < N - H; j++) gmask |= 1ULL << j;
        paper.assign(K, Paper{});
        col_of.assign(K, -1);
        group_of.assign(K, -1);
        local_of.assign(K, -1);
        ded.assign(P, -1);
        int next = 0;
        std::vector<int> generic_order;
        // Tile G with as many 6-window groups as possible, then 5- and 4-window ones (fewest papers).
        int G = N - H;
        std::vector<int> types;
        {
            int best = 1 << 30;
            for (int a6 = G / 6; a6 >= 0; a6--)
                for (int b5 = 0; 6 * a6 + 5 * b5 <= G; b5++) {
                    int rem = G - 6 * a6 - 5 * b5;
                    if (rem % 4) continue;
                    int c4 = rem / 4, cost = 7 * a6 + 6 * b5 + 6 * c4;
                    if (cost < best) {
                        best = cost;
                        types.assign(a6, 0);
                        types.insert(types.end(), b5, 1);
                        types.insert(types.end(), c4, 2);
                    }
                }
        }
        int start = 0;
        for (int gi = 0; gi < (int)types.size(); gi++) {
            Group gr;
            gr.type = types[gi];
            const GroupMDP& md = mdps[gr.type];
            for (int i = 0; i < md.g; i++) gr.windows.push_back(start + i);
            start += md.g;
            for (int i = 0; i < md.m; i++) {
                Paper pp;
                for (int b = 0; b < md.g; b++) {
                    if (md.op[i] >> b & 1) pp.opaque |= 1ULL << gr.windows[b];
                    if (md.bl[i] >> b & 1) pp.black |= 1ULL << gr.windows[b];
                }
                paper[next] = pp;
                group_of[next] = groups.size();
                local_of[next] = i;
                gr.papers.push_back(next);
                generic_order.push_back(next);
                next++;
            }
            groups.push_back(gr);
        }
        // Column sizes: c_l proportional to (1 + slope * l), rounded to even numbers.
        int n_ded = K - next;
        std::vector<double> w(H);
        for (int l = 0; l < H; l++) w[l] = std::max(0.0, 1.0 + slope * l);
        double ws = std::accumulate(w.begin(), w.end(), 0.0);
        std::vector<int> csize(H);
        int tot = 0;
        for (int l = 0; l < H; l++) {
            csize[l] = std::max(2, 2 * (int)std::floor(n_ded * w[l] / ws / 2));
            tot += csize[l];
        }
        for (int l = H - 1; tot + 2 <= n_ded; l = (l + H - 1) % H) {
            csize[l] += 2;
            tot += 2;
        }
        while (tot > n_ded) {  // too many (all columns at the minimum size): shrink the largest
            int l = std::max_element(csize.begin(), csize.end()) - csize.begin();
            csize[l]--;
            tot--;
        }
        // Units: a dedicated paper serves one target, or a pair of close targets (holes where the
        // two differ, filled by the generic layer or by digging shallow columns). Pairs are taken
        // greedily by Hamming distance up to dmax, at most as many as needed to cover all targets.
        int dmax = env_int("HUB_DMAX", 22);
        int max_pairs = std::max(0, P - n_ded);
        std::vector<std::array<int, 3>> cand;  // (distance, u, v)
        for (int u = 0; u < P; u++)
            for (int v = u + 1; v < P; v++) {
                int d = __builtin_popcountll(A[u] ^ A[v]);
                if (d <= dmax) cand.push_back({d, u, v});
            }
        std::sort(cand.begin(), cand.end());
        std::vector<char> used(P, 0);
        std::vector<std::array<int, 2>> units;  // (u, v), v = -1 for a single
        for (auto [d, u, v] : cand) {
            if ((int)units.size() >= max_pairs) break;
            if (used[u] || used[v]) continue;
            used[u] = used[v] = 1;
            units.push_back({u, v});
        }
        std::vector<int> singles;
        for (int u = 0; u < P; u++) if (!used[u]) singles.push_back(u);
        std::shuffle(singles.begin(), singles.end(), rng);
        for (int i = 0; i < (int)singles.size() && (int)units.size() < n_ded; i++)
            units.push_back({singles[i], -1});
        std::shuffle(units.begin(), units.end(), rng);
        // Column assignment. A pair must agree at the handle of its column (its own handle cannot be
        // a hole). Every column first gets one unit of each color at its handle (so that any color
        // can be dug up there), then the columns are filled to their sizes, and each column is
        // ordered to alternate the colors as much as possible.
        auto color_at = [&](int x, int l) {  // color of unit x at handle l, -1 if a pair differs
            auto [u, v] = units[x];
            int c = A[u] >> handle[l] & 1;
            if (v >= 0 && (int)(A[v] >> handle[l] & 1) != c) return -1;
            return c;
        };
        std::vector<char> placed(units.size(), 0);
        std::vector<std::array<std::vector<int>, 2>> members(H);
        // Pairs are requested twice as often and pay the triangle holes of their column twice, so
        // they go to the deep columns (few holes) and single targets to the shallow ones.
        auto take = [&](int l, int c, bool pairs_first) {
            for (int pass = 0; pass < 2; pass++) {
                bool want_pair = (pass == 0) == pairs_first;
                for (int x = 0; x < (int)units.size(); x++) {
                    if (placed[x] || (units[x][1] >= 0) != want_pair) continue;
                    if (color_at(x, l) != c) continue;
                    placed[x] = 1;
                    members[l][c].push_back(x);
                    return true;
                }
            }
            return false;
        };
        for (int l = 0; l < H; l++) for (int c = 0; c < 2; c++) take(l, c, false);
        for (int l = H - 1; l >= 0; l--) {
            while ((int)(members[l][0].size() + members[l][1].size()) < csize[l]) {
                int c = members[l][0].size() <= members[l][1].size() ? 0 : 1;
                if (!take(l, c, true) && !take(l, 1 - c, true)) break;
            }
        }
        for (int x = 0; x < (int)units.size(); x++) {  // leftovers: the deepest column that fits
            if (placed[x]) continue;
            for (int l = H - 1; l >= 0; l--) {
                int c = color_at(x, l);
                if (c < 0) continue;
                placed[x] = 1;
                members[l][c].push_back(x);
                break;
            }
        }
        anneal_units(units, members, color_at);
        std::vector<int> dedicated_order;
        for (int l = 0; l < H; l++) {
            u64 base = gmask;
            for (int i = 0; i <= l; i++) base |= 1ULL << handle[i];
            auto& m0 = members[l][0];
            auto& m1 = members[l][1];
            size_t i0 = 0, i1 = 0;
            while (i0 < m0.size() || i1 < m1.size()) {
                // Alternate, spending the more numerous color when one runs ahead.
                bool use0 = i1 >= m1.size() || (i0 < m0.size() && (m0.size() - i0) >= (m1.size() - i1));
                int x = use0 ? m0[i0++] : m1[i1++];
                auto [u, v] = units[x];
                u64 opq = base;
                if (v >= 0) opq &= ~(A[u] ^ A[v]);
                paper[next] = {opq, A[u] & opq};
                col_of[next] = l;
                ded[u] = next;
                if (v >= 0) ded[v] = next;
                dedicated_order.push_back(next);
                next++;
            }
        }
        order = generic_order;
        order.insert(order.end(), dedicated_order.begin(), dedicated_order.end());
        for (int k = next; k < K; k++) order.push_back(k);  // all-hole leftovers
        // The judge starts from papers 0, 1, ..., K-1 top to bottom: renumber so that id = position.
        std::vector<int> new_id(K);
        for (int i = 0; i < K; i++) new_id[order[i]] = i;
        std::vector<Paper> p2(K);
        std::vector<int> c2(K), g2(K), l2(K);
        for (int k = 0; k < K; k++) {
            p2[new_id[k]] = paper[k];
            c2[new_id[k]] = col_of[k];
            g2[new_id[k]] = group_of[k];
            l2[new_id[k]] = local_of[k];
        }
        paper = p2;
        col_of = c2;
        group_of = g2;
        local_of = l2;
        for (int& d : ded) if (d >= 0) d = new_id[d];
        for (auto& gr : groups) for (int& x : gr.papers) x = new_id[x];
        std::iota(order.begin(), order.end(), 0);
        std::vector<std::string> rows(K);
        for (int k = 0; k < K; k++) {
            std::string s(N, '.');
            for (int j = 0; j < N; j++) {
                if (paper[k].opaque >> j & 1) s[j] = (paper[k].black >> j & 1) ? '1' : '0';
            }
            rows[k] = s;
        }
        return rows;
    }

    // Simulated annealing over the pairing of targets and the column of every unit, minimizing an
    // estimate of the total moves over all targets (each target requested equally often):
    //   holes at handles (deeper handles of the column, and for a pair the shallower handles where
    //   its two targets differ) cost kHandleHole each, holes in G (a pair's differences) kGHole each,
    //   and reaching a unit costs (column size - 1) / 2 digs on average.
    // A pair must agree at the handle of its column, and every column keeps at least one unit of
    // each color at its handle; unequal color counts in a column are penalized (no alternation).
    template <class ColorAt>
    void anneal_units(std::vector<std::array<int, 2>>& units,
                      std::vector<std::array<std::vector<int>, 2>>& members, ColorAt color_at) {
        const double kHandleHole = 0.51, kGHole = 0.45, kImbalance = env_double("HUB_IMB", 50.0);
        const int U = units.size();
        std::vector<int> col(U, -1);
        for (int l = 0; l < H; l++) for (int c = 0; c < 2; c++) for (int x : members[l][c]) col[x] = l;
        std::vector<u64> shallow(H + 1, 0);  // handles h_0..h_{l-1}
        for (int l = 0; l < H; l++) shallow[l + 1] = shallow[l] | 1ULL << handle[l];
        auto unit_cost = [&](int u, int v, int l) {  // holes cost of unit (u, v) in column l
            int targets = v >= 0 ? 2 : 1;
            double c = kHandleHole * (H - 1 - l);
            if (v >= 0) {
                u64 diff = A[u] ^ A[v];
                c += kGHole * __builtin_popcountll(diff & gmask) +
                     kHandleHole * __builtin_popcountll(diff & shallow[l]);
            }
            return targets * c;
        };
        std::vector<int> cnt0(H, 0), cnt1(H, 0), tgt(H, 0);
        for (int x = 0; x < U; x++) {
            if (col[x] < 0) continue;
            int c = color_at(x, col[x]);
            (c ? cnt1 : cnt0)[col[x]]++;
            tgt[col[x]] += units[x][1] >= 0 ? 2 : 1;
        }
        auto col_cost = [&](int l) {  // digs and imbalance of column l
            int n = cnt0[l] + cnt1[l];
            int imb = std::max(0, std::abs(cnt0[l] - cnt1[l]) - 1);
            double c = tgt[l] * (n - 1) * 0.5 + kImbalance * imb;
            if (cnt0[l] == 0 || cnt1[l] == 0) c += 1e6;
            return c;
        };
        auto total_cost = [&]() {
            double c = 0;
            for (int x = 0; x < U; x++) if (col[x] >= 0) c += unit_cost(units[x][0], units[x][1], col[x]);
            for (int l = 0; l < H; l++) c += col_cost(l);
            return c / P;
        };
        std::cerr << "model_cost_before = " << total_cost() << '\n';
        std::mt19937_64 rng(777);
        auto rnd = [&](int n) { return (int)(rng() % n); };
        const int iters = env_int("HUB_ANNEAL", 3000000);
        std::vector<int> env_types;
        {
            int mask = env_int("HUB_MOVES", 6 + 8);
            for (int t = 0; t < 4; t++) if (mask >> t & 1) env_types.push_back(t);
        }
        const double handle_swap_rate = env_double("HUB_HSWAP", 0.05);
        const double t0 = 3.0, t1 = 0.05;
        // Helper to apply a unit change: remove unit x from its column accounting, re-add.
        auto remove_unit = [&](int x) {
            int l = col[x], c = color_at(x, l);
            (c ? cnt1 : cnt0)[l]--;
            tgt[l] -= units[x][1] >= 0 ? 2 : 1;
        };
        auto add_unit = [&](int x) {
            int l = col[x], c = color_at(x, l);
            (c ? cnt1 : cnt0)[l]++;
            tgt[l] += units[x][1] >= 0 ? 2 : 1;
        };
        auto pairs_agree_in = [&](int l) {  // every pair of column l agrees at its handle
            for (int x = 0; x < U; x++) {
                if (col[x] != l || units[x][1] < 0) continue;
                if ((A[units[x][0]] ^ A[units[x][1]]) >> handle[l] & 1) return false;
            }
            return true;
        };
        auto recount = [&]() {
            std::fill(cnt0.begin(), cnt0.end(), 0);
            std::fill(cnt1.begin(), cnt1.end(), 0);
            std::fill(tgt.begin(), tgt.end(), 0);
            for (int x = 0; x < U; x++) if (col[x] >= 0) add_unit(x);
        };
        double cur_total = total_cost() * P;
        for (int it = 0; it < iters; it++) {
            double temp = t0 * std::pow(t1 / t0, (double)it / iters);
            if (handle_swap_rate > 0 && (rng() >> 11) * 0x1.0p-53 < handle_swap_rate) {
                // Swap the handle windows of two columns (changes colors, agreement, shallow sets).
                int a = rnd(H), b = rnd(H);
                if (a == b) continue;
                std::swap(handle[a], handle[b]);
                for (int l = 0; l < H; l++) shallow[l + 1] = shallow[l] | 1ULL << handle[l];
                bool ok = pairs_agree_in(a) && pairs_agree_in(b);
                double after = 1e18;
                if (ok) {
                    recount();
                    after = total_cost() * P;
                }
                double delta = after - cur_total;
                if (!ok || (delta > 0 && std::exp(-delta / temp) < (rng() >> 11) * 0x1.0p-53)) {
                    std::swap(handle[a], handle[b]);
                    for (int l = 0; l < H; l++) shallow[l + 1] = shallow[l] | 1ULL << handle[l];
                    recount();
                } else {
                    cur_total = after;
                }
                continue;
            }
            int type = env_types[rnd((int)env_types.size())];
            int x = rnd(U);
            if (col[x] < 0) continue;
            if (type == 3) {  // move two units of opposite colors from column l1 to column l2
                int l1 = col[x], l2 = rnd(H);
                if (l2 == l1 || cnt0[l1] + cnt1[l1] <= 2) continue;
                int cx = color_at(x, l1), y = -1;
                for (int tries = 0; tries < 8 && y < 0; tries++) {
                    int z = rnd(U);
                    if (z != x && col[z] == l1 && color_at(z, l1) == 1 - cx) y = z;
                }
                if (y < 0) continue;
                int c2x = color_at(x, l2), c2y = color_at(y, l2);
                if (c2x < 0 || c2y < 0 || c2x == c2y) continue;
                double before = unit_cost(units[x][0], units[x][1], l1) +
                                unit_cost(units[y][0], units[y][1], l1) + col_cost(l1) + col_cost(l2);
                remove_unit(x);
                remove_unit(y);
                col[x] = col[y] = l2;
                add_unit(x);
                add_unit(y);
                double after = unit_cost(units[x][0], units[x][1], l2) +
                               unit_cost(units[y][0], units[y][1], l2) + col_cost(l1) + col_cost(l2);
                double delta = after - before;
                if (delta > 0 && std::exp(-delta / temp) < (rng() >> 11) * 0x1.0p-53) {
                    remove_unit(x);
                    remove_unit(y);
                    col[x] = col[y] = l1;
                    add_unit(x);
                    add_unit(y);
                } else {
                    cur_total += delta;
                }
                continue;
            }
            if (type == 0) {  // move unit x to another column
                int l2 = rnd(H), l1 = col[x];
                if (l2 == l1 || color_at(x, l2) < 0) continue;
                double before = unit_cost(units[x][0], units[x][1], l1) + col_cost(l1) + col_cost(l2);
                remove_unit(x);
                col[x] = l2;
                add_unit(x);
                double after = unit_cost(units[x][0], units[x][1], l2) + col_cost(l1) + col_cost(l2);
                double delta = after - before;
                if (delta > 0 && std::exp(-delta / temp) < (rng() >> 11) * 0x1.0p-53) {
                    remove_unit(x);
                    col[x] = l1;
                    add_unit(x);
                } else {
                    cur_total += delta;
                }
            } else if (type == 1) {  // swap the columns of two units
                int y = rnd(U);
                if (y == x || col[y] < 0 || col[x] == col[y]) continue;
                int lx = col[x], ly = col[y];
                if (color_at(x, ly) < 0 || color_at(y, lx) < 0) continue;
                double before = unit_cost(units[x][0], units[x][1], lx) +
                                unit_cost(units[y][0], units[y][1], ly) + col_cost(lx) + col_cost(ly);
                remove_unit(x);
                remove_unit(y);
                col[x] = ly;
                col[y] = lx;
                add_unit(x);
                add_unit(y);
                double after = unit_cost(units[x][0], units[x][1], ly) +
                               unit_cost(units[y][0], units[y][1], lx) + col_cost(lx) + col_cost(ly);
                double delta = after - before;
                if (delta > 0 && std::exp(-delta / temp) < (rng() >> 11) * 0x1.0p-53) {
                    remove_unit(x);
                    remove_unit(y);
                    col[x] = lx;
                    col[y] = ly;
                    add_unit(x);
                    add_unit(y);
                } else {
                    cur_total += delta;
                }
            } else {  // exchange one target between two units (re-pairing), columns kept
                int y = rnd(U);
                if (y == x || col[y] < 0) continue;
                if (units[x][1] < 0) continue;  // x must be a pair
                int ix = rnd(2), iy = (units[y][1] >= 0) ? rnd(2) : 0;
                auto nx = units[x], ny = units[y];
                std::swap(nx[ix], ny[iy]);
                // Pairs must agree at their handle.
                auto agrees = [&](const std::array<int, 2>& un, int l) {
                    return un[1] < 0 || ((A[un[0]] ^ A[un[1]]) >> handle[l] & 1) == 0;
                };
                int lx = col[x], ly = col[y];
                if (!agrees(nx, lx) || !agrees(ny, ly)) continue;
                double before = unit_cost(units[x][0], units[x][1], lx) +
                                unit_cost(units[y][0], units[y][1], ly) + col_cost(lx) +
                                (lx != ly ? col_cost(ly) : 0);
                auto ox = units[x], oy = units[y];
                remove_unit(x);
                remove_unit(y);
                units[x] = nx;
                units[y] = ny;
                add_unit(x);
                add_unit(y);
                double after = unit_cost(nx[0], nx[1], lx) + unit_cost(ny[0], ny[1], ly) +
                               col_cost(lx) + (lx != ly ? col_cost(ly) : 0);
                double delta = after - before;
                if (delta > 0 && std::exp(-delta / temp) < (rng() >> 11) * 0x1.0p-53) {
                    remove_unit(x);
                    remove_unit(y);
                    units[x] = ox;
                    units[y] = oy;
                    add_unit(x);
                    add_unit(y);
                } else {
                    cur_total += delta;
                }
            }
        }
        std::cerr << "model_cost_after = " << total_cost() << '\n';
        {
            double dig = 0, hh = 0, gh = 0;
            for (int l = 0; l < H; l++) dig += tgt[l] * (cnt0[l] + cnt1[l] - 1) * 0.5;
            for (int x = 0; x < U; x++) {
                if (col[x] < 0) continue;
                auto [u, v] = units[x];
                int t = v >= 0 ? 2 : 1, l = col[x];
                hh += t * (H - 1 - l);
                if (v >= 0) {
                    u64 diff = A[u] ^ A[v];
                    hh += t * __builtin_popcountll(diff & shallow[l]);
                    gh += t * __builtin_popcountll(diff & gmask);
                }
            }
            std::cerr << "model_dig = " << dig / P << "\nmodel_handle_holes = " << hh / P << "\nmodel_g_holes = " << gh / P << '\n';
        }
        for (int l = 0; l < H; l++) members[l][0].clear(), members[l][1].clear();
        for (int x = 0; x < U; x++) {
            if (col[x] < 0) continue;
            members[col[x]][color_at(x, col[x])].push_back(x);
        }
    }

    int index_of(int k) const {
        for (int i = 0; i < K; i++) if (order[i] == k) return i;
        return -1;
    }
    bool visible(int k) const {
        u64 e = paper[k].opaque;
        for (int x : order) {
            if (x == k) return e != 0;
            e &= ~paper[x].opaque;
        }
        return false;
    }
    // Moves paper k so that d papers are above it.
    void move(int k, int d) {
#ifdef DEBUG_VIS
        if (!visible(k)) { std::cerr << "invisible move of " << k << '\n'; std::exit(1); }
#endif
        int i = index_of(k);
        order.erase(order.begin() + i);
        order.insert(order.begin() + d, k);
        ops.push_back({k, d});
    }
    void move_after(int k, int x) {
#ifdef DEBUG_VIS
        if (!visible(k)) { std::cerr << "invisible move of " << k << '\n'; std::exit(1); }
#endif
        int i = index_of(k);
        order.erase(order.begin() + i);
        int j = 0;
        while (order[j] != x) j++;
        order.insert(order.begin() + j + 1, k);
        ops.push_back({k, j + 1});
    }
    int column_top(int l) const {
        for (int k : order) if (col_of[k] == l && k != top_d) return k;
        return -1;
    }
    int column_bottom(int l) const {
        int last = -1;
        for (int k : order) if (col_of[k] == l && k != top_d) last = k;
        return last;
    }
    void dig(int l) {
        int t = column_top(l), b = column_bottom(l);
        if (t != b) move_after(t, b);
    }
    // Digs column l until its handle window shows color c (at most one full turn).
    void set_handle(int l, int c) {
        int hw = handle[l];
        int t0 = column_top(l);
        for (int it = 0; it < K; it++) {
            int t = column_top(l);
            if ((int)(paper[t].black >> hw & 1) == c) return;
            if (it > 0 && t == t0) return;
            dig(l);
        }
    }
    // Shows the colors of a on the windows of `care` in group gi, following the MDP policy.
    void set_group(int gi, u64 care_mask, u64 a) {
        const Group& gr = groups[gi];
        const GroupMDP& mdp = mdps[gr.type];
        int target = 0, care = 0;
        for (int b = 0; b < mdp.g; b++) {
            if (care_mask >> gr.windows[b] & 1) care |= 1 << b;
            if (a >> gr.windows[b] & 1) target |= 1 << b;
        }
        target &= care;
        if (!care) return;
        for (int step = 0; step < 64; step++) {
            std::array<std::int8_t, 8> p{};
            int t = 0;
            for (int k : order) if (group_of[k] == gi) p[t++] = local_of[k];
            int s = mdp.rank(p.data());
            int e = mdp.next_edge(care, target, s);
            if (e < 0) return;
            int k = gr.papers[mdp.adj_paper[e]];
            int np = mdp.adj_pos[e];
            // Place k so that exactly np papers of its group are above it.
            std::vector<int> rest;
            for (int x : order) if (group_of[x] == gi && x != k) rest.push_back(x);
            int i = index_of(k);
            order.erase(order.begin() + i);
            int d;
            if (np == 0) {
                d = 0;
                while (order[d] != rest[0]) d++;
            } else {
                d = 0;
                while (order[d] != rest[np - 1]) d++;
                d++;
            }
            order.insert(order.begin() + i, k);  // restore, then do the recorded move
            move(k, d);
        }
    }

    u64 display() const {
        u64 covered = 0, black = 0;
        for (int k : order) {
            black |= paper[k].black & ~covered;
            covered |= paper[k].opaque;
        }
        return black;
    }

    std::vector<std::pair<int, int>> process(int u) {
        ops.clear();
        if (top_d >= 0) {
            // Back to the bottom of its column: below the last paper of the generic layer and of
            // columns 0..l (the column may have no other member).
            int d = top_d, l = col_of[d];
            top_d = -1;
            int last = -1;
            for (int k : order) {
                if (k == d) continue;
                if (group_of[k] >= 0 || (col_of[k] >= 0 && col_of[k] <= l)) last = k;
            }
            move_after(d, last);
        }
        u64 all = gmask;
        for (int l = 0; l < H; l++) all |= 1ULL << handle[l];
        if (ded[u] >= 0) {
            int d = ded[u], l = col_of[d];
            u64 holes = all & ~paper[d].opaque;
            size_t before0 = ops.size();
            for (int gi = 0; gi < (int)groups.size(); gi++) set_group(gi, holes, A[u]);
            stat_gcare_moves += ops.size() - before0;
            stat_gcare_windows += __builtin_popcountll(holes & gmask);
            stat_hholes += __builtin_popcountll(holes & ~gmask);
            size_t before = ops.size();
            while (column_top(l) != d) dig(l);
            stat_dig += ops.size() - before;
            move(d, 0);
            top_d = d;
            before = ops.size();
            for (int l2 = 0; l2 < H; l2++)
                if (holes >> handle[l2] & 1) set_handle(l2, A[u] >> handle[l2] & 1);
            stat_tri += ops.size() - before;
        } else {
            for (int gi = 0; gi < (int)groups.size(); gi++) set_group(gi, all, A[u]);
            for (int l = 0; l < H; l++) set_handle(l, A[u] >> handle[l] & 1);
        }
        return ops;
    }
};

}  // namespace

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n, k, p, r;
    std::cin >> n >> k >> p >> r;
    std::vector<u64> A(p);
    for (auto& a : A) {
        std::string s;
        std::cin >> s;
        a = 0;
        for (int j = 0; j < n; j++) if (s[j] == '1') a |= 1ULL << j;
    }
    Solver solver(A);
    auto rows = solver.design();
    std::string out;
    for (auto& s : rows) out += s + '\n';
    std::cout << out << std::flush;
    long long total = 0, ded_req = 0, ded_moves = 0, wrong = 0;
    for (int t = 0; t < r; t++) {
        int u;
        std::cin >> u;
        if (u == -1) return 0;
        bool is_ded = solver.ded[u] >= 0;
        auto ops = solver.process(u);
        if (solver.display() != A[u]) wrong++;
        std::string o = std::to_string(ops.size()) + '\n';
        for (auto [kk, d] : ops) o += std::to_string(kk) + ' ' + std::to_string(d) + '\n';
        std::cout << o << std::flush;
        total += ops.size();
        if (is_ded) {
            ded_req++;
            ded_moves += ops.size();
        }
    }
    int n_ded = 0;
    for (int d : solver.ded) n_ded += d >= 0;
    std::cerr << "dedicated = " << n_ded << '\n';
    std::cerr << "ded_moves_per_req = " << (ded_req ? (double)ded_moves / ded_req : 0) << '\n';
    std::cerr << "gen_moves_per_req = " << (r - ded_req ? (double)(total - ded_moves) / (r - ded_req) : 0) << '\n';
    std::cerr << "self_wrong = " << wrong << '\n';
    std::cerr << "dig_per_ded = " << (ded_req ? (double)solver.stat_dig / ded_req : 0) << '\n';
    std::cerr << "tri_per_ded = " << (ded_req ? (double)solver.stat_tri / ded_req : 0) << '\n';
    std::cerr << "gcare_moves_per_ded = " << (double)solver.stat_gcare_moves / std::max(1LL, ded_req) << '\n';
    std::cerr << "gcare_windows_per_ded = " << (double)solver.stat_gcare_windows / std::max(1LL, ded_req) << '\n';
    std::cerr << "handle_holes_per_ded = " << (double)solver.stat_hholes / std::max(1LL, ded_req) << '\n';
    return 0;
}
