// clean-base: solutions/audit4-flip-clk (the best solution, grown by many agents) rewritten without
// the options that were off or never taken, the experiment switches and most diagnostics. The
// moves are the same: with the annealing and the climb fixed to the same iteration counts
// (ANNEAL_ITERS, CLIMB_ITERS), the output is identical (solutions/clean-base/eqcheck.py). The
// history and the measurements of every part are in trial_log.md (hub .. audit4-, cons-).
//
// Windows: G = 30 generic windows cut into 5 blocks of 6, and H = 34 handle windows h_0..h_33.
// Papers, top to bottom at the start:
//   - Generic layer: the base paper F (colors Y_b on every block b) and one flip paper per block
//     (~Y_b on b, and Y_c on the blocks c < b). Block b shows ~Y_b ("on") iff its own flip is its
//     topmost covering paper: moving the flip of b up turns b on and the blocks c < b off.
//   - Dedicated papers in H columns: a paper of column l is opaque on G and on h_0..h_l and a hole
//     on the deeper handles. It serves one target u, or a pair (u, v) whose patterns differ only
//     where the blocks can show both (a consistent pair); then it is also a hole where A_u and A_v
//     differ. Under the generic layer the columns lie in the order 0, 1, ..., so the top of
//     column l shows on h_l only.
// Request u (paper D of column l): set the orientations of the blocks, rotate column l until D is
// its top ("dig") and move D to the very top. Every handle hole of D must then show A_u: by
// fillers (column papers placed just below the generic layer, showing on an interval of handles)
// or by digging the columns. D and the fillers stay out until a later request returns or re-uses
// them.
//
// Design (Solver::design):
//   choose_blocks       the G windows, the blocks and Y_b (hill climbing on the pair consistency)
//   (greedy)            the units (pairs and singles of targets) and their columns
//   anneal_units        simulated annealing of the pairing, the columns, the handle order and Y
//                       on a model of the moves (until 1.1 s)
//   filler_climb        exchanges of units between columns for better fillers (until 1.15 s)
//   split_inconsistent  fallback for a pair still inconsistent: split a block
//   build_block_tables  the lookahead policy of the generic layer (set_blocks)
// Requests (Solver::process): every combination of the plan options (PlanOpt) is simulated on a
// copy of the state; the plan of least cost (moves after merge_double_moves, + 0.8 per paper left
// out of its column, + 0.55 tops_penalty) is kept, and the records of the papers out of their
// columns are rebuilt from the order (canonicalize).
//   run_plan            the previous lifted paper (return_paper, re-used as a filler, or left under
//                       the new one), the old fillers (return_paper or refill_or_return), the
//                       blocks (set_blocks), new fillers (choose_fillers_prelift, place_filler), the
//                       lift of D (lift) and the digs of the remaining handle holes (fix_handles)
//   run_joint           the papers out and the new fillers chosen by one interval DP
//   set_blocks          the generic layer: the lookahead policy on the precomputed tables, or a BFS
//                       when a dedicated paper lies above it (set_blocks_blocked), or the plain
//                       procedure after a split (set_blocks_plain)
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

constexpr int N = 64, K = 192, P = 256, H = 34, G = N - H;

// Every clock reading is multiplied by CLOCK_SCALE (CLAUDE.md, the clock scale): the local
// evaluation compiles with -DCLOCK_SCALE=1.1 so that it searches as much as the judge.
#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
const auto kStartTime = std::chrono::steady_clock::now();
double elapsed_sec() {
    return CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() - kStartTime).count();
}

// Fixed iteration counts for experiments (ANNEAL_ITERS, CLIMB_ITERS; 0 or unset: until the time
// limits). The output then does not depend on the speed of the machine.
int env_int(const char* name) {
    const char* s = std::getenv(name);
    return s ? std::atoi(s) : 0;
}

// xoshiro256** seeded by splitmix64 (the annealing's generator).
struct Xoshiro256 {
    u64 s[4];
    explicit Xoshiro256(u64 seed) {
        for (auto& x : s) {
            u64 z = (seed += 0x9e3779b97f4a7c15ULL);
            z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
            z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
            x = z ^ (z >> 31);
        }
    }
    static u64 rotl(u64 x, int k) { return (x << k) | (x >> (64 - k)); }
    u64 operator()() {
        const u64 r = rotl(s[1] * 5, 7) * 9, t = s[1] << 17;
        s[2] ^= s[0];
        s[3] ^= s[1];
        s[1] ^= s[2];
        s[0] ^= s[3];
        s[2] ^= t;
        s[3] = rotl(s[3], 45);
        return r;
    }
};

u64 low_bits(int n) { return (1ULL << n) - 1; }  // bits 0..n-1 (n < 64)

// Persistence-weighted handle holes of a target (colors tb at the handles, column l) that the
// paper of a unit (colors yb, pair differences dy) of column c > l would cover as a filler, at the
// level just past its deepest mismatch with the target (h_c excluded), minus kT, at least 0.
// q[j] = sum over the handles m < j of 2 (1 - p_m(color of the target at h_m)): the fixes a covered
// hole saves relative to an unbiased handle (filler_climb's proxy, linearized in anneal_units).
double filler_gain(u64 tb, int l, u64 yb, u64 dy, int c, const double* q) {
    constexpr int kT = 3;
    u64 range = low_bits(c + 1) & ~dy & ~low_bits(l + 1);
    u64 mis = (yb ^ tb) & range;
    if (mis >> c & 1) return 0.0;
    int lvl = mis ? 64 - __builtin_clzll(mis) : 0;
    u64 cov = range & low_bits(c) & ~low_bits(lvl);
    if (!cov) return 0.0;
    int lo = __builtin_ctzll(cov);
    double g = q[c] - q[lo];
    for (u64 d = dy & low_bits(c) & ~low_bits(lo); d; d &= d - 1) {
        int m = __builtin_ctzll(d);
        g -= q[m + 1] - q[m];
    }
    return std::max(0.0, g - kT);
}

struct Paper {
    u64 opaque = 0, black = 0;
};

struct Block {
    u64 mask = 0;  // windows of the block
    u64 y = 0;     // colors Y_b (black windows, subset of mask)
    int pf = -1;   // flip paper
};

struct Solver {
    std::vector<u64> A;
    std::vector<int> handle;   // window of each handle h_j
    std::vector<int> hidx;     // handle index of each window (-1 for the G windows)
    u64 gmask = 0, hmask = 0;  // G windows, handle windows
    std::vector<Block> blocks;
    std::vector<int> flip_cov;  // flip_cov[b]: the other blocks (bits) the flip of b covers with Y
    std::vector<Paper> paper;
    std::vector<u64> h_opq, h_blk;  // per paper: opaque / black handles, by handle index
    std::vector<int> col_of;        // column of a dedicated paper, -1 otherwise
    std::vector<int> block_of;      // block of a flip paper (nb for the base paper), -1 otherwise
    std::vector<int> ded;           // dedicated paper of each target, -1 if none
    int base_paper = 0;
    std::vector<int> bias_c;     // majority color of the targets with a hole at handle h_m
    std::vector<double> bias_g;  // 2 p_m - 1: fixes saved when the top of column m shows bias_c[m]
    // Design: units (u, v), v = -1 for a single target; members[l][c] = units of column l whose
    // color at h_l is c.
    std::vector<std::array<int, 2>> units;
    std::vector<std::array<std::vector<int>, 2>> members;

    // State of the stack.
    std::vector<int> order;  // top first
    int top_d = -1;          // dedicated paper lifted to the top, -1 if none
    int top_pred = -1;       // its cyclic predecessor in its column when lifted from the fillers
    // Fillers: column papers out of their column, showing on the handles h_lvl..h_hi (hi = their
    // column). pred >= 0: goes back just below pred (its cyclic predecessor); -1: at either end.
    struct Filler {
        int paper, pred;
        int lvl = 0, hi = 0;
    };
    std::vector<Filler> fillers;
    std::vector<std::pair<int, int>> ops;  // moves (paper, depth) of the plan being simulated

    explicit Solver(std::vector<u64> a) : A(std::move(a)) {}

    // ------------------------------------------------------------------------------------------
    // Design

    // Number of blocks touched by the windows `diff` where a pair differs, and number of those
    // blocks where the pair is inconsistent (A_u neither Y_b nor ~Y_b on the differing windows).
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
    // Want codes of the two targets of the pair (u, v) (base 3 per block: 0 untouched, 1 off,
    // 2 on, as wanted_blocks), and the number of blocks where the pair is inconsistent.
    std::array<int, 3> pair_codes(int u, int v) const {
        u64 diff = A[u] ^ A[v];
        int cu = 0, cv = 0, bad = 0, pw = 1;
        for (const auto& b : blocks) {
            u64 d = diff & b.mask;
            if (d) {
                u64 x = (A[u] ^ b.y) & d;
                if (x != 0 && x != d) bad++;
                int on = __builtin_popcountll(x) * 2 > __builtin_popcountll(d);
                cu += pw * (on + 1);
                cv += pw * (2 - on);
            }
            pw *= 3;
        }
        return {cu, cv, bad};
    }
    // Color of unit x at handle h_l, -1 if the two targets of a pair differ there.
    int color_at(int x, int l) const {
        auto [u, v] = units[x];
        int c = A[u] >> handle[l] & 1;
        if (v >= 0 && (int)(A[v] >> handle[l] & 1) != c) return -1;
        return c;
    }
    std::vector<int> unit_columns() const {  // column of each unit, from members
        std::vector<int> col(units.size(), -1);
        for (int l = 0; l < H; l++) for (int c = 0; c < 2; c++) for (int x : members[l][c]) col[x] = l;
        return col;
    }
    u64 handle_bits(u64 windows) const {  // the window set by handle index (bit j = window h_j)
        u64 r = 0;
        for (int j = 0; j < H; j++) r |= (windows >> handle[j] & 1) << j;
        return r;
    }
    void set_members(const std::vector<int>& col) {
        for (int l = 0; l < H; l++) members[l][0].clear(), members[l][1].clear();
        for (int x = 0; x < (int)units.size(); x++)
            if (col[x] >= 0) members[col[x]][color_at(x, col[x])].push_back(x);
    }

    std::vector<std::string> design() {
        std::mt19937_64 rng(12345);
        // The G windows, blocks and Y: the best of kGselK runs of choose_blocks by greedy_pair_obj
        // (after the annealing, the expected moves vary between such runs with a sd of about 0.4%,
        // and the climbing objective itself does not predict them). Run 0 uses rng.
        const int kGselK = env_int("GSEL_K") ? env_int("GSEL_K") : 4;
        {
            double best = 1e18;
            std::vector<Block> bb;
            std::vector<int> bh;
            u64 bg = 0;
            int bi = 0;
            for (int i = 0; i < kGselK; i++) {
                std::mt19937_64 r2(12345 + 1000 * i);
                blocks.clear(), gmask = 0;
                choose_blocks(i == 0 ? rng : r2);
                sort_pairs();
                double o = greedy_pair_obj();
                if (o < best) best = o, bb = blocks, bh = handle, bg = gmask, bi = i;
            }
            blocks = bb, handle = bh, gmask = bg;
            std::cerr << "gsel_obj = " << best << "\ngsel_pick = " << bi << '\n';
        }
        climb_greedy(rng, env_int("GOPT_STEPS") ? env_int("GOPT_STEPS") : 3000);
        std::cerr << "gopt_end_sec = " << elapsed_sec() << '\n';
        // Column sizes: about proportional to 1 + l, even (both colors at the handle).
        const int n_ded = K - ((int)blocks.size() + 1);
        std::vector<double> w(H);
        for (int l = 0; l < H; l++) w[l] = 1.0 + l;
        double ws = std::accumulate(w.begin(), w.end(), 0.0);
        std::vector<int> csize(H);
        int tot = 0;
        for (int l = 0; l < H; l++) tot += csize[l] = std::max(2, 2 * (int)std::floor(n_ded * w[l] / ws / 2));
        for (int l = H - 1; tot + 2 <= n_ded; l = (l + H - 1) % H) csize[l] += 2, tot += 2;
        while (tot > n_ded) {
            int l = std::max_element(csize.begin(), csize.end()) - csize.begin();
            csize[l]--, tot--;
        }
        // Units: every target needs a paper (the generic layer cannot show arbitrary patterns), so
        // P - n_ded pairs, greedily by (inconsistent blocks, distance); the leftover singles are
        // paired arbitrarily (the annealing repairs inconsistent pairs).
        const int need_pairs = std::max(0, P - n_ded);
        std::vector<std::array<int, 3>> cand;  // (key, u, v)
        for (int u = 0; u < P; u++)
            for (int v = u + 1; v < P; v++)
                cand.push_back({touch(A[u], A[u] ^ A[v]).second * 1000 + __builtin_popcountll(A[u] ^ A[v]), u, v});
        std::sort(cand.begin(), cand.end());
        std::vector<char> used(P, 0);
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
        for (int i = 0; i < (int)singles.size() && (int)units.size() < n_ded; i++) units.push_back({singles[i], -1});
        std::shuffle(units.begin(), units.end(), rng);
        // Columns (a pair must agree at the handle of its column): both colors in every column
        // first, then the columns deepest first up to their sizes, balancing the colors, pairs
        // first; leftovers in the deepest column that fits.
        std::vector<char> placed(units.size(), 0);
        members.assign(H, {});
        auto take = [&](int l, int c, bool pairs_first) {
            for (int pass = 0; pass < 2; pass++) {
                bool want_pair = (pass == 0) == pairs_first;
                for (int x = 0; x < (int)units.size(); x++) {
                    if (placed[x] || (units[x][1] >= 0) != want_pair || color_at(x, l) != c) continue;
                    placed[x] = 1;
                    members[l][c].push_back(x);
                    return true;
                }
            }
            return false;
        };
        for (int l = 0; l < H; l++) for (int c = 0; c < 2; c++) take(l, c, false);
        for (int l = H - 1; l >= 0; l--)
            while ((int)(members[l][0].size() + members[l][1].size()) < csize[l]) {
                int c = members[l][0].size() <= members[l][1].size() ? 0 : 1;
                if (!take(l, c, true) && !take(l, 1 - c, true)) break;
            }
        for (int x = 0; x < (int)units.size(); x++) {
            if (placed[x]) continue;
            for (int l = H - 1; l >= 0; l--) {
                int c = color_at(x, l);
                if (c < 0) continue;
                placed[x] = 1;
                members[l][c].push_back(x);
                break;
            }
        }
        flip_cov.assign(blocks.size(), 0);
        for (int b = 0; b < (int)blocks.size(); b++) flip_cov[b] = (1 << b) - 1;
        anneal_units();
        filler_climb();
        split_inconsistent();
        return make_papers();
    }

