// gen-cb2: solutions/gen-cb with H = 36 handles, a repair pass for inconsistent pairs after the
// annealing, and an (unused by default) annealing move of G windows between blocks.
// gen-cb: solutions/hub8 with the generic layer replaced by complementary blocks.
//
// Windows are split into G (generic windows) and H handle windows h_0..h_{H-1}.
//   - Generic layer (top of the stack): G is cut into blocks S_b of about CB_S windows. Each block
//     has exactly two papers, opaque only on S_b: F_b with colors Y_b and F'_b with the complement.
//     The upper one of the two decides what S_b shows (Y_b or ~Y_b); one move (the upper one below
//     the other) flips the whole block. The layer always covers every G window.
//   - Dedicated papers, grouped into H "columns" as in hub8. A paper of column l is opaque on all G
//     windows and on h_0..h_l, and a hole on h_{l+1}..h_{H-1} (the "triangle"). A paper serves one
//     target u, or a pair u, v: then it is also a hole where A_u and A_v differ.
// A pair (u, v) can only be served if it is "consistent" with every block it touches: on the
// windows D of S_b where u and v differ, A_u equals Y_b or ~Y_b (then A_v is the other one), so
// the block shows A_u on D in one orientation and A_v in the other. A touched block then costs one
// move half of the time, whatever the number of differing windows. The generic layer cannot show
// arbitrary patterns, so every target needs a unit (pair or single); the annealing (pairing,
// columns, the colors Y_b) keeps every pair consistent with a large penalty.
// Request u (paper D, column l): flip the blocks touched by the holes of D whose orientation is
// wrong, rotate column l until D is its top ("dig"), move D to the very top, then dig every column
// whose handle is a hole of D until its top shows the color of A_u there. Before the next request,
// D goes back to the top or the bottom of its column (hub7).
#include <algorithm>
#include <array>
#include <chrono>
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

struct Block {
    u64 mask = 0;   // windows of the block
    u64 y = 0;      // colors Y_b (black windows, subset of mask)
    int pa = -1;    // paper showing Y_b
    int pb = -1;    // paper showing ~Y_b
};

struct Solver {
    std::vector<u64> A;
    int H = 0;
    std::vector<int> handle;
    u64 gmask = 0;
    std::vector<Paper> paper;
    std::vector<int> col_of;    // column of a dedicated paper, -1 otherwise
    std::vector<int> block_of;  // block of a generic paper, -1 otherwise
    std::vector<int> ded;       // ded[u] = dedicated paper of target u, -1 if none
    std::vector<Block> blocks;
    std::vector<int> order;     // stack, top first
    int top_d = -1;             // dedicated paper lifted to the top, -1 if none
    std::vector<std::pair<int, int>> ops;
    long long stat_dig = 0, stat_tri = 0, stat_flip = 0, stat_touched = 0, stat_gholes = 0, stat_hholes = 0;

    explicit Solver(std::vector<u64> a) : A(std::move(a)) {}

    // Number of blocks touched by the windows `diff` where a pair differs, and number of those
    // blocks where the pair is not consistent (A_u neither Y_b nor ~Y_b on the differing windows).
    std::pair<int, int> touch(u64 au, u64 diff) const {
        int t = 0, bad = 0;
        for (const auto& b : blocks) {
            u64 d = diff & b.mask;
            if (!d) continue;
            t++;
            u64 x = (au ^ b.y) & d;
            if (x != 0 && x != d) bad++;
        }
        return {t, bad};
    }

