// audit2-blk: solutions/audit2-ret whose generic layer is driven by a lookahead policy (set_blocks):
// over the orders of the base paper and the flip papers (720 states for 5 blocks, legal moves of
// visible papers only), the request takes a shortest path to a state showing the wanted
// orientations, and among those end states the one with the least expected moves for the next
// pair target (mean over the pair targets of the design of the distance to a satisfying state).
// The second audit (solutions/audit2-probe/blk_sim.cpp, seed 0-11) measured the generic layer at
// 1.235 moves per request with the former set_blocks, 1.21 with the lookahead and 1.19 with the
// exact MDP policy: the former procedure is 0.02 above the per-request minimum and leaves the end
// state arbitrary. A mixed orientation pattern on 5 touched blocks costs 2.5 moves, a uniform one
// (all on or all off) 1.0; they are 94% / 6% of the pair requests.
// audit2-ret: solutions/audit-mix with one more plan option (PlanOpt::fret_ret): in the plans that
// re-use or keep the old fillers (fret_mode 3, 4, 5), the old fillers that do go back to their
// column were always returned at the bottom; now plans with the hub7 rule (return_paper mode 0:
// at the top when the handle of that column is a hole of the new paper whose current top shows the
// wrong color and the returned paper the right one, else at the bottom) are tried too. The second
// audit (audit2-probe) found about 60-80 requests per case where an old filler went back to the
// bottom of a column that the same plan then dug as a handle fix, 12-28 of them with the fitting
// color: one move each.
// audit-mix: solutions/mix-pt with the fixes found by the audit of the best solutions: the peephole
// merging two moves of one paper in a plan (merge_double_moves), no move to the same place, and the
// previous lifted paper may stay under the new one (ret_mode 4 of run_plan; a paper lifted from the
// fillers keeps its cyclic predecessor).
// mix-pt: solutions/pool-climb (fillers chosen jointly with the papers out, filler_climb after the
// annealing) and solutions/tiny-bias (persistence of the handle-hole colors in the annealing cost,
// tops_penalty in the plan cost) together, both applied to solutions/hole-relax. The two design
// objectives conflict: the bias makes the targets of the shallow columns take the majority color
// c_m at a deep handle h_m, so (each window being about half 0 / half 1 over all targets) the
// papers of the deeper columns, the fillers, lean to the other color and the filler proxy drops
// (0.49 -> 0.35 per target). A climb that kept the uniform hole cost of pool-climb undid the bias
// (+0.33% against pool-climb, seed 0-95). So filler_climb here
//   - prices the handle holes with the exact persistence cost (counts per handle, as anneal_units'
//     refresh) and recomputes the majority colors used by the plan search after the exchanges,
//   - weights each covered hole of the proxy by 2 (1 - p_m(A_u[m])), the fixes it saves under the
//     persistence model (seed 0-191 / 192-383: -0.24 / -0.19% each, CLIMB_PQ),
//   - with the weight 0.3 instead of 0.7 (0.7 / 0.5 / 0.3 / 0.1 / 0: +0.6 / +0.3 / 0 / 0 / +0.4%).
// pool-climb: solutions/pool-value with a hill climbing after the annealing (filler_climb, until
// 1.15 s) that exchanges two units between columns (same kind, same colors at both handles) when the
// model cost minus 0.7 x a proxy of the filler opportunities decreases: for each target u, how many
// holes of D_u the papers of each deeper column would cover at their leveled position. A unit of
// this proxy saved about 0.7 moves per request, and the annealing alone leaves it at its random
// level (0.49 per target; the climb raises it to about 0.77).
// pool-value: solutions/hole-relax with one more plan for each request (fret_mode 5, run_joint): the
// papers out of their columns (the previous lifted paper and the old fillers: return, move to a new
// level, or stay) and the new fillers from the column tops are chosen together by one weighted
// interval scheduling over the handles, and the requested paper is lifted straight from the
// fillers when it is one of them (no return and no dig; it keeps its cyclic predecessor, top_pred).
// A plain expected-value lookahead over the next request (sampled targets) did not improve the
// choice among the plans (seed 0-47: -0.10 +- 0.07%), so no explicit value of the papers left out.
// tiny-bias: solutions/hole-relax whose annealing prices the handle holes with a persistence model
// found in the exact tiny models (solutions/tiny-model): the top of column m keeps the color set
// for the last request that needed handle h_m, so a hole there costs 2 p_m (1 - p_m) fixes instead
// of 1/2 when the targets with a hole at h_m have color 1 with frequency p_m. The annealing biases
// the assignment (which units go to the columns shallower than m) towards one color per handle,
// with marginal weights frozen between refreshes (see anneal_units). Handle swaps are evaluated
// incrementally. The plan search of a request adds 0.55 x (2 p_m - 1) for every column whose top
// is left at the minority color (tops_penalty), so that ties and filler choices keep the majority
// colors on the column tops.
// hole-relax: solutions/gen-relax with the fillers of solutions/hole-level3 (same changes as from
// solutions/search-bf2 to hole-level3): leveled fillers (a column paper inserted just above the
// top of column c' covers only the handles h_{c'}..h_c), chosen by an interval DP before the paper
// D is lifted (shallower columns too), the previous lifted paper and the previous fillers re-used
// as fillers or left in place when harmless, papers left out charged 0.8 move in the plan cost,
// plans kept only if every paper left out stays visible, annealing until 1.10 s; a filler is taken
// when it saves at least 2 + depth digs (kFillerCost).
// gen-relax: solutions/search-bf2 with more pairs consistent with the blocks, so that larger
// blocks (6 windows) and fewer handles (34) can be used:
//   - Before the annealing, the G windows, their partition into blocks and the block colors Y_b are
//     chosen by hill climbing to maximize sum_b log(fraction of target pairs consistent with block
//     b) (a pair is consistent iff its patterns relative to Y_b are nested on the block; counted
//     by a subset-sum transform over the local patterns). G windows may be exchanged with handle
//     windows. This raises the consistent partners per target by about 40% and more.
//   - From 10% of the annealing on, Y is frozen and the re-pairing move draws the new partner
//     among the consistent partners of the target kept (random exchanges are mostly rejected).
//   - A pair still inconsistent after the annealing and its repair (about 2% of the cases at
//     H = 34) is fixed by splitting the block (a new flip paper), paid by one unit less: two
//     singles merged, or an augmenting path (a pair keeps one target with a single, the other
//     target joins another single).
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
    std::vector<int> bias_c;    // majority color of the targets with a hole at handle h_m
    std::vector<double> bias_g; // 2 p_m - 1: expected fixes saved when column m shows bias_c[m]
    std::vector<int> block_of;  // block of a generic paper, -1 otherwise
    std::vector<int> ded;       // ded[u] = dedicated paper of target u, -1 if none
    std::vector<Block> blocks;
    int base_paper = -1;        // base paper F (Y on all G windows)
    std::vector<int> order;     // stack, top first
    int top_d = -1;             // dedicated paper lifted to the top, -1 if none
    int top_pred = -1;          // its cyclic predecessor in its column when lifted from the fillers
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
        H = env_int("HUB_H", 34);
        double slope = env_double("HUB_SLOPE", 1.0);
        std::mt19937_64 rng(12345);
        int G = N - H;
        paper.assign(K, Paper{});
        col_of.assign(K, -1);
        block_of.assign(K, -1);
        ded.assign(P, -1);
        // Blocks: G windows cut into nb blocks of nearly equal sizes. Each block takes the colors
        // Y_b that maximize the number of target pairs consistent with it (patterns relative to Y_b
        // nested), and windows are exchanged between blocks (hill climbing) to maximize the sum
        // over blocks of log(fraction of consistent target pairs): a pair must be consistent with
        // every block it touches, so the fraction of usable pairs is about the product.
        int s = env_int("CB_S", 6);
        int nb = std::max(1, (G + s / 2) / s);
        {
            std::vector<std::vector<int>> bw(nb);  // windows of each block
            for (int j = 0, b = 0; b < nb; b++) {
                int sz = G / nb + (b < G % nb ? 1 : 0);
                for (int i = 0; i < sz; i++) bw[b].push_back(j++);
            }
            // comparable[x1][x2] for local patterns of up to 8 windows is computed on the fly.
            auto best_y = [&](const std::vector<int>& w, int& ybest) {
                int sz = w.size(), T = 1 << sz;
                std::vector<long long> cnt(T, 0);
                for (int u = 0; u < P; u++) {
                    int x = 0;
                    for (int i = 0; i < sz; i++) x |= (int)(A[u] >> w[i] & 1) << i;
                    cnt[x]++;
                }
                // For each y: pairs (x1, x2) of relative patterns x = a ^ y with x1 subset of x2,
                // by a subset-sum (zeta) transform; comparable = 2 * nested - equal.
                long long best = -1;
                std::vector<long long> c2(T), z(T);
                for (int y = 0; y < T; y++) {
                    long long eq = 0;
                    for (int x = 0; x < T; x++) c2[x] = cnt[x ^ y], eq += c2[x] * c2[x];
                    z = c2;
                    for (int i = 0; i < sz; i++)
                        for (int x = 0; x < T; x++)
                            if (x >> i & 1) z[x] += z[x ^ (1 << i)];
                    long long nested = 0;
                    for (int x = 0; x < T; x++) nested += c2[x] * z[x];
                    long long c = 2 * nested - eq;
                    if (c > best) best = c, ybest = y;
                }
                return std::log((double)best / ((double)P * P));
            };
            std::vector<double> fb(nb);
            std::vector<int> yb(nb, 0);
            for (int b = 0; b < nb; b++) fb[b] = best_y(bw[b], yb[b]);
            // Also exchanges a G window with a handle window (which windows are generic).
            std::vector<int> hw;
            for (int j = G; j < N; j++) hw.push_back(j);
            int swaps = env_int("CB_PSWAPS", 3000);
            const double gh_rate = env_double("CB_PGH", 0.3), pmove_rate = env_double("CB_PMOVE", 0.0);
            const int pmin = env_int("CB_PMIN", 3);
            for (int it = 0; it < swaps && nb >= 2; it++) {
                if ((rng() >> 11) * 0x1.0p-53 < gh_rate) {
                    int b1 = rng() % nb, i1 = rng() % bw[b1].size(), k = rng() % hw.size();
                    std::swap(bw[b1][i1], hw[k]);
                    int y1;
                    double f1 = best_y(bw[b1], y1);
                    if (f1 > fb[b1] + 1e-12) fb[b1] = f1, yb[b1] = y1;
                    else std::swap(bw[b1][i1], hw[k]);
                    continue;
                }
                int b1 = rng() % nb, b2 = rng() % (nb - 1);
                if (b2 >= b1) b2++;
                if ((rng() >> 11) * 0x1.0p-53 < pmove_rate) {
                    // Move a window from b1 to b2 (block sizes change; at most 8 windows).
                    if ((int)bw[b1].size() <= pmin || bw[b2].size() >= 8) continue;
                    int i1 = rng() % bw[b1].size();
                    auto o1 = bw[b1], o2 = bw[b2];
                    bw[b2].push_back(bw[b1][i1]);
                    bw[b1].erase(bw[b1].begin() + i1);
                    int y1, y2;
                    double f1 = best_y(bw[b1], y1), f2 = best_y(bw[b2], y2);
                    if (f1 + f2 > fb[b1] + fb[b2] + 1e-12) fb[b1] = f1, fb[b2] = f2, yb[b1] = y1, yb[b2] = y2;
                    else bw[b1] = o1, bw[b2] = o2;
                    continue;
                }
                int i1 = rng() % bw[b1].size(), i2 = rng() % bw[b2].size();
                std::swap(bw[b1][i1], bw[b2][i2]);
                int y1, y2;
                double f1 = best_y(bw[b1], y1), f2 = best_y(bw[b2], y2);
                if (f1 + f2 > fb[b1] + fb[b2] + 1e-12) {
                    fb[b1] = f1, fb[b2] = f2, yb[b1] = y1, yb[b2] = y2;
                } else {
                    std::swap(bw[b1][i1], bw[b2][i2]);
                }
            }
            double ftot = 0;
            for (int b = 0; b < nb; b++) {
                Block bl;
                for (int i = 0; i < (int)bw[b].size(); i++) {
                    bl.mask |= 1ULL << bw[b][i];
                    if (yb[b] >> i & 1) bl.y |= 1ULL << bw[b][i];
                }
                blocks.push_back(bl);
                ftot += fb[b];
            }
            std::cerr << "block_log_consistency = " << ftot << '\n';
            std::sort(hw.begin(), hw.end());
            handle = hw;
            for (auto& bl : blocks) gmask |= bl.mask;
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
        filler_climb(units, members, color_at);
        // Fallback for a pair still inconsistent after the annealing and its repair (about 2% of
        // the cases): split each block where it is inconsistent (a new flip paper for the windows
        // where A_u differs from Y_b; splitting never breaks another pair), paying the paper by
        // merging two single targets into a pair consistent with the blocks.
        {
            std::vector<u64> shallow_l(H + 1, 0);
            for (int l = 0; l < H; l++) shallow_l[l + 1] = shallow_l[l] | 1ULL << handle[l];
            std::vector<int> col_of_unit(units.size(), -1);
            for (int l = 0; l < H; l++) for (int c = 0; c < 2; c++) for (int x : members[l][c]) col_of_unit[x] = l;
            int splits = 0, failed = 0;
            for (int x = 0; x < (int)units.size() && env_int("CB_SPLIT", 1); x++) {
                auto [u, v] = units[x];
                if (v < 0 || col_of_unit[x] < 0) continue;
                for (int b = 0; b < (int)blocks.size(); b++) {
                    u64 d = (A[u] ^ A[v]) & blocks[b].mask;
                    u64 xx = (A[u] ^ blocks[b].y) & d;
                    if (!d || xx == 0 || xx == d) continue;
                    // The cheapest merge of two singles: consistent, agreeing at the handle of the
                    // first one's column, and the second one's column keeps both colors.
                    double best = 1e18;
                    int bw_ = -1, bz = -1;
                    for (int xw = 0; xw < (int)units.size(); xw++) {
                        if (units[xw][1] >= 0 || col_of_unit[xw] < 0) continue;
                        int lw = col_of_unit[xw], w = units[xw][0];
                        for (int xz = 0; xz < (int)units.size(); xz++) {
                            if (xz == xw || units[xz][1] >= 0 || col_of_unit[xz] < 0) continue;
                            int z = units[xz][0], lz = col_of_unit[xz];
                            u64 dz = A[w] ^ A[z];
                            if (dz >> handle[lw] & 1) continue;
                            auto [t, bad] = touch(A[w], dz);
                            if (bad) continue;
                            int cz = A[z] >> handle[lz] & 1;
                            if (members[lz][cz].size() <= 1) continue;
                            double c = 2 * (0.51 * __builtin_popcountll(dz & shallow_l[lw]) + 0.5 * t);
                            if (c < best) best = c, bw_ = xw, bz = xz;
                        }
                    }
                    if (bw_ < 0) {
                        // Two singles rarely make a consistent pair (the annealing paired those
                        // that could), so take an augmenting path: a pair (a, b) keeps a with a
                        // single c (consistent, same color at its handle), and b joins a single d
                        // in d's column. One unit less, columns keep their colors.
                        int bp = -1, bkeep = -1, bc = -1, bd = -1;
                        for (int xp = 0; xp < (int)units.size(); xp++) {
                            if (units[xp][1] < 0 || col_of_unit[xp] < 0 || xp == x) continue;
                            int lp = col_of_unit[xp];
                            for (int keep = 0; keep < 2; keep++) {
                                int a = units[xp][keep], bb = units[xp][1 - keep];
                                for (int xc = 0; xc < (int)units.size(); xc++) {
                                    if (units[xc][1] >= 0 || col_of_unit[xc] < 0) continue;
                                    int c = units[xc][0], lc = col_of_unit[xc];
                                    u64 dac = A[a] ^ A[c];
                                    if (dac >> handle[lp] & 1) continue;
                                    int colc = A[c] >> handle[lc] & 1;
                                    if (members[lc][colc].size() <= 1) continue;
                                    auto [t1, bad1] = touch(A[a], dac);
                                    if (bad1) continue;
                                    double c1 = 0.51 * __builtin_popcountll(dac & shallow_l[lp]) + 0.5 * t1;
                                    if (2 * c1 >= best) continue;
                                    for (int xd = 0; xd < (int)units.size(); xd++) {
                                        if (xd == xc || units[xd][1] >= 0 || col_of_unit[xd] < 0) continue;
                                        int d2 = units[xd][0], ld = col_of_unit[xd];
                                        u64 dbd = A[bb] ^ A[d2];
                                        if (dbd >> handle[ld] & 1) continue;
                                        auto [t2, bad2] = touch(A[bb], dbd);
                                        if (bad2) continue;
                                        double cc = 2 * (c1 + 0.51 * __builtin_popcountll(dbd & shallow_l[ld]) + 0.5 * t2);
                                        if (cc < best) best = cc, bp = xp, bkeep = keep, bc = xc, bd = xd;
                                    }
                                }
                            }
                        }
                        if (bp < 0) {
                            failed++;
                            continue;
                        }
                        int a = units[bp][bkeep], bb = units[bp][1 - bkeep];
                        int c = units[bc][0], lc = col_of_unit[bc], colc = A[c] >> handle[lc] & 1;
                        auto& mc = members[lc][colc];
                        mc.erase(std::find(mc.begin(), mc.end(), bc));
                        col_of_unit[bc] = -1;
                        units[bp] = {a, c};
                        units[bd][1] = bb;
                        Block nbk;
                        nbk.mask = xx;
                        nbk.y = blocks[b].y & xx;
                        blocks[b].mask &= ~xx;
                        blocks[b].y &= ~xx;
                        blocks.push_back(nbk);
                        splits++;
                        continue;
                    }
                    int z = units[bz][0], lz = col_of_unit[bz], cz = A[z] >> handle[lz] & 1;
                    auto& mz = members[lz][cz];
                    mz.erase(std::find(mz.begin(), mz.end(), bz));
                    col_of_unit[bz] = -1;
                    units[bw_][1] = z;
                    Block nbk;
                    nbk.mask = xx;
                    nbk.y = blocks[b].y & xx;
                    blocks[b].mask &= ~xx;
                    blocks[b].y &= ~xx;
                    blocks.push_back(nbk);
                    splits++;
                }
            }
            nb = blocks.size();
            next = nb + 1;
            std::cerr << "split_fallback = " << splits << "\nsplit_failed = " << failed << '\n';
        }
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
        build_block_tables();
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
    // After the annealing: hill climbing over exchanges of two units of the same kind (two pairs or
    // two singles) between two columns, with the same colors at both handles (the column balance
    // and the digs of the model are kept). Besides the model cost (handle holes), it rewards the
    // papers of the deeper columns being good fillers for each target u:
    //   proxy(u) = sum over the columns c deeper than u's of the mean over the units y of c of
    //              max(0, g - kT), g = holes of D_u on the deeper handles that the paper of y covers
    //              at the level just past its deepest mismatch with A_u (h_c excluded).
    // Per request, one unit of proxy(u) saved about 0.7 moves (regression on seed 0-95, with the
    // triangle holes, pair holes, blocks and column size), while the annealing leaves it at random.
    // Objective: model cost - kW * sum of proxy. Seed 0-95 (annealing fixed at 3M iterations, 20k
    // exchanges): -1.07 +- 0.10% against pool-value; kW 0.4 / 1.5 -0.93 / -0.89%, kT 2 / 4 worse by
    // 0.22 / 0.14%, also exchanging a pair with a single +0.18 +- 0.10%, re-pairing moves +0.14%,
    // pair holes in the proxy +0.06%, 3x / 10x more exchanges +0.09 / -0.07% (converged), simulated
    // annealing over 200k exchanges (start temperature 0.3 / 1.0) -0.03 / +0.32%.
    template <class ColorAt>
    void filler_climb(std::vector<std::array<int, 2>>& units,
                      std::vector<std::array<std::vector<int>, 2>>& members, ColorAt color_at) {
        // A fixed number of exchanges (CLIMB_ITERS > 0, experiments) or until CLIMB_TL seconds.
        const int iters = env_int("CLIMB_ITERS", 0);
        const double t_end = env_double("CLIMB_TL", 1.15);
        if (iters < 0) return;
        const double kW = env_double("CLIMB_W", 0.3), kH = env_double("HUB_KH", 0.51);
        const int kT = env_int("CLIMB_T", 3);
        const int U = units.size();
        std::vector<int> col(U, -1);
        for (int l = 0; l < H; l++) for (int c = 0; c < 2; c++) for (int x : members[l][c]) col[x] = l;
        auto hb = [&](u64 m) {  // bit j = window h_j
            u64 r = 0;
            for (int j = 0; j < H; j++) r |= (m >> handle[j] & 1) << j;
            return r;
        };
        std::vector<u64> hu(P), diffb(U, 0);  // colors on the handles, pair differences
        for (int u = 0; u < P; u++) hu[u] = hb(A[u]);
        for (int x = 0; x < U; x++) if (units[x][1] >= 0) diffb[x] = hu[units[x][0]] ^ hu[units[x][1]];
        // Handle-hole part of the model cost (mix-pt): the persistence model of anneal_units, exact.
        // hn[m] / hn1[m] = targets with a hole at handle h_m / of them with color 1 there; the
        // holes of h_m cost kH * hn (a * 4 p (1 - p) + 1 - a) with p = hn1 / hn (a = BIAS_MIX).
        // With CLIMB_BIAS=0, the uniform cost kH per hole of pool-climb.
        const bool kClimbBias = env_int("CLIMB_BIAS", 1) != 0;
        const double kMix = kClimbBias ? env_double("BIAS_MIX", 1.0) : 0.0;
        const u64 all_h = H >= 64 ? ~0ULL : (1ULL << H) - 1;
        auto unit_holes = [&](int x, int l) {  // handles where the paper of unit x in column l is a hole
            return (all_h & ~((2ULL << l) - 1)) | diffb[x];
        };
        std::vector<int> hn(H, 0), hn1(H, 0);
        auto add_holes = [&](int x, int l, int sgn) {
            u64 hs = unit_holes(x, l);
            for (int t : units[x]) {
                if (t < 0) continue;
                for (u64 s = hs; s; s &= s - 1) {
                    int m = __builtin_ctzll(s);
                    hn[m] += sgn;
                    hn1[m] += sgn * (int)(hu[t] >> m & 1);
                }
            }
        };
        for (int x = 0; x < U; x++) if (col[x] >= 0) add_holes(x, col[x], 1);
        auto fix_cost = [&](u64 ms) {  // model cost of the holes of the handles in ms
            double c = 0;
            for (; ms; ms &= ms - 1) {
                int m = __builtin_ctzll(ms), n = hn[m];
                if (n == 0) continue;
                double p = (double)hn1[m] / n;
                c += n * (kMix * 4 * p * (1 - p) + 1 - kMix);
            }
            return kH * c;
        };
        // Proxy weighted by the persistence model (CLIMB_PQ=1): a covered hole of D_u at h_m counts
        // 2 (1 - p_m(A_u[m])) instead of 1, the expected fixes it saves relative to an unbiased
        // handle (p_m(c) = frequency of color c among the targets with a hole at h_m, after the
        // annealing; the column top keeps the color of the last request that needed h_m).
        // pq[u][j] = sum of those weights over the handles m < j.
        const bool kPQ = env_int("CLIMB_PQ", 1) != 0;
        std::vector<std::vector<double>> pq;
        if (kPQ) {
            pq.assign(P, std::vector<double>(H + 1, 0.0));
            for (int u = 0; u < P; u++)
                for (int m = 0; m < H; m++) {
                    double p1 = hn[m] ? (double)hn1[m] / hn[m] : 0.5;
                    double pc = (hu[u] >> m & 1) ? p1 : 1 - p1;
                    pq[u][m + 1] = pq[u][m] + 2 * (1 - pc);
                }
        }
        std::vector<std::vector<int>> colm(H);  // units of each column
        for (int x = 0; x < U; x++) if (col[x] >= 0) colm[col[x]].push_back(x);
        std::vector<int> ucol(P, -1);  // unit of each target
        for (int x = 0; x < U; x++) for (int t : units[x]) if (t >= 0) ucol[t] = x;
        auto tcol = [&](int u) { return col[ucol[u]]; };
        // g - kT (at least 0) for the paper of unit y (column c) as a filler for target u (column l < c).
        auto gval = [&](int u, int l, int y, int c) {
            u64 ob = (c + 1 >= 64 ? ~0ULL : (1ULL << (c + 1)) - 1) & ~diffb[y];
            u64 range = ob & ~((1ULL << (l + 1)) - 1);
            u64 mis = (hu[units[y][0]] ^ hu[u]) & range;
            if (mis >> c & 1) return 0.0;
            int lvl = mis ? 64 - __builtin_clzll(mis) : 0;
            u64 cov = range & ((1ULL << c) - 1) & ~((1ULL << lvl) - 1);
            if (!kPQ) return (double)std::max(0, __builtin_popcountll(cov) - kT);
            if (!cov) return 0.0;
            int lo = __builtin_ctzll(cov);
            double g = pq[u][c] - pq[u][lo];
            for (u64 d = diffb[y] & ((1ULL << c) - 1) & ~((1ULL << lo) - 1); d; d &= d - 1) {
                int m = __builtin_ctzll(d);
                g -= pq[u][m + 1] - pq[u][m];
            }
            return std::max(0.0, g - kT);
        };
        // colsum[u][c] = sum of gval(u, y) over the units y of column c (c deeper than u's column).
        std::vector<std::vector<double>> colsum(P, std::vector<double>(H, 0.0));
        auto recompute_u = [&](int u) {
            int l = tcol(u);
            for (int c = 0; c < H; c++) {
                colsum[u][c] = 0;
                if (c <= l) continue;
                for (int y : colm[c]) colsum[u][c] += gval(u, l, y, c);
            }
        };
        for (int u = 0; u < P; u++) if (ucol[u] >= 0 && col[ucol[u]] >= 0) recompute_u(u);
        auto proxy_u = [&](int u) {
            int l = tcol(u);
            double s = 0;
            for (int c = l + 1; c < H; c++) if (!colm[c].empty()) s += (double)colsum[u][c] / colm[c].size();
            return s;
        };
        double total_proxy = 0;
        for (int u = 0; u < P; u++) if (ucol[u] >= 0 && col[ucol[u]] >= 0) total_proxy += proxy_u(u);
        std::cerr << "climb_proxy_before = " << total_proxy / P << '\n';
        std::mt19937_64 rng(999);
        int accepted = 0;
        long long climb_iters = 0;
        // Incremental: a target u not in x or y only sees the sums of columns a and b change, by
        // g(u, y in a) - g(u, x in a) and g(u, x in b) - g(u, y in b); the targets of x and y are
        // recomputed. Optional simulated annealing (CLIMB_T0, temperature falling to 0).
        const double kT0 = env_double("CLIMB_T0", 0.0), t_begin = elapsed_sec();
        double temp = kT0;
        std::vector<int> others;
        std::vector<std::array<double, 2>> dlt;
        std::vector<int> moved;
        std::vector<std::vector<double>> moved_saved;
        auto unif = [&]() { return (rng() >> 11) * 0x1.0p-53; };
        for (int it = 0;; it++) {
            if (iters > 0) {
                if (it >= iters) break;
                temp = kT0 * (1.0 - (double)it / iters);
            } else if ((it & 63) == 0) {
                double now = elapsed_sec();
                if (now >= t_end) break;
                temp = kT0 * std::max(0.0, (t_end - now) / std::max(1e-9, t_end - t_begin));
            }
            climb_iters = it + 1;
            int x = rng() % U, y = rng() % U;
            int a = col[x], b = col[y];
            if (a < 0 || b < 0 || a == b) continue;
            if ((units[x][1] >= 0) != (units[y][1] >= 0)) continue;
            int cxa = color_at(x, a), cyb = color_at(y, b);
            if (color_at(x, b) != cyb || color_at(y, a) != cxa) continue;
            const u64 affected = (unit_holes(x, a) ^ unit_holes(x, b)) | (unit_holes(y, a) ^ unit_holes(y, b));
            double dmodel = -fix_cost(affected);
            add_holes(x, a, -1), add_holes(y, b, -1), add_holes(x, b, 1), add_holes(y, a, 1);
            dmodel += fix_cost(affected);
            const double na = colm[a].size(), nb = colm[b].size();
            const int hi = std::max(a, b);
            double dproxy = 0;
            others.clear();
            dlt.clear();
            for (int u = 0; u < P; u++) {
                if (ucol[u] < 0 || ucol[u] == x || ucol[u] == y) continue;
                int l = tcol(u);
                if (l >= hi) continue;
                double da = 0, db = 0;
                if (a > l) da = gval(u, l, y, a) - gval(u, l, x, a);
                if (b > l) db = gval(u, l, x, b) - gval(u, l, y, b);
                if (da || db) {
                    others.push_back(u);
                    dlt.push_back({da, db});
                    dproxy += da / na + db / nb;
                }
            }
            moved.clear();
            for (int t : units[x]) if (t >= 0) moved.push_back(t);
            for (int t : units[y]) if (t >= 0) moved.push_back(t);
            moved_saved.resize(moved.size());
            for (size_t i = 0; i < moved.size(); i++) {
                dproxy -= proxy_u(moved[i]);
                moved_saved[i] = colsum[moved[i]];
            }
            auto apply = [&](int cx, int cy) {
                auto& ma = colm[col[x]];
                ma.erase(std::find(ma.begin(), ma.end(), x));
                auto& mb = colm[col[y]];
                mb.erase(std::find(mb.begin(), mb.end(), y));
                col[x] = cx;
                col[y] = cy;
                colm[cx].push_back(x);
                colm[cy].push_back(y);
            };
            apply(b, a);
            for (int t : moved) {
                recompute_u(t);
                dproxy += proxy_u(t);
            }
            double delta = dmodel - kW * dproxy;
            if (delta < -1e-9 || (temp > 0 && std::exp(-delta / temp) > unif())) {
                accepted++;
                total_proxy += dproxy;
                for (size_t i = 0; i < others.size(); i++) {
                    colsum[others[i]][a] += dlt[i][0];
                    colsum[others[i]][b] += dlt[i][1];
                }
            } else {
                apply(a, b);
                for (size_t i = 0; i < moved.size(); i++) colsum[moved[i]] = moved_saved[i];
                add_holes(x, b, -1), add_holes(y, a, -1), add_holes(x, a, 1), add_holes(y, b, 1);
            }
        }
        std::cerr << "climb_proxy_after = " << total_proxy / P << "\nclimb_accepted = " << accepted
                  << "\nclimb_iters = " << climb_iters << "\nclimb_end_sec = " << elapsed_sec() << '\n';
        // The majority colors and their gains used by the plan search (set by anneal_units) follow
        // the exchanges.
        if (kClimbBias && !bias_c.empty()) {
            double fixes = 0;
            for (int m = 0; m < H; m++) {
                double p1 = hn[m] ? (double)hn1[m] / hn[m] : 0.5;
                bias_c[m] = p1 > 0.5 ? 1 : 0;
                bias_g[m] = std::abs(2 * p1 - 1);
                fixes += 2.0 * hn[m] * p1 * (1 - p1);
            }
            std::cerr << "climb_hole_fixes = " << fixes / P << '\n';
        }
        for (int l = 0; l < H; l++) members[l][0].clear(), members[l][1].clear();
        for (int x = 0; x < U; x++) {
            if (col[x] < 0) continue;
            members[col[x]][color_at(x, col[x])].push_back(x);
        }
    }
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
        // Handle holes (tiny-bias). A hole at handle h_m shows the top of column m, which keeps the
        // color set for the last request that needed h_m (the tiny exact models keep such stable
        // backgrounds and put the holes where the targets agree with them). If the targets with a
        // hole at h_m have color 1 with frequency p_m, a request needs a fix with probability
        // 2 p_m (1 - p_m) instead of 1/2: the holes of handle m cost kHandleHole * n_m *
        // (a * 4 p_m (1 - p_m) + 1 - a) (n_m = targets with a hole there, a = kBiasMix; a = 0 is
        // the former cost of kHandleHole per hole). For speed the annealing uses the marginal
        // cost of one hole of color c at h_m, w[c][m] = a * 4 (1 - p_m(c))^2 + 1 - a with p_m(c)
        // the frequency of color c, frozen between refreshes (every kRefresh iterations, from a
        // recount of the current assignment). dsum[t][l] = sum of w over the handles m > l at
        // the colors of target t (the triangle holes of t in column l).
        const double kBiasMix = env_double("BIAS_MIX", 1.0);
        const int kRefresh = env_int("BIAS_REFRESH", 1 << 14);
        std::vector<std::array<double, 2>> wcol(H, {1.0, 1.0});
        std::vector<u64> hb(P, 0);  // hb[t] bit m: color of target t at handle h_m
        std::vector<double> dsum((size_t)P * (H + 1), 0.0);
        auto make_tables = [&]() {
            for (int t = 0; t < P; t++) {
                hb[t] = 0;
                for (int m = 0; m < H; m++) hb[t] |= (A[t] >> handle[m] & 1) << m;
                double* d = &dsum[(size_t)t * (H + 1)];
                d[H - 1] = 0;
                for (int l = H - 2; l >= 0; l--) d[l] = d[l + 1] + wcol[l + 1][hb[t] >> (l + 1) & 1];
            }
        };
        make_tables();
        // Updates hb and dsum after the handles a and b (and their weights) were swapped: only the
        // prefix sums dsum[t][l] with a <= l < b change, by the change of the term at position b.
        auto swap_tables = [&](int a, int b) {
            if (a > b) std::swap(a, b);
            for (int t = 0; t < P; t++) {
                int ca = hb[t] >> a & 1, cb = hb[t] >> b & 1;
                if (ca != cb) hb[t] ^= (1ULL << a) | (1ULL << b);
                double delta = wcol[b][ca] - wcol[a][cb];
                double* d = &dsum[(size_t)t * (H + 1)];
                for (int l = a; l < b; l++) d[l] += delta;
            }
        };
        auto hole_w = [&](int u, int v, int l) {  // weighted handle holes of unit (u, v) in column l
            double c = dsum[(size_t)u * (H + 1) + l];
            if (v >= 0) {
                c += dsum[(size_t)v * (H + 1) + l];
                u64 d = (hb[u] ^ hb[v]) & ((2ULL << l) - 1);
                for (; d; d &= d - 1) {
                    int m = __builtin_ctzll(d);
                    c += wcol[m][0] + wcol[m][1];
                }
            }
            return c;
        };
        auto unit_cost = [&](int u, int v, int l) {  // holes cost of unit (u, v) in column l
            int targets = v >= 0 ? 2 : 1;
            double c = kHandleHole * hole_w(u, v, l);
            if (v >= 0) {
                u64 diff = A[u] ^ A[v];
                auto [t, bad] = touch(A[u], diff);
                c += targets * (kBlock * t + kIncons * bad);
            }
            return c;
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
        // Recounts the holes per handle and their colors from the current assignment, sets the
        // marginal weights and returns the persistence-model cost of the holes (fixes/request).
        auto refresh = [&]() {
            std::vector<int> n(H, 0), n1(H, 0);
            for (int x = 0; x < U; x++) {
                if (col[x] < 0) continue;
                auto [u, v] = units[x];
                u64 holes = ((H >= 64 ? ~0ULL : (1ULL << H) - 1)) & ~((2ULL << col[x]) - 1);
                if (v >= 0) holes |= hb[u] ^ hb[v];
                for (int t : {u, v}) {
                    if (t < 0) continue;
                    for (u64 s = holes; s; s &= s - 1) {
                        int m = __builtin_ctzll(s);
                        n[m]++;
                        n1[m] += hb[t] >> m & 1;
                    }
                }
            }
            double fixes = 0;
            if (std::getenv("BIAS_DUMP")) {
                std::cerr << "bias_p_by_depth:";
                for (int m = 0; m < H; m++)
                    std::cerr << ' ' << n[m] << ':' << (n[m] ? std::max(n1[m], n[m] - n1[m]) * 100 / n[m] : 50);
                std::cerr << '\n';
            }
            for (int m = 0; m < H; m++) {
                double p1 = n[m] ? (double)n1[m] / n[m] : 0.5;
                wcol[m][1] = kBiasMix * 4 * (1 - p1) * (1 - p1) + 1 - kBiasMix;
                wcol[m][0] = kBiasMix * 4 * p1 * p1 + 1 - kBiasMix;
                fixes += 2.0 * n[m] * p1 * (1 - p1);
            }
            make_tables();
            return fixes / P;
        };
        auto total_cost = [&]() {
            double c = 0;
            for (int x = 0; x < U; x++) if (col[x] >= 0) c += unit_cost(units[x][0], units[x][1], col[x]);
            for (int l = 0; l < H; l++) c += col_cost(l);
            return c / P;
        };
        if (kBiasMix > 0) refresh();
        std::cerr << "anneal_start_sec = " << elapsed_sec() << '\n';
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
        [[maybe_unused]] auto pairs_agree_in = [&](int l) {  // every pair of column l agrees at its handle
            for (int x = 0; x < U; x++) {
                if (col[x] != l || units[x][1] < 0) continue;
                if ((A[units[x][0]] ^ A[units[x][1]]) >> handle[l] & 1) return false;
            }
            return true;
        };
        [[maybe_unused]] auto recount = [&]() {
            std::fill(cnt0.begin(), cnt0.end(), 0);
            std::fill(cnt1.begin(), cnt1.end(), 0);
            std::fill(tgt.begin(), tgt.end(), 0);
            for (int x = 0; x < U; x++) if (col[x] >= 0) add_unit(x);
        };
        double cur_total = total_cost() * P;
        const bool bias_debug = std::getenv("BIAS_DEBUG") != nullptr;
        double max_drift = 0;
        const double t_begin = elapsed_sec(), t_end = env_double("HUB_TL", 1.1);
        double progress = 0, temp = t0;
        long long anneal_iters = 0;
        // Targeted re-pairing: from progress kTgtStart on, Y is frozen and the exchange move takes
        // the new partner of a pair's target among its consistent partners (most random exchanges
        // make an inconsistent pair and are rejected).
        const double kTgtStart = env_double("CB_TGT_START", 0.1), kTgtRate = env_double("CB_TGT_RATE", 0.9);
        bool targeted = false;
        std::vector<std::vector<int>> partners(P);
        std::vector<int> unit_of(P, -1);
        for (int x = 0; x < U; x++) {
            unit_of[units[x][0]] = x;
            if (units[x][1] >= 0) unit_of[units[x][1]] = x;
        }
        for (int it = 0;; it++) {
            anneal_iters = it;
            if (!targeted && kTgtRate > 0 && progress >= kTgtStart) {
                targeted = true;
                for (int u = 0; u < P; u++)
                    for (int w = 0; w < P; w++)
                        if (w != u && touch(A[u], A[u] ^ A[w]).second == 0) partners[u].push_back(w);
            }
            if (iters > 0) {
                if (it >= iters) break;
                progress = (double)it / iters;
            } else if ((it & 255) == 0) {
                progress = (elapsed_sec() - t_begin) / std::max(1e-9, t_end - t_begin);
                if (progress >= 1) break;
            }
            temp = t0 * std::pow(t1 / t0, progress);
            if (kBiasMix > 0 && (it % kRefresh) == kRefresh - 1) {
                if (bias_debug) {  // the incremental total must match a full recomputation
                    double full = total_cost() * P;
                    max_drift = std::max(max_drift, std::abs(full - cur_total));
                }
                refresh();
                cur_total = total_cost() * P;  // the weights changed
            }
            double r = unif();
            if (targeted && r < yflip_rate) r += yflip_rate + wmove_rate;  // Y is frozen
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
                int j1 = rnd(N);
                if (!(gmask >> j1 & 1)) continue;
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
                // Swap the handle windows of two columns a < b (changes colors, agreement, shallow
                // sets). The weights follow the windows, so only the units of the columns a..b-1
                // change their hole cost (their deep holes include position b but not a, their
                // pair differences position a but not b), plus the column costs of a and b (the
                // colors at their handles): computed incrementally, the tables are updated only
                // when the swap is accepted.
                int a = rnd(H), b = rnd(H);
                if (a == b) continue;
                if (a > b) std::swap(a, b);
                // One pass over the units of the columns a..b: hole cost change dh, and the colors
                // of the units of columns a and b at their new handles (a takes the window of b
                // and vice versa; a pair must agree there).
                double dh = 0;
                int n0a = 0, n1a = 0, n0b = 0, n1b = 0;
                bool ok = true;
                for (int x = 0; x < U && ok; x++) {
                    int l = col[x];
                    if (l < a || l > b) continue;
                    auto [u, v] = units[x];
                    if (l < b) {
                        for (int t : {u, v}) {
                            if (t < 0) continue;
                            dh += wcol[a][hb[t] >> a & 1] - wcol[b][hb[t] >> b & 1];
                        }
                        if (v >= 0) {
                            u64 df = hb[u] ^ hb[v];
                            if (df >> b & 1) dh += wcol[b][0] + wcol[b][1];
                            if (df >> a & 1) dh -= wcol[a][0] + wcol[a][1];
                        }
                    }
                    if (l == a || l == b) {
                        int pos = l == a ? b : a;  // position of the new handle window of l
                        if (v >= 0 && ((hb[u] ^ hb[v]) >> pos & 1)) ok = false;
                        int c = hb[u] >> pos & 1;
                        if (l == a) (c ? n1a : n0a)++;
                        else (c ? n1b : n0b)++;
                    }
                }
                if (!ok) continue;
                double before_cols = col_cost(a) + col_cost(b);
                std::swap(handle[a], handle[b]);
                int s0a = cnt0[a], s1a = cnt1[a], s0b = cnt0[b], s1b = cnt1[b];
                cnt0[a] = n0a, cnt1[a] = n1a, cnt0[b] = n0b, cnt1[b] = n1b;
                double delta = kHandleHole * dh + col_cost(a) + col_cost(b) - before_cols;
                if (delta > 0 && std::exp(-delta / temp) < unif()) {
                    std::swap(handle[a], handle[b]);
                    cnt0[a] = s0a, cnt1[a] = s1a, cnt0[b] = s0b, cnt1[b] = s1b;
                } else {
                    cur_total += delta;
                    std::swap(wcol[a], wcol[b]);
                    swap_tables(a, b);
                    for (int l = 0; l < H; l++) shallow[l + 1] = shallow[l] | 1ULL << handle[l];
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
                if (units[x][1] < 0) continue;  // x must be a pair
                int y, ix, iy;
                if (targeted && unif() < kTgtRate) {
                    ix = rnd(2);
                    const auto& pl = partners[units[x][1 - ix]];
                    if (pl.empty()) continue;
                    int w = pl[rnd((int)pl.size())];
                    y = unit_of[w];
                    if (y == x || y < 0 || col[y] < 0) continue;
                    iy = units[y][0] == w ? 0 : 1;
                } else {
                    y = rnd(U);
                    if (y == x || col[y] < 0) continue;
                    ix = rnd(2), iy = (units[y][1] >= 0) ? rnd(2) : 0;
                }
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
                    for (int t : nx) if (t >= 0) unit_of[t] = x;
                    for (int t : ny) if (t >= 0) unit_of[t] = y;
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
        if (bias_debug) std::cerr << "bias_max_drift = " << max_drift << '\n';
        std::cerr << "repaired_pairs = " << repaired << '\n';
        std::cerr << "anneal_iters = " << anneal_iters << '\n';
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
            std::cerr << "model_hole_fixes = " << refresh() << '\n';
            // Majority color c_m and its gain 2 p_m - 1 per handle position, for the value of the
            // column tops left by a plan (see process()).
            bias_c.assign(H, 0);
            bias_g.assign(H, 0.0);
            for (int m = 0; m < H; m++) {
                double w0 = wcol[m][0], w1 = wcol[m][1];  // w1 < w0 iff color 1 is the majority
                bias_c[m] = w1 < w0 ? 1 : 0;
                // w = 4 (1 - p(c))^2 with mix 1: p(majority) = 1 - sqrt(w_majority) / 2
                double wm = std::min(w0, w1);
                double pm = kBiasMix > 0 ? 1 - std::sqrt(std::max(0.0, (wm - (1 - kBiasMix)) / kBiasMix)) / 2 : 0.5;
                bias_g[m] = std::max(0.0, 2 * pm - 1);
            }
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
    // audit-merge: a move that leaves the paper where it is (1 to 5 per case in tiny-bias, pool-climb
    // and mix-pt, e.g. a filler re-leveled to its own place) is not output.
    void move(int k, int d) {
        int i = index_of(k);
        if (i == d) return;
        if (check_vis && !visible(k)) invalid = true;
#ifdef DEBUG_VIS
        if (!visible(k)) { std::cerr << "invisible move of " << k << '\n'; std::exit(1); }
#endif
        order.erase(order.begin() + i);
        order.insert(order.begin() + d, k);
        ops.push_back({k, d});
    }
    void move_after(int k, int x) {
        int i = index_of(k);
        if (index_of(x) + 1 == i) return;
        if (check_vis && !visible(k)) invalid = true;
#ifdef DEBUG_VIS
        if (!visible(k)) { std::cerr << "invisible move of " << k << '\n'; std::exit(1); }
#endif
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
    // audit2-blk: lookahead policy for the generic layer (see the header comment). Local paper
    // index 0 = base, 1 + b = flip paper of block b; a state is their order (top first), encoded in
    // base 6 (nb <= 5, 6 papers; otherwise the former procedure is used).
    bool blk_ok = false;
    std::vector<int> blk_paper;                 // local index -> paper id
    std::vector<std::array<int8_t, 6>> blk_st;  // states
    std::vector<int> blk_code;                  // base-6 code -> state index (-1)
    std::vector<int16_t> blk_dist;              // [s * S + t] moves from s to t
    std::vector<int16_t> blk_nxt;               // [s * S + t] first move on a shortest path: paper local index * 8 + depth
    std::vector<double> blk_v;                  // expected moves of the next pair target from s
    std::vector<std::vector<int>> blk_sat;      // satisfying states per want code (3^nb), filled lazily
    std::vector<char> blk_sat_done;
    int blk_S = 0;
    long long stat_blk_policy = 0, stat_blk_fallback = 0;
    const bool kBlkPolicy = env_int("BLK_POLICY", 1) != 0;
    int blk_encode(const std::array<int8_t, 6>& o, int n) const {
        int c = 0;
        for (int i = n - 1; i >= 0; i--) c = c * 6 + o[i];
        return c;
    }
    bool blk_visible(const std::array<int8_t, 6>& o, int n, int pos) const {
        int k = o[pos];
        if (k == 0) {  // base: visible iff some flip is below it
            for (int i = pos + 1; i < n; i++) if (o[i] != 0) return true;
            return false;
        }
        for (int i = 0; i < pos; i++) if (o[i] == 0) return false;  // a flip below the base is hidden
        return true;
    }
    int blk_orient(const std::array<int8_t, 6>& o, int n, int b) const {  // 1 iff flip b above the base
        for (int i = 0; i < n; i++) {
            if (o[i] == 1 + b) return 1;
            if (o[i] == 0) return 0;
        }
        return 0;
    }
    int blk_want_code(const std::vector<int>& want) const {
        int c = 0;
        for (int b = (int)want.size() - 1; b >= 0; b--) c = c * 3 + (want[b] + 1);
        return c;
    }
    bool blk_sat_state(int s, const std::vector<int>& want) const {
        int n = blocks.size() + 1;
        for (int b = 0; b < (int)want.size(); b++)
            if (want[b] >= 0 && blk_orient(blk_st[s], n, b) != want[b]) return false;
        return true;
    }
    const std::vector<int>& blk_sat_list(const std::vector<int>& want) {
        int c = blk_want_code(want);
        if (!blk_sat_done[c]) {
            blk_sat_done[c] = 1;
            for (int s = 0; s < blk_S; s++) if (blk_sat_state(s, want)) blk_sat[c].push_back(s);
        }
        return blk_sat[c];
    }
    void build_block_tables() {
        int nb = blocks.size(), n = nb + 1;
        if (!kBlkPolicy || nb < 1 || nb > 5) return;
        blk_paper.assign(n, -1);
        blk_paper[0] = base_paper;
        for (int b = 0; b < nb; b++) blk_paper[1 + b] = blocks[b].pf;
        std::array<int8_t, 6> o{};
        for (int i = 0; i < n; i++) o[i] = i;
        int pw = 1;
        for (int i = 0; i < n; i++) pw *= 6;
        blk_code.assign(pw, -1);
        do {
            blk_code[blk_encode(o, n)] = blk_st.size();
            blk_st.push_back(o);
        } while (std::next_permutation(o.begin(), o.begin() + n));
        blk_S = blk_st.size();
        const int S = blk_S;
        // Legal moves: (next state, paper local index, depth)
        std::vector<std::vector<std::array<int, 3>>> adj(S);
        std::vector<std::vector<int>> radj(S);
        for (int s = 0; s < S; s++) {
            const auto& st = blk_st[s];
            for (int i = 0; i < n; i++) {
                if (!blk_visible(st, n, i)) continue;
                for (int d = 0; d < n; d++) {
                    if (d == i) continue;
                    auto o2 = st;
                    int k = o2[i];
                    for (int j = i; j + 1 < n; j++) o2[j] = o2[j + 1];
                    for (int j = n - 1; j > d; j--) o2[j] = o2[j - 1];
                    o2[d] = k;
                    int t = blk_code[blk_encode(o2, n)];
                    adj[s].push_back({t, k, d});
                    radj[t].push_back(s);
                }
            }
        }
        blk_dist.assign((size_t)S * S, 1000);
        blk_nxt.assign((size_t)S * S, -1);
        std::vector<int> q;
        for (int s = 0; s < S; s++) {
            // BFS from s; nxt[s][t] = the first move of the path found (parents propagate it).
            int16_t* ds = &blk_dist[(size_t)s * S];
            int16_t* nx = &blk_nxt[(size_t)s * S];
            q.assign(1, s);
            ds[s] = 0;
            for (size_t h = 0; h < q.size(); h++) {
                int x = q[h];
                for (auto [t, k, d] : adj[x]) {
                    if (ds[t] <= ds[x] + 1) continue;
                    ds[t] = ds[x] + 1;
                    nx[t] = x == s ? (int16_t)(k * 8 + d) : nx[x];
                    q.push_back(t);
                }
            }
        }
        // Wants of the pair targets, their satisfying states and distances (backward BFS), V.
        int W3 = 1;
        for (int b = 0; b < nb; b++) W3 *= 3;
        blk_sat.assign(W3, {});
        blk_sat_done.assign(W3, 0);
        blk_v.assign(S, 0.0);
        std::vector<int> wcount(W3, 0);
        int npair = 0;
        for (int u = 0; u < P; u++) {
            int D = ded[u];
            if (D < 0) continue;
            u64 gh = gmask & ~paper[D].opaque;
            if (!gh) continue;
            wcount[blk_want_code(wanted_blocks(u, gh))]++;
            npair++;
        }
        std::vector<int> dsat(S);
        for (int c = 0; c < W3 && npair > 0; c++) {
            if (!wcount[c]) continue;
            std::vector<int> want(nb);
            for (int b = 0, x = c; b < nb; b++, x /= 3) want[b] = x % 3 - 1;
            const auto& sl = blk_sat_list(want);
            std::fill(dsat.begin(), dsat.end(), 1000);
            q.clear();
            for (int s : sl) dsat[s] = 0, q.push_back(s);
            for (size_t h = 0; h < q.size(); h++) {
                int x = q[h];
                for (int p : radj[x])
                    if (dsat[p] > dsat[x] + 1) dsat[p] = dsat[x] + 1, q.push_back(p);
            }
            for (int s = 0; s < S; s++) blk_v[s] += (double)wcount[c] * dsat[s] / npair;
        }
        blk_ok = true;
        std::cerr << "blk_states = " << S << "\nblk_build_sec = " << elapsed_sec() << '\n';
    }
    // Sets block b to orientation want[b] for every b with want[b] >= 0 (others are free).
    void set_blocks(const std::vector<int>& want) {
        int nb = blocks.size();
        if (blk_ok) {
            // The policy applies when the generic papers are the top of the stack (the lifted paper
            // of the previous request is back or set aside); otherwise the former procedure.
            int n = nb + 1;
            std::array<int8_t, 6> o{};
            bool top = true;
            for (int i = 0; i < n && top; i++) {
                int k = order[i];
                int li = k == base_paper ? 0 : (block_of[k] >= 0 && block_of[k] < nb ? 1 + block_of[k] : -1);
                if (li < 0) top = false;
                else o[i] = li;
            }
            if (top) {
                int s = blk_code[blk_encode(o, n)];
                const auto& sl = blk_sat_list(want);
                int best = -1;
                for (int t : sl) {
                    if (best < 0) { best = t; continue; }
                    int16_t dt = blk_dist[(size_t)s * blk_S + t], db = blk_dist[(size_t)s * blk_S + best];
                    if (dt < db || (dt == db && blk_v[t] < blk_v[best] - 1e-12)) best = t;
                }
                if (best >= 0 && blk_dist[(size_t)s * blk_S + best] < 1000) {
                    stat_blk_policy++;
                    while (s != best) {
                        int mv = blk_nxt[(size_t)s * blk_S + best];
                        int k = mv / 8, d = mv % 8;
                        move(blk_paper[k], d);
                        // follow the state
                        auto o2 = blk_st[s];
                        int i = 0;
                        while (o2[i] != k) i++;
                        for (int j = i; j + 1 < n; j++) o2[j] = o2[j + 1];
                        for (int j = n - 1; j > d; j--) o2[j] = o2[j - 1];
                        o2[d] = k;
                        s = blk_code[blk_encode(o2, n)];
                    }
                    return;
                }
            }
            stat_blk_fallback++;
        }
        set_blocks_old(want);
    }
    void set_blocks_old(const std::vector<int>& want) {
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
        if (x == top_d) {
            // Lifted straight from the fillers: back below its cyclic predecessor (keeps the color
            // alternation of the column).
            int pr = top_pred;
            top_d = -1;
            top_pred = -1;
            if (pr >= 0 && in_column(pr, col_of[pr])) {
                move_after(x, pr);
                return;
            }
        }
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
        int fret_ret = 1;       // audit2-ret: return_paper mode of the old fillers not re-used (fret_mode 3-5)
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
                int gain = save - kFillerCost - depth;
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
                int gain = save - kFillerCost - depth;
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
                int gain = save - kFillerCost - depth;
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
    // A filler from a column costs 1 move (+ depth) now and is charged at most 1 more for its return,
    // but papers left out are usually re-used or left in place: one that saves 2 + depth digs is
    // worth taking (2 instead of 3 + depth: seed 0-95 -1.48%, 96-191 -1.45%; 1 + depth: +6%).
    int kFillerCost = env_int("FILL_COST", 1);
    bool keep_harmless = env_int("KEEP_HARMLESS", 1) != 0;
    bool keep_harmless_now = false;
    // Joint choice of the papers out of their columns (the previous lifted paper x0 and the old
    // fillers) and of the new fillers from the column tops (fret_mode 5): one weighted interval
    // scheduling over the handle indices, where every candidate is an interval [lvl, c] of handles
    // that a paper of column c shows on (matching A_u on all the holes of D it covers):
    //   - a new filler, the paper at depth p <= kFillerDepth of column c: gain = saved digs - 1 - p
    //     (taken only if it saves at least kFillerCost + 1 + p, as choose_fillers_prelift);
    //   - an old paper moved to a new level (the move replaces its return, but it stays out):
    //     gain = saved digs - kJointRelevel (x0: - kJointPrev);
    //   - an old filler left where it is, when harmless: gain = saved digs + 1 - kJointStay.
    // Old papers not chosen go back to their columns (old fillers at the bottom or below their
    // predecessor, x0 with ret_mode). Saved digs are the handle_fix_cost of the covered holes in the
    // state before any move (such returns do not change the column tops). The requested paper D,
    // when it is an old filler, is lifted straight from there (no return, no dig).
    // seed 0-95 (annealing fixed at 3M iterations), against the plans of hole-relax alone:
    // re-level 1 / x0 0.8 -0.30 +- 0.05%, 0.5 / 0.5 -0.48 +- 0.05%, 1.5 / 1.5 -0.25 +- 0.06%;
    // the joint plan alone (without the other plans) is +1.1% worse.
    double kJointRelevel = env_double("JOINT_RELEVEL", 0.5), kJointPrev = env_double("JOINT_PREV", 0.5);
    double kJointStay = env_double("JOINT_STAY", 0.8);
    struct JointCand {
        int lvl, c;
        double gain;
        int kind;   // 0 new (idx = paper), 1 old re-level, 2 old stay (idx = index in olds), 3 x0
        int idx;
        bool post;  // new filler placed after the lift
    };
    // Depth of paper x in its column (papers in place only).
    int depth_in_column(int x) const {
        int i = 0;
        for (int k : order) {
            if (k == x) return i;
            if (in_column(k, col_of[x])) i++;
        }
        return -1;
    }
    bool last_pool_lift = false;
    void run_joint(int u, const PlanOpt& opt) {
        int d = ded[u];
        if (d < 0 || d == top_d) {
            invalid = true;
            return;
        }
        int l = col_of[d];
        u64 all = gmask;
        for (int j = 0; j < H; j++) all |= 1ULL << handle[j];
        u64 hole_all = all & ~paper[d].opaque;
        u64 hh = hole_all & ~gmask;
        std::vector<int> hidx(N, -1);
        for (int j = 0; j < H; j++) hidx[handle[j]] = j;
        std::vector<int> fix(H, 0);
        for (int j = 0; j < H; j++)
            if (hh >> handle[j] & 1) fix[j] = handle_fix_cost(j, A[u] >> handle[j] & 1);
        bool d_out = is_filler(d);  // D is an old filler: lifted directly
        std::vector<Filler> olds;
        for (auto& f : fillers) if (f.paper != d) olds.push_back(f);
        int x0 = top_d;
        std::vector<std::vector<JointCand>> cand_end(H);
        auto mism_level = [&](int x) {  // just past the deepest wrong handle of x
            u64 shown = paper[x].opaque & hh;
            u64 bad = (paper[x].black ^ A[u]) & shown;
            int lvl = 0;
            for (u64 b = bad; b; b &= b - 1) lvl = std::max(lvl, hidx[__builtin_ctzll(b)] + 1);
            return lvl;
        };
        auto saved = [&](int x, int lvl, int c, bool skip_c) {
            int sv = 0;
            for (int j = lvl; j <= c; j++)
                if ((hh >> handle[j] & 1) && (paper[x].opaque >> handle[j] & 1) && !(skip_c && j == c)) sv += fix[j];
            return sv;
        };
        // Old papers (L: current level of an old filler).
        auto add_old = [&](int x, int idx, int L, bool is_x0) {
            int c = col_of[x];
            int lvl = mism_level(x);
            bool hides_l = c >= l && (paper[x].opaque >> handle[l] & 1);  // could hide D's column top
            if (!d_out && hides_l) lvl = std::max(lvl, l + 1);
            if (lvl <= c) {
                int sv = saved(x, lvl, c, false);
                double g = sv - (is_x0 ? kJointPrev : kJointRelevel);
                if (!is_x0 && lvl == L) g = sv + 1 - kJointStay;  // already there
                if (g > 0) cand_end[c].push_back({lvl, c, g, is_x0 ? 3 : (lvl == L ? 2 : 1), idx, false});
            }
            if (!is_x0 && L > lvl && L <= c) {
                // Left at its level L (narrower than lvl): harmless iff it does not hide D's column
                // top (and it shows A_u on the holes it covers there, as L > lvl).
                bool harm = !d_out && L <= l && l <= c && (paper[x].opaque >> handle[l] & 1);
                if (!harm) {
                    double g = saved(x, L, c, false) + 1 - kJointStay;
                    if (g > 0) cand_end[c].push_back({L, c, g, 2, idx, false});
                }
            }
        };
        for (int i = 0; i < (int)olds.size(); i++) add_old(olds[i].paper, i, olds[i].lvl, false);
        if (x0 >= 0) add_old(x0, -1, -1, true);
        // New fillers from the column tops (as choose_fillers_prelift; all after the lift if D is
        // lifted from the fillers, as D on top hides the columns whose handles it covers).
        std::vector<int> top;
        for (int c = 0; c < H; c++) {
            if (c == l) continue;
            bool hole_c = hh >> handle[c] & 1;
            if (d_out && !hole_c) continue;
            top.clear();
            for (int k : order) {
                if (!in_column(k, c)) continue;
                top.push_back(k);
                if ((int)top.size() > kFillerDepth) break;
            }
            for (int depth = 0; depth < (int)top.size(); depth++) {
                int f = top[depth];
                int lvl = mism_level(f);
                if (lvl > c) continue;
                bool post = d_out || (c > l && lvl <= l && (paper[f].opaque >> handle[l] & 1));
                int sv = saved(f, lvl, c, depth == 0 && hole_c);
                int g = sv - 1 - depth;
                if (g >= kFillerCost && g > 0) cand_end[c].push_back({lvl, c, (double)g, 0, f, post});
            }
        }
        std::vector<double> best(H + 1, 0);
        std::vector<int> pick(H + 1, -1);
        for (int c = 0; c < H; c++) {
            best[c + 1] = best[c];
            for (int i = 0; i < (int)cand_end[c].size(); i++) {
                auto& cd = cand_end[c][i];
                if (best[cd.lvl] + cd.gain > best[c + 1] + 1e-9) {
                    best[c + 1] = best[cd.lvl] + cd.gain;
                    pick[c + 1] = i;
                }
            }
        }
        std::vector<JointCand> picks;
        for (int j = H; j > 0;) {
            if (pick[j] < 0) {
                j--;
                continue;
            }
            auto cd = cand_end[j - 1][pick[j]];
            picks.push_back(cd);
            j = cd.lvl;
        }
        std::vector<int> old_dec(olds.size(), 0), old_lvl(olds.size(), -1);  // 0 return, 1 re-level, 2 stay
        int x0_lvl = -1;
        for (auto& cd : picks) {
            if (cd.kind == 1 || cd.kind == 2) old_dec[cd.idx] = cd.kind, old_lvl[cd.idx] = cd.lvl;
            if (cd.kind == 3) x0_lvl = cd.lvl;
        }
        Filler fd{d, -1};  // D's record if it is an old filler (keeps its predecessor)
        for (auto& f : fillers) if (f.paper == d) fd = f;
        fillers = olds;
        auto relevel = [&](int x, int lvl) {  // just above the top of the first column >= lvl
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
        };
        if (d_out) fillers.push_back(fd);  // D stays a filler (in_column false) until lifted
        // Returns of the visible old fillers, then x0 (which may hide the others), then the other
        // returns, then the re-levels.
        std::vector<char> done(olds.size(), 0);
        for (int i = (int)olds.size() - 1; i >= 0; i--) {
            if (old_dec[i] != 0 || !visible(olds[i].paper)) continue;
            return_paper(olds[i].paper, u, opt.fret_ret);
            done[i] = 1;
        }
        if (x0 >= 0) {
            if (x0_lvl >= 0) {
                top_d = -1;
                relevel(x0, x0_lvl);
                Filler fl{x0, top_pred};
                top_pred = -1;
                fl.lvl = x0_lvl;
                fl.hi = col_of[x0];
                fillers.push_back(fl);
            } else {
                return_paper(x0, u, opt.ret_mode);
            }
        }
        for (int i = (int)olds.size() - 1; i >= 0; i--)
            if (old_dec[i] == 0 && !done[i]) return_paper(olds[i].paper, u, opt.fret_ret);
        for (int i = 0; i < (int)olds.size(); i++) {
            if (old_dec[i] == 0) continue;
            int x = olds[i].paper;
            for (auto& f : fillers)
                if (f.paper == x) f.lvl = old_lvl[i], f.hi = col_of[x];
            if (old_dec[i] == 1) relevel(x, old_lvl[i]);
        }
        u64 cov = 0;
        for (auto& f : fillers) {
            if (f.paper == d) continue;
            for (int j = f.lvl; j <= f.hi; j++)
                if (paper[f.paper].opaque >> handle[j] & 1) cov |= 1ULL << handle[j];
        }
        hh &= ~cov;
        set_blocks(wanted_blocks(u, hole_all));
        for (auto& cd : picks)
            if (cd.kind == 0 && !cd.post) place_filler(cd.c, depth_in_column(cd.idx), cd.lvl, hh);
        if (d_out) {
            for (size_t k = 0; k < fillers.size(); k++)
                if (fillers[k].paper == d) {
                    fillers.erase(fillers.begin() + k);
                    break;
                }
            move(d, 0);
        } else {
            while (column_top(l) != d) dig(l);
            move(d, 0);
        }
        top_d = d;
        top_pred = d_out ? fd.pred : -1;
        last_pool_lift = d_out;
        for (auto& cd : picks)
            if (cd.kind == 0 && cd.post) place_filler(cd.c, depth_in_column(cd.idx), cd.lvl, hh);
        for (int j = 0; j < H; j++)
            if (hh >> handle[j] & 1) set_handle(j, A[u] >> handle[j] & 1);
    }

    void run_plan(int u, const PlanOpt& opt) {
        if (opt.fret_mode == 5) {
            last_pool_lift = false;
            run_joint(u, opt);
            return;
        }
        keep_harmless_now = opt.fret_mode == 4;
        u64 all = gmask;
        for (int l = 0; l < H; l++) all |= 1ULL << handle[l];
        bool kept = opt.keep && top_d >= 0 && ded[u] == top_d;
        u64 pre_cov = 0;  // handles covered by the previous paper used as a filler (ret_mode 3)
        // ret_mode 4 (audit-stay): the previous paper x stays where it is and D goes above it, so x
        // shows on the holes of D up to its own handle (it must show A_u there; it is above the
        // generic layer, so D must have no generic hole where x is opaque). x is then kept out of its
        // column as a filler of level 0 (handles h_0..h_x), returned or re-used at a later request.
        int stay = -1, stay_pred = -1;
        if (opt.ret_mode == 4) {
            int d = ded[u];
            if (top_d < 0 || kept || d < 0 || d == top_d || ((all & ~paper[d].opaque & gmask) & paper[top_d].opaque)) {
                invalid = true;
                return;
            }
            stay = top_d;
            stay_pred = top_pred;  // lifted from the fillers: keeps its cyclic predecessor
            top_d = -1;
            top_pred = -1;
        }
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
                Filler fp{x, top_pred};
                fp.lvl = lvl;
                fp.hi = lp;
                placed.push_back(fp);
            }
            pre_cov |= cov0;
            if (opt.fret_mode >= 3) {
                refill_or_return(u, vis_old, all, pre_cov, placed, opt.fret_ret);
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
            top_pred = -1;
            if (opt.fret_mode >= 3) {
                refill_or_return(u, def_old, all, pre_cov, placed, opt.fret_ret);
            } else {
                for (int i = (int)def_old.size() - 1; i >= 0; i--) return_paper(def_old[i].paper, u, opt.fret_mode);
            }
            for (auto& f : placed) fillers.push_back(f);
            stat_prev_fill_try++;
        } else if (opt.fret_mode >= 3) {
            if (top_d >= 0 && !kept) return_paper(top_d, u, opt.ret_mode);
            std::vector<Filler> old = fillers, placed;
            refill_or_return(u, old, all, pre_cov, placed, opt.fret_ret);
            for (auto& f : placed) fillers.push_back(f);
        } else {
            if (top_d >= 0 && !kept) return_paper(top_d, u, opt.ret_mode);
            while (!fillers.empty()) return_paper(fillers.back().paper, u, opt.fret_mode);
        }
        if (stay >= 0) {
            Filler f{stay, stay_pred};
            f.lvl = 0;
            f.hi = col_of[stay];
            fillers.push_back(f);
            for (int j = 0; j <= f.hi; j++)
                if (paper[stay].opaque >> handle[j] & 1) pre_cov |= 1ULL << handle[j];
            stat_stay_try++;
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
                top_pred = -1;
                for (auto& pk : picks)
                    if (pk.post) place_filler(pk.c, pk.depth, pk.lvl, hh);
            } else {
                if (!kept) {
                    while (column_top(l) != d) dig(l);
                    move(d, 0);
                    top_d = d;
                    top_pred = -1;
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
        int top_d, top_pred;
        std::vector<Filler> fillers;
    };
    State save() const { return {order, top_d, top_pred, fillers}; }
    void restore(const State& st) {
        order = st.order;
        top_d = st.top_d;
        top_pred = st.top_pred;
        fillers = st.fillers;
    }
    bool search_on = env_int("SEARCH", 1) != 0;
    bool prev_filler = env_int("PREV_FILLER", 1) != 0;
    bool refill = env_int("REFILL", 1) != 0;
    bool joint_on = env_int("JOINT", 1) != 0;
    long long stat_joint = 0, stat_pool_lift = 0;
    long long stat_pred_out = 0, stat_stay = 0, stat_stay_try = 0;
    const bool kPrevStay = env_int("PREV_STAY", 1) != 0;
    const bool kFretRule = env_int("FRET_RULE", 1) != 0;  // audit2-ret
    long long stat_fret_rule = 0;
    long long stat_kept = 0, stat_fill = 0, stat_level_fill = 0, stat_prev_fill_try = 0, stat_prev_fill = 0,
              stat_refill_try = 0, stat_refill = 0;
    // Probe (BIAS_PROBE=1): at the start of a request, how many handle holes of the target's
    // paper see a column top of the wrong color (what the persistence model of the annealing
    // predicts as 2 p (1 - p) per hole).
    long long probe_holes = 0, probe_wrong = 0;
    void probe(int u) {
        int D = ded[u];
        if (D < 0) return;
        for (int m = 0; m < H; m++) {
            int w = handle[m];
            if (paper[D].opaque >> w & 1) continue;
            int t = column_top(m);
            if (t < 0) continue;
            probe_holes++;
            probe_wrong += (paper[t].black >> w & 1) != (A[u] >> w & 1);
        }
    }
    // Expected extra fixes caused by the column tops of the current state: a column whose top
    // shows the minority color at its handle costs 2 p_m - 1 more at the next request that needs
    // that handle (persistence model of the annealing).
    double tops_penalty() const {
        if (bias_g.empty()) return 0;
        static std::vector<char> seen;
        seen.assign(H, 0);
        double pen = 0;
        int found = 0;
        for (int k : order) {
            int l = col_of[k];
            if (l < 0 || seen[l] || !in_column(k, l)) continue;
            seen[l] = 1;
            if ((int)(paper[k].black >> handle[l] & 1) != bias_c[l]) pen += bias_g[l];
            if (++found == H) break;
        }
        return pen;
    }
    const double kTopValue = env_double("BIAS_TOPV", 0.55);
    // Peephole on the moves of a plan (audit-merge). The plans sometimes move a paper twice: an old
    // filler goes back below its predecessor and its column is then dug past it, or it goes back
    // and is placed again as a filler, or the requested paper is returned and then lifted. Moving
    // it at the first step straight to where the second step puts it (the same depth after the
    // second step, or just below the paper the second step puts it under) often keeps every move
    // legal and gives exactly the same final order: one move less, and the rest of the game is
    // unchanged. Each candidate is checked by replaying the moves, the others keeping the paper
    // they are inserted under. (seed 0-23: about 25 / 22 / 19 moves saved per case in tiny-bias / pool-climb / mix-pt.)
    const bool kMergeDouble = env_int("MERGE_DOUBLE", 1) != 0;
    void merge_double_moves(const std::vector<int>& start, std::vector<std::pair<int, int>>& mvs) const {
        bool dup = false;
        for (size_t i = 0; i < mvs.size() && !dup; i++)
            for (size_t j = i + 1; j < mvs.size(); j++)
                if (mvs[i].first == mvs[j].first) {
                    dup = true;
                    break;
                }
        if (!dup) return;
        struct M {
            int k, anchor, pos;  // inserted just below paper anchor (-1: at the top; -2: at index pos)
        };
        auto apply = [](std::vector<int>& ord, const M& m) {
            ord.erase(std::find(ord.begin(), ord.end(), m.k));
            if (m.anchor == -2) ord.insert(ord.begin() + m.pos, m.k);
            else if (m.anchor < 0) ord.insert(ord.begin(), m.k);
            else ord.insert(std::find(ord.begin(), ord.end(), m.anchor) + 1, m.k);
        };
        auto vis = [&](const std::vector<int>& ord, int k) {
            u64 cov = 0;
            for (int x : ord) {
                if (x == k) return (paper[k].opaque & ~cov) != 0;
                cov |= paper[x].opaque;
            }
            return false;
        };
        std::vector<int> want = start;
        std::vector<M> mv;
        for (auto [k, d] : mvs) {
            want.erase(std::find(want.begin(), want.end(), k));
            mv.push_back({k, d == 0 ? -1 : want[d - 1], 0});
            want.insert(want.begin() + d, k);
        }
        auto replay_ok = [&](const std::vector<M>& ms, int skip) {
            std::vector<int> ord = start;
            for (int t = 0; t < (int)ms.size(); t++) {
                if (t == skip) continue;
                if (ms[t].anchor == ms[t].k || !vis(ord, ms[t].k)) return false;
                apply(ord, ms[t]);
            }
            return ord == want;
        };
        for (bool again = true; again;) {
            again = false;
            for (int i = 0; i < (int)mv.size() && !again; i++)
                for (int j = i + 1; j < (int)mv.size(); j++) {
                    if (mv[j].k != mv[i].k) continue;
                    int k = mv[i].k;
                    std::vector<int> st = start;  // before step i
                    for (int t = 0; t < i; t++) apply(st, mv[t]);
                    std::vector<int> s2 = st;  // after step j
                    for (int t = i; t <= j; t++) apply(s2, mv[t]);
                    int pj = std::find(s2.begin(), s2.end(), k) - s2.begin();
                    st.erase(std::find(st.begin(), st.end(), k));
                    int pa = mv[j].anchor < 0 ? 0 : (int)(std::find(st.begin(), st.end(), mv[j].anchor) - st.begin()) + 1;
                    for (int p : {pj, pa}) {
                        if (p > (int)st.size()) continue;
                        auto m2 = mv;
                        m2[i] = {k, -2, p};
                        if (replay_ok(m2, j)) {
                            m2.erase(m2.begin() + j);
                            mv = m2;
                            again = true;
                            break;
                        }
                    }
                    if (!again && replay_ok(mv, i)) {  // or the first move is not needed at all
                        mv.erase(mv.begin() + i);
                        again = true;
                    }
                    break;  // only the next move of the same paper
                }
        }
        std::vector<int> ord = start;
        mvs.clear();
        for (auto& m : mv) {
            int before = std::find(ord.begin(), ord.end(), m.k) - ord.begin();
            apply(ord, m);
            int after = std::find(ord.begin(), ord.end(), m.k) - ord.begin();
            if (after != before) mvs.push_back({m.k, after});  // a merged move may leave it in place
        }
    }

    std::vector<std::pair<int, int>> process(int u) {
        static const bool kProbe = std::getenv("BIAS_PROBE") != nullptr;
        if (kProbe) probe(u);
        const State st0 = save();
        int top0 = top_d;
        std::vector<PlanOpt> opts;
        if (!search_on) {
            opts.push_back(PlanOpt{});
        } else {
            bool has_free_filler = false;  // a filler that goes back to the top or the bottom
            for (auto& f : fillers) has_free_filler |= f.pred < 0;
            bool prev_ok = top0 >= 0 && ded[u] >= 0 && ded[u] != top0 && prev_filler;
            // audit2-ret: the old fillers not re-used go back at the bottom (fret_ret 1) or by the
            // hub7 rule (0); only with a free filler (one taken from a column top), as the others go
            // back below their predecessor whatever the mode.
            std::vector<int> frets = {1};
            if (kFretRule && has_free_filler) frets.push_back(0);
            for (int rm = 1; rm <= (prev_ok ? 3 : 2); rm++)
                for (int fm : {1, 2, 3, 4})
                    for (int uf = env_int("UF_MIN", 1); uf < 2; uf++)  // plans without fillers are never better
                        for (int kp = 0; kp < ((top0 >= 0 && ded[u] == top0) ? 2 : 1); kp++)
                            for (int fr : (fm >= 3 ? frets : std::vector<int>{1}))
                                if ((fm == 2 && !has_free_filler) || (fm >= 3 && (!refill || fillers.empty())) || (fm == 4 && !keep_harmless))
                                    continue;
                                else
                                    opts.push_back(PlanOpt{rm, fm, uf == 1, kp == 1, fr});
            if (joint_on && ded[u] >= 0 && ded[u] != top0)
                for (int rm = 1; rm <= 2; rm++)
                    for (int fr : frets) opts.push_back(PlanOpt{rm, 5, true, false, fr});
            if (prev_ok && kPrevStay)  // audit-stay: the previous paper stays under the new one
                for (int fm : {1, 2, 3, 4})
                    for (int fr : (fm >= 3 ? frets : std::vector<int>{1}))
                        if (!((fm == 2 && !has_free_filler) || (fm >= 3 && (!refill || fillers.empty())) || (fm == 4 && !keep_harmless)))
                            opts.push_back(PlanOpt{4, fm, true, false, fr});
        }
        double best = 1e18;
        std::vector<std::pair<int, int>> best_ops;
        State best_state;
        PlanOpt best_opt;
        bool best_pool_lift = false;
        check_vis = true;
        for (const PlanOpt& o : opts) {
            restore(st0);
            ops.clear();
            invalid = false;
            run_plan(u, o);
            if (invalid || display() != A[u]) continue;
            if (!fillers_reachable()) continue;
            if (kMergeDouble) merge_double_moves(st0.order, ops);
            // A filler left out costs its return later, but is often re-used (refill) instead,
            // so it is charged less than a move now (seed 0-95: 1.0 -> 0.8 is -0.48%).
            double cost = ops.size() + kFillerCharge * fillers.size() + kTopValue * tops_penalty();
            if (cost < best) {
                best = cost;
                best_ops = ops;
                best_state = save();
                best_opt = o;
                best_pool_lift = o.fret_mode == 5 && last_pool_lift;
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
        stat_stay += best_opt.ret_mode == 4;
        stat_fret_rule += best_opt.fret_ret == 0;
        ops = best_ops;
        stat_kept += best_opt.keep && top0 >= 0 && ded[u] == top0;
        stat_prev_fill += best_opt.ret_mode == 3;
        stat_refill += best_opt.fret_mode == 3;
        stat_joint += best_opt.fret_mode == 5;
        stat_pool_lift += best_pool_lift;
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
    if (solver.probe_holes) {
        std::cerr << "probe_holes_per_req = " << (double)solver.probe_holes / r << '\n';
        std::cerr << "probe_wrong_rate = " << (double)solver.probe_wrong / solver.probe_holes << '\n';
    }
    std::cerr << "level_fillers_tried = " << solver.stat_level_fill << '\n';
    std::cerr << "prev_fillers_used = " << solver.stat_prev_fill << '\n';
    std::cerr << "refill_plans_used = " << solver.stat_refill << '\n';
    std::cerr << "prev_stay_used = " << solver.stat_stay << '\n';
    std::cerr << "pred_out_returns = " << solver.stat_pred_out << '\n';
    std::cerr << "joint_plans_used = " << solver.stat_joint << '\n';
    std::cerr << "pool_lifts = " << solver.stat_pool_lift << '\n';
    std::cerr << "fret_rule_used = " << solver.stat_fret_rule << '\n';
    std::cerr << "blk_policy = " << solver.stat_blk_policy << "\nblk_fallback = " << solver.stat_blk_fallback << '\n';
    std::cerr << "total_moves = " << total << '\n';
    return 0;
}