    // Mean number of handle windows where the two targets differ, over the pairs needed (P minus
    // the dedicated papers) of a greedy matching, fewest differences first, of the pairs consistent
    // with the blocks (1 pair short costs 10). A G with good consistent partners at few handle
    // holes: about the handle hole cost the annealing will reach (between G choices, correlation
    // 0.54 with the expected moves after the annealing; trial_log ceil-).
    // The pairs are kept sorted by their handle differences (sort_pairs, after the handle windows
    // change) and the matching scans them checking the consistency on the way; eval stops early
    // (returns 1e9) once the objective must exceed `limit`.
    struct GreedyPairs {
        std::vector<std::array<std::uint8_t, 2>> pr;  // pairs (u, v), by handle differences
        std::vector<int> start;                       // start[d]: first pair with d differences
    } gp, gp_prev;  // gp_prev: the sorting before the last handle move, restored on its rejection
    void sort_pairs() {
        u64 hm = 0;
        for (int j : handle) hm |= 1ULL << j;
        static std::vector<std::uint8_t> hd(P * (P - 1) / 2);
        std::vector<int> cnt(H + 2, 0);
        for (int u = 0, i = 0; u < P; u++) {
            const u64 au = A[u] & hm;
            for (int v = u + 1; v < P; v++, i++) cnt[(hd[i] = __builtin_popcountll(au ^ (A[v] & hm))) + 1]++;
        }
        for (int d = 0; d <= H; d++) cnt[d + 1] += cnt[d];
        gp.start = cnt;
        gp.pr.resize(P * (P - 1) / 2);
        for (int u = 0, i = 0; u < P; u++)
            for (int v = u + 1; v < P; v++, i++) gp.pr[cnt[hd[i]]++] = {(std::uint8_t)u, (std::uint8_t)v};
    }
    bool consistent(u64 au, u64 diff) const {  // touch(au, diff).second == 0
        for (const auto& b : blocks) {
            u64 d = diff & b.mask, x = (au ^ b.y) & d;
            if (x != 0 && x != d) return false;
        }
        return true;
    }
    double greedy_pair_obj(double limit = 1e18) const {
        const int need = P - (K - ((int)blocks.size() + 1));
        std::array<char, P> used{};
        int n = 0;
        double tot = 0;
        for (int d = 0; d <= H && n < need; d++) {
            if (tot + (double)(need - n) * d > limit * need) return 1e9;
            for (int i = gp.start[d]; i < gp.start[d + 1]; i++) {
                auto [u, v] = gp.pr[i];
                if (used[u] || used[v] || !consistent(A[u], A[u] ^ A[v])) continue;
                used[u] = used[v] = 1, tot += d;
                if (++n == need) break;
            }
        }
        return tot / need + (need - n) * 10.0;
    }

    // Hill climbing of the G windows on greedy_pair_obj after choose_blocks (the same moves: a block
    // window with a handle window, or two windows of two blocks, each changed block taking its best
    // Y_b by best_y), for `steps` steps; a move is kept if the objective does not increase and the
    // climbing objective of choose_blocks stays within kSlack of its start.
    void climb_greedy(std::mt19937_64& rng, int steps) {
        const double kSlack = std::getenv("GOPT_SLACK") ? std::atof(std::getenv("GOPT_SLACK")) : 0.5;
        const int nb = blocks.size();
        std::vector<std::vector<int>> bw(nb);
        std::vector<int> yb(nb, 0);
        std::vector<double> fb(nb);
        for (int b = 0; b < nb; b++) {
            for (int j = 0; j < N; j++) if (blocks[b].mask >> j & 1) bw[b].push_back(j);
            fb[b] = best_y(bw[b], yb[b]);
        }
        std::vector<int> hw = handle;
        auto set_block = [&](int b) {
            Block& bl = blocks[b];
            bl.mask = bl.y = 0;
            for (int i = 0; i < (int)bw[b].size(); i++) {
                bl.mask |= 1ULL << bw[b][i];
                if (yb[b] >> i & 1) bl.y |= 1ULL << bw[b][i];
            }
        };
        for (int b = 0; b < nb; b++) set_block(b);
        sort_pairs();
        double cur = greedy_pair_obj();
        const double f0 = std::accumulate(fb.begin(), fb.end(), 0.0);
        double fsum = f0;
        int acc = 0;
        for (int it = 0; it < steps; it++) {
            int b1, b2 = -1, i1, i2 = -1, k = -1, y1 = 0, y2 = 0;
            double f1, f2 = 0;
            const bool with_handle = (rng() >> 11) * 0x1.0p-53 < 0.3;
            if (with_handle) {
                b1 = rng() % nb, i1 = rng() % bw[b1].size(), k = rng() % hw.size();
                std::swap(bw[b1][i1], hw[k]);
            } else {
                b1 = rng() % nb, b2 = rng() % (nb - 1);
                if (b2 >= b1) b2++;
                i1 = rng() % bw[b1].size(), i2 = rng() % bw[b2].size();
                std::swap(bw[b1][i1], bw[b2][i2]);
                f2 = best_y(bw[b2], y2);
            }
            f1 = best_y(bw[b1], y1);
            const double fnew = fsum - fb[b1] + f1 - (b2 >= 0 ? fb[b2] - f2 : 0);
            bool ok = fnew >= f0 - kSlack;
            const Block s1 = blocks[b1], s2 = b2 >= 0 ? blocks[b2] : Block{};
            const int sy1 = yb[b1], sy2 = b2 >= 0 ? yb[b2] : 0;
            if (ok) {
                yb[b1] = y1, set_block(b1);
                if (b2 >= 0) yb[b2] = y2, set_block(b2);
                if (with_handle) handle = hw, std::sort(handle.begin(), handle.end()), std::swap(gp, gp_prev), sort_pairs();
                double o = greedy_pair_obj(cur);
                ok = o <= cur;
                if (ok) cur = o, fsum = fnew, fb[b1] = f1, acc++;
                if (ok && b2 >= 0) fb[b2] = f2;
            }
            if (!ok) {
                bool resort = with_handle && blocks[b1].mask != s1.mask;
                blocks[b1] = s1, yb[b1] = sy1;
                if (b2 >= 0) blocks[b2] = s2, yb[b2] = sy2;
                if (with_handle) std::swap(bw[b1][i1], hw[k]);
                else std::swap(bw[b1][i1], bw[b2][i2]);
                if (resort) handle = hw, std::sort(handle.begin(), handle.end()), std::swap(gp, gp_prev);
            }
        }
        gmask = 0;
        for (auto& bl : blocks) gmask |= bl.mask;
        std::cerr << "gopt_obj = " << cur << "\ngopt_acc = " << acc << "\ngopt_blockobj_drop = " << f0 - fsum << '\n';
    }

    // log(fraction of the pairs consistent with the block of windows w) for its best Y (ybest):
    // pairs (x1, x2) of relative patterns x = a ^ y with x1 subset of x2, by a subset-sum
    // transform; consistent = 2 * nested - equal.
    // y and its complement give the same count, and the first best y has its top bit 0, so
    // only those y are tried. Blocks have at most 7 windows (the counts fit in int).
    double best_y(const std::vector<int>& w, int& ybest) const {
        const int sz = w.size(), T = 1 << sz;
        int cnt[128] = {}, c2[128], z[128];
        for (int u = 0; u < P; u++) {
            int x = 0;
            for (int i = 0; i < sz; i++) x |= (int)(A[u] >> w[i] & 1) << i;
            cnt[x]++;
        }
        int best = -1;
        for (int y = 0; y < std::max(1, T / 2); y++) {
            int eq = 0;
            for (int x = 0; x < T; x++) c2[x] = cnt[x ^ y], eq += c2[x] * c2[x];
            for (int x = 0; x < T; x++) z[x] = c2[x];
            for (int bit = 1; bit < T; bit <<= 1)
                for (int lo = 0; lo < T; lo += 2 * bit)
                    for (int x = lo; x < lo + bit; x++) z[x + bit] += z[x];
            int nested = 0;
            for (int x = 0; x < T; x++) nested += c2[x] * z[x];
            int c = 2 * nested - eq;
            if (c > best) best = c, ybest = y;
        }
        return std::log((double)best / ((double)P * P));
    }

    // The G windows, their 5 blocks and the colors Y_b. Each block takes the Y_b maximizing the
    // target pairs consistent with it (patterns relative to Y_b nested), and windows are exchanged
    // between blocks, or with handle windows, by hill climbing on the sum over the blocks of
    // log(fraction of consistent pairs) (a pair must be consistent with every block it touches).
    void choose_blocks(std::mt19937_64& rng) {
        const int nb = (G + 3) / 6;
        std::vector<std::vector<int>> bw(nb);  // windows of each block
        for (int j = 0, b = 0; b < nb; b++) {
            int sz = G / nb + (b < G % nb ? 1 : 0);
            for (int i = 0; i < sz; i++) bw[b].push_back(j++);
        }
        std::vector<double> fb(nb);
        std::vector<int> yb(nb, 0);
        for (int b = 0; b < nb; b++) fb[b] = best_y(bw[b], yb[b]);
        std::vector<int> hw;  // handle windows
        for (int j = G; j < N; j++) hw.push_back(j);
        for (int it = 0; it < 3000; it++) {
            if ((rng() >> 11) * 0x1.0p-53 < 0.3) {  // a block window with a handle window
                int b1 = rng() % nb, i1 = rng() % bw[b1].size(), k = rng() % hw.size();
                std::swap(bw[b1][i1], hw[k]);
                int y1;
                double f1 = best_y(bw[b1], y1);
                if (f1 > fb[b1] + 1e-12) fb[b1] = f1, yb[b1] = y1;
                else std::swap(bw[b1][i1], hw[k]);
                continue;
            }
            int b1 = rng() % nb, b2 = rng() % (nb - 1);  // two windows of two blocks
            if (b2 >= b1) b2++;
            rng();  // (the draw of a former move, never taken: kept for the same sequence)
            int i1 = rng() % bw[b1].size(), i2 = rng() % bw[b2].size();
            std::swap(bw[b1][i1], bw[b2][i2]);
            int y1, y2;
            double f1 = best_y(bw[b1], y1), f2 = best_y(bw[b2], y2);
            if (f1 + f2 > fb[b1] + fb[b2] + 1e-12) fb[b1] = f1, fb[b2] = f2, yb[b1] = y1, yb[b2] = y2;
            else std::swap(bw[b1][i1], bw[b2][i2]);
        }
        for (int b = 0; b < nb; b++) {
            Block bl;
            for (int i = 0; i < (int)bw[b].size(); i++) {
                bl.mask |= 1ULL << bw[b][i];
                if (yb[b] >> i & 1) bl.y |= 1ULL << bw[b][i];
            }
            blocks.push_back(bl);
            gmask |= bl.mask;
        }
        std::sort(hw.begin(), hw.end());
        handle = hw;
    }