    std::vector<std::string> design() {
        H = env_int("HUB_H", 36);
        double slope = env_double("HUB_SLOPE", 1.0);
        std::mt19937_64 rng(12345);
        for (int l = 0; l < H; l++) handle.push_back(N - H + l);
        int G = N - H;
        for (int j = 0; j < G; j++) gmask |= 1ULL << j;
        paper.assign(K, Paper{});
        col_of.assign(K, -1);
        block_of.assign(K, -1);
        ded.assign(P, -1);
        // Blocks: G windows cut into nb contiguous blocks of nearly equal sizes.
        int s = env_int("CB_S", 4);
        int nb = std::max(1, (G + s / 2) / s);
        {
            int start = 0;
            for (int b = 0; b < nb; b++) {
                int sz = G / nb + (b < G % nb ? 1 : 0);
                Block bl;
                for (int j = start; j < start + sz; j++) bl.mask |= 1ULL << j;
                bl.y = rng() & bl.mask;
                start += sz;
                blocks.push_back(bl);
            }
        }
        int next = 2 * nb;  // generic papers are created after the annealing (Y_b changes)
        int n_ded = K - next;
        // Column sizes: c_l proportional to (1 + slope * l), rounded to even numbers.
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
        while (tot > n_ded) {
            int l = std::max_element(csize.begin(), csize.end()) - csize.begin();
            csize[l]--;
            tot--;
        }
        // Units: every target must be covered (the generic layer cannot show arbitrary patterns),
        // so exactly P - n_ded pairs. Greedy by (inconsistent blocks, distance), then the leftover
        // singles are paired arbitrarily; the annealing repairs inconsistent pairs.
        int need_pairs = std::max(0, P - n_ded);
        std::vector<std::array<int, 3>> cand;  // (key, u, v)
        for (int u = 0; u < P; u++)
            for (int v = u + 1; v < P; v++) {
                int d = __builtin_popcountll(A[u] ^ A[v]);
                auto [t, bad] = touch(A[u], A[u] ^ A[v]);
                cand.push_back({bad * 1000 + d, u, v});
            }
        std::sort(cand.begin(), cand.end());
        std::vector<char> used(P, 0);
        std::vector<std::array<int, 2>> units;  // (u, v), v = -1 for a single
        for (auto [key, u, v] : cand) {
            if ((int)units.size() >= need_pairs) break;
            if (used[u] || used[v]) continue;
            used[u] = used[v] = 1;
            units.push_back({u, v});
        }
        std::vector<int> singles;
        for (int u = 0; u < P; u++) if (!used[u]) singles.push_back(u);
        std::shuffle(singles.begin(), singles.end(), rng);
        while ((int)(units.size() + singles.size()) > n_ded && singles.size() >= 2) {
            int u = singles.back();
            singles.pop_back();
            int v = singles.back();
            singles.pop_back();
            units.push_back({u, v});
        }
        for (int i = 0; i < (int)singles.size() && (int)units.size() < n_ded; i++)
            units.push_back({singles[i], -1});
        std::shuffle(units.begin(), units.end(), rng);
        // Column assignment (hub8). A pair must agree at the handle of its column.
        auto color_at = [&](int x, int l) {  // color of unit x at handle l, -1 if a pair differs
            auto [u, v] = units[x];
            int c = A[u] >> handle[l] & 1;
            if (v >= 0 && (int)(A[v] >> handle[l] & 1) != c) return -1;
            return c;
        };
        std::vector<char> placed(units.size(), 0);
        std::vector<std::array<std::vector<int>, 2>> members(H);
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
        // Generic papers (after the annealing fixed Y_b).
        std::vector<int> generic_order;
        for (int b = 0; b < nb; b++) {
            int ia = 2 * b, ib = 2 * b + 1;
            paper[ia] = {blocks[b].mask, blocks[b].y};
            paper[ib] = {blocks[b].mask, blocks[b].mask & ~blocks[b].y};
            block_of[ia] = block_of[ib] = b;
            blocks[b].pa = ia;
            blocks[b].pb = ib;
            generic_order.push_back(ia);
            generic_order.push_back(ib);
        }
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
        std::vector<int> c2(K), b2(K);
        for (int k = 0; k < K; k++) {
            p2[new_id[k]] = paper[k];
            c2[new_id[k]] = col_of[k];
            b2[new_id[k]] = block_of[k];
        }
        paper = p2;
        col_of = c2;
        block_of = b2;
        for (int& d : ded) if (d >= 0) d = new_id[d];
        for (auto& bl : blocks) {
            bl.pa = new_id[bl.pa];
            bl.pb = new_id[bl.pb];
        }
        std::iota(order.begin(), order.end(), 0);
        std::vector<std::string> rows(K);
        for (int k = 0; k < K; k++) {
            std::string str(N, '.');
            for (int j = 0; j < N; j++) {
                if (paper[k].opaque >> j & 1) str[j] = (paper[k].black >> j & 1) ? '1' : '0';
            }
            rows[k] = str;
        }
        if (env_int("CB_DIAG", 0)) {
            // Consistent partners per target (any partner, ignoring handles).
            int zero = 0;
            long long tot_c = 0;
            for (int u = 0; u < P; u++) {
                int c = 0;
                for (int v = 0; v < P; v++)
                    if (v != u && touch(A[u], A[u] ^ A[v]).second == 0) c++;
                tot_c += c;
                zero += c == 0;
            }
            std::cerr << "diag_partners_mean = " << (double)tot_c / P << "\ndiag_no_partner = " << zero << '\n';
        }
        int uncovered = 0, bad_pairs = 0;
        for (int u = 0; u < P; u++) uncovered += ded[u] < 0;
        for (auto [u, v] : units)
            if (v >= 0 && touch(A[u], A[u] ^ A[v]).second > 0) bad_pairs++;
        std::cerr << "blocks = " << nb << "\nuncovered = " << uncovered << "\ninconsistent_pairs = " << bad_pairs << '\n';
        return rows;
    }

