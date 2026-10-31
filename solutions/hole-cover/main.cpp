// hole-cover: solutions/hub8 with the generic layer replaced by a lean "2-cover" layer, which frees
// papers for dedicated use (fewer pairs).
//
// Why: with every target covered by a dedicated paper, the generic layer is only used for the
// holes of pair papers inside G (about 9 of the 30 windows of G per pair request). hub8 spent 35
// papers on MDP groups built for full random targets. Here every window of G is covered by exactly
// two generic papers of opposite colors, so the window shows the color of the higher one:
// generic papers = vertices, windows of G = edges of a graph (default: the dodecahedron, 20
// vertices, 30 edges, girth 5). A partial target is a set of constraints "paper X above paper Y".
// Fixing a violated constraint moves one of its two papers; one move can fix several violated
// constraints that share a paper, so a hole costs about as much as with the MDP groups (~0.45
// moves) while 15 more papers become dedicated papers (84 pairs instead of 99).
// A constraint set whose digraph has a cycle cannot be shown, so pairs are restricted to target
// pairs whose differences in G give an acyclic digraph (checked once for all target pairs), and
// every target gets a dedicated paper (pairs of any distance are allowed; the annealing repairs).
//
// Hub8 (unchanged here): dedicated papers hidden under the generic layer in H "columns". A paper of
// column l is opaque on G and on handles h_0..h_l, a hole on h_{l+1}..h_{H-1} (the "triangle"),
// and a hole where the two targets of a pair differ. Request u: fix the generic layer on the holes
// of D = ded[u] inside G, dig column l until D is on top, lift D to the very top, then dig every
// column whose handle is a hole of D until it shows A_u there. Before the next request D goes back
// to the top or the bottom of its column (whichever suits the new target). The pairing and the
// columns are optimized by simulated annealing on an estimate of the moves.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

using u64 = std::uint64_t;

namespace {

constexpr int N = 64, K = 192, P = 256;

const auto kStartTime = std::chrono::steady_clock::now();
double elapsed_sec() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - kStartTime).count();
}

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

// Graph of the generic layer: vertices are generic papers, edges are windows of G.
// ends[e][c] = the vertex showing color c at the window of edge e.
struct CoverGraph {
    int m = 0;
    std::vector<std::array<int, 2>> ends;
};

// kind 0: dodecahedron = generalized Petersen graph GP(10, 2) (20 vertices, 30 edges, girth 5).
// kind 1: icosahedron (12 vertices, 30 edges, 5-regular, girth 3).
// The color orientation of every edge is random.
CoverGraph make_cover_graph(int kind, std::mt19937_64& rng) {
    CoverGraph g;
    std::vector<std::array<int, 2>> e;
    if (kind == 1) {
        g.m = 12;  // 0 top, 1..5 upper ring, 6..10 lower ring, 11 bottom
        for (int i = 0; i < 5; i++) {
            int ui = 1 + i, un = 1 + (i + 1) % 5, li = 6 + i, ln = 6 + (i + 1) % 5;
            e.push_back({0, ui});
            e.push_back({ui, un});
            e.push_back({ui, li});
            e.push_back({ui, ln});
            e.push_back({li, ln});
            e.push_back({11, li});
        }
    } else {
        g.m = 20;
        for (int i = 0; i < 10; i++) {
            e.push_back({i, (i + 1) % 10});
            e.push_back({i, 10 + i});
            e.push_back({10 + i, 10 + (i + 2) % 10});
        }
    }
    for (auto& x : e)
        if (rng() & 1) std::swap(x[0], x[1]);
    g.ends = e;
    return g;
}

// Exact search used by Solver::fix_cover: IDA* over moves of generic papers. A move takes a
// visible paper (above one of its neighbors) to a slot given by its relative order to its
// neighbors, which is all that matters for the windows of its edges and for whether the
// neighbors are visible. The heuristic is the minimum vertex cover of the violated constraints:
// each violated constraint needs one of its two papers moved, and a move moves one paper.
struct CoverIDA {
    int m = 0;
    const std::vector<std::vector<int>>* nbr = nullptr;
    std::vector<std::array<int, 2>> cons;  // (hi, lo): hi must be above lo
    std::vector<int> ord, ps;              // order of the vertices (top first), position of each
    std::vector<std::pair<int, int>> path;  // (vertex, index after its removal)
    long long nodes = 0, cap = 0;