    // Simulated annealing over the pairing of the targets, the column of every unit, the handle
    // order and the block colors Y_b, minimizing a model of the moves per target:
    //   - digs: (column size - 1) / 2 per request of a target of the column; a column must keep
    //     both colors at its handle, and about as many of each (kImbalance);
    //   - handle holes (the deeper handles of the column, and for a pair the shallower handles
    //     where its targets differ): kHandleHole times a persistence weight each (see refresh);
    //   - generic layer of a pair: the simulated costs of its two want codes (want_costs), and
    //     kIncons per target and inconsistent block;
    //   - from half of the run on, -kApW times a linearized filler proxy (ap_compute).
    // Moves: complement Y on a block, flip one color of Y (until Y is frozen at 10%), swap two
    // handles, move two units of opposite colors to another column, swap the columns of two units,
    // exchange a target between two units (from 10% on, mostly towards a consistent partner).
    // Afterwards a repair exchanges a target of every inconsistent pair if possible.
    void anneal_units() {
        constexpr double kHandleHole = 0.51, kImbalance = 50.0, kIncons = 30.0, kMix = 1.0;
        constexpr double kApW = 0.5, kApStart = 0.5, kTgtStart = 0.1, kTgtRate = 0.9;
        constexpr double kBlkCmp = 0.001, kYFlip = 0.05, kHandleSwap = 0.05, t0 = 3.0, t1 = 0.05;
        constexpr int kApRefresh = 4, kResim = 2, kRefresh = 1 << 14;
        const int U = units.size();
        std::vector<int> col = unit_columns();
        // Handle holes (tiny-bias). A hole at h_m shows the top of column m, which keeps the color
        // set for the last request that needed h_m. If the targets with a hole at h_m have color 1
        // with frequency p_m, a request needs a fix with probability 2 p_m (1 - p_m) instead of
        // 1/2: the holes of h_m cost kHandleHole n_m 4 p_m (1 - p_m) (n_m holes; kMix = 1 of a mix
        // with the uniform cost). The annealing uses the marginal cost of one hole of color c at
        // h_m, wcol[m][c] = 4 (1 - p_m(c))^2, frozen between refreshes (every kRefresh iterations,
        // from a recount). dsum[t][l] = sum of wcol over the handles m > l at the colors of target
        // t (the triangle holes of t in column l).
        std::vector<std::array<double, 2>> wcol(H, {1.0, 1.0});
        std::vector<u64> hb(P, 0);  // hb[t] bit m: color of target t at h_m
        std::vector<double> dsum((size_t)P * (H + 1), 0.0);
        auto make_tables = [&]() {
            for (int t = 0; t < P; t++) {
                hb[t] = handle_bits(A[t]);
                double* d = &dsum[(size_t)t * (H + 1)];
                d[H - 1] = 0;
                for (int l = H - 2; l >= 0; l--) d[l] = d[l + 1] + wcol[l + 1][hb[t] >> (l + 1) & 1];
            }
        };
        make_tables();
        // hb and dsum after the handles a and b (and their weights) were swapped: only the prefix
        // sums dsum[t][l] with a <= l < b change, by the change of the term at position b.
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
                for (u64 d = (hb[u] ^ hb[v]) & ((2ULL << l) - 1); d; d &= d - 1) {
                    int m = __builtin_ctzll(d);
                    c += wcol[m][0] + wcol[m][1];
                }
            }
            return c;
        };
        build_abstract();
        std::vector<double> wcost = want_costs();
        auto unit_cost = [&](int u, int v, int l) {
            double c = kHandleHole * hole_w(u, v, l);
            if (v >= 0) {
                auto [cu, cv, bad] = pair_codes(u, v);
                c += wcost[cu] + wcost[cv] + 2 * kIncons * bad;
            }
            return c;
        };
        auto uc = [&](int x, int l) { return unit_cost(units[x][0], units[x][1], l); };
        // Per column: units of each color at the handle, targets, and the units (mem, with the
        // position of each unit in its list, so that a handle swap scans only the columns it changes).
        std::vector<int> cnt0(H, 0), cnt1(H, 0), tgt(H, 0), mpos(U, -1);
        std::vector<std::vector<int>> mem(H);
        auto remove_unit = [&](int x) {
            int l = col[x];
            (color_at(x, l) ? cnt1 : cnt0)[l]--;
            tgt[l] -= units[x][1] >= 0 ? 2 : 1;
            auto& v = mem[l];
            int last = v.back();
            v[mpos[x]] = last;
            mpos[last] = mpos[x];
            v.pop_back();
        };
        auto add_unit = [&](int x) {
            int l = col[x];
            (color_at(x, l) ? cnt1 : cnt0)[l]++;
            tgt[l] += units[x][1] >= 0 ? 2 : 1;
            mpos[x] = mem[l].size();
            mem[l].push_back(x);
        };
        for (int x = 0; x < U; x++) if (col[x] >= 0) add_unit(x);
        auto col_cost = [&](int l) {  // digs and imbalance of column l
            int n = cnt0[l] + cnt1[l];
            int imb = std::max(0, std::abs(cnt0[l] - cnt1[l]) - 1);
            double c = tgt[l] * (n - 1) * 0.5 + kImbalance * imb;
            if (cnt0[l] == 0 || cnt1[l] == 0) c += 1e6;
            return c;
        };
        std::vector<double> pone(H, 0.5);  // frequency of color 1 among the holes of each handle
        // Recounts the holes per handle and their colors, and sets the marginal weights.
        auto refresh = [&]() {
            std::vector<int> n(H, 0), n1(H, 0);
            for (int x = 0; x < U; x++) {
                if (col[x] < 0) continue;
                auto [u, v] = units[x];
                u64 holes = low_bits(H) & ~((2ULL << col[x]) - 1);
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
            for (int m = 0; m < H; m++) {
                double p1 = n[m] ? (double)n1[m] / n[m] : 0.5;
                pone[m] = p1;
                wcol[m][1] = kMix * 4 * (1 - p1) * (1 - p1) + 1 - kMix;
                wcol[m][0] = kMix * 4 * p1 * p1 + 1 - kMix;
            }
            make_tables();
        };
        // Linearized filler proxy (mix-ap): the proxy of filler_climb costs a pass over all targets
        // per exchange, so from progress kApStart on the annealing adds -kApW V[x][l] for each unit
        // x in column l, where V[x][l] = the proxy of the targets of x if x were in column l (the
        // other units fixed) + the proxy that the paper of x gives, as a filler in column l, to the
        // targets of the shallower columns, divided by the size of column l (with x). Recomputed
        // kApRefresh times and frozen in between; the re-pairing and the handle swaps ignore it.
        std::vector<double> apv;  // apv[x * H + l]; empty while off
        std::vector<double> pqs;  // pqs[t * (H + 1) + j]: q of filler_gain for target t
        auto ap_v = [&](int x, int l) { return apv.empty() ? 0.0 : apv[(size_t)x * H + l]; };
        auto ap_g = [&](int t, int l, int y, int c) {  // paper of unit y (column c), target t (column l)
            int y0 = units[y][0], y1 = units[y][1];
            return filler_gain(hb[t], l, hb[y0], y1 >= 0 ? hb[y0] ^ hb[y1] : 0, c, &pqs[(size_t)t * (H + 1)]);
        };
        auto ap_compute = [&]() {
            pqs.assign((size_t)P * (H + 1), 0.0);
            for (int t = 0; t < P; t++) {
                double* q = &pqs[(size_t)t * (H + 1)];
                for (int m = 0; m < H; m++) q[m + 1] = q[m] + 2 * ((hb[t] >> m & 1) ? 1 - pone[m] : pone[m]);
            }
            std::vector<std::vector<int>> colm(H), colt(H);  // units / targets of each column
            std::vector<int> tx(P, -1);
            for (int x = 0; x < U; x++) {
                if (col[x] < 0) continue;
                colm[col[x]].push_back(x);
                for (int t : units[x]) if (t >= 0) colt[col[x]].push_back(t), tx[t] = x;
            }
            apv.assign((size_t)U * H, 0.0);
            for (int x = 0; x < U; x++) {
                if (col[x] < 0) continue;
                for (int c = 0; c < H; c++) {
                    if (color_at(x, c) < 0) continue;
                    double f = 0;
                    for (int l = 0; l < c; l++)
                        for (int t : colt[l]) if (tx[t] != x) f += ap_g(t, l, x, c);
                    double v = f / (colm[c].size() + (col[x] != c ? 1 : 0));
                    for (int t : units[x]) {
                        if (t < 0) continue;
                        for (int c2 = c + 1; c2 < H; c2++) {
                            double s2 = 0;
                            int n2 = 0;
                            for (int y : colm[c2]) if (y != x) s2 += ap_g(t, c, y, c2), n2++;
                            if (n2) v += s2 / n2;
                        }
                    }
                    apv[(size_t)x * H + c] = v;
                }
            }
        };
        auto total_cost = [&]() {
            double c = 0;
            for (int x = 0; x < U; x++)
                if (col[x] >= 0) c += uc(x, col[x]) - kApW * ap_v(x, col[x]);
            for (int l = 0; l < H; l++) c += col_cost(l);
            return c / P;
        };
        refresh();
        Xoshiro256 rng(777);
        auto rnd = [&](int n) { return (int)(((unsigned __int128)rng() * (unsigned)n) >> 64); };
        auto unif = [&]() { return (rng() >> 11) * 0x1.0p-53; };
        // The acceptance test exp(-delta / T) < u is delta > T (-log u), -log u from a table.
        static std::vector<double> neglog(1 << 16);
        for (int i = 0; i < (1 << 16); i++) neglog[i] = -std::log((i + 0.5) / (1 << 16));
        const int iters = env_int("ANNEAL_ITERS");
        auto change = [&](int x, int y, auto&& f) {  // f changes the units x, y or their columns
            remove_unit(x);
            remove_unit(y);
            f();
            add_unit(x);
            add_unit(y);
        };
        double cur_total = total_cost() * P;
        const double t_begin = elapsed_sec(), t_end = 1.1;
        double progress = 0, temp = t0;
        auto reject = [&](double delta) { return delta > 0 && delta > temp * neglog[rng() >> 48]; };
        // A change of the units x and y (apply, undo) judged by cost() before and after.
        auto attempt = [&](int x, int y, auto&& cost, auto&& apply, auto&& undo) {
            double before = cost();
            change(x, y, apply);
            double delta = cost() - before;
            bool ok = !reject(delta);
            if (ok) cur_total += delta;
            else change(x, y, undo);
            return ok;
        };
        auto try_y = [&](int b, u64 bits) {  // complement Y_b on the windows `bits`
            blocks[b].y ^= bits;
            double after = total_cost() * P;
            if (reject(after - cur_total)) blocks[b].y ^= bits;
            else cur_total = after;
        };
        long long anneal_iters = 0;
        int ap_done = 0, resim_done = 0;
        // Targeted re-pairing: from progress kTgtStart on, Y is frozen and the exchange move takes
        // the new partner of a pair's target among its consistent partners.
        bool targeted = false;
        std::vector<std::vector<int>> partners(P);
        std::vector<int> unit_of(P, -1);
        for (int x = 0; x < U; x++)
            for (int t : units[x]) if (t >= 0) unit_of[t] = x;
        for (int it = 0;; it++) {
            anneal_iters = it;
            if (!targeted && progress >= kTgtStart) {
                targeted = true;
                for (int u = 0; u < P; u++)
                    for (int w = 0; w < P; w++)
                        if (w != u && touch(A[u], A[u] ^ A[w]).second == 0) partners[u].push_back(w);
            }
            if (iters > 0 && it >= iters) break;
            if ((it & 255) == 0) {  // the progress and the temperature only every 256 iterations
                progress = iters > 0 ? (double)it / iters : (elapsed_sec() - t_begin) / std::max(1e-9, t_end - t_begin);
                if (progress >= 1) break;
                temp = t0 * std::pow(t1 / t0, progress);
            }
            if (ap_done < kApRefresh && progress >= kApStart + (1 - kApStart) * ap_done / kApRefresh) {
                ap_compute();
                ap_done++;
                cur_total = total_cost() * P;
            }
            if (resim_done < kResim && progress >= (resim_done + 1.0) / (kResim + 1)) {
                // the want costs simulated again with the wants of the current pairs
                std::vector<int> codes;
                for (int x = 0; x < U; x++) {
                    if (col[x] < 0 || units[x][1] < 0) continue;
                    auto [cu, cv, bad] = pair_codes(units[x][0], units[x][1]);
                    codes.push_back(cu);
                    codes.push_back(cv);
                }
                if (!codes.empty()) wcost = want_costs(codes);
                resim_done++;
                cur_total = total_cost() * P;
            }
            if ((it % kRefresh) == kRefresh - 1) {
                refresh();
                cur_total = total_cost() * P;  // the weights changed
            }
            if (unif() < kBlkCmp) {
                // Complement Y on a whole block (the base and the flip swap their colors there):
                // every pair keeps its consistency, the orientations wanted on the block swap.
                int b = rnd((int)blocks.size());
                try_y(b, blocks[b].mask);
                continue;
            }
            double r = unif();
            if (targeted && r < kYFlip) r += kYFlip;  // Y is frozen
            if (r < kYFlip) {  // flip one color of a block (changes which pairs are consistent)
                int b = rnd((int)blocks.size());
                u64 m = blocks[b].mask;
                int j = rnd(__builtin_popcountll(m));
                u64 bit = m;
                for (int i = 0; i < j; i++) bit &= bit - 1;
                try_y(b, bit & -bit);
                continue;
            }
            if (r < kYFlip + kHandleSwap) {
                // Swap the handle windows of two columns a < b. The weights follow the windows, so
                // only the units of the columns a..b-1 change their hole cost (their deep holes
                // include position b but not a, their pair differences position a but not b), plus
                // the column costs of a and b. First the validity (a pair must agree at its new
                // handle) and the colors on the columns a and b, then the cost on a..b-1.
                int a = rnd(H), b = rnd(H);
                if (a == b) continue;
                if (a > b) std::swap(a, b);
                double dh = 0;
                int n0a = 0, n1a = 0, n0b = 0, n1b = 0;
                bool ok = true;
                for (int l : {a, b}) {
                    const int pos = l == a ? b : a;  // position of the new handle window of l
                    for (int x : mem[l]) {
                        auto [u, v] = units[x];
                        if (v >= 0 && ((hb[u] ^ hb[v]) >> pos & 1)) {
                            ok = false;
                            break;
                        }
                        int c = hb[u] >> pos & 1;
                        if (l == a) (c ? n1a : n0a)++;
                        else (c ? n1b : n0b)++;
                    }
                    if (!ok) break;
                }
                if (!ok) continue;
                for (int l = a; l < b; l++)
                    for (int x : mem[l]) {
                        auto [u, v] = units[x];
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
                double before_cols = col_cost(a) + col_cost(b);
                std::swap(handle[a], handle[b]);
                int s0a = cnt0[a], s1a = cnt1[a], s0b = cnt0[b], s1b = cnt1[b];
                cnt0[a] = n0a, cnt1[a] = n1a, cnt0[b] = n0b, cnt1[b] = n1b;
                double delta = kHandleHole * dh + col_cost(a) + col_cost(b) - before_cols;
                if (reject(delta)) {
                    std::swap(handle[a], handle[b]);
                    cnt0[a] = s0a, cnt1[a] = s1a, cnt0[b] = s0b, cnt1[b] = s1b;
                } else {
                    cur_total += delta;
                    std::swap(wcol[a], wcol[b]);
                    swap_tables(a, b);
                }
                continue;
            }
            const int type = rnd(3);
            int x = rnd(U);
            if (col[x] < 0) continue;
            if (type == 2) {  // move two units of opposite colors from column l1 to column l2
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
                auto cost = [&] {
                    return uc(x, col[x]) + uc(y, col[y]) + col_cost(l1) + col_cost(l2) - kApW * (ap_v(x, col[x]) + ap_v(y, col[y]));
                };
                attempt(x, y, cost, [&] { col[x] = col[y] = l2; }, [&] { col[x] = col[y] = l1; });
            } else if (type == 0) {  // swap the columns of two units
                int y = rnd(U);
                if (y == x || col[y] < 0 || col[x] == col[y]) continue;
                int lx = col[x], ly = col[y];
                if (color_at(x, ly) < 0 || color_at(y, lx) < 0) continue;
                auto cost = [&] {
                    return uc(x, col[x]) + uc(y, col[y]) + col_cost(lx) + col_cost(ly) - kApW * (ap_v(x, col[x]) + ap_v(y, col[y]));
                };
                attempt(x, y, cost, [&] { col[x] = ly, col[y] = lx; }, [&] { col[x] = lx, col[y] = ly; });
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
                auto ox = units[x], oy = units[y];
                auto cost = [&] { return uc(x, lx) + uc(y, ly) + col_cost(lx) + (lx != ly ? col_cost(ly) : 0); };
                if (attempt(x, y, cost, [&] { units[x] = nx, units[y] = ny; }, [&] { units[x] = ox, units[y] = oy; })) {
                    for (int t : nx) if (t >= 0) unit_of[t] = x;
                    for (int t : ny) if (t >= 0) unit_of[t] = y;
                }
            }
        }
        // Repair: an inconsistent pair cannot be served at all, so exchange one of its targets with
        // a target of another unit whenever both new units are consistent and agree at their
        // handles, taking the exchange of the least cost.
        for (int x = 0; x < U; x++) {
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
                        change(x, y, [&] { units[x] = nx, units[y] = ny; });
                        double c = unit_cost(nx[0], nx[1], col[x]) + unit_cost(ny[0], ny[1], col[y]) +
                                   col_cost(col[x]) + (col[y] != col[x] ? col_cost(col[y]) : 0);
                        change(x, y, [&] { units[x] = ox, units[y] = oy; });
                        if (c < best) best = c, by = y, bix = ix, biy = iy;
                    }
            }
            if (by >= 0) change(x, by, [&] { std::swap(units[x][bix], units[by][biy]); });
        }