    // Simulated annealing over the pairing of targets, the column of every unit, the handle order
    // and the block colors Y_b, minimizing an estimate of the total moves over all targets:
    //   holes at handles (deeper handles of the column, and for a pair the shallower handles where
    //   its two targets differ) cost kHandleHole each, a block touched by a pair costs kBlock per
    //   request (a flip half of the time) and kIncons if the pair is inconsistent with it, and
    //   reaching a unit costs (column size - 1) / 2 digs on average.
    template <class ColorAt>
    void anneal_units(std::vector<std::array<int, 2>>& units,
                      std::vector<std::array<std::vector<int>, 2>>& members, ColorAt color_at) {
        const double kHandleHole = env_double("HUB_KH", 0.51), kImbalance = env_double("HUB_IMB", 50.0);
        const double kBlock = env_double("CB_KB", 0.5), kIncons = env_double("CB_KI", 30.0);
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
                auto [t, bad] = touch(A[u], diff);
                c += kHandleHole * __builtin_popcountll(diff & shallow[l]) + kBlock * t + kIncons * bad;
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
        auto unif = [&]() { return (rng() >> 11) * 0x1.0p-53; };
        const int iters = env_int("HUB_ANNEAL", 0);  // 0: time-bounded
        std::vector<int> env_types;
        {
            int mask = env_int("HUB_MOVES", 6 + 8);
            for (int t = 0; t < 4; t++) if (mask >> t & 1) env_types.push_back(t);
        }
        const double handle_swap_rate = env_double("HUB_HSWAP", 0.05);
        const double yflip_rate = env_double("CB_YFLIP", 0.05);
        const double wmove_rate = env_double("CB_WMOVE", 0.0);  // not effective (seed 100-195), off
        const int min_block = env_int("CB_MINB", 2);
        const double t0 = env_double("HUB_T0", 3.0), t1 = 0.05;
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
        const double t_begin = elapsed_sec(), t_end = env_double("HUB_TL", 1.2);
        double progress = 0, temp = t0;
        for (int it = 0;; it++) {
            if (iters > 0) {
                if (it >= iters) break;
                progress = (double)it / iters;
            } else if ((it & 255) == 0) {
                progress = (elapsed_sec() - t_begin) / std::max(1e-9, t_end - t_begin);
                if (progress >= 1) break;
            }
            temp = t0 * std::pow(t1 / t0, progress);
            double r = unif();
            if (r < yflip_rate) {
                // Flip one color of a block (changes which pairs are consistent with it).
                int b = rnd((int)blocks.size());
                u64 m = blocks[b].mask;
                int j = rnd(__builtin_popcountll(m));
                u64 bit = m;
                for (int i = 0; i < j; i++) bit &= bit - 1;
                bit &= -bit;
                blocks[b].y ^= bit;
                double after = total_cost() * P;
                double delta = after - cur_total;
                if (delta > 0 && std::exp(-delta / temp) < unif()) blocks[b].y ^= bit;
                else cur_total = after;
                continue;
            }
            if (r < yflip_rate + wmove_rate) {
                // Move a G window to another block, or swap two windows of two blocks (each window
                // keeps its color in Y). Changes which pairs touch and are consistent with a block.
                int nb = blocks.size();
                if (nb < 2) continue;
                int j1 = rnd(N - H);
                u64 bit1 = 1ULL << j1;
                int b1 = 0;
                while (!(blocks[b1].mask & bit1)) b1++;
                int b2 = rnd(nb - 1);
                if (b2 >= b1) b2++;
                auto saved1 = blocks[b1], saved2 = blocks[b2];
                auto take_out = [&](int b, u64 bit) {
                    u64 y = blocks[b].y & bit;
                    blocks[b].mask &= ~bit;
                    blocks[b].y &= ~bit;
                    return y;
                };
                if (rnd(2) == 0) {  // swap with a random window of b2
                    int cnt2 = __builtin_popcountll(blocks[b2].mask);
                    int k = rnd(cnt2);
                    u64 bit2 = blocks[b2].mask;
                    for (int i = 0; i < k; i++) bit2 &= bit2 - 1;
                    bit2 &= -bit2;
                    u64 y1 = take_out(b1, bit1), y2 = take_out(b2, bit2);
                    blocks[b1].mask |= bit2;
                    blocks[b1].y |= y2 ? bit2 : 0;
                    blocks[b2].mask |= bit1;
                    blocks[b2].y |= y1 ? bit1 : 0;
                } else {  // move
                    if (__builtin_popcountll(blocks[b1].mask) <= min_block) continue;
                    u64 y1 = take_out(b1, bit1);
                    blocks[b2].mask |= bit1;
                    blocks[b2].y |= y1;
                }
                double after = total_cost() * P;
                double delta = after - cur_total;
                if (delta > 0 && std::exp(-delta / temp) < unif()) {
                    blocks[b1] = saved1;
                    blocks[b2] = saved2;
                } else {
                    cur_total = after;
                }
                continue;
            }
            if (r < yflip_rate + wmove_rate + handle_swap_rate) {
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
                if (!ok || (delta > 0 && std::exp(-delta / temp) < unif())) {
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
                if (delta > 0 && std::exp(-delta / temp) < unif()) {
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
                if (delta > 0 && std::exp(-delta / temp) < unif()) {
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
                if (delta > 0 && std::exp(-delta / temp) < unif()) {
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
                if (delta > 0 && std::exp(-delta / temp) < unif()) {
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
        // Repair: an inconsistent pair cannot be served at all, so exchange one of its targets with
        // a target of another unit whenever both new units are consistent and agree at their
        // handles, taking the exchange of the least cost (digs and column balance included; a
        // column must keep both colors at its handle).
        int repaired = 0;
        for (int x = 0; x < U && env_int("CB_REPAIR", 1); x++) {
            if (units[x][1] < 0 || touch(A[units[x][0]], A[units[x][0]] ^ A[units[x][1]]).second == 0) continue;
            auto ok_unit = [&](const std::array<int, 2>& un, int l) {
                if (un[1] < 0) return true;
                u64 diff = A[un[0]] ^ A[un[1]];
                return ((diff >> handle[l]) & 1) == 0 && touch(A[un[0]], diff).second == 0;
            };
            double best = 1e5;
            int by = -1, bix = -1, biy = -1;
            for (int y = 0; y < U; y++) {
                if (y == x) continue;
                for (int ix = 0; ix < 2; ix++)
                    for (int iy = 0; iy < (units[y][1] >= 0 ? 2 : 1); iy++) {
                        auto nx = units[x], ny = units[y];
                        std::swap(nx[ix], ny[iy]);
                        if (!ok_unit(nx, col[x]) || !ok_unit(ny, col[y])) continue;
                        auto ox = units[x], oy = units[y];
                        remove_unit(x);
                        remove_unit(y);
                        units[x] = nx;
                        units[y] = ny;
                        add_unit(x);
                        add_unit(y);
                        double c = unit_cost(nx[0], nx[1], col[x]) + unit_cost(ny[0], ny[1], col[y]) +
                                   col_cost(col[x]) + (col[y] != col[x] ? col_cost(col[y]) : 0);
                        remove_unit(x);
                        remove_unit(y);
                        units[x] = ox;
                        units[y] = oy;
                        add_unit(x);
                        add_unit(y);
                        if (c < best) best = c, by = y, bix = ix, biy = iy;
                    }
            }
            if (by < 0) continue;
            remove_unit(x);
            remove_unit(by);
            std::swap(units[x][bix], units[by][biy]);
            add_unit(x);
            add_unit(by);
            repaired++;
        }
        std::cerr << "repaired_pairs = " << repaired << '\n';
        std::cerr << "model_cost_after = " << total_cost() << '\n';
        std::cerr << "anneal_end_sec = " << elapsed_sec() << '\n';
        {
            double dig = 0, hh = 0, gt = 0;
            for (int l = 0; l < H; l++) dig += tgt[l] * (cnt0[l] + cnt1[l] - 1) * 0.5;
            for (int x = 0; x < U; x++) {
                if (col[x] < 0) continue;
                auto [u, v] = units[x];
                int t = v >= 0 ? 2 : 1, l = col[x];
                hh += t * (H - 1 - l);
                if (v >= 0) {
                    u64 diff = A[u] ^ A[v];
                    hh += t * __builtin_popcountll(diff & shallow[l]);
                    gt += t * touch(A[u], diff).first;
                }
            }
            std::cerr << "model_dig = " << dig / P << "\nmodel_handle_holes = " << hh / P << "\nmodel_touched_blocks = " << gt / P << '\n';
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
    // Orientation of block b: 0 if F_b (Y_b) is above F'_b, else 1.
    int orientation(int b) const {
        for (int k : order) {
            if (k == blocks[b].pa) return 0;
            if (k == blocks[b].pb) return 1;
        }
        return 0;
    }
    void set_block(int b, int o) {
        if (orientation(b) == o) return;
        int top = o ? blocks[b].pa : blocks[b].pb, other = o ? blocks[b].pb : blocks[b].pa;
        move_after(top, other);
        stat_flip++;
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
            // column. The new target is known, so take the end that leaves the better top (hub7).
            int d = top_d, l = col_of[d];
            top_d = -1;
            std::vector<int> mem;  // column l top to bottom, without d
            for (int k : order) if (k != d && col_of[k] == l) mem.push_back(k);
            bool at_top = false;
            if (!mem.empty()) {
                int want_paper = ded[u];
                int hw = handle[l];
                if (want_paper >= 0 && col_of[want_paper] == l && want_paper != d) {
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
                    if (block_of[k] >= 0 || (col_of[k] >= 0 && col_of[k] <= l)) last = k;
                }
                move_after(d, last);
            }
        }
        u64 all = gmask;
        for (int l = 0; l < H; l++) all |= 1ULL << handle[l];
        if (ded[u] >= 0) {
            int d = ded[u], l = col_of[d];
            u64 holes = all & ~paper[d].opaque;
            for (int b = 0; b < (int)blocks.size(); b++) {
                u64 dm = holes & blocks[b].mask;
                if (!dm) continue;
                stat_touched++;
                // Y_b matches A_u on the holes -> orientation 0; otherwise 1 (consistent pairs
                // match ~Y_b there; an inconsistent pair takes the closer one and is wrong).
                u64 x = (A[u] ^ blocks[b].y) & dm;
                int o = __builtin_popcountll(x) * 2 <= __builtin_popcountll(dm) ? 0 : 1;
                set_block(b, o);
            }
            stat_gholes += __builtin_popcountll(holes & gmask);
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
            // No unit (should not happen): the closer orientation per block, then every handle.
            for (int b = 0; b < (int)blocks.size(); b++) {
                u64 x = (A[u] ^ blocks[b].y) & blocks[b].mask;
                set_block(b, __builtin_popcountll(x) * 2 <= __builtin_popcountll(blocks[b].mask) ? 0 : 1);
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
        if (is_ded) {
            ded_req++;
            ded_moves += ops.size();
        }
    }
    int n_ded = 0;
    for (int d : solver.ded) n_ded += d >= 0;
    std::cerr << "dedicated = " << n_ded << '\n';
    std::cerr << "ded_moves_per_req = " << (ded_req ? (double)ded_moves / ded_req : 0) << '\n';
    std::cerr << "self_wrong = " << wrong << '\n';
    std::cerr << "dig_per_ded = " << (ded_req ? (double)solver.stat_dig / ded_req : 0) << '\n';
    std::cerr << "tri_per_ded = " << (ded_req ? (double)solver.stat_tri / ded_req : 0) << '\n';
    std::cerr << "flips_per_ded = " << (double)solver.stat_flip / std::max(1LL, ded_req) << '\n';
    std::cerr << "touched_blocks_per_ded = " << (double)solver.stat_touched / std::max(1LL, ded_req) << '\n';
    std::cerr << "g_holes_per_ded = " << (double)solver.stat_gholes / std::max(1LL, ded_req) << '\n';
    std::cerr << "handle_holes_per_ded = " << (double)solver.stat_hholes / std::max(1LL, ded_req) << '\n';
    return 0;
}