    int vc_rec(const int* v, int nv, int idx, u64 mask, int sz, int best) const {
        while (idx < nv && ((mask >> cons[v[idx]][0] & 1) || (mask >> cons[v[idx]][1] & 1))) idx++;
        if (idx == nv) return sz;
        if (sz + 1 >= best) return best;
        int b = vc_rec(v, nv, idx + 1, mask | 1ULL << cons[v[idx]][0], sz + 1, best);
        return vc_rec(v, nv, idx + 1, mask | 1ULL << cons[v[idx]][1], sz + 1, b);
    }
    int min_vc() const {
        int v[64], nv = 0;
        for (int i = 0; i < (int)cons.size(); i++)
            if (ps[cons[i][0]] > ps[cons[i][1]]) v[nv++] = i;
        return nv ? vc_rec(v, nv, 0, 0, 0, 64) : 0;
    }
    bool visible(int x) const {
        for (int y : (*nbr)[x]) if (ps[x] < ps[y]) return true;
        return false;
    }
    void put(int x, int idx) {  // remove x and insert it at index idx of the remaining order
        ord.erase(ord.begin() + ps[x]);
        ord.insert(ord.begin() + idx, x);
        for (int i = 0; i < m; i++) ps[ord[i]] = i;
    }
    // Moves of two non-adjacent papers commute (each slot is relative to the paper's own
    // neighbors), so after a move of `last` an independent paper x is only tried if x > last
    // (lexicographic normal form of the move sequence); the same paper never moves twice in a row.
    bool dfs(int g, int bound, int last = -1) {
        if (++nodes > cap) return false;
        int h = min_vc();
        if (h == 0) return true;
        if (g + h > bound) return false;
        // Endpoints of violated constraints first, then the other papers.
        std::vector<int> cand;
        std::vector<char> inc(m, 0);
        for (auto& c : cons)
            if (ps[c[0]] > ps[c[1]]) {
                for (int x : {c[0], c[1]})
                    if (!inc[x]) { inc[x] = 1; cand.push_back(x); }
            }
        // With no slack left (g + h == bound) every move must lower the cover, which only a
        // paper of a violated constraint can do; with slack, any paper may help (visibility).
        if (g + h < bound)
            for (int x = 0; x < m; x++) if (!inc[x]) cand.push_back(x);
        std::vector<int> saved = ord;
        for (int x : cand) {
            if (x == last) continue;
            if (last >= 0 && x < last) {
                bool adj = false;
                for (int y : (*nbr)[x]) adj |= y == last;
                if (!adj) continue;
            }
            if (!visible(x)) continue;
            int p0 = ps[x], above = 0;
            std::vector<int> q;
            for (int y : (*nbr)[x]) {
                q.push_back(ps[y] - (ps[y] > p0));
                above += ps[y] < p0;
            }
            std::sort(q.begin(), q.end());
            for (int k = 0; k <= (int)q.size(); k++) {
                if (k == above) continue;  // same relative order: no change
                if (k > 0 && k < (int)q.size() && q[k] == q[k - 1]) continue;
                int idx = k == 0 ? 0 : q[k - 1] + 1;
                put(x, idx);
                path.push_back({x, idx});
                if (dfs(g + 1, bound, x)) return true;
                path.pop_back();
                ord = saved;
                for (int i = 0; i < m; i++) ps[ord[i]] = i;
            }
        }
        return false;
    }
};

struct Solver {
    std::vector<u64> A;
    int H = 0;
    std::vector<int> handle;
    u64 gmask = 0;
    std::vector<Paper> paper;
    std::vector<int> col_of;   // column of a dedicated paper, -1 otherwise
    std::vector<int> gen_of;   // vertex of a generic paper, -1 otherwise
    std::vector<int> gvert;    // gvert[v] = paper of vertex v
    std::vector<int> ded;      // ded[u] = dedicated paper of target u, -1 if none
    CoverGraph graph;
    std::vector<int> win_edge;  // window of G -> edge, -1 for handles
    std::vector<int> edge_win;
    std::vector<std::vector<int>> nbr;  // neighbors of each vertex
    std::vector<std::uint8_t> pair_ok;  // [u * P + v]: differences of u, v in G give an acyclic digraph
    std::vector<int> order;    // stack, top first
    int top_d = -1;            // dedicated paper lifted to the top, -1 if none
    std::vector<std::pair<int, int>> ops;
    long long stat_dig = 0, stat_tri = 0, stat_gcare_moves = 0, stat_gcare_windows = 0, stat_hholes = 0;
    long long stat_fallback = 0, stat_cover_calls = 0, stat_infeasible = 0, stat_ida_nodes = 0, stat_ida_fail = 0;