#ifdef SIM_HARNESS
        {  // the terms of the model after the annealing (experiments)
            double cd = 0, ch = 0, cb = 0;
            for (int x = 0; x < U; x++) {
                if (col[x] < 0) continue;
                auto [u, v] = units[x];
                ch += kHandleHole * hole_w(u, v, col[x]);
                if (v >= 0) {
                    auto [cu, cv, bad] = pair_codes(u, v);
                    cb += wcost[cu] + wcost[cv];
                }
            }
            for (int l = 0; l < H; l++) cd += tgt[l] * (cnt0[l] + cnt1[l] - 1) * 0.5;
            std::cerr << "model_cost = " << total_cost() << "\nm_dig = " << cd / P << "\nm_hole = " << ch / P << "\nm_blk = " << cb / P << '\n';
        }
#endif
        std::cerr << "anneal_iters = " << anneal_iters << "\nanneal_end_sec = " << elapsed_sec() << '\n';
        set_members(col);
    }

    // Hill climbing after the annealing (until 1.15 s): exchanges two units of the same kind (two
    // pairs or two singles) between two columns, with the same colors at both handles (keeps the
    // column balance and the digs of the model), when the persistence cost of the handle holes
    // minus kW times the filler proxy decreases:
    //   proxy(u) = sum over the columns c deeper than u's of the mean over the units y of c of
    //              filler_gain(u, paper of y), with the persistence weights of the exact counts.
    // One unit of proxy saved about 0.7 moves per request, and the annealing alone leaves it at
    // random. Sets the majority colors bias_c / bias_g used by the plan search (tops_penalty).
    void filler_climb() {
        constexpr double kW = 0.3, kH = 0.51, kMix = 1.0;
        const int iters = env_int("CLIMB_ITERS");
        const double t_end = 1.15;
        const int U = units.size();
        std::vector<int> col = unit_columns();
        std::vector<u64> hu(P), diffb(U, 0);  // colors at the handles, pair differences
        for (int u = 0; u < P; u++) hu[u] = handle_bits(A[u]);
        for (int x = 0; x < U; x++) if (units[x][1] >= 0) diffb[x] = hu[units[x][0]] ^ hu[units[x][1]];
        // hn[m] / hn1[m] = targets with a hole at h_m / of them with color 1 there; the holes of
        // h_m cost kH hn 4 p (1 - p) with p = hn1 / hn (the persistence model, exact).
        auto unit_holes = [&](int x, int l) { return (low_bits(H) & ~((2ULL << l) - 1)) | diffb[x]; };
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
        // q of filler_gain, from the frequencies after the annealing.
        std::vector<std::vector<double>> pq(P, std::vector<double>(H + 1, 0.0));
        for (int u = 0; u < P; u++)
            for (int m = 0; m < H; m++) {
                double p1 = hn[m] ? (double)hn1[m] / hn[m] : 0.5;
                double pc = (hu[u] >> m & 1) ? p1 : 1 - p1;
                pq[u][m + 1] = pq[u][m] + 2 * (1 - pc);
            }
        std::vector<std::vector<int>> colm(H);  // units of each column
        for (int x = 0; x < U; x++) if (col[x] >= 0) colm[col[x]].push_back(x);
        std::vector<int> ucol(P, -1);  // unit of each target
        for (int x = 0; x < U; x++) for (int t : units[x]) if (t >= 0) ucol[t] = x;
        auto tcol = [&](int u) { return col[ucol[u]]; };
        auto gval = [&](int u, int l, int y, int c) {
            return filler_gain(hu[u], l, hu[units[y][0]], diffb[y], c, pq[u].data());
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
        std::mt19937_64 rng(999);
        long long climb_iters = 0;
        // Incremental: a target u not in x or y only sees the sums of the columns a and b change,
        // by g(u, y in a) - g(u, x in a) and g(u, x in b) - g(u, y in b); the targets of x and y are
        // recomputed.
        std::vector<int> others, moved;
        std::vector<std::array<double, 2>> dlt;
        std::vector<std::vector<double>> moved_saved;
        for (int it = 0;; it++) {
            if (iters > 0 ? it >= iters : (it & 63) == 0 && elapsed_sec() >= t_end) break;
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
            if (dmodel - kW * dproxy < -1e-9) {
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
        std::cerr << "climb_iters = " << climb_iters << "\nclimb_end_sec = " << elapsed_sec() << '\n';
        bias_c.assign(H, 0);
        bias_g.assign(H, 0.0);
        for (int m = 0; m < H; m++) {
            double p1 = hn[m] ? (double)hn1[m] / hn[m] : 0.5;
            bias_c[m] = p1 > 0.5 ? 1 : 0;
            bias_g[m] = std::abs(2 * p1 - 1);
        }
        set_members(col);
    }

    // Fallback for a pair still inconsistent after the annealing and its repair (rare; 0-5 cases
    // in 2000): split each block where it is inconsistent (a new flip paper for the windows where
    // A_u differs from Y_b; splitting never breaks another pair), paying the paper by merging two
    // single targets into a pair consistent with the blocks, or by an augmenting path (a pair
    // (a, b) keeps a with a single c, and b joins a single d in d's column). After a split the
    // flips are plain (set_blocks_plain).
    void split_inconsistent() {
        std::vector<u64> shallow_l(H + 1, 0);
        for (int l = 0; l < H; l++) shallow_l[l + 1] = shallow_l[l] | 1ULL << handle[l];
        std::vector<int> col_of_unit = unit_columns();
        auto single = [&](int x) { return units[x][1] < 0 && col_of_unit[x] >= 0; };
        auto drop_single = [&](int x) {  // single x leaves its column (its target joins a pair)
            int t = units[x][0], l = col_of_unit[x];
            auto& m = members[l][A[t] >> handle[l] & 1];
            m.erase(std::find(m.begin(), m.end(), x));
            col_of_unit[x] = -1;
        };
        // model cost of a pair in column l (differences d, t touched blocks): 0.51 per shallow
        // handle hole + 0.5 per touched block, per target
        auto sh = [&](u64 d, int l) { return 0.51 * __builtin_popcountll(d & shallow_l[l]); };
        int splits = 0, failed = 0;
        for (int x = 0; x < (int)units.size(); x++) {
            auto [u, v] = units[x];
            if (v < 0 || col_of_unit[x] < 0) continue;
            for (int b = 0; b < (int)blocks.size(); b++) {
                u64 d = (A[u] ^ A[v]) & blocks[b].mask;
                u64 xx = (A[u] ^ blocks[b].y) & d;
                if (!d || xx == 0 || xx == d) continue;
                // The cheapest merge of two singles: consistent, agreeing at the handle of the first
                // one's column, and the second one's column keeps both colors.
                double best = 1e18;
                int bw = -1, bz = -1;
                for (int xw = 0; xw < (int)units.size(); xw++) {
                    if (!single(xw)) continue;
                    int lw = col_of_unit[xw], w = units[xw][0];
                    for (int xz = 0; xz < (int)units.size(); xz++) {
                        if (xz == xw || !single(xz)) continue;
                        int z = units[xz][0], lz = col_of_unit[xz];
                        u64 dz = A[w] ^ A[z];
                        if (dz >> handle[lw] & 1) continue;
                        auto [t, bad] = touch(A[w], dz);
                        if (bad || members[lz][A[z] >> handle[lz] & 1].size() <= 1) continue;
                        double c = 2 * (sh(dz, lw) + 0.5 * t);
                        if (c < best) best = c, bw = xw, bz = xz;
                    }
                }
                if (bw >= 0) {
                    drop_single(bz);
                    units[bw][1] = units[bz][0];
                } else {
                    // Augmenting path: pair xp = (a, bb) keeps a with single xc, bb joins single xd.
                    int bp = -1, bkeep = -1, bc = -1, bd = -1;
                    for (int xp = 0; xp < (int)units.size(); xp++) {
                        if (units[xp][1] < 0 || col_of_unit[xp] < 0 || xp == x) continue;
                        int lp = col_of_unit[xp];
                        for (int keep = 0; keep < 2; keep++) {
                            int a = units[xp][keep], bb = units[xp][1 - keep];
                            for (int xc = 0; xc < (int)units.size(); xc++) {
                                if (!single(xc)) continue;
                                int c = units[xc][0], lc = col_of_unit[xc];
                                u64 dac = A[a] ^ A[c];
                                if (dac >> handle[lp] & 1) continue;
                                if (members[lc][A[c] >> handle[lc] & 1].size() <= 1) continue;
                                auto [t1, bad1] = touch(A[a], dac);
                                if (bad1) continue;
                                double c1 = sh(dac, lp) + 0.5 * t1;
                                if (2 * c1 >= best) continue;
                                for (int xd = 0; xd < (int)units.size(); xd++) {
                                    if (xd == xc || !single(xd)) continue;
                                    int d2 = units[xd][0], ld = col_of_unit[xd];
                                    u64 dbd = A[bb] ^ A[d2];
                                    if (dbd >> handle[ld] & 1) continue;
                                    auto [t2, bad2] = touch(A[bb], dbd);
                                    if (bad2) continue;
                                    double cc = 2 * (c1 + sh(dbd, ld) + 0.5 * t2);
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
                    drop_single(bc);
                    units[bp] = {a, units[bc][0]};
                    units[bd][1] = bb;
                }
                Block nbk;
                nbk.mask = xx;
                nbk.y = blocks[b].y & xx;
                blocks[b].mask &= ~xx;
                blocks[b].y &= ~xx;
                blocks.push_back(nbk);
                splits++;
            }
        }
        std::cerr << "split_fallback = " << splits << "\nsplit_failed = " << failed << '\n';
        if (splits > 0) flip_cov.assign(blocks.size(), 0);
    }

    // Papers, top to bottom (ids = initial positions): the base paper, the flips, the columns
    // 0..H-1 (each alternating its two colors at the handle), then all-hole leftovers.
    std::vector<std::string> make_papers() {
        const int nb = blocks.size();
        paper.assign(K, Paper{});
        col_of.assign(K, -1);
        block_of.assign(K, -1);
        ded.assign(P, -1);
        u64 y = 0;
        for (auto& bl : blocks) y |= bl.y;
        paper[0] = {gmask, y};
        block_of[0] = nb;  // (any value >= 0 marks a generic paper)
        for (int b = 0; b < nb; b++) {
            Paper& f = paper[1 + b];
            f = {blocks[b].mask, blocks[b].mask & ~blocks[b].y};
            for (int c = 0; c < nb; c++)
                if (flip_cov[b] >> c & 1) f.opaque |= blocks[c].mask, f.black |= blocks[c].y;
            block_of[1 + b] = b;
            blocks[b].pf = 1 + b;
        }
        int next = nb + 1;
        for (int l = 0; l < H; l++) {
            u64 opq = gmask;
            for (int i = 0; i <= l; i++) opq |= 1ULL << handle[i];
            auto &m0 = members[l][0], &m1 = members[l][1];
            for (size_t i0 = 0, i1 = 0; i0 < m0.size() || i1 < m1.size(); next++) {
                // alternate, spending the more numerous color when one runs ahead
                bool use0 = i1 >= m1.size() || (i0 < m0.size() && m0.size() - i0 >= m1.size() - i1);
                auto [u, v] = units[use0 ? m0[i0++] : m1[i1++]];
                Paper& p = paper[next];
                p.opaque = v >= 0 ? opq & ~(A[u] ^ A[v]) : opq;
                p.black = A[u] & p.opaque;
                col_of[next] = l;
                ded[u] = next;
                if (v >= 0) ded[v] = next;
            }
        }
        order.resize(K);
        std::iota(order.begin(), order.end(), 0);
        hidx.assign(N, -1);
        for (int j = 0; j < H; j++) hidx[handle[j]] = j, hmask |= 1ULL << handle[j];
        h_opq.assign(K, 0);
        h_blk.assign(K, 0);
        for (int k = 0; k < K; k++) h_opq[k] = handle_bits(paper[k].opaque), h_blk[k] = handle_bits(paper[k].black);
        build_block_tables();
        init_cycles();
        int bad_pairs = 0;
        for (auto [u, v] : units)
            if (v >= 0 && touch(A[u], A[u] ^ A[v]).second > 0) bad_pairs++;
        std::cerr << "blocks = " << nb << "\ninconsistent_pairs = " << bad_pairs << '\n';
        std::vector<std::string> rows(K, std::string(N, '.'));
        for (int k = 0; k < K; k++)
            for (int j = 0; j < N; j++)
                if (paper[k].opaque >> j & 1) rows[k][j] = (paper[k].black >> j & 1) ? '1' : '0';
        return rows;
    }

    // ------------------------------------------------------------------------------------------
    // Generic layer: the orders of the base paper (local index 0) and the flips (1 + b) as states
    // (720 for 5 blocks; encoded in base 6). A paper can move iff a block it covers is not covered
    // by the papers above it; block b is on iff its own flip is its topmost covering paper.
    bool blk_ok = false;                         // the lookahead policy is available (no split)
    std::vector<int> blk_paper;                  // local index -> paper id
    std::vector<std::array<int8_t, 6>> blk_st;  // states
    std::vector<int> blk_code;                   // base-6 code -> state index (-1)
    std::vector<int16_t> blk_dist;               // [s * S + t] moves from s to t
    std::vector<int16_t> blk_nxt;                // [s * S + t] first move from s to t: paper * 8 + depth
    std::vector<double> blk_v;                   // expected moves of the next pair target from s
    std::vector<std::vector<int>> blk_sat;       // satisfying states per want code (3^nb codes)
    std::vector<std::vector<uint8_t>> blk_dsat;  // [code][state] distance to a satisfying state
    std::vector<std::vector<int>> blk_radj;      // predecessors of each state
    std::vector<int> blk_disp;                   // orientation bits of each state
    int blk_S = 0;
    int blk_encode(const std::array<int8_t, 6>& o, int n) const {
        int c = 0;
        for (int i = n - 1; i >= 0; i--) c = c * 6 + o[i];
        return c;
    }
    int blk_cover(int k, int nb) const {  // blocks covered by local paper k
        return k == 0 ? (1 << nb) - 1 : (1 << (k - 1)) | flip_cov[k - 1];
    }
    int local_index(int k, int nb) const {  // local index of paper k, -1 if not generic
        return k == base_paper ? 0 : (block_of[k] >= 0 && block_of[k] < nb ? 1 + block_of[k] : -1);
    }
    static std::array<int8_t, 6> blk_moved(std::array<int8_t, 6> o, int n, int i, int d) {
        int k = o[i];  // the order o with its paper at position i moved to position d
        for (int j = i; j + 1 < n; j++) o[j] = o[j + 1];
        for (int j = n - 1; j > d; j--) o[j] = o[j - 1];
        o[d] = k;
        return o;
    }
    int blk_want_code(const std::vector<int>& want) const {
        int c = 0;
        for (int b = (int)want.size() - 1; b >= 0; b--) c = c * 3 + (want[b] + 1);
        return c;
    }
    bool blk_sat_state(int s, const std::vector<int>& want) const {
        for (int b = 0; b < (int)want.size(); b++)
            if (want[b] >= 0 && (blk_disp[s] >> b & 1) != want[b]) return false;
        return true;
    }
    // The states, the legal moves, all shortest paths (dist, first move), the orientations, and for
    // every want code its satisfying states and the distances to them.
    void build_abstract() {
        const int nb = blocks.size(), n = nb + 1;
        std::array<int8_t, 6> o{};
        for (int i = 0; i < n; i++) o[i] = i;
        int pw = 1;
        for (int i = 0; i < n; i++) pw *= 6;
        blk_code.assign(pw, -1);
        do {
            blk_code[blk_encode(o, n)] = blk_st.size();
            blk_st.push_back(o);
        } while (std::next_permutation(o.begin(), o.begin() + n));
        const int S = blk_S = blk_st.size();
        std::vector<std::vector<std::array<int, 3>>> adj(S);  // (next state, paper, depth)
        blk_disp.assign(S, 0);
        blk_radj.assign(S, {});
        for (int s = 0; s < S; s++) {
            const auto& st = blk_st[s];
            int covered = 0;
            for (int i = 0; i < n; i++) {
                int cov = blk_cover(st[i], nb);
                for (int b = 0; b < nb; b++)  // b's topmost covering paper
                    if ((cov & ~covered) >> b & 1) blk_disp[s] |= (st[i] == 1 + b) << b;
                bool vis = (cov & ~covered) != 0;
                covered |= cov;
                if (!vis) continue;
                for (int d = 0; d < n; d++) {
                    if (d == i) continue;
                    int t = blk_code[blk_encode(blk_moved(st, n, i, d), n)];
                    adj[s].push_back({t, st[i], d});
                    blk_radj[t].push_back(s);
                }
            }
        }
        blk_dist.assign((size_t)S * S, 1000);
        blk_nxt.assign((size_t)S * S, -1);
        std::vector<int> q;
        for (int s = 0; s < S; s++) {  // BFS from s; the first move propagates to the descendants
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
        const int W3 = blk_want_code(std::vector<int>(nb, 1)) + 1;  // 3^nb
        blk_dsat.assign(W3, std::vector<uint8_t>(S, 255));
        blk_sat.assign(W3, {});
        for (int c = 0; c < W3; c++) {  // backward BFS from the satisfying states
            std::vector<int> want = want_of(c, nb);
            q.clear();
            for (int s = 0; s < S; s++)
                if (blk_sat_state(s, want)) blk_sat[c].push_back(s), blk_dsat[c][s] = 0, q.push_back(s);
            for (size_t h = 0; h < q.size(); h++) {
                int x = q[h];
                for (int p : blk_radj[x])
                    if (blk_dsat[c][p] > blk_dsat[c][x] + 1) blk_dsat[c][p] = blk_dsat[c][x] + 1, q.push_back(p);
            }
        }
    }
    static std::vector<int> want_of(int code, int nb) {  // the want (-1 free, 0 off, 1 on) of a code
        std::vector<int> want(nb);
        for (int b = 0; b < nb; b++, code /= 3) want[b] = code % 3 - 1;
        return want;
    }
    // Expected generic moves of a request by its want code (3^nb codes), for the annealing: the
    // lookahead policy is simulated on a synthetic request mix shaped as measured (pairs touching
    // 5 / 4 / 3 / 2 blocks: 70 / 20 / 7 / 3%; orientations uniform / one minority block / two:
    // 18 / 41 / 41%; singles 46% of the requests), averaged over 8 synthetic pair sets; the cost of
    // a want is its distance to a satisfying order averaged over the orders met at the pair
    // requests. given: the want codes of the current pairs instead of the synthetic mix.
    std::vector<double> want_costs(const std::vector<int>& given = {}) {
        const int nb = blocks.size(), S = blk_S, W3 = blk_sat.size();
        const auto& dsat = blk_dsat;
        const auto& sat = blk_sat;
        const int sets = given.empty() ? 8 : 1;
        std::vector<double> wsum(W3, 0.0);
        for (int set = 0; set < sets; set++) {
            std::mt19937_64 rng(4242 + set);
            auto unif = [&]() { return (rng() >> 11) * 0x1.0p-53; };
            std::vector<int> wl = given;  // want codes of the (synthetic) pair targets
            for (int i = 0; i < 70 && given.empty(); i++) {
                double r = unif();
                int t = std::min(nb, r < 0.70 ? 5 : r < 0.90 ? 4 : r < 0.97 ? 3 : 2);
                std::vector<int> bl(nb);
                std::iota(bl.begin(), bl.end(), 0);
                std::shuffle(bl.begin(), bl.end(), rng);
                double r2 = unif();
                int minority = std::min(t / 2, r2 < 0.18 ? 0 : r2 < 0.59 ? 1 : 2);
                int flip = rng() & 1;
                int cu = 0, cv = 0;
                for (int j = 0; j < t; j++) {
                    int on = (j < minority) ^ flip;
                    int pwb = 1;
                    for (int b = 0; b < bl[j]; b++) pwb *= 3;
                    cu += pwb * (on + 1);
                    cv += pwb * (2 - on);
                }
                wl.push_back(cu);
                wl.push_back(cv);
            }
            std::vector<double> V(S, 0.0);
            for (int c : wl)
                for (int s = 0; s < S; s++) V[s] += (double)dsat[c][s] / wl.size();
            std::vector<double> hist(S, 0.0);
            int cur = 0;
            for (int r = 0; r < 30000; r++) {
                if (unif() < 0.46) continue;  // a single: the generic layer stays
                int c = wl[rng() % wl.size()];
                hist[cur] += 1;
                int best = -1, ties = 0;
                for (int t : sat[c]) {
                    if (best < 0) {
                        best = t, ties = 1;
                        continue;
                    }
                    int16_t dt = blk_dist[(size_t)cur * S + t], db = blk_dist[(size_t)cur * S + best];
                    if (dt < db || (dt == db && V[t] < V[best] - 1e-12)) {
                        best = t, ties = 1;
                    } else if (dt == db && V[t] < V[best] + 1e-12 && rng() % ++ties == 0) {
                        best = t;  // equal end states: uniformly at random
                    }
                }
                cur = best;
            }
            double tot = 0;
            for (double h : hist) tot += h;
            for (int c = 0; c < W3; c++) {
                double e = 0;
                for (int s = 0; s < S; s++) if (hist[s] > 0) e += hist[s] * dsat[c][s];
                wsum[c] += e / tot / sets;
            }
        }
        return wsum;
    }
    // The lookahead policy (after the papers are made): blk_v[s] = mean over the pair targets of
    // the distance from s to a state satisfying their want. Not after a split (nb > 5).
    void build_block_tables() {
        const int nb = blocks.size(), n = nb + 1;
        if (nb > 5) return;
        blk_paper.assign(n, -1);
        blk_paper[0] = base_paper;
        for (int b = 0; b < nb; b++) blk_paper[1 + b] = blocks[b].pf;
        std::vector<int> wcount(blk_sat.size(), 0);
        int npair = 0;
        for (int u = 0; u < P; u++) {
            int D = ded[u];
            if (D < 0 || !(gmask & ~paper[D].opaque)) continue;
            wcount[blk_want_code(wanted_blocks(u, gmask & ~paper[D].opaque))]++;
            npair++;
        }
        blk_v.assign(blk_S, 0.0);
        for (int c = 0; c < (int)blk_sat.size(); c++)
            if (wcount[c])
                for (int s = 0; s < blk_S; s++) blk_v[s] += (double)wcount[c] * blk_dsat[c][s] / npair;
        blk_ok = true;
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
    // Sets block b to orientation want[b] for every b with want[b] >= 0 (others are free). When the
    // generic papers are the top of the stack, the lookahead policy: a shortest path to a
    // satisfying order, the one of least blk_v among them.
    void set_blocks(const std::vector<int>& want) {
        if (!blk_ok) {
            set_blocks_plain(want);
            return;
        }
        const int nb = blocks.size(), n = nb + 1;
        std::array<int8_t, 6> o{};
        bool top = true;
        for (int i = 0; i < n && top; i++) {
            int li = local_index(order[i], nb);
            if (li < 0) top = false;
            else o[i] = li;
        }
        if (top) {
            int s = blk_code[blk_encode(o, n)];
            int best = -1;
            for (int t : blk_sat[blk_want_code(want)]) {
                if (best < 0) {
                    best = t;
                    continue;
                }
                int16_t dt = blk_dist[(size_t)s * blk_S + t], db = blk_dist[(size_t)s * blk_S + best];
                if (dt < db || (dt == db && blk_v[t] < blk_v[best] - 1e-12)) best = t;
            }
            if (best >= 0 && blk_dist[(size_t)s * blk_S + best] < 1000) {
                while (s != best) {
                    int mv = blk_nxt[(size_t)s * blk_S + best];
                    int k = mv / 8, d = mv % 8;
                    move(blk_paper[k], d);
                    int i = 0;
                    while (blk_st[s][i] != k) i++;
                    s = blk_code[blk_encode(blk_moved(blk_st[s], n, i, d), n)];
                }
                return;
            }
        }
        set_blocks_blocked(want);
    }
    // A dedicated paper lies above the generic papers: a BFS over the orders of the generic papers
    // in which a paper may move only if a block it covers is covered neither by generic papers
    // above it nor entirely by the papers above the layer; among the nearest satisfying orders the
    // one of least blk_v. If the generic papers are not contiguous or no satisfying order is
    // reachable, the plan is invalid (another plan is chosen).
    void set_blocks_blocked(const std::vector<int>& want) {
        const int nb = blocks.size(), n = nb + 1;
        int p0 = -1;
        u64 blocked = 0;
        for (int i = 0; i < K; i++) {
            if (local_index(order[i], nb) >= 0) {
                p0 = i;
                break;
            }
            blocked |= paper[order[i]].opaque;
        }
        std::array<int8_t, 6> o{};
        for (int i = 0; i < n; i++) {
            int li = p0 + i < K ? local_index(order[p0 + i], nb) : -1;
            if (li < 0) {
                invalid = true;
                return;
            }
            o[i] = li;
        }
        int s0 = blk_code[blk_encode(o, n)];
        if (blk_sat_state(s0, want)) return;
        int freeb = 0;  // blocks with a window not covered above the generic layer
        for (int b = 0; b < nb; b++) if (blocks[b].mask & ~blocked) freeb |= 1 << b;
        static std::vector<int> par, pmv, seen_at;
        static int stamp = 0;
        if ((int)seen_at.size() != blk_S) seen_at.assign(blk_S, 0), par.assign(blk_S, -1), pmv.assign(blk_S, 0);
        stamp++;
        std::vector<int> q = {s0};
        seen_at[s0] = stamp;
        int best = -1;
        for (size_t h = 0, end = 1; h < q.size() && best < 0; end = q.size()) {
            for (; h < end; h++) {
                int x = q[h];
                const auto& st = blk_st[x];
                int covered = 0;
                for (int i = 0; i < n; i++) {
                    int k = st[i], cov = blk_cover(k, nb);
                    bool vis = (cov & ~covered & freeb) != 0;
                    covered |= cov;
                    if (!vis) continue;
                    for (int d = 0; d < n; d++) {
                        if (d == i) continue;
                        int t = blk_code[blk_encode(blk_moved(st, n, i, d), n)];
                        if (seen_at[t] == stamp) continue;
                        seen_at[t] = stamp;
                        par[t] = x;
                        pmv[t] = k * 8 + d;
                        q.push_back(t);
                        if (blk_sat_state(t, want) && (best < 0 || blk_v[t] < blk_v[best] - 1e-12)) best = t;
                    }
                }
            }
        }
        if (best < 0) {
            invalid = true;
            return;
        }
        std::vector<int> path;
        for (int x = best; x != s0; x = par[x]) path.push_back(pmv[x]);
        for (int i = (int)path.size() - 1; i >= 0; i--) move(blk_paper[path[i] / 8], p0 + path[i] % 8);
    }
    // After a split (plain flips, more than 5 blocks): one move of the base, to just below the
    // deepest flip that must be on (or to the very top if none must), or no base move if every flip
    // that must be on is already above it, whichever leaves fewer flips to turn off one by one
    // (moving the base up turns off every flip it passes); then the others off, just below the base.
    int orientation(int b) const {  // 1 iff the flip of b is above the base paper
        for (int k : order) {
            if (k == blocks[b].pf) return 1;
            if (k == base_paper) return 0;
        }
        return 0;
    }
    void set_blocks_plain(const std::vector<int>& want) {
        const int nb = blocks.size();
        int bpos = index_of(base_paper);
        int pmin = -1, pmin_b = -1;  // position of the deepest flip that must be on
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
        for (int b = 0; b < nb; b++)
            if (want[b] == 0 && orientation(b) == 1) move_after(blocks[b].pf, base_paper);
    }

    // ------------------------------------------------------------------------------------------
    // The stack

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
    u64 display() const {
        u64 covered = 0, black = 0;
        for (int k : order) {
            black |= paper[k].black & ~covered;
            covered |= paper[k].opaque;
        }
        return black;
    }
    // Moves paper k so that d papers are above it (no move if it is there already). While plans
    // are simulated (check_vis), a move of an invisible paper marks the plan invalid.
    bool check_vis = false, invalid = false;
    void move(int k, int d) {
        int i = index_of(k);
        if (i == d) return;
        if (check_vis && !visible(k)) invalid = true;
        order.erase(order.begin() + i);
        order.insert(order.begin() + d, k);
        ops.push_back({k, d});
    }
    void move_after(int k, int x) {  // just below paper x
        int i = index_of(k);
        if (index_of(x) + 1 == i) return;
        if (check_vis && !visible(k)) invalid = true;
        order.erase(order.begin() + i);
        int j = 0;
        while (order[j] != x) j++;
        order.insert(order.begin() + j + 1, k);
        ops.push_back({k, j + 1});
    }
    bool is_filler(int k) const {
        for (auto& f : fillers) if (f.paper == k) return true;
        return false;
    }
    void drop_filler(int k) {
        std::erase_if(fillers, [&](const Filler& f) { return f.paper == k; });
    }
    // Papers of column l that are in place (not lifted to the top, not out as a filler).
    bool in_column(int k, int l) const { return col_of[k] == l && k != top_d && !is_filler(k); }
    // Up to n papers in place at the top of column l, top first, into `top`.
    void column_tops(int l, int n, std::vector<int>& top) const {
        top.clear();
        for (int k : order)
            if (in_column(k, l)) {
                top.push_back(k);
                if ((int)top.size() >= n) break;
            }
    }
    int column_top(int l) const {
        for (int k : order) if (in_column(k, l)) return k;
        return -1;
    }
    void dig(int l) {  // the top of column l to its bottom
        int t = column_top(l), b = -1;
        for (int k : order) if (in_column(k, l)) b = k;
        if (t != b) move_after(t, b);
    }
    void lift(int d) {  // dedicated paper d (in place) to the very top
        while (column_top(col_of[d]) != d) dig(col_of[d]);
        move(d, 0);
        top_d = d;
        top_pred = -1;
    }
    // Digs column l until its handle shows color c (at most one full turn).
    void set_handle(int l, int c) {
        int t0 = column_top(l);
        for (int it = 0; it < K; it++) {
            int t = column_top(l);
            if ((int)(paper[t].black >> handle[l] & 1) == c) return;
            if (it > 0 && t == t0) return;
            dig(l);
        }
    }
    void fix_handles(int u, u64 hh) {  // every handle hole in hh to the color of A_u
        for (int j = 0; j < H; j++)
            if (hh >> handle[j] & 1) set_handle(j, A[u] >> handle[j] & 1);
    }
    // Digs set_handle(l, c) would spend (without moving anything).
    int handle_fix_cost(int l, int c) const {
        int i = 0;
        for (int k : order) {
            if (!in_column(k, l)) continue;
            if ((int)(paper[k].black >> handle[l] & 1) == c) return i;
            i++;
        }
        return 0;
    }
    std::vector<int> fix_costs(int u, u64 hh) const {  // handle_fix_cost of the holes in hh, per handle
        std::vector<int> fix(H, 0);
        for (int j = 0; j < H; j++)
            if (hh >> handle[j] & 1) fix[j] = handle_fix_cost(j, A[u] >> handle[j] & 1);
        return fix;
    }
    int level_past(u64 wrong) const {  // level just past the deepest handle window in `wrong`
        int lvl = 0;
        for (u64 x = wrong; x; x &= x - 1) lvl = std::max(lvl, hidx[__builtin_ctzll(x)] + 1);
        return lvl;
    }
    u64 shown_by(const Filler& f) const {  // handle windows a filler shows on
        u64 m = 0;
        for (int j = f.lvl; j <= f.hi; j++)
            if (paper[f.paper].opaque >> handle[j] & 1) m |= 1ULL << handle[j];
        return m;
    }
    // A filler [lvl, c] placed now would sit above a filler of a deeper level that it reaches.
    static bool reaches_deeper(int lvl, int c, const std::vector<Filler>& placed) {
        for (auto& f : placed) if (f.lvl > lvl && c >= f.lvl) return true;
        return false;
    }
    // Paper x to level lvl: just above the first paper in place of a column >= lvl, i.e. below the
    // generic layer, the columns 0..lvl-1 and the fillers of lower levels. lazy: no move if x is
    // already between the last paper in place of a column < lvl (or the base paper, below_generic)
    // and that position.
    void move_to_level(int x, int lvl, bool lazy = false, bool below_generic = false) {
        int q = K, last_above = -1;
        for (int i = 0; i < K; i++) {
            int k = order[i];
            if (below_generic && k == base_paper) last_above = i;
            if (k == x || col_of[k] < 0 || !in_column(k, col_of[k])) continue;
            if (col_of[k] < lvl) last_above = i;
            else if (q == K) q = i;
        }
        int xi = index_of(x);
        if (lazy && xi < q && xi > last_above) return;
        move(x, xi < q ? q - 1 : q);
    }
    // A filler from column c at depth `depth` (moved after X_0..X_{depth-1} go just below it in
    // their order, which keeps the cyclic order of the column) placed at level lvl.
    void place_filler(int c, int depth, int lvl, u64& hh) {
        std::vector<int> top;
        column_tops(c, depth + 1, top);
        int pred = -1;
        for (int i = 0, prev = top[depth]; i < depth; i++) move_after(top[i], prev), prev = top[i];
        if (depth > 0) pred = top[depth - 1];
        int x = top[depth];
        move_to_level(x, lvl);
        fillers.push_back({x, pred, lvl, c});
        hh &= ~shown_by(fillers.back());
    }

    // An out-of-place paper x (the lifted paper or a filler) goes back to its column: just below its
    // cyclic predecessor if it has one in place; otherwise (pred -1: taken from the column top, or
    // its predecessor is the column bottom, see canonicalize) at the top (mode 2) or the bottom
    // (mode 1), both keeping the cyclic order. Mode 0 is the hub7 rule: at the top when u's paper
    // has a hole at the column's handle whose current top shows the wrong color and x the right
    // one (at the bottom if u's paper is of this column, at the top if it is x).
    void return_paper(int x, int u, int mode) {
        int l = col_of[x], pred = -1;
        if (x == top_d) {
            pred = top_pred;
            top_d = top_pred = -1;
        } else if (auto it = std::find_if(fillers.begin(), fillers.end(), [&](const Filler& f) { return f.paper == x; });
                   it != fillers.end()) {
            pred = it->pred;
            fillers.erase(it);
        }
        if (pred >= 0 && in_column(pred, col_of[pred])) {
            move_after(x, pred);
            return;
        }
        int top = -1;  // column top without x
        for (int k : order)
            if (k != x && in_column(k, l)) {
                top = k;
                break;
            }
        bool at_top = false;
        if (top >= 0) {
            if (mode == 2) {
                at_top = true;
            } else if (mode == 0) {
                int wp = ded[u], hw = handle[l];
                if (wp == x) {
                    at_top = true;
                } else if (!(wp >= 0 && col_of[wp] == l) && (wp < 0 || !(paper[wp].opaque >> hw & 1))) {
                    int c = A[u] >> hw & 1;
                    at_top = (int)(paper[top].black >> hw & 1) != c && (int)(paper[x].black >> hw & 1) == c;
                }
            }
        }
        if (at_top) {
            int j = index_of(top);
            move(x, index_of(x) < j ? j - 1 : j);
        } else {  // below the last paper of the generic layer and of the columns 0..l
            int last = -1;
            for (int k : order) {
                if (k == x || k == top_d || is_filler(k)) continue;
                if (block_of[k] >= 0 || (col_of[k] >= 0 && col_of[k] <= l)) last = k;
            }
            move_after(x, last);
        }
    }

    // ------------------------------------------------------------------------------------------
    // Plans of a request

    struct PlanOpt {
        int ret_mode = 0;   // the previous lifted paper: return_paper mode; 3 re-used as a filler,
                            // 4 stays under the new one
        int fret_mode = 0;  // the old fillers: return_paper mode (1, 2); 3 re-used if useful,
                            // 4 also left in place when harmless; 5 the joint plan (run_joint)
        bool use_filler = false;
        bool keep = false;  // the previous lifted paper is also the paper of u (a pair): keep it
        int fret_ret = 1;   // return_paper mode of the old fillers not re-used (fret_mode 3-5)
    };
    struct FillerPick {
        int c = -1, depth = 0, lvl = 0;
        bool post = false;  // placed after D is lifted
    };
    // A candidate interval [lvl, c] of handles for the interval DPs.
    struct Cand {
        int lvl;
        double gain;
        int c, depth;  // a paper at depth `depth` of column c; depth < 0: stack -1 - depth
        int kind = 0;  // run_joint: 0 new filler (idx = paper), 1 old re-leveled, 2 old stays, 3 x0
        int idx = -1;
        bool post = false;
    };
    // Weighted interval scheduling over the handle indices (cand[c]: the candidates ending at c):
    // the best set of disjoint intervals, deepest first. Disjoint intervals never cover each
    // other's column handles, so their gains add up.
    std::vector<Cand> best_intervals(const std::vector<std::vector<Cand>>& cand) const {
        std::vector<double> best(H + 1, 0);
        std::vector<int> pick(H + 1, -1);
        for (int c = 0; c < H; c++) {
            best[c + 1] = best[c];
            for (int i = 0; i < (int)cand[c].size(); i++)
                if (best[cand[c][i].lvl] + cand[c][i].gain > best[c + 1] + 1e-9) {
                    best[c + 1] = best[cand[c][i].lvl] + cand[c][i].gain;
                    pick[c + 1] = i;
                }
        }
        std::vector<Cand> res;
        for (int j = H; j > 0;) {
            if (pick[j] < 0) {
                j--;
                continue;
            }
            res.push_back(cand[j - 1][pick[j]]);
            j = res.back().lvl;
        }
        return res;
    }
    // A filler from a column costs 1 move (+ depth) now and is charged at most 1 more for its
    // return, but papers left out are often re-used or left in place: one that saves 2 + depth digs
    // is worth taking.
    static constexpr int kFillerDepth = 3, kFillerCost = 1, kMaxFillers = 8;
    // Fillers when D (column l) is already on top (kept plans): the papers at depth <= kFillerDepth
    // of the columns whose handle is a hole of D, at the level just past their deepest wrong handle.
    std::vector<FillerPick> choose_fillers_dp(int u, int d, u64 hh) const {
        auto fix = fix_costs(u, hh);
        std::vector<std::vector<Cand>> cand(H);
        std::vector<int> top;
        for (int c = 0; c < H; c++) {
            if (!(hh >> handle[c] & 1)) continue;
            column_tops(c, kFillerDepth + 1, top);
            if (top.empty() || top[0] == d) continue;
            for (int depth = 0; depth < (int)top.size(); depth++) {
                u64 shown = paper[top[depth]].opaque & hh;
                int lvl = level_past((paper[top[depth]].black ^ A[u]) & shown);
                if (lvl > c || reaches_deeper(lvl, c, fillers)) continue;
                int save = 0;
                for (int j = lvl; j <= c; j++)
                    if ((j != c || depth) && (shown >> handle[j] & 1)) save += fix[j];
                int gain = save - kFillerCost - depth;
                if (gain > 0) cand[c].push_back({lvl, (double)gain, c, depth});
            }
        }
        std::vector<FillerPick> res;
        for (auto& cd : best_intervals(cand)) res.push_back({cd.c, cd.depth, cd.lvl, false});
        std::reverse(res.begin(), res.end());
        return res;
    }
    // Fillers chosen before D (column l, in place) is lifted: candidates are the top papers of every
    // column c != l whose handle is not covered by a filler already placed, at the level just past
    // their deepest wrong handle and at the narrower levels lv whose handle h_lv is a hole they
    // cover (audit3-narrow). A candidate of a column c > l whose interval reaches h_l would hide D's
    // column top: it is placed after the lift (post). A candidate of a column c < l whose handle D
    // covers can only be placed before the lift.
    // Stacks (audit3-stack): two papers at one level a, U (column cU) placed first and L (column
    // cL > cU) next, which inserts L just below U. U shows on its opaque handles in [a, cU], L on
    // the holes of U there and on (cU, cL]; L may be wrong where U masks it.
    std::vector<FillerPick> choose_fillers_prelift(int u, int d, u64 hh) const {
        const int l = col_of[d];
        const u64 hole_all = hmask & ~paper[d].opaque;  // handle holes of D (also those covered)
        u64 covered = 0;  // handles shown by fillers already placed
        for (auto& f : fillers) covered |= shown_by(f);
        auto fix = fix_costs(u, hh);
        std::vector<std::vector<Cand>> cand(H);
        std::vector<int> top;
        for (int c = 0; c < H; c++) {
            if (c == l || (covered >> handle[c] & 1)) continue;
            bool hole_c = hole_all >> handle[c] & 1;
            column_tops(c, kFillerDepth + 1, top);
            for (int depth = 0; depth < (int)top.size(); depth++) {
                int f = top[depth];
                u64 shown = paper[f].opaque & hh;
                int lvl = level_past((paper[f].black ^ A[u]) & shown);
                if (lvl > c || reaches_deeper(lvl, c, fillers)) continue;
                for (int lv = lvl; lv <= c; lv++) {
                    if (lv > lvl && (!(shown >> handle[lv] & 1) || reaches_deeper(lv, c, fillers))) continue;
                    bool post = c > l && lv <= l && (paper[f].opaque >> handle[l] & 1);
                    int save = 0;
                    for (int j = lv; j <= c; j++)
                        if ((shown >> handle[j] & 1) && (j != c || depth || !hole_c)) save += fix[j];
                    int gain = save - kFillerCost - depth;
                    if (gain > 0) cand[c].push_back({lv, (double)gain, c, depth, 0, -1, post});
                }
            }
        }
        // Stacks, on bitsets by handle index.
        struct PC {
            int c, depth;
            u64 opq, shown, bad;  // opaque, on a hole to fill, wrong there
            bool hole_c;
            int fsum;  // digs saved if it showed on all of `shown` (an upper bound)
        };
        struct Stack {
            int cU, dU, cL, dL;
            bool postU, postL;
        };
        std::vector<Stack> stacks;
        auto hib = [](u64 x) { return x ? 63 - __builtin_clzll(x) : -1; };
        auto upto = [](int b) -> u64 { return b < 0 ? 0 : b >= 63 ? ~0ULL : (1ULL << (b + 1)) - 1; };
        const u64 hh_i = handle_bits(hh), au_i = handle_bits(A[u]);  // holes to fill, colors of A_u
        // The top papers of the usable columns: pcs of column c are [first_of[c], first_of[c + 1]).
        std::vector<std::array<int, kFillerDepth + 1>> tops(H);
        std::vector<int> ntop(H, 0);
        for (int k : order) {
            int c = col_of[k];
            if (c < 0 || ntop[c] > kFillerDepth || !in_column(k, c)) continue;
            tops[c][ntop[c]++] = k;
        }
        std::vector<PC> pcs;
        std::vector<int> first_of(H + 1, 0);
        for (int c = 0; c < H; c++) {
            first_of[c] = pcs.size();
            if (c == l || (covered >> handle[c] & 1)) continue;
            for (int dpt = 0; dpt < ntop[c]; dpt++) {
                int k = tops[c][dpt];
                PC pc{c, dpt, h_opq[k] & upto(c), 0, 0, (bool)(hole_all >> handle[c] & 1), 0};
                pc.shown = pc.opq & hh_i;
                pc.bad = pc.shown & (h_blk[k] ^ au_i);
                for (u64 x = pc.shown; x; x &= x - 1) pc.fsum += fix[__builtin_ctzll(x)];
                pcs.push_back(pc);
            }
        }
        first_of[H] = pcs.size();
        for (auto& L : pcs) {
            if (!L.bad) continue;  // right everywhere: a single filler at level 0 does it
            // U must mask the deepest wrong handle of L: columns mL..L.c-1
            for (int ui = first_of[std::max(hib(L.bad), 0)]; ui < first_of[L.c]; ui++) {
                const PC& U = pcs[ui];
                if (U.fsum + L.fsum < 2 * kFillerCost + U.depth + L.depth + 2) continue;  // cannot pay
                int aU = hib(U.bad) + 1;
                if (aU > U.c) continue;
                int a = std::max(aU, hib(L.bad & ~U.opq & upto(U.c)) + 1);
                if (a > U.c) continue;
                bool postU = U.c > l && a <= l && (U.opq >> l & 1);
                bool postL = postU || (L.c > l && a <= l && (L.opq >> l & 1));
                if ((postU && !U.hole_c) || (postL && !L.hole_c) || reaches_deeper(a, L.c, fillers)) continue;
                u64 from_a = ~upto(a - 1);
                u64 covU = U.shown & from_a & upto(U.c), covL = L.shown & ~U.opq & from_a & upto(L.c);
                if (U.depth == 0 && U.hole_c) covU &= ~(1ULL << U.c);
                if (L.depth == 0 && L.hole_c) covL &= ~(1ULL << L.c);
                int save = 0;
                for (u64 x = covU | covL; x; x &= x - 1) save += fix[__builtin_ctzll(x)];
                int gain = save - 2 * kFillerCost - U.depth - L.depth;
                if (gain < 2) continue;
                stacks.push_back({U.c, U.depth, L.c, L.depth, postU, postL});
                cand[L.c].push_back({a, (double)gain, L.c, -(int)stacks.size()});
            }
        }
        std::vector<FillerPick> res;
        for (auto& cd : best_intervals(cand)) {
            if (cd.depth < 0) {  // a stack: U then L after the reversal
                const Stack& st = stacks[-1 - cd.depth];
                res.push_back({st.cL, st.dL, cd.lvl, st.postL});
                res.push_back({st.cU, st.dU, cd.lvl, st.postU});
            } else {
                res.push_back({cd.c, cd.depth, cd.lvl, cd.post});
            }
        }
        std::reverse(res.begin(), res.end());
        return res;
    }

    // Level for an out-of-place paper x (the previous lifted paper or an old filler) to serve as a
    // filler for D (column l, handle holes hh): just past its deepest wrong handle, and below D's
    // column when x would cover h_l (it must not hide D's column top). -1 if it covers nothing
    // there. cov receives the covered holes.
    int level_for(int x, int d, u64 hh, int u, u64& cov) const {
        int cx = col_of[x], l = col_of[d];
        u64 shown = paper[x].opaque & hh;
        int lvl = level_past((paper[x].black ^ A[u]) & shown);
        if (cx >= l && (paper[x].opaque >> handle[l] & 1)) lvl = std::max(lvl, l + 1);
        cov = 0;
        for (int j = lvl; j <= cx; j++)
            if (shown >> handle[j] & 1) cov |= 1ULL << handle[j];
        return cov ? lvl : -1;
    }
    // An old filler above the base paper (the previous lifted paper left under the new one by the
    // stay plan) shows its colors on the generic holes of the next paper D. Where they differ from
    // A_u it cannot stay there: re-leveling moves it below the generic layer, and it is not
    // harmless in place (audit4).
    bool gen_harm(int x, int d, int u) const {
        if (d < 0 || index_of(x) > index_of(base_paper)) return false;
        return (paper[x].opaque & gmask & ~paper[d].opaque & (paper[x].black ^ A[u])) != 0;
    }
    // Old fillers (olds) that can cover holes of D = ded[u] not yet covered (pre_cov) move straight
    // to their new level if that saves at least 2 digs (no move if they already sit at that level);
    // with keep_harmless, the others stay where they are when they do not hide D's column top and
    // show A_u on the holes they cover; the rest go back to their columns (mode). `placed` holds
    // the fillers of this request so far.
    void refill_or_return(int u, const std::vector<Filler>& olds, u64& pre_cov, std::vector<Filler>& placed,
                          int mode, bool keep_harmless) {
        int d = ded[u];
        for (int i = (int)olds.size() - 1; i >= 0; i--) {
            int x = olds[i].paper, cf = col_of[x];
            bool use = false;
            int lvl = 0;
            u64 cov = 0;
            if (d >= 0 && x != d && visible(x)) {
                lvl = level_for(x, d, hmask & ~paper[d].opaque & ~pre_cov, u, cov);
                if (lvl >= 0 && !reaches_deeper(lvl, cf, placed)) {
                    int save = 0;
                    for (int j = lvl; j <= cf; j++)
                        if (cov >> handle[j] & 1) save += handle_fix_cost(j, A[u] >> handle[j] & 1);
                    use = save >= 2;
                }
            }
            if (!use && keep_harmless && d >= 0 && x != d) {
                int L = olds[i].lvl, l = col_of[d];
                bool harm = (L <= l && l <= cf && (paper[x].opaque >> handle[l] & 1)) || reaches_deeper(L, cf, placed);
                u64 hcov = 0;
                for (int j = L; j <= cf; j++) hcov |= 1ULL << handle[j];
                hcov &= paper[x].opaque & hmask & ~paper[d].opaque & ~pre_cov;
                if ((paper[x].black ^ A[u]) & hcov || gen_harm(x, d, u)) harm = true;
                if (!harm && visible(x)) {
                    drop_filler(x);
                    placed.push_back(olds[i]);
                    pre_cov |= hcov;
                    continue;
                }
            }
            if (!use) {
                return_paper(x, u, mode);
                continue;
            }
            drop_filler(x);
            move_to_level(x, lvl, true, gen_harm(x, d, u));
            placed.push_back({x, olds[i].pred, lvl, cf});
            pre_cov |= cov;
        }
    }

    // Joint choice (fret_mode 5, pool-value) of the papers out of their columns (the previous
    // lifted paper x0 and the old fillers) and of the new fillers from the column tops: one
    // weighted interval scheduling over the handles, every candidate an interval [lvl, c] that a
    // paper of column c shows on (matching A_u on all the holes of D it covers):
    //   - a new filler, the paper at depth p <= kFillerDepth of column c: gain = saved digs - 1 - p
    //     (taken only if at least kFillerCost);
    //   - an old paper moved to a new level: gain = saved digs - kRelevel;
    //   - an old filler left where it is: gain = saved digs + 1 - kStay;
    // all also at narrower levels. Old papers not chosen go back to their columns. Saved digs are
    // the handle_fix_cost of the covered holes before any move. The requested paper D, when it is
    // an old filler, is lifted straight from there (no return, no dig).
    static constexpr double kRelevel = 0.5, kStay = 0.8;
    int depth_in_column(int x) const {  // depth of paper x (in place) in its column
        int i = 0;
        for (int k : order) {
            if (k == x) return i;
            if (in_column(k, col_of[x])) i++;
        }
        return -1;
    }
    void run_joint(int u, const PlanOpt& opt) {
        int d = ded[u];
        if (d < 0 || d == top_d) {
            invalid = true;
            return;
        }
        const int l = col_of[d];
        const u64 hole_all = (gmask | hmask) & ~paper[d].opaque;
        u64 hh = hole_all & ~gmask;
        auto fix = fix_costs(u, hh);
        const bool d_out = is_filler(d);  // D is an old filler: lifted directly
        std::vector<Filler> olds;
        for (auto& f : fillers) if (f.paper != d) olds.push_back(f);
        const int x0 = top_d;
        std::vector<std::vector<Cand>> cand(H);
        auto mism_level = [&](int x) { return level_past((paper[x].black ^ A[u]) & paper[x].opaque & hh); };
        auto saved = [&](int x, int lvl, int c, bool skip_c) {
            int sv = 0;
            for (int j = lvl; j <= c; j++)
                if ((hh >> handle[j] & 1) && (paper[x].opaque >> handle[j] & 1) && !(skip_c && j == c)) sv += fix[j];
            return sv;
        };
        auto covers = [&](int x, int j) { return (hh >> handle[j] & 1) && (paper[x].opaque >> handle[j] & 1); };
        // Old papers (L: current level of an old filler; -1 for x0).
        auto add_old = [&](int x, int idx, int L, bool is_x0) {
            int c = col_of[x];
            int lvl = mism_level(x);
            if (!is_x0 && gen_harm(x, d, u)) L = -2;  // cannot stay where it is
            if (!d_out && c >= l && (paper[x].opaque >> handle[l] & 1)) lvl = std::max(lvl, l + 1);  // hides D's column top
            if (lvl <= c) {
                int sv = saved(x, lvl, c, false);
                double g = sv - kRelevel;
                if (!is_x0 && lvl == L) g = sv + 1 - kStay;  // already there
                if (g > 0) cand[c].push_back({lvl, g, c, 0, is_x0 ? 3 : (lvl == L ? 2 : 1), idx});
            }
            if (!is_x0 && L > lvl && L <= c) {
                // left at its (narrower) level L: harmless iff it does not hide D's column top
                bool harm = !d_out && L <= l && l <= c && (paper[x].opaque >> handle[l] & 1);
                double g = saved(x, L, c, false) + 1 - kStay;
                if (!harm && g > 0) cand[c].push_back({L, g, c, 0, 2, idx});
            }
            for (int lv = lvl + 1; lv <= c; lv++) {  // narrower levels
                if (!covers(x, lv) || (!is_x0 && lv == L)) continue;
                double g = saved(x, lv, c, false) - kRelevel;
                if (g > 0) cand[c].push_back({lv, g, c, 0, is_x0 ? 3 : 1, idx});
            }
        };
        for (int i = 0; i < (int)olds.size(); i++) add_old(olds[i].paper, i, olds[i].lvl, false);
        if (x0 >= 0) add_old(x0, -1, -1, true);
        // New fillers from the column tops (all after the lift if D is lifted from the fillers, as D
        // on top hides the columns whose handles it covers).
        std::vector<int> top;
        for (int c = 0; c < H; c++) {
            bool hole_c = hh >> handle[c] & 1;
            if (c == l || (d_out && !hole_c)) continue;
            column_tops(c, kFillerDepth + 1, top);
            for (int depth = 0; depth < (int)top.size(); depth++) {
                int f = top[depth];
                int lvl = mism_level(f);
                for (int lv = lvl; lv <= c; lv++) {
                    if (lv > lvl && !covers(f, lv)) continue;
                    bool post = d_out || (c > l && lv <= l && (paper[f].opaque >> handle[l] & 1));
                    int g = saved(f, lv, c, depth == 0 && hole_c) - 1 - depth;
                    if (g >= kFillerCost) cand[c].push_back({lv, (double)g, c, 0, 0, f, post});
                }
            }
        }
        const auto picks = best_intervals(cand);
        std::vector<int> old_dec(olds.size(), 0), old_lvl(olds.size(), -1);  // 0 return, 1 re-level, 2 stay
        int x0_lvl = -1;
        for (auto& cd : picks) {
            if (cd.kind == 1 || cd.kind == 2) old_dec[cd.idx] = cd.kind, old_lvl[cd.idx] = cd.lvl;
            if (cd.kind == 3) x0_lvl = cd.lvl;
        }
        Filler fd{d, -1};  // D's record if it is an old filler (keeps its predecessor)
        for (auto& f : fillers) if (f.paper == d) fd = f;
        fillers = olds;
        if (d_out) fillers.push_back(fd);  // D stays a filler (in_column false) until lifted
        // The returns of the visible old fillers, then x0 (which may hide the others), then the
        // other returns, then the re-levels.
        std::vector<char> done(olds.size(), 0);
        for (int i = (int)olds.size() - 1; i >= 0; i--) {
            if (old_dec[i] != 0 || !visible(olds[i].paper)) continue;
            return_paper(olds[i].paper, u, opt.fret_ret);
            done[i] = 1;
        }
        if (x0 >= 0) {
            if (x0_lvl >= 0) {
                top_d = -1;
                move_to_level(x0, x0_lvl, true, gen_harm(x0, d, u));
                fillers.push_back({x0, top_pred, x0_lvl, col_of[x0]});
                top_pred = -1;
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
            if (old_dec[i] == 1) move_to_level(x, old_lvl[i], true, gen_harm(x, d, u));
        }
        for (auto& f : fillers) if (f.paper != d) hh &= ~shown_by(f);
        set_blocks(wanted_blocks(u, hole_all));
        for (auto& cd : picks)
            if (cd.kind == 0 && !cd.post) place_filler(cd.c, depth_in_column(cd.idx), cd.lvl, hh);
        if (d_out) {
            drop_filler(d);
            move(d, 0);
            top_d = d;
            top_pred = fd.pred;
        } else {
            lift(d);
        }
        for (auto& cd : picks)
            if (cd.kind == 0 && cd.post) place_filler(cd.c, depth_in_column(cd.idx), cd.lvl, hh);
        fix_handles(u, hh);
    }

    void run_plan(int u, const PlanOpt& opt) {
        if (opt.fret_mode == 5) {
            run_joint(u, opt);
            return;
        }
        const bool kept = opt.keep && top_d >= 0 && ded[u] == top_d;
        u64 pre_cov = 0;  // handles covered by papers kept out (ret_mode 3 and 4)
        // ret_mode 4 (audit-stay): the previous paper x stays where it is and D goes above it, so x
        // shows on the holes of D up to its own handle (it must show A_u there; it is above the
        // generic layer, so D must have no generic hole where x is opaque). x is then a filler of
        // level 0, returned or re-used at a later request.
        int stay = -1, stay_pred = -1;
        if (opt.ret_mode == 4) {
            int d = ded[u];
            if (top_d < 0 || kept || d < 0 || d == top_d || (gmask & ~paper[d].opaque & paper[top_d].opaque)) {
                invalid = true;
                return;
            }
            stay = top_d, stay_pred = top_pred;  // lifted from the fillers: keeps its predecessor
            top_d = top_pred = -1;
        }
        if (top_d >= 0 && !kept && opt.ret_mode == 3) {
            // The previous paper x (column lp) as a filler for D = ded[u] (column l < lvl <= lp):
            // at level lvl it covers the holes of D in h_lvl..h_lp where it is opaque, and must show
            // A_u there. The visible old fillers go back first (x may hide them), the others after.
            int x = top_d, lp = col_of[x], d = ded[u];
            if (d < 0 || d == x) {
                invalid = true;
                return;
            }
            u64 cov0 = 0;
            int lvl = level_for(x, d, hmask & ~paper[d].opaque, u, cov0);
            if (lvl < 0) {
                invalid = true;
                return;
            }
            std::vector<Filler> vis_old, def_old;
            for (auto& f : fillers) (visible(f.paper) ? vis_old : def_old).push_back(f);
            std::vector<Filler> placed = {{x, top_pred, lvl, lp}};
            pre_cov |= cov0;
            auto put_back = [&](const std::vector<Filler>& olds) {
                if (opt.fret_mode >= 3) refill_or_return(u, olds, pre_cov, placed, opt.fret_ret, opt.fret_mode == 4);
                else for (int i = (int)olds.size() - 1; i >= 0; i--) return_paper(olds[i].paper, u, opt.fret_mode);
            };
            put_back(vis_old);
            move_to_level(x, lvl);
            top_d = top_pred = -1;
            put_back(def_old);
            for (auto& f : placed) fillers.push_back(f);
        } else {
            if (top_d >= 0 && !kept) return_paper(top_d, u, opt.ret_mode);
            if (opt.fret_mode >= 3) {
                std::vector<Filler> olds = fillers, placed;
                refill_or_return(u, olds, pre_cov, placed, opt.fret_ret, opt.fret_mode == 4);
                for (auto& f : placed) fillers.push_back(f);
            } else {
                while (!fillers.empty()) return_paper(fillers.back().paper, u, opt.fret_mode);
            }
        }
        if (stay >= 0) {
            fillers.push_back({stay, stay_pred, 0, col_of[stay]});
            pre_cov |= shown_by(fillers.back());
        }
        if (ded[u] < 0) {  // no unit (does not happen): the closer orientation per block, every handle
            set_blocks(wanted_blocks(u, gmask));
            for (int l = 0; l < H; l++) set_handle(l, A[u] >> handle[l] & 1);
            return;
        }
        const int d = ded[u];
        const u64 holes = (gmask | hmask) & ~paper[d].opaque;
        set_blocks(wanted_blocks(u, holes));
        u64 hh = holes & ~gmask & ~pre_cov;
        if (!kept && opt.use_filler) {
            // Fillers chosen with every column top visible; those that do not reach D's handle go
            // in before the dig and the lift, the others after.
            auto picks = choose_fillers_prelift(u, d, hh);
            for (auto& pk : picks) if (!pk.post) place_filler(pk.c, pk.depth, pk.lvl, hh);
            lift(d);
            for (auto& pk : picks) if (pk.post) place_filler(pk.c, pk.depth, pk.lvl, hh);
        } else {
            if (!kept) lift(d);
            if (opt.use_filler)
                for (auto& pk : choose_fillers_dp(u, d, hh)) {
                    if ((int)fillers.size() >= kMaxFillers) break;
                    place_filler(pk.c, pk.depth, pk.lvl, hh);
                }
        }
        fix_handles(u, hh);
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
    // Expected extra fixes caused by the column tops of the current state: a column whose top
    // shows the minority color at its handle costs 2 p_m - 1 more at the next request that needs
    // that handle (the persistence model of the annealing).
    double tops_penalty() const {
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
    // Peephole on the moves of a plan (audit-merge). A plan sometimes moves a paper twice (an old
    // filler goes back below its predecessor and its column is then dug past it, or it goes back
    // and is placed again, or the requested paper is returned and then lifted). Moving it at the
    // first step straight to where the second step puts it (the same depth after the second step,
    // or just below the paper the second step puts it under), or dropping the first move, often
    // keeps every move legal and gives the same final order: each candidate is checked by
    // replaying the moves, the others keeping the paper they are inserted under.
    void merge_double_moves(const std::vector<int>& start, std::vector<std::pair<int, int>>& mvs) const {
        bool dup = false;
        for (size_t i = 0; i < mvs.size() && !dup; i++)
            for (size_t j = i + 1; j < mvs.size() && !dup; j++) dup = mvs[i].first == mvs[j].first;
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

    // The records of the papers out of their columns rebuilt from the order after every request
    // (audit4). Every plan keeps the cyclic order of each column (the papers in place form a
    // rotation of the column's initial order with the papers out removed), so the order alone
    // tells which papers are in place, the level of each filler (the column of the first paper in
    // place below it) and its cyclic predecessor. Compared with the records kept by the plans: a
    // filler whose nearest cyclic predecessor in place is the column bottom may go back at either
    // end (pred -1); one whose predecessor is out goes back below the nearest one in place; one at
    // level c of its own column c sitting on the column top in cyclic order is in place.
    std::vector<std::vector<int>> cyc;  // per column, its cyclic order (top to bottom at the start)
    std::vector<int> cpos;              // position of a dedicated paper in its cycle
    void init_cycles() {
        cyc.assign(H, {});
        cpos.assign(K, -1);
        for (int k : order)
            if (col_of[k] >= 0) {
                cpos[k] = cyc[col_of[k]].size();
                cyc[col_of[k]].push_back(k);
            }
    }
    // Walking up from the bottom, a paper of column c <= cur (cur = column of the nearest paper in
    // place below) is in place, one of a column > cur is out (a filler of level cur), and a column
    // paper above a generic paper is out (level 0). A run that is not a cyclic subsequence of its
    // column loses its top paper (a filler of level c); if it is still not cyclic, the records are
    // left as they are.
    void canonicalize() {
        static std::vector<char> inpl;
        static std::vector<int> lv;
        static std::vector<std::vector<int>> run;
        inpl.assign(K, 0);
        lv.assign(K, -1);
        run.assign(H, {});
        int cur = H;
        bool gen_seen = false;
        for (int i = K - 1; i >= 0; i--) {
            int k = order[i], c = col_of[k];
            if (c < 0) {
                if (block_of[k] >= 0) gen_seen = true;
                continue;
            }
            if (!gen_seen && c <= cur) {
                cur = c;
                run[c].push_back(k);  // bottom to top
                inpl[k] = 1;
            } else {
                lv[k] = gen_seen ? 0 : std::min(cur, c);
            }
        }
        for (int c = 0; c < H; c++) {
            auto& r = run[c];
            int n = cyc[c].size();
            auto cyclic = [&](int skip_top) {
                int m = (int)r.size() - skip_top;
                if (m <= 1) return true;
                long tot = 0;
                for (int t = m - 1; t > 0; t--) tot += ((cpos[r[t - 1]] - cpos[r[t]]) % n + n) % n;
                tot += ((cpos[r[m - 1]] - cpos[r[0]]) % n + n) % n;
                return tot == n;
            };
            if (cyclic(0)) continue;
            if (!cyclic(1)) return;
            int k = r.back();
            r.pop_back();
            inpl[k] = 0;
            lv[k] = c;
        }
        auto pred_of = [&](int x) {
            int c = col_of[x], n = cyc[c].size();
            if (run[c].empty()) return -1;
            for (int t = 1; t < n; t++) {
                int p = cyc[c][((cpos[x] - t) % n + n) % n];
                if (inpl[p]) return p == run[c][0] ? -1 : p;
            }
            return -1;
        };
        int ntop = -1, npred = -1;
        std::vector<Filler> nf;
        for (int i = 0; i < K; i++) {
            int k = order[i];
            if (col_of[k] < 0 || inpl[k]) continue;
            if (i == 0) ntop = k, npred = pred_of(k);
            else nf.push_back({k, pred_of(k), lv[k], col_of[k]});
        }
        // keep the order of the records of the plan (the returns go from the back)
        std::vector<Filler> res;
        for (auto& f : fillers)
            for (auto& g : nf)
                if (g.paper == f.paper) res.push_back(g);
        for (auto& g : nf)
            if (!is_filler(g.paper)) res.push_back(g);
        top_d = ntop;
        top_pred = npred;
        fillers = res;
    }

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
    // A paper left out costs its return later but is often re-used instead (kFillerCharge), and
    // the column tops left are valued by tops_penalty.
    static constexpr double kFillerCharge = 0.8, kTopValue = 0.55;
    std::vector<std::pair<int, int>> process(int u) {
        const State st0 = save();
        const int top0 = top_d, d = ded[u];
        bool free_filler = false;  // a filler that may go back at either end of its column
        for (auto& f : fillers) free_filler |= f.pred < 0;
        const bool prev_ok = top0 >= 0 && d >= 0 && d != top0;
        // the old fillers not re-used go back at the bottom (1), or by the hub7 rule (0) if one is free
        const std::vector<int> frets = free_filler ? std::vector<int>{1, 0} : std::vector<int>{1};
        auto skip = [&](int fm) { return (fm == 2 && !free_filler) || (fm >= 3 && fillers.empty()); };
        std::vector<PlanOpt> opts;
        for (int rm = 1; rm <= (prev_ok ? 3 : 2); rm++)
            for (int fm : {1, 2, 3, 4})
                for (int kp = 0; kp < ((top0 >= 0 && d == top0) ? 2 : 1); kp++)
                    for (int fr : (fm >= 3 ? frets : std::vector<int>{1}))
                        if (!skip(fm)) opts.push_back({rm, fm, true, kp == 1, fr});
        if (d >= 0 && d != top0)
            for (int rm = 1; rm <= 2; rm++)
                for (int fr : frets) opts.push_back({rm, 5, true, false, fr});
        if (prev_ok)
            for (int fm : {1, 2, 3, 4})
                for (int fr : (fm >= 3 ? frets : std::vector<int>{1}))
                    if (!skip(fm)) opts.push_back({4, fm, true, false, fr});
        double best = 1e18;
        std::vector<std::pair<int, int>> best_ops;
        State best_state;
        check_vis = true;
        for (const PlanOpt& o : opts) {
            restore(st0);
            ops.clear();
            invalid = false;
            run_plan(u, o);
            if (invalid || display() != A[u] || !fillers_reachable()) continue;
            merge_double_moves(st0.order, ops);
            double cost = ops.size() + kFillerCharge * fillers.size() + kTopValue * tops_penalty();
            if (cost < best) best = cost, best_ops = ops, best_state = save();
        }
        check_vis = false;
        if (best > 1e17) {  // no valid plan (inconsistent pair, or no unit): the plain procedure
            restore(st0);
            ops.clear();
            run_plan(u, PlanOpt{});
            return ops;
        }
        restore(best_state);
        canonicalize();
        return best_ops;
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
    std::string out;
    for (auto& s : solver.design()) out += s + '\n';
#ifdef SIM_HARNESS
    // Experiments only (-DSIM_HARNESS): SIM_SEQS=n random request sequences (as the generator) on
    // copies of the designed solver; prints the mean moves per request and exits.
    if (int ns = env_int("SIM_SEQS"); ns > 0) {
        double tot = 0;
        long long wr = 0;
        for (int q = 0; q < ns; q++) {
            Solver sim = solver;
            std::mt19937_64 rr(1000003ULL * (q + 1));
            int prev = rr() % p;
            for (int t = 0; t < r; t++) {
                int u = t == 0 ? prev : (int)(rr() % (p - 1));
                if (t > 0 && u >= prev) u++;
                prev = u;
                tot += sim.process(u).size();
                wr += sim.display() != A[u];
            }
        }
        std::cerr << "sim_moves = " << tot / ((double)ns * r) << "\nsim_wrong = " << (double)wr / ns << '\n';
        return 0;
    }
#endif
    std::cout << out << std::flush;
    long long total = 0, generic = 0, wrong = 0;
    double req_sec = 0;  // time spent planning the requests (without waiting for them)
    for (int t = 0; t < r; t++) {
        int u;
        std::cin >> u;
        if (u == -1) return 0;
        const double t_req = elapsed_sec();
        auto ops = solver.process(u);
        req_sec += elapsed_sec() - t_req;
        wrong += solver.display() != A[u];
        std::string o = std::to_string(ops.size()) + '\n';
        for (auto [kk, d] : ops) {
            o += std::to_string(kk) + ' ' + std::to_string(d) + '\n';
            generic += solver.block_of[kk] >= 0;
        }
        std::cout << o << std::flush;
        total += ops.size();
    }
    std::cerr << "self_wrong = " << wrong << "\ngeneric_moves = " << generic << "\ntotal_moves = " << total
              << "\nreq_sec = " << req_sec << "\nend_sec = " << elapsed_sec() << '\n';
    return 0;
}
