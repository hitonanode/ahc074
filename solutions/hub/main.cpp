// Hub: dedicated papers kept hidden under a generic layer, reachable through "handle" windows.
//
// Windows are split into G (generic windows) and H handle windows h_0..h_{H-1}.
//   - Generic layer (top of the stack): for every G window j, two papers opaque only at j (white
//     and black), like solutions/bit-pair. It always covers every G window.
//   - Dedicated papers D_u (one per chosen target u), grouped into H "columns". A paper of column l
//     is opaque on all G windows and on h_0..h_l (colors of A_u), and a hole on h_{l+1}..h_{H-1}.
//     Columns are stacked in order 0, 1, ..., H-1 below the generic layer, so the top paper of
//     column l is visible exactly at h_l (columns 0..l-1 are holes there, deeper ones are below),
//     and every other cell of a dedicated paper is hidden.
// Request u with a dedicated paper (column l):
//   rotate column l until D_u is its top ("dig": top paper to the bottom of its column, which only
//   changes window h_l), move D_u to the very top (it shows A_u on G and h_0..h_l), then dig each
//   deeper column l' > l until its top shows A_u[h_l'] at h_l' (D_u is a hole there).
// Request u without one: set every G window with the generic layer, and every handle window by
//   digging its column.
// Before the next request, D_u goes back to the bottom of its column. Rotations and this return keep
// the cyclic order of every column, so a column whose colors at its handle alternate keeps
// alternating, and one dig flips its handle window.
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <fstream>
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

struct Solver {
    std::vector<u64> A;  // A[v] bit j = window j is black
    int H;
    std::vector<int> handle;            // handle[l] = window of column l
    u64 gmask = 0;                      // G windows
    std::vector<Paper> paper;
    std::vector<int> col_of;            // column of a dedicated paper, -1 otherwise
    std::vector<int> ded;               // ded[u] = dedicated paper of target u, -1 if none
    std::vector<std::array<int, 2>> pair_of;  // generic papers of a G window (white, black)
    std::vector<int> order;             // stack, top first
    int top_d = -1;                     // dedicated paper currently on top of everything
    std::vector<std::pair<int, int>> ops;

    explicit Solver(std::vector<u64> a) : A(std::move(a)) {}

    std::vector<std::string> design() {
        H = env_int("HUB_H", 16);
        std::mt19937_64 rng(12345);
        // Handle windows: the last H windows (any choice works; refined later).
        for (int l = 0; l < H; l++) handle.push_back(N - H + l);
        for (int j = 0; j < N - H; j++) gmask |= 1ULL << j;
        paper.assign(K, Paper{});
        col_of.assign(K, -1);
        ded.assign(P, -1);
        pair_of.assign(N, {-1, -1});
        int next = 0;
        // Generic layer: majority color on top (the most likely color of the first request).
        std::vector<int> generic_order;
        for (int j = 0; j < N; j++) {
            if (!(gmask >> j & 1)) continue;
            int ones = 0;
            for (u64 a : A) ones += a >> j & 1;
            int top_color = 2 * ones > P ? 1 : 0;
            for (int c = 0; c < 2; c++) {
                paper[next] = {1ULL << j, c ? 1ULL << j : 0};
                pair_of[j][c] = next;
                next++;
            }
            generic_order.push_back(pair_of[j][top_color]);
            generic_order.push_back(pair_of[j][1 - top_color]);
        }
        // Dedicated papers: distribute the remaining papers over the columns; each column alternates
        // the color at its handle window.
        int n_ded = K - next;
        std::vector<int> pool(P);
        std::iota(pool.begin(), pool.end(), 0);
        std::shuffle(pool.begin(), pool.end(), rng);
        std::vector<char> used(P, 0);
        std::vector<int> dedicated_order;
        // Even column sizes keep the alternation cyclic.
        int base_c = n_ded / H;
        if (base_c % 2) base_c--;
        int extra_cols = (n_ded - base_c * H) / 2;
        for (int l = 0; l < H; l++) {
            int c = base_c + (l < extra_cols ? 2 : 0);
            int h = handle[l];
            u64 opq = gmask;
            for (int i = 0; i <= l; i++) opq |= 1ULL << handle[i];
            for (int i = 0; i < c; i++) {
                int want = i % 2;
                int pick = -1;
                for (int u : pool) {
                    if (!used[u] && (int)(A[u] >> h & 1) == want) { pick = u; break; }
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
        {
            std::vector<int> new_id(K);
            for (int i = 0; i < K; i++) new_id[order[i]] = i;
            std::vector<Paper> p2(K);
            std::vector<int> c2(K);
            for (int k = 0; k < K; k++) { p2[new_id[k]] = paper[k]; c2[new_id[k]] = col_of[k]; }
            paper = p2;
            col_of = c2;
            for (int& d : ded) if (d >= 0) d = new_id[d];
            for (auto& pr : pair_of) for (int& x : pr) if (x >= 0) x = new_id[x];
            std::iota(order.begin(), order.end(), 0);
        }
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
    // Moves paper k so that d papers are above it.
    bool visible(int k) const {
        u64 e = paper[k].opaque;
        for (int x : order) {
            if (x == k) return e != 0;
            e &= ~paper[x].opaque;
        }
        return false;
    }
    void check(int k) const {
#ifdef DEBUG_VIS
        if (!visible(k)) { std::cerr << "invisible move of " << k << " col " << col_of[k] << " top_d " << top_d << '\n'; std::exit(1); }
#endif
    }
    void move(int k, int d) {
        check(k);
        int i = index_of(k);
        order.erase(order.begin() + i);
        order.insert(order.begin() + d, k);
        ops.push_back({k, d});
    }
    void move_after(int k, int x) {
        check(k);
        int i = index_of(k);
        order.erase(order.begin() + i);
        int j = 0;
        while (order[j] != x) j++;
        order.insert(order.begin() + j + 1, k);
        ops.push_back({k, j + 1});
    }
    // Top and bottom member of column l (ignoring the dedicated paper lifted to the top).
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
    // Digs column l until its handle window shows color c (gives up after a full turn).
    void set_handle(int l, int c) {
        int h = handle[l];
        for (int it = 0; it < K; it++) {
            int t = column_top(l);
            if ((int)(paper[t].black >> h & 1) == c) return;
            if (it > 0 && t == column_top(l) && column_top(l) == column_bottom(l)) return;
            dig(l);
            if (it > 64) return;
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
            for (int j = 0; j < N; j++) {
                if (!(gmask >> j & 1)) continue;
                int want = A[u] >> j & 1;
                int z = pair_of[j][0], o = pair_of[j][1];
                int iz = index_of(z), io = index_of(o);
                int cur = iz < io ? 0 : 1;
                if (cur != want) move_after(cur ? o : z, cur ? z : o);
            }
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
        if (is_ded) { ded_req++; ded_moves += ops.size(); }
    }
    std::cerr << "moves = " << total << '\n';
    std::cerr << "ded_requests = " << ded_req << '\n';
    std::cerr << "ded_moves_per_req = " << (ded_req ? (double)ded_moves / ded_req : 0) << '\n';
    std::cerr << "gen_moves_per_req = " << (r - ded_req ? (double)(total - ded_moves) / (r - ded_req) : 0) << '\n';
    std::cerr << "self_wrong = " << wrong << '\n';
    return 0;
}
