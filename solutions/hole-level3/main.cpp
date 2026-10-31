// hole-level3: solutions/hole-level2 whose fillers are chosen before D is lifted, when every
// column top is visible: a paper of a column c shallower than D whose handle D covers can still
// cover the shallow holes of a pair paper D in h_{c'}..h_c (it is a hole at D's handle, so it
// never hides D). Fillers whose interval reaches D's own handle are placed after the lift.
// Papers left out of their column are charged 0.8 move in the plan cost (they are often re-used
// instead of returned), and old fillers that are harmless for the new target (they do not hide its
// column and show its colors on the holes they cover) may stay where they are (fret_mode 4). A plan
// is kept only if every paper left out stays visible once the lifted paper is set aside.
// hole-level2:solutions/hole-level where the previous lifted paper may itself become a leveled
// filler for the new target (plan option ret_mode 3) instead of going back to its column: it has
// to leave the top anyway, so it costs one move less than a filler taken from a column. Likewise
// a filler of the previous request may move straight to a new level (fret_mode 3).
// hole-level: solutions/search-bf2 whose fillers may also be inserted deeper in the stack, just
// above the top of column c' (the "level"): there a filler X of column c shows only on the handles
// h_{c'}..h_c (every paper of columns 0..c'-1 is a hole there), so it only has to match A_u on
// that suffix of the holes of D. The level is taken just past the deepest handle where X has the
// wrong color, which turns many near misses into fillers. A filler is placed below every filler
// of a smaller or equal level; one placed above a deeper filler must not reach its handles.
// search-bf2: solutions/gen-bf2 with the moves of every request chosen by a search over plans
// (solutions/search-ops): each combination of the plan options (return of the previous paper at the
// top or the bottom of its column, fillers or not, keeping the lifted paper for its pair partner)
// is simulated on a copy of the state and the one with the fewest moves is kept. Fillers: after
// the lifted paper D, a paper near the top of a column whose colors match A_u on several handle
// holes of D is moved just below the generic layer, where it covers those holes in one move
// (see choose_filler).
// gen-bf2: solutions/gen-bf whose base paper may also move up (turning off the flip papers it
// passes in one move), when that leaves fewer flip papers to turn off one by one.
// gen-bf: solutions/gen-cb2 whose blocks share one base paper. The generic layer is a base paper F
// (colors Y on all G windows) and one flip paper F_b per block (colors ~Y_b on S_b only): block b
// shows ~Y_b iff F_b is above F. A flip paper above F is visible and is turned off by moving it just
// below F; a flip paper below F is hidden, so blocks are turned on together by moving F just below
// the deepest flip paper to turn on (which also turns on the flip papers passed; touched blocks that
// must stay off are turned off again). nb + 1 papers instead of 2 nb, for about the same moves.
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
    int pf = -1;    // flip paper (~Y_b on the block)
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
    int base_paper = -1;        // base paper F (Y on all G windows)
    std::vector<int> order;     // stack, top first
    int top_d = -1;             // dedicated paper lifted to the top, -1 if none
    // Fillers: column papers moved just below the generic layer to cover handle holes of the lifted
    // paper (see choose_filler). pred >= 0: taken from below the column top, goes back below pred.
    struct Filler {
        int paper, pred;
        int lvl = 0, hi = 0;  // shows on the handles h_lvl..h_hi (hi = its column)
    };
    std::vector<Filler> fillers;
    bool is_filler(int k) const {
        for (auto& f : fillers) if (f.paper == k) return true;
        return false;
    }
    std::vector<std::pair<int, int>> ops;

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
        int next = nb + 1;  // generic papers are created after the annealing (Y_b changes)
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
        {
            u64 y = 0;
            for (auto& bl : blocks) y |= bl.y;
            paper[0] = {gmask, y};
            block_of[0] = nb;  // the base belongs to no block (any value >= 0 marks a generic paper)
            base_paper = 0;
            generic_order.push_back(0);
            for (int b = 0; b < nb; b++) {
                paper[1 + b] = {blocks[b].mask, blocks[b].mask & ~blocks[b].y};
                block_of[1 + b] = b;
                blocks[b].pf = 1 + b;
                generic_order.push_back(1 + b);
            }
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
        for (auto& bl : blocks) bl.pf = new_id[bl.pf];
        base_paper = new_id[base_paper];
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
        const double t_begin = elapsed_sec(), t_end = env_double("HUB_TL", 1.1);
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
    // Moves paper k so that d papers are above it. While plans are simulated (check_vis), a move of
    // an invisible paper marks the plan invalid instead of being an error.
    bool check_vis = false, invalid = false;
    void move(int k, int d) {
        if (check_vis && !visible(k)) invalid = true;
#ifdef DEBUG_VIS
        if (!visible(k)) { std::cerr << "invisible move of " << k << '\n'; std::exit(1); }
#endif
        int i = index_of(k);
        order.erase(order.begin() + i);
        order.insert(order.begin() + d, k);
        ops.push_back({k, d});
    }
    void move_after(int k, int x) {
        if (check_vis && !visible(k)) invalid = true;
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
    // Papers of column l that are in place (not lifted to the top, not used as a filler).
    bool in_column(int k, int l) const { return col_of[k] == l && k != top_d && !is_filler(k); }
    int column_top(int l) const {
        for (int k : order) if (in_column(k, l)) return k;
        return -1;
    }
    int column_bottom(int l) const {
        int last = -1;
        for (int k : order) if (in_column(k, l)) last = k;
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
    // Orientation of block b: 1 if its flip paper is above the base paper (~Y_b shown), else 0.
    int orientation(int b) const {
        for (int k : order) {
            if (k == blocks[b].pf) return 1;
            if (k == base_paper) return 0;
        }
        return 0;
    }
    // Sets block b to orientation want[b] for every b with want[b] >= 0 (others are free).
    void set_blocks(const std::vector<int>& want) {
        int nb = blocks.size();
        // One move of the base, to just below the deepest flip paper that must be on (or to the
        // very top if none must be on), or no base move if every flip paper that must be on is
        // already above the base: whichever leaves fewer flip papers to turn off one by one. Moving
        // the base up turns off, in one move, every flip paper it passes.
        int bpos = index_of(base_paper);
        int pmin = -1, pmin_b = -1;  // position of the deepest flip paper that must be on
        bool base_visible = false;
        for (int b = 0; b < nb; b++) {
            int pos = index_of(blocks[b].pf);
            if (pos > bpos) base_visible = true;
            if (want[b] == 1 && pos > pmin) pmin = pos, pmin_b = b;
        }
        auto offs_above = [&](int pos) {
            int c = 0;
            for (int b = 0; b < nb; b++)
                if (want[b] == 0 && index_of(blocks[b].pf) < pos) c++;
            return c;
        };
        bool move_base = true;
        if (bpos > pmin) move_base = base_visible && 1 + offs_above(pmin + 1) < offs_above(bpos);
        if (move_base) {
            if (pmin_b >= 0) move_after(base_paper, blocks[pmin_b].pf);
            else move(base_paper, 0);
        }
        // Turn off one by one: just below the base.
        for (int b = 0; b < nb; b++) {
            if (want[b] != 0 || orientation(b) == 0) continue;
            move_after(blocks[b].pf, base_paper);
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

    // Digs set_handle(l, c) would spend (without moving anything).
    int handle_fix_cost(int l, int c) const {
        int hw = handle[l];
        int i = 0;
        for (int k : order) {
            if (!in_column(k, l)) continue;
            if ((int)(paper[k].black >> hw & 1) == c) return i;
            i++;
        }
        return 0;
    }

    // Returns the out-of-place paper x (the lifted paper or a filler) to its column, at the top
    // (mode 2) or at the bottom (mode 1); both keep the cyclic order of the column. Mode 0 is the
    // hub7 rule: take the end that leaves the better top for target u. A filler taken from below
    // the column top goes back just below its cyclic predecessor instead.
    void return_paper(int x, int u, int mode) {
        int l = col_of[x];
        if (x == top_d) top_d = -1;
        for (size_t i = 0; i < fillers.size(); i++) {
            if (fillers[i].paper != x) continue;
            int pred = fillers[i].pred;
            fillers.erase(fillers.begin() + i);
            // Below its cyclic predecessor if that one is in place; a filler kept out over several
            // requests (refill) may find it lifted or used as a filler: then the top or the bottom.
            if (pred >= 0 && in_column(pred, col_of[pred])) {
                move_after(x, pred);
                return;
            }
            if (pred >= 0) stat_pred_out++;
            break;
        }
        std::vector<int> mem;  // column l top to bottom, without x
        for (int k : order) if (k != x && in_column(k, l)) mem.push_back(k);
        bool at_top = false;
        if (!mem.empty()) {
            if (mode == 2) {
                at_top = true;
            } else if (mode == 0) {
                int want_paper = ded[u];
                int hw = handle[l];
                if (want_paper >= 0 && col_of[want_paper] == l && want_paper != x) {
                    at_top = false;
                } else if (want_paper == x) {
                    at_top = true;
                } else {
                    bool hole = want_paper < 0 || !(paper[want_paper].opaque >> hw & 1);
                    if (hole) {
                        int c = A[u] >> hw & 1;
                        bool top_ok = (int)(paper[mem[0]].black >> hw & 1) == c;
                        bool d_ok = (int)(paper[x].black >> hw & 1) == c;
                        at_top = !top_ok && d_ok;
                    }
                }
            }
        }
        if (at_top) {
            // Just above the current top of the column.
            int i = index_of(x);
            order.erase(order.begin() + i);
            int j = 0;
            while (order[j] != mem[0]) j++;
            order.insert(order.begin() + i, x);
            move(x, j);
        } else {
            // Below the last paper of the generic layer and of columns 0..l.
            int last = -1;
            for (int k : order) {
                if (k == x || k == top_d || is_filler(k)) continue;
                if (block_of[k] >= 0 || (col_of[k] >= 0 && col_of[k] <= l)) last = k;
            }
            move_after(x, last);
        }
    }

    // Plan options for one request (see process()).
    struct PlanOpt {
        int ret_mode = 0;       // return of the previous top paper (return_paper modes)
        int fret_mode = 0;      // return of the previous fillers taken from the column tops
        bool use_filler = false;
        bool keep = false;      // the previous top paper is also the paper of u (a pair): keep it
    };

    // After D (target u) is lifted: the column top X of a column c whose handle is a hole of D,
    // placed just below the generic layer (or below the fillers already placed), shows on every
    // remaining handle hole of D up to h_c where X is opaque. If X has the colors of A_u there, the
    // columns it covers need no digs. X goes back to its column at the next request, so it pays
    // when it saves at least 3 digs.
    // A deeper paper X_p of the column (p <= kFillerDepth) can serve too: X_0, ..., X_{p-1} are moved
    // in this order just below X_p, X_0, ..., X_{p-2}, which leaves X_p on top and X_0, ..., X_{p-1}
    // in their cyclic order below it; X_p goes back below X_{p-1} at the next request, so the
    // cyclic order of the column (and its color alternation) is kept. Cost p + 2.
    // Returns {column, depth} of the best filler, or {-1, 0}.
    int kFillerDepth = env_int("FILLER_DEPTH", 3);
    struct FillerChoice {
        int c = -1, depth = 0, lvl = 0;
    };
    bool leveled = env_int("LEVELED", 1) != 0;
    FillerChoice choose_filler(int u, int d, u64 hh) const {
        std::vector<int> fix(H, 0);
        for (int j = 0; j < H; j++)
            if (hh >> handle[j] & 1) fix[j] = handle_fix_cost(j, A[u] >> handle[j] & 1);
        std::vector<int> hidx(N, -1);  // window -> handle index
        for (int j = 0; j < H; j++) hidx[handle[j]] = j;
        int best = 0;
        FillerChoice bc;
        std::vector<int> top;
        for (int c = 0; c < H; c++) {
            if (!(hh >> handle[c] & 1)) continue;
            top.clear();  // the top papers of column c
            for (int k : order) {
                if (!in_column(k, c)) continue;
                top.push_back(k);
                if ((int)top.size() > kFillerDepth) break;
            }
            if (top.empty() || top[0] == d) continue;
            for (int depth = 0; depth < (int)top.size(); depth++) {
                int f = top[depth];
                u64 shown = paper[f].opaque & hh;
                u64 bad = (paper[f].black ^ A[u]) & shown;
                int lvl = 0;
                if (bad) {  // only below its deepest wrong handle
                    if (!leveled) continue;
                    for (u64 x = bad; x; x &= x - 1) lvl = std::max(lvl, hidx[__builtin_ctzll(x)] + 1);
                    if (lvl > c) continue;
                }
                bool ok = true;  // must not reach the handles of a deeper filler placed below it
                for (auto& fl : fillers) if (fl.lvl > lvl && c >= fl.lvl) ok = false;
                if (!ok) continue;
                int save = 0;
                for (int j = lvl; j <= c; j++)
                    if ((j != c || depth) && (shown >> handle[j] & 1)) save += fix[j];
                int gain = save - 2 - depth;
                if (gain > best) {
                    best = gain;
                    bc = {c, depth, lvl};
                }
            }
        }
        return bc;
    }

    // Best set of fillers with pairwise disjoint handle intervals [lvl, c] (weighted interval
    // scheduling over the handle indices), each candidate being a paper at depth <= kFillerDepth
    // of a column c whose handle is a hole of D, at the level just past its deepest wrong handle.
    // Disjoint intervals never cover each other's column handles, so their gains add up.
    std::vector<FillerChoice> choose_fillers_dp(int u, int d, u64 hh) const {
        std::vector<int> fix(H, 0);
        for (int j = 0; j < H; j++)
            if (hh >> handle[j] & 1) fix[j] = handle_fix_cost(j, A[u] >> handle[j] & 1);
        std::vector<int> hidx(N, -1);
        for (int j = 0; j < H; j++) hidx[handle[j]] = j;
        // cand_end[c]: candidates whose interval ends at c (lvl, gain, depth)
        std::vector<std::vector<std::array<int, 3>>> cand_end(H);
        std::vector<int> top;
        for (int c = 0; c < H; c++) {
            if (!(hh >> handle[c] & 1)) continue;
            top.clear();
            for (int k : order) {
                if (!in_column(k, c)) continue;
                top.push_back(k);
                if ((int)top.size() > kFillerDepth) break;
            }
            if (top.empty() || top[0] == d) continue;
            for (int depth = 0; depth < (int)top.size(); depth++) {
                int f = top[depth];
                u64 shown = paper[f].opaque & hh;
                u64 bad = (paper[f].black ^ A[u]) & shown;
                int lvl = 0;
                if (bad) {
                    if (!leveled) continue;
                    for (u64 x = bad; x; x &= x - 1) lvl = std::max(lvl, hidx[__builtin_ctzll(x)] + 1);
                    if (lvl > c) continue;
                }
                bool ok = true;  // must not reach the handles of a deeper filler placed below it
                for (auto& fl : fillers) if (fl.lvl > lvl && c >= fl.lvl) ok = false;
                if (!ok) continue;
                int save = 0;
                for (int j = lvl; j <= c; j++)
                    if ((j != c || depth) && (shown >> handle[j] & 1)) save += fix[j];
                int gain = save - 2 - depth;
                if (gain > 0) cand_end[c].push_back({lvl, gain, depth});
            }
        }
        // best[j + 1] = best total gain with intervals inside handles 0..j
        std::vector<int> best(H + 1, 0), pick_c(H + 1, -1), pick_i(H + 1, -1);
        for (int c = 0; c < H; c++) {
            best[c + 1] = best[c];
            for (int i = 0; i < (int)cand_end[c].size(); i++) {
                auto [lvl, gain, depth] = cand_end[c][i];
                if (best[lvl] + gain > best[c + 1]) {
                    best[c + 1] = best[lvl] + gain;
                    pick_c[c + 1] = c;
                    pick_i[c + 1] = i;
                }
            }
        }
        std::vector<FillerChoice> res;
        for (int j = H; j > 0;) {
            if (pick_c[j] < 0) {
                j--;
                continue;
            }
            int c = pick_c[j];
            auto [lvl, gain, depth] = cand_end[c][pick_i[j]];
            res.push_back({c, depth, lvl});
            j = lvl;
        }
        std::reverse(res.begin(), res.end());
        return res;
    }

    struct FillerPick {
        int c = -1, depth = 0, lvl = 0;
        bool post = false;  // must be placed after D is lifted
    };
    // Like choose_fillers_dp, but evaluated before D (column l, in place) is lifted: candidates are
    // the top papers of every column c != l whose handle is not covered by a filler already placed.
    // A candidate of a column c > l whose interval reaches h_l would hide D's column top: it is
    // placed after the lift (post). A candidate of a column c < l whose handle D covers can only be
    // placed before the lift (its top is hidden once D is on top).
    std::vector<FillerPick> choose_fillers_prelift(int u, int d, u64 hh) const {
        int l = col_of[d];
        u64 hole_all = 0;  // handle holes of D (also those already covered)
        for (int j = 0; j < H; j++)
            if (!(paper[d].opaque >> handle[j] & 1)) hole_all |= 1ULL << handle[j];
        u64 covered = 0;  // handles shown by fillers already placed
        for (auto& f : fillers)
            for (int j = f.lvl; j <= f.hi; j++)
                if (paper[f.paper].opaque >> handle[j] & 1) covered |= 1ULL << handle[j];
        std::vector<int> fix(H, 0);
        for (int j = 0; j < H; j++)
            if (hh >> handle[j] & 1) fix[j] = handle_fix_cost(j, A[u] >> handle[j] & 1);
        std::vector<int> hidx(N, -1);
        for (int j = 0; j < H; j++) hidx[handle[j]] = j;
        std::vector<std::vector<std::array<int, 4>>> cand_end(H);  // (lvl, gain, depth, post)
        std::vector<int> top;
        for (int c = 0; c < H; c++) {
            if (c == l || (covered >> handle[c] & 1)) continue;
            bool hole_c = hole_all >> handle[c] & 1;
            top.clear();
            for (int k : order) {
                if (!in_column(k, c)) continue;
                top.push_back(k);
                if ((int)top.size() > kFillerDepth) break;
            }
            if (top.empty()) continue;
            for (int depth = 0; depth < (int)top.size(); depth++) {
                int f = top[depth];
                u64 shown = paper[f].opaque & hh;
                u64 bad = (paper[f].black ^ A[u]) & shown;
                int lvl = 0;
                for (u64 x = bad; x; x &= x - 1) lvl = std::max(lvl, hidx[__builtin_ctzll(x)] + 1);
                if (lvl > c) continue;
                bool post = false;
                if (c > l && lvl <= l && (paper[f].opaque >> handle[l] & 1)) post = true;
                if (post && !hole_c) continue;  // (cannot happen: deeper handles are holes of D)
                bool ok = true;
                for (auto& fl : fillers) if (fl.lvl > lvl && c >= fl.lvl) ok = false;
                if (!ok) continue;
                int save = 0;
                for (int j = lvl; j <= c; j++)
                    if ((shown >> handle[j] & 1) && (j != c || depth || !hole_c)) save += fix[j];
                int gain = save - 2 - depth;
                if (gain > 0) cand_end[c].push_back({lvl, gain, depth, post ? 1 : 0});
            }
        }
        std::vector<int> best(H + 1, 0), pick_c(H + 1, -1), pick_i(H + 1, -1);
        for (int c = 0; c < H; c++) {
            best[c + 1] = best[c];
            for (int i = 0; i < (int)cand_end[c].size(); i++) {
                auto [lvl, gain, depth, post] = cand_end[c][i];
                if (best[lvl] + gain > best[c + 1]) {
                    best[c + 1] = best[lvl] + gain;
                    pick_c[c + 1] = c;
                    pick_i[c + 1] = i;
                }
            }
        }
        std::vector<FillerPick> res;
        for (int j = H; j > 0;) {
            if (pick_c[j] < 0) {
                j--;
                continue;
            }
            int c = pick_c[j];
            auto [lvl, gain, depth, post] = cand_end[c][pick_i[j]];
            res.push_back({c, depth, lvl, post != 0});
            j = lvl;
        }
        std::reverse(res.begin(), res.end());
        return res;
    }

    // Places the filler at depth `depth` of column c at level lvl (see run_plan) and records it.
    void place_filler(int c, int depth, int lvl, u64& hh) {
        std::vector<int> top;  // the top papers of column c
        for (int k : order) {
            if (!in_column(k, c)) continue;
            top.push_back(k);
            if ((int)top.size() > depth) break;
        }
        int pred = -1;
        if (depth > 0) {  // X_0..X_{depth-1} below X_depth, keeping their order
            int prev = top[depth];
            for (int i = 0; i < depth; i++) {
                move_after(top[i], prev);
                prev = top[i];
            }
            pred = top[depth - 1];
        }
        int x = top[depth];
        int q = -1;
        for (int i = 0; i < K; i++) {
            int k = order[i];
            if (k != x && col_of[k] >= lvl && in_column(k, col_of[k])) {
                q = i;
                break;
            }
        }
        int xi = index_of(x);
        if (q < 0) q = K;
        move(x, xi < q ? q - 1 : q);
        Filler fl{x, pred};
        fl.lvl = lvl;
        fl.hi = c;
        fillers.push_back(fl);
        u64 cov = 0;
        for (int j = lvl; j <= c; j++) cov |= 1ULL << handle[j];
        hh &= ~(paper[x].opaque & cov);
        stat_level_fill += lvl > 0;
    }

    // The orientation of every block touched by `holes` that shows A_u there (consistent pairs
    // match Y_b or ~Y_b; an inconsistent pair takes the closer one and is wrong).
    std::vector<int> wanted_blocks(int u, u64 holes) const {
        std::vector<int> want(blocks.size(), -1);
        for (int b = 0; b < (int)blocks.size(); b++) {
            u64 dm = holes & blocks[b].mask;
            if (!dm) continue;
            u64 x = (A[u] ^ blocks[b].y) & dm;
            want[b] = __builtin_popcountll(x) * 2 <= __builtin_popcountll(dm) ? 0 : 1;
        }
        return want;
    }

    // Level for an out-of-place paper x (the previous lifted paper or an old filler, column cx) to
    // serve as a filler for D (column l, handle holes hh): just past its deepest wrong handle, and
    // below D's column when x would cover h_l (it must not hide D's column top). -1 if it covers
    // nothing there. cov receives the covered holes.
    int level_for(int x, int d, u64 hh, int u, u64& cov) const {
        int cx = col_of[x], l = col_of[d];
        u64 shown = paper[x].opaque & hh;
        u64 bad = (paper[x].black ^ A[u]) & shown;
        int lvl = 0;
        for (int j = 0; j < H; j++)
            if (bad >> handle[j] & 1) lvl = std::max(lvl, j + 1);
        if (cx >= l && (paper[x].opaque >> handle[l] & 1)) lvl = std::max(lvl, l + 1);
        cov = 0;
        for (int j = lvl; j <= cx; j++)
            if (shown >> handle[j] & 1) cov |= 1ULL << handle[j];
        return cov ? lvl : -1;
    }

    // Old fillers (olds, from the previous request) that can cover holes of D = ded[u] not yet
    // covered (pre_cov) move straight to their new level if that saves at least 2 digs (no move at
    // all if they already sit at that level); the others go back to their column (mode). `placed`
    // holds the fillers of this request so far (intervals that a new one must not reach from above).
    void refill_or_return(int u, const std::vector<Filler>& olds, u64 all, u64& pre_cov,
                          std::vector<Filler>& placed, int mode) {
        int d = ded[u];
        for (int i = (int)olds.size() - 1; i >= 0; i--) {
            int x = olds[i].paper, cf = col_of[x];
            bool use = false;
            int lvl = 0;
            u64 cov = 0;
            if (d >= 0 && x != d && visible(x)) {
                lvl = level_for(x, d, all & ~paper[d].opaque & ~gmask & ~pre_cov, u, cov);
                bool ok = lvl >= 0;
                for (auto& e : placed) if (e.lvl > lvl && cf >= e.lvl) ok = false;
                if (ok) {
                    int save = 0;
                    for (int j = lvl; j <= cf; j++)
                        if (cov >> handle[j] & 1) save += handle_fix_cost(j, A[u] >> handle[j] & 1);
                    use = save >= 2;
                }
            }
            if (!use && keep_harmless_now && d >= 0 && x != d) {
                // Leave it where it is if it does not hide D's column top and shows A_u on the
                // holes of D it covers (it may serve a later target).
                int L = olds[i].lvl, l = col_of[d];
                bool harm = L <= l && l <= cf && (paper[x].opaque >> handle[l] & 1);
                for (auto& e : placed) if (e.lvl > L && cf >= e.lvl) harm = true;
                u64 hcov = 0;
                for (int j = L; j <= cf; j++) hcov |= 1ULL << handle[j];
                hcov &= paper[x].opaque & (all & ~paper[d].opaque & ~gmask) & ~pre_cov;
                if ((paper[x].black ^ A[u]) & hcov) harm = true;
                if (!harm && visible(x)) {
                    for (size_t k = 0; k < fillers.size(); k++)
                        if (fillers[k].paper == x) {
                            fillers.erase(fillers.begin() + k);
                            break;
                        }
                    placed.push_back(olds[i]);
                    pre_cov |= hcov;
                    continue;
                }
            }
            if (!use) {
                return_paper(x, u, mode);
                continue;
            }
            for (size_t k = 0; k < fillers.size(); k++)
                if (fillers[k].paper == x) {
                    fillers.erase(fillers.begin() + k);
                    break;
                }
            int q = -1, last_above = -1;
            for (int k2 = 0; k2 < K; k2++) {
                int k = order[k2];
                if (k == x || col_of[k] < 0 || !in_column(k, col_of[k])) continue;
                if (col_of[k] < lvl) last_above = k2;
                else if (q < 0) q = k2;
            }
            int xi = index_of(x);
            if (q < 0) q = K;
            if (!(xi < q && xi > last_above)) move(x, xi < q ? q - 1 : q);
            Filler fl = olds[i];
            fl.lvl = lvl;
            fl.hi = cf;
            placed.push_back(fl);
            pre_cov |= cov;
            stat_refill_try++;
        }
    }

    int kMaxFillers = env_int("MAX_FILLERS", 8);
    bool filler_dp = env_int("FILLER_DP", 1) != 0;
    bool prelift = env_int("PRELIFT", 1) != 0;
    double kFillerCharge = env_double("FILL_W", 0.8);
    bool keep_harmless = env_int("KEEP_HARMLESS", 1) != 0;
    bool keep_harmless_now = false;
    void run_plan(int u, const PlanOpt& opt) {
        keep_harmless_now = opt.fret_mode == 4;
        u64 all = gmask;
        for (int l = 0; l < H; l++) all |= 1ULL << handle[l];
        bool kept = opt.keep && top_d >= 0 && ded[u] == top_d;
        u64 pre_cov = 0;  // handles covered by the previous paper used as a filler (ret_mode 3)
        if (top_d >= 0 && !kept && opt.ret_mode == 3) {
            // The previous paper x (column lp) as a filler for D = ded[u] (column l < lvl <= lp):
            // at level lvl it covers the holes of D in h_lvl..h_lp where it is opaque, and must
            // show A_u there. The old fillers go back first when they can (x on top may hide them).
            int x = top_d, lp = col_of[x], d = ded[u];
            if (d < 0 || d == x) {
                invalid = true;
                return;
            }
            u64 cov0 = 0;
            int lvl = level_for(x, d, all & ~paper[d].opaque & ~gmask, u, cov0);
            if (lvl < 0) {
                invalid = true;
                return;
            }
            std::vector<Filler> old = fillers, vis_old, def_old;
            for (auto& f : old) (visible(f.paper) ? vis_old : def_old).push_back(f);
            std::vector<Filler> placed;
            {
                Filler fp{x, -1};
                fp.lvl = lvl;
                fp.hi = lp;
                placed.push_back(fp);
            }
            pre_cov |= cov0;
            if (opt.fret_mode >= 3) {
                refill_or_return(u, vis_old, all, pre_cov, placed, 1);
            } else {
                for (int i = (int)vis_old.size() - 1; i >= 0; i--) return_paper(vis_old[i].paper, u, opt.fret_mode);
            }
            int q = -1;
            for (int i = 0; i < K; i++) {
                int k = order[i];
                if (k != x && col_of[k] >= lvl && in_column(k, col_of[k])) {
                    q = i;
                    break;
                }
            }
            int xi = index_of(x);
            if (q < 0) q = K;
            move(x, xi < q ? q - 1 : q);
            top_d = -1;
            if (opt.fret_mode >= 3) {
                refill_or_return(u, def_old, all, pre_cov, placed, 1);
            } else {
                for (int i = (int)def_old.size() - 1; i >= 0; i--) return_paper(def_old[i].paper, u, opt.fret_mode);
            }
            for (auto& f : placed) fillers.push_back(f);
            stat_prev_fill_try++;
        } else if (opt.fret_mode >= 3) {
            if (top_d >= 0 && !kept) return_paper(top_d, u, opt.ret_mode);
            std::vector<Filler> old = fillers, placed;
            refill_or_return(u, old, all, pre_cov, placed, 1);
            for (auto& f : placed) fillers.push_back(f);
        } else {
            if (top_d >= 0 && !kept) return_paper(top_d, u, opt.ret_mode);
            while (!fillers.empty()) return_paper(fillers.back().paper, u, opt.fret_mode);
        }
        if (ded[u] >= 0) {
            int d = ded[u], l = col_of[d];
            u64 holes = all & ~paper[d].opaque;
            set_blocks(wanted_blocks(u, holes));
            u64 hh = holes & ~gmask & ~pre_cov;
            std::vector<FillerChoice> plan_f;
            if (!kept && opt.use_filler && filler_dp && prelift) {
                // Fillers chosen with every column top visible; those that do not reach D's
                // handle go in before the dig and the lift, the others after.
                auto picks = choose_fillers_prelift(u, d, hh);
                for (auto& pk : picks)
                    if (!pk.post) place_filler(pk.c, pk.depth, pk.lvl, hh);
                while (column_top(l) != d) dig(l);
                move(d, 0);
                top_d = d;
                for (auto& pk : picks)
                    if (pk.post) place_filler(pk.c, pk.depth, pk.lvl, hh);
            } else {
                if (!kept) {
                    while (column_top(l) != d) dig(l);
                    move(d, 0);
                    top_d = d;
                }
                if (opt.use_filler && filler_dp) plan_f = choose_fillers_dp(u, d, hh);
            }
            size_t plan_i = 0;
            while (opt.use_filler && (int)fillers.size() < kMaxFillers) {
                FillerChoice ch;
                if (filler_dp) {
                    if (plan_i >= plan_f.size()) break;
                    ch = plan_f[plan_i++];
                } else {
                    ch = choose_filler(u, d, hh);
                }
                auto [c, depth, lvl] = ch;
                if (c < 0) break;
                std::vector<int> top;  // the top papers of column c
                for (int k : order) {
                    if (!in_column(k, c)) continue;
                    top.push_back(k);
                    if ((int)top.size() > depth) break;
                }
                int pred = -1;
                if (depth > 0) {  // X_0..X_{depth-1} below X_depth, keeping their order
                    int prev = top[depth];
                    for (int i = 0; i < depth; i++) {
                        move_after(top[i], prev);
                        prev = top[i];
                    }
                    pred = top[depth - 1];
                }
                int x = top[depth];
                // Just above the first paper in place of a column >= lvl: below the generic layer,
                // the columns 0..lvl-1 and the fillers of levels <= lvl.
                int q = -1;
                for (int i = 0; i < K; i++) {
                    int k = order[i];
                    if (k != x && col_of[k] >= lvl && in_column(k, col_of[k])) {
                        q = i;
                        break;
                    }
                }
                int xi = index_of(x);
                if (q < 0) q = K;
                move(x, xi < q ? q - 1 : q);
                Filler fl{x, pred};
                fl.lvl = lvl;
                fl.hi = c;
                fillers.push_back(fl);
                u64 cov = 0;
                for (int j = lvl; j <= c; j++) cov |= 1ULL << handle[j];
                hh &= ~(paper[x].opaque & cov);
                stat_level_fill += lvl > 0;
            }
            for (int l2 = 0; l2 < H; l2++)
                if (hh >> handle[l2] & 1) set_handle(l2, A[u] >> handle[l2] & 1);
        } else {
            // No unit (should not happen): the closer orientation per block, then every handle.
            set_blocks(wanted_blocks(u, gmask));
            for (int l = 0; l < H; l++) set_handle(l, A[u] >> handle[l] & 1);
        }
    }

    // Every filler is visible with the lifted paper set aside (it goes back first at the next
    // request), so that it can always be returned.
    bool fillers_reachable() const {
        for (auto& f : fillers) {
            u64 e = paper[f.paper].opaque;
            bool vis = false;
            for (int x : order) {
                if (x == top_d) continue;
                if (x == f.paper) {
                    vis = e != 0;
                    break;
                }
                e &= ~paper[x].opaque;
            }
            if (!vis) return false;
        }
        return true;
    }

    // Search over plans: every combination of the options is simulated on a copy of the state, and
    // the one with the fewest moves (+1 per filler left to return later) is kept.
    struct State {
        std::vector<int> order;
        int top_d;
        std::vector<Filler> fillers;
    };
    State save() const { return {order, top_d, fillers}; }
    void restore(const State& st) {
        order = st.order;
        top_d = st.top_d;
        fillers = st.fillers;
    }
    bool search_on = env_int("SEARCH", 1) != 0;
    bool prev_filler = env_int("PREV_FILLER", 1) != 0;
    bool refill = env_int("REFILL", 1) != 0;
    long long stat_pred_out = 0;
    long long stat_kept = 0, stat_fill = 0, stat_level_fill = 0, stat_prev_fill_try = 0, stat_prev_fill = 0,
              stat_refill_try = 0, stat_refill = 0;
    std::vector<std::pair<int, int>> process(int u) {
        const State st0 = save();
        int top0 = top_d;
        std::vector<PlanOpt> opts;
        if (!search_on) {
            opts.push_back(PlanOpt{});
        } else {
            bool has_free_filler = false;  // a filler that goes back to the top or the bottom
            for (auto& f : fillers) has_free_filler |= f.pred < 0;
            bool prev_ok = top0 >= 0 && ded[u] >= 0 && ded[u] != top0 && prev_filler;
            for (int rm = 1; rm <= (prev_ok ? 3 : 2); rm++)
                for (int fm : {1, 2, 3, 4})
                    for (int uf = env_int("UF_MIN", 1); uf < 2; uf++)  // plans without fillers are never better
                        for (int kp = 0; kp < ((top0 >= 0 && ded[u] == top0) ? 2 : 1); kp++)
                            if ((fm == 2 && !has_free_filler) || (fm >= 3 && (!refill || fillers.empty())) || (fm == 4 && !keep_harmless))
                                continue;
                            else
                                opts.push_back(PlanOpt{rm, fm, uf == 1, kp == 1});
        }
        double best = 1e18;
        std::vector<std::pair<int, int>> best_ops;
        State best_state;
        PlanOpt best_opt;
        check_vis = true;
        for (const PlanOpt& o : opts) {
            restore(st0);
            ops.clear();
            invalid = false;
            run_plan(u, o);
            if (invalid || display() != A[u]) continue;
            if (!fillers_reachable()) continue;
            // A filler left out costs its return later, but is often re-used (refill) instead,
            // so it is charged less than a move now (seed 0-95: 1.0 -> 0.8 is -0.48%).
            double cost = ops.size() + kFillerCharge * fillers.size();
            if (cost < best) {
                best = cost;
                best_ops = ops;
                best_state = save();
                best_opt = o;
            }
        }
        check_vis = false;
        if (best > 1e17) {  // no valid plan (inconsistent pair, or no unit): the plain procedure
            restore(st0);
            ops.clear();
            run_plan(u, PlanOpt{});
            return ops;
        }
        restore(best_state);
        ops = best_ops;
        stat_kept += best_opt.keep && top0 >= 0 && ded[u] == top0;
        stat_prev_fill += best_opt.ret_mode == 3;
        stat_refill += best_opt.fret_mode == 3;
        stat_fill += fillers.size();
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
    std::cerr << "kept_partner = " << solver.stat_kept << '\n';
    std::cerr << "fillers_used = " << solver.stat_fill << '\n';
    std::cerr << "level_fillers_tried = " << solver.stat_level_fill << '\n';
    std::cerr << "prev_fillers_used = " << solver.stat_prev_fill << '\n';
    std::cerr << "refill_plans_used = " << solver.stat_refill << '\n';
    std::cerr << "pred_out_returns = " << solver.stat_pred_out << '\n';
    std::cerr << "total_moves = " << total << '\n';
    return 0;
}
