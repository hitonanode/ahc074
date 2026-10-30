// Hub2: solutions/hub with an MDP-optimized generic layer and configurable column sizes.
//
// Windows are split into G (generic windows) and H handle windows h_0..h_{H-1}.
//   - Generic layer (top of the stack): G is cut into groups of g windows. Each group has m papers
//     opaque only inside the group, with fixed local patterns (found offline by an exact
//     average-cost MDP search, see trial_log.md). Moves inside a group follow the optimal MDP policy
//     for a uniformly random target pattern, computed at startup by relative value iteration.
//     The layer always covers every G window.
//   - Dedicated papers D_u (one per chosen target u), grouped into H "columns". A paper of column l
//     is opaque on all G windows and on h_0..h_l (colors of A_u), and a hole on h_{l+1}..h_{H-1}.
//     Columns are stacked in order 0, 1, ..., H-1 below the generic layer, so the top paper of
//     column l is visible exactly at h_l, and every other cell of a dedicated paper is hidden.
// Request u with a dedicated paper (column l):
//   rotate column l until D_u is its top ("dig": top paper to the bottom of its column, which only
//   changes window h_l), move D_u to the very top (it shows A_u on G and h_0..h_l), then dig each
//   deeper column l' > l until its top shows A_u[h_l'] at h_l' (D_u is a hole there).
// Request u without one: set every group of the generic layer by its MDP policy, and every handle
//   window by digging its column.
// Before the next request, D_u goes back to the bottom of its column. Rotations and this return keep
// the cyclic order of every column, so a column whose colors at its handle alternate keeps
// alternating, and one dig flips its handle window.
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
    std::vector<std::vector<int>> next_edge;  // [target][state] edge to take, -1 = done

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

    // f[s] = min over paths s -> s' with disp(s') == target of (length + h[s']), by a multi-source
    // search on the reversed graph (unit edges, sources sorted by h).
    void shortest(int target, const std::vector<int>& rstart, const std::vector<int>& radj,
                  std::vector<double>& f, std::vector<std::pair<double, int>>& src,
                  std::vector<int>& queue, std::vector<char>& done) const {
        src.clear();
        for (int s = 0; s < S; s++) if (disp[s] == target) src.push_back({h[s], s});
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
                shortest(t, rstart, radj, f, src, queue, done);
                for (int s = 0; s < S; s++) nh[s] += f[s] / T;
            }
            double mx = -1e18, mn = 1e18;
            for (int s = 0; s < S; s++) {
                mx = std::max(mx, nh[s] - h[s]);
                mn = std::min(mn, nh[s] - h[s]);
            }
            double base = nh[0];
            for (int s = 0; s < S; s++) h[s] = 0.5 * h[s] + 0.5 * (nh[s] - base);
            if (mx - mn < 1e-7) break;
        }
        next_edge.assign(T, std::vector<int>(S, -1));
        for (int t = 0; t < T; t++) {
            shortest(t, rstart, radj, f, src, queue, done);
            for (int s = 0; s < S; s++) {
                int best = -1;
                double bv = (disp[s] == t) ? h[s] : 1e18;
                for (int e = adj_start[s]; e < adj_start[s + 1]; e++) {
                    if (f[adj_to[e]] + 1 < bv - 1e-9) {
                        bv = f[adj_to[e]] + 1;
                        best = e;
                    }
                }
                next_edge[t][s] = best;
            }
        }
    }
};

// Group structures found offline (window count, local patterns): see trial_log.md.
const std::vector<std::string> kGroup4 = {"1110", "..0.", "...1", "0110", ".0..", ".100"};

struct Group {
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
    GroupMDP mdp;
    std::vector<int> order;    // stack, top first
    int top_d = -1;            // dedicated paper lifted to the top, -1 if none
    std::vector<std::pair<int, int>> ops;

    explicit Solver(std::vector<u64> a) : A(std::move(a)) {}

    std::vector<std::string> design() {
        mdp.build(kGroup4);
        const int g = mdp.g, m = mdp.m;
        H = env_int("HUB_H", 32);
        while ((N - H) % g) H++;  // G must split into whole groups
        double slope = env_double("HUB_SLOPE", 0.3);
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
        for (int start = 0; start < N - H; start += g) {
            Group gr;
            for (int i = 0; i < g; i++) gr.windows.push_back(start + i);
            for (int i = 0; i < m; i++) {
                Paper pp;
                for (int b = 0; b < g; b++) {
                    if (mdp.op[i] >> b & 1) pp.opaque |= 1ULL << gr.windows[b];
                    if (mdp.bl[i] >> b & 1) pp.black |= 1ULL << gr.windows[b];
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
        std::vector<int> pool(P);
        std::iota(pool.begin(), pool.end(), 0);
        std::shuffle(pool.begin(), pool.end(), rng);
        std::vector<char> used(P, 0);
        std::vector<int> dedicated_order;
        for (int l = 0; l < H; l++) {
            int hw = handle[l];
            u64 opq = gmask;
            for (int i = 0; i <= l; i++) opq |= 1ULL << handle[i];
            for (int i = 0; i < csize[l]; i++) {
                int want = i % 2, pick = -1;
                for (int u : pool) {
                    if (!used[u] && (int)(A[u] >> hw & 1) == want) { pick = u; break; }
                }
                if (pick < 0) continue;
                used[pick] = 1;
                paper[next] = {opq, A[pick] & opq};
                col_of[next] = l;
                ded[pick] = next;
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
    // Sets the generic group gi to the pattern of target u by following the MDP policy.
    void set_group(int gi, u64 a) {
        const Group& gr = groups[gi];
        int target = 0;
        for (int b = 0; b < mdp.g; b++) if (a >> gr.windows[b] & 1) target |= 1 << b;
        for (int step = 0; step < 64; step++) {
            std::array<std::int8_t, 8> p{};
            int t = 0;
            for (int k : order) if (group_of[k] == gi) p[t++] = local_of[k];
            int s = mdp.rank(p.data());
            int e = mdp.next_edge[target][s];
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
            int d = top_d;
            top_d = -1;
            move_after(d, column_bottom(col_of[d]));
        }
        if (ded[u] >= 0) {
            int d = ded[u], l = col_of[d];
            while (column_top(l) != d) dig(l);
            move(d, 0);
            top_d = d;
            for (int l2 = l + 1; l2 < H; l2++) set_handle(l2, A[u] >> handle[l2] & 1);
        } else {
            for (int gi = 0; gi < (int)groups.size(); gi++) set_group(gi, A[u]);
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
    return 0;
}