    explicit Solver(std::vector<u64> a) : A(std::move(a)) {}

    // True if the constraints of showing `a` on the windows of `care` (inside G) are acyclic.
    bool acyclic(u64 care, u64 a) const {
        int m = graph.m;
        std::vector<int> indeg(m, 0);
        std::vector<std::vector<int>> adj(m);
        for (u64 x = care & gmask; x; x &= x - 1) {
            int w = __builtin_ctzll(x), e = win_edge[w], c = a >> w & 1;
            adj[graph.ends[e][c]].push_back(graph.ends[e][1 - c]);
            indeg[graph.ends[e][1 - c]]++;
        }
        std::vector<int> st;
        for (int v = 0; v < m; v++) if (!indeg[v]) st.push_back(v);
        int seen = 0;
        while (!st.empty()) {
            int v = st.back();
            st.pop_back();
            seen++;
            for (int y : adj[v]) if (--indeg[y] == 0) st.push_back(y);
        }
        return seen == m;
    }

    std::vector<std::string> design() {
        H = env_int("HUB_H", 34);
        double slope = env_double("HUB_SLOPE", 1.0);
        std::mt19937_64 rng(12345);
        for (int l = 0; l < H; l++) handle.push_back(N - H + l);
        for (int j = 0; j < N - H; j++) gmask |= 1ULL << j;
        paper.assign(K, Paper{});
        col_of.assign(K, -1);
        gen_of.assign(K, -1);
        ded.assign(P, -1);
        // Generic layer: one paper per vertex, opaque on the windows of its edges.
        graph = make_cover_graph(env_int("HUB_GRAPH", 0), rng);
        int G = N - H;
        if ((int)graph.ends.size() != G) {
            std::cerr << "graph edges != G\n";
            std::exit(1);
        }
        win_edge.assign(N, -1);
        edge_win.assign(G, -1);
        {
            std::vector<int> perm(G);
            std::iota(perm.begin(), perm.end(), 0);
            std::shuffle(perm.begin(), perm.end(), rng);
            for (int w = 0; w < G; w++) {
                win_edge[w] = perm[w];
                edge_win[perm[w]] = w;
            }
        }
        int next = 0;
        std::vector<int> generic_order;
        gvert.assign(graph.m, -1);
        for (int v = 0; v < graph.m; v++) {
            Paper pp;
            for (int e = 0; e < G; e++)
                for (int c = 0; c < 2; c++)
                    if (graph.ends[e][c] == v) {
                        pp.opaque |= 1ULL << edge_win[e];
                        if (c) pp.black |= 1ULL << edge_win[e];
                    }
            paper[next] = pp;
            gen_of[next] = v;
            gvert[v] = next;
            generic_order.push_back(next);
            next++;
        }
        nbr.assign(graph.m, {});
        for (auto& e : graph.ends) {
            nbr[e[0]].push_back(e[1]);
            nbr[e[1]].push_back(e[0]);
        }
        pair_ok.assign(P * P, 0);
        int n_ok = 0;
        for (int u = 0; u < P; u++)
            for (int v = u + 1; v < P; v++) {
                bool ok = acyclic(A[u] ^ A[v], A[u]);
                pair_ok[u * P + v] = pair_ok[v * P + u] = ok;
                n_ok += ok;
            }
        std::cerr << "pair_ok_frac = " << (double)n_ok / (P * (P - 1) / 2) << '\n';
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
        // Units: a dedicated paper serves one target, or a pair of targets (holes where the two
        // differ). Pairs are taken greedily by Hamming distance among the allowed pairs, as many
        // as needed to cover all targets.
        int dmax = env_int("HUB_DMAX", 64);
        int max_pairs = std::max(0, P - n_ded);
        std::vector<std::array<int, 3>> cand;  // (distance, u, v)
        for (int u = 0; u < P; u++)
            for (int v = u + 1; v < P; v++) {
                int d = __builtin_popcountll(A[u] ^ A[v]);
                if (d <= dmax && pair_ok[u * P + v]) cand.push_back({d, u, v});
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
        std::vector<int> c2(K), g2(K);
        for (int k = 0; k < K; k++) {
            p2[new_id[k]] = paper[k];
            c2[new_id[k]] = col_of[k];
            g2[new_id[k]] = gen_of[k];
        }
        paper = p2;
        col_of = c2;
        gen_of = g2;
        for (int& d : ded) if (d >= 0) d = new_id[d];
        for (int& x : gvert) x = new_id[x];
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
    // A pair must agree at the handle of its column, its differences in G must be showable (acyclic
    // constraints, pair_ok), and every column keeps at least one unit of each color at its handle;
    // unequal color counts in a column are penalized (no alternation).
    template <class ColorAt>
    void anneal_units(std::vector<std::array<int, 2>>& units,
                      std::vector<std::array<std::vector<int>, 2>>& members, ColorAt color_at) {
        const double kHandleHole = env_double("HUB_KH", 0.51), kGHole = env_double("HUB_KG", 0.45), kImbalance = env_double("HUB_IMB", 50.0);
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
        const int iters = env_int("HUB_ANNEAL", 0);  // 0: time-bounded
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
        // Runs until the time limit (seconds from the program start) unless an iteration count is
        // given; the temperature decays geometrically with the elapsed fraction.
        const double t_begin = elapsed_sec(), t_end = env_double("HUB_TL", 1.0);
        double progress = 0, temp = t0;
        long long n_iter = 0;
        for (int it = 0;; it++) {
            n_iter = it;
            if (iters > 0) {
                if (it >= iters) break;
                progress = (double)it / iters;
            } else if ((it & 255) == 0) {
                progress = (elapsed_sec() - t_begin) / std::max(1e-9, t_end - t_begin);
                if (progress >= 1) break;
            }
            temp = t0 * std::pow(t1 / t0, progress);
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
                // Pairs must agree at their handle and be showable in G.
                auto agrees = [&](const std::array<int, 2>& un, int l) {
                    if (un[1] < 0) return true;
                    if ((A[un[0]] ^ A[un[1]]) >> handle[l] & 1) return false;
                    return pair_ok[un[0] * P + un[1]] != 0;
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
        std::cerr << "anneal_iters = " << n_iter << '\n';
        std::cerr << "model_cost_after = " << total_cost() << '\n';
        std::cerr << "anneal_end_sec = " << elapsed_sec() << '\n';
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

    // Shows `a` on the windows of `care` inside G. Needs the generic papers to be the top m papers
    // of the stack (true before the dedicated paper is lifted). Every window is a constraint
    // "hi above lo" between the two generic papers of its edge. Search: vertex covers of the
    // violated constraints (smallest first, then with one extra paper), each checked for a final
    // order (the kept papers keep their relative order; the constraints must stay acyclic) and for
    // a move order in which every moved paper is visible when it moves. Fallback (always works for
    // acyclic constraints, at most m - 1 moves): repeatedly move the top generic paper into the
    // bottom part, which is kept sorted in a fixed final order.
    void fix_cover(u64 care, u64 a) {
        const int m = graph.m;
        care &= gmask;
        if (!care) return;
        stat_cover_calls++;
        std::vector<int> cur(m), pos(m);
        for (int i = 0; i < m; i++) cur[i] = gen_of[order[i]];
        for (int i = 0; i < m; i++) pos[cur[i]] = i;
        std::vector<std::array<int, 2>> cons;  // (hi, lo)
        for (u64 x = care; x; x &= x - 1) {
            int w = __builtin_ctzll(x), e = win_edge[w], c = a >> w & 1;
            cons.push_back({graph.ends[e][c], graph.ends[e][1 - c]});
        }
        std::vector<int> viol;
        for (int i = 0; i < (int)cons.size(); i++) if (pos[cons[i][0]] > pos[cons[i][1]]) viol.push_back(i);
        if (viol.empty()) return;
        // Final order for a moved set: kept papers chained in the current order + constraints,
        // topologically sorted preferring the current order. Empty if cyclic.
        auto final_order = [&](u64 moved) {
            std::vector<int> indeg(m, 0);
            std::vector<std::vector<int>> adj(m);
            int prev = -1;
            for (int v : cur) {
                if (moved >> v & 1) continue;
                if (prev >= 0) { adj[prev].push_back(v); indeg[v]++; }
                prev = v;
            }
            for (auto& c : cons) { adj[c[0]].push_back(c[1]); indeg[c[1]]++; }
            std::vector<int> out;
            std::vector<char> taken(m, 0);
            for (int step = 0; step < m; step++) {
                int pick = -1;
                for (int v : cur) if (!taken[v] && indeg[v] == 0) { pick = v; break; }
                if (pick < 0) return std::vector<int>();
                taken[pick] = 1;
                out.push_back(pick);
                for (int y : adj[pick]) indeg[y]--;
            }
            return out;
        };
        // Visibility of vertex x in the order `sim`: above the other end of one of its edges.
        auto vis_in = [&](const std::vector<int>& sim, int x) {
            std::vector<int> p(m);
            for (int i = 0; i < m; i++) p[sim[i]] = i;
            for (auto& e : graph.ends) {
                if (e[0] == x && p[x] < p[e[1]]) return true;
                if (e[1] == x && p[x] < p[e[0]]) return true;
            }
            return false;
        };
        // Tries to realize the moved set; on success performs the moves and returns true.
        auto attempt = [&](u64 moved) {
            std::vector<int> fin = final_order(moved);
            if (fin.empty()) return false;
            std::vector<int> fpos(m);
            for (int i = 0; i < m; i++) fpos[fin[i]] = i;
            std::vector<int> M;
            for (int v = 0; v < m; v++) if (moved >> v & 1) M.push_back(v);
            std::vector<std::pair<int, int>> plan;  // (vertex, index in the generic order)
            int perms = 0;
            do {
                if (++perms > 720) break;
                std::vector<int> sim = cur;
                std::vector<char> placed(m, 1);
                for (int v : M) placed[v] = 0;
                plan.clear();
                bool ok = true;
                for (int x : M) {
                    if (!vis_in(sim, x)) { ok = false; break; }
                    sim.erase(std::find(sim.begin(), sim.end(), x));
                    int ins = sim.size();
                    for (int i = 0; i < (int)sim.size(); i++)
                        if (placed[sim[i]] && fpos[sim[i]] > fpos[x]) { ins = i; break; }
                    sim.insert(sim.begin() + ins, x);
                    placed[x] = 1;
                    plan.push_back({x, ins});
                }
                if (ok) {
                    for (auto [x, ins] : plan) move(gvert[x], ins);
                    return true;
                }
            } while (std::next_permutation(M.begin(), M.end()));
            return false;
        };
        {
            CoverIDA ida;
            ida.m = m;
            ida.nbr = &nbr;
            ida.cons = cons;
            ida.cap = env_int("HUB_IDA_CAP", 30000);
            int h0 = -1;
            for (int extra = 0; extra <= 2; extra++) {
                ida.ord = cur;
                ida.ps = pos;
                ida.path.clear();
                if (h0 < 0) h0 = ida.min_vc();
                if (ida.dfs(0, h0 + extra)) {
                    stat_ida_nodes += ida.nodes;
                    for (auto [x, idx] : ida.path) move(gvert[x], idx);
                    return;
                }
                if (ida.nodes > ida.cap) break;
            }
            stat_ida_nodes += ida.nodes;
            stat_ida_fail++;
        }
        // Vertex covers of the violated constraints, by size.
        std::vector<u64> covers;
        const int kMaxCover = 7;
        std::function<void(int, u64)> rec = [&](int idx, u64 mask) {
            while (idx < (int)viol.size() &&
                   ((mask >> cons[viol[idx]][0] & 1) || (mask >> cons[viol[idx]][1] & 1)))
                idx++;
            if (idx == (int)viol.size()) {
                covers.push_back(mask);
                return;
            }
            if (__builtin_popcountll(mask) >= kMaxCover || covers.size() > 4000) return;
            rec(idx + 1, mask | 1ULL << cons[viol[idx]][0]);
            rec(idx + 1, mask | 1ULL << cons[viol[idx]][1]);
        };
        rec(0, 0);
        std::sort(covers.begin(), covers.end(), [](u64 x, u64 y) {
            int a = __builtin_popcountll(x), b = __builtin_popcountll(y);
            return a != b ? a < b : x < y;
        });
        covers.erase(std::unique(covers.begin(), covers.end()), covers.end());
        int tries = 0;
        for (size_t i = 0; i < covers.size(); i++) {
            int sz = __builtin_popcountll(covers[i]);
            // Before trying covers of size sz + 1, try those of size sz with one extra paper.
            if (++tries > 600) break;
            if (attempt(covers[i])) return;
            bool last_of_size = i + 1 == covers.size() || __builtin_popcountll(covers[i + 1]) != sz;
            if (last_of_size) {
                for (size_t j = 0; j <= i && tries <= 600; j++) {
                    if (__builtin_popcountll(covers[j]) != sz) continue;
                    for (int v = 0; v < m && tries <= 600; v++) {
                        if (covers[j] >> v & 1) continue;
                        // An extra paper only helps if a smaller-size option was infeasible.
                        u64 mk = covers[j] | 1ULL << v;
                        if (i + 1 < covers.size() && __builtin_popcountll(covers[i + 1]) <= sz + 1 &&
                            std::find(covers.begin(), covers.end(), mk) != covers.end())
                            continue;
                        ++tries;
                        if (attempt(mk)) return;
                    }
                }
            }
        }
        // Fallback: final order from the constraints alone (all papers movable).
        stat_fallback++;
        std::vector<int> fin = final_order((1ULL << m) - 1);
        if (fin.empty()) {  // cyclic: cannot be shown; keep the current order
            stat_infeasible++;
            return;
        }
        std::vector<int> fpos(m);
        for (int i = 0; i < m; i++) fpos[fin[i]] = i;
        auto satisfied = [&]() {
            std::vector<int> p(m);
            for (int i = 0; i < m; i++) p[gen_of[order[i]]] = i;
            for (auto& c : cons) if (p[c[0]] > p[c[1]]) return false;
            return true;
        };
        // The sorted part: the longest suffix of the current order that is increasing in fin.
        for (int step = 0; step < m && !satisfied(); step++) {
            std::vector<int> g(m);
            for (int i = 0; i < m; i++) g[i] = gen_of[order[i]];
            int s = m - 1;
            while (s > 0 && fpos[g[s - 1]] < fpos[g[s]]) s--;
            if (s == 0) break;  // fully sorted
            int x = g[0];        // the top paper is always visible
            // Insert x into the sorted suffix g[s..m-1] (indices shift by one after removal).
            int ins = m - 1;
            for (int i = s; i < m; i++)
                if (fpos[g[i]] > fpos[x]) { ins = i - 1; break; }
            move(gvert[x], ins);
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
            // Back into its column, at the bottom or at the top: both keep the cyclic order of the
            // column. The new target is known, so take the end that leaves the better top: the paper
            // to dig for if it is in this column, else the color the new target needs at this
            // handle (if its paper has a hole there).
            int d = top_d, l = col_of[d];
            top_d = -1;
            std::vector<int> mem;  // column l top to bottom, without d
            for (int k : order) if (k != d && col_of[k] == l) mem.push_back(k);
            bool at_top = false;
            if (!mem.empty()) {
                int want_paper = ded[u];
                int hw = handle[l];
                if (want_paper >= 0 && col_of[want_paper] == l && want_paper != d) {
                    // digs: bottom -> index in mem; top -> index + 1
                    at_top = false;
                } else if (want_paper == d) {
                    at_top = true;
                } else {
                    bool hole = want_paper < 0 || !(paper[want_paper].opaque >> hw & 1);
                    if (hole) {
                        int c = A[u] >> hw & 1;
                        bool top_ok = (int)(paper[mem[0]].black >> hw & 1) == c;
                        bool d_ok = (int)(paper[d].black >> hw & 1) == c;
                        at_top = !top_ok && d_ok;
                    }
                }
            }
            if (at_top) {
                // Just above the current top of the column.
                int i = index_of(d);
                order.erase(order.begin() + i);
                int j = 0;
                while (order[j] != mem[0]) j++;
                order.insert(order.begin() + i, d);
                move(d, j);
            } else {
                // Below the last paper of the generic layer and of columns 0..l.
                int last = -1;
                for (int k : order) {
                    if (k == d) continue;
                    if (gen_of[k] >= 0 || (col_of[k] >= 0 && col_of[k] <= l)) last = k;
                }
                move_after(d, last);
            }
        }
        u64 all = gmask;
        for (int l = 0; l < H; l++) all |= 1ULL << handle[l];
        if (ded[u] >= 0) {
            int d = ded[u], l = col_of[d];
            u64 holes = all & ~paper[d].opaque;
            size_t before0 = ops.size();
            fix_cover(holes, A[u]);
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
            fix_cover(gmask, A[u]);
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
    std::cerr << "cover_fallback = " << solver.stat_fallback << '\n';
    std::cerr << "cover_infeasible = " << solver.stat_infeasible << '\n';
    std::cerr << "ida_nodes_per_call = " << (double)solver.stat_ida_nodes / std::max(1LL, solver.stat_cover_calls) << '\n';
    std::cerr << "ida_fail = " << solver.stat_ida_fail << '\n';
    std::cerr << "total_sec = " << elapsed_sec() << '\n';
    return 0;
}
