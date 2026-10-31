// cmp-base: solutions/cmp-climb (gpt6pro-06-01-comparator with a timed design and the filler climb)
// rewritten without the dead code of its ancestors; with the window assignment, the annealing and
// the climb fixed to the same iteration counts (MAP_ITERS, ANNEAL_ITERS, CLIMB_ITERS), the output is
// identical (solutions/cmp-base/eqcheck.py). History: trial_log.md (gpt6pro-06, cmp-, clean-, hub..).
//
// Windows: G = 36 generic windows and H = 28 handle windows h_0..h_27 (which physical windows is a
// choice of the design; internally the generic windows are 0..G-1 and h_j is window G + j before
// the annealing reorders the handles).
// Papers, top to bottom at the start:
//   - Generic layer: M = 6 sheets 0..5. Each generic window compares two of them (one black, one
//     white, the other four holes): it shows the color of the upper one. All 15 pairs of sheets are
//     used, so the 720 orders of the sheets are told apart, and every sheet but the bottom one is
//     visible somewhere. A partial display (the generic holes of a dedicated paper) asks for "a above
//     b" relations; it can be shown iff these form a DAG (Comparator).
//   - Dedicated papers in H columns: a paper of column c is opaque on the generic windows and on
//     h_0..h_c, a hole on the deeper handles; it serves one target, or a pair of targets whose
//     generic differences form a DAG (it is then also a hole where they differ). Under the generic
//     layer the columns lie in the order 0, 1, ..., so the top of column c shows on h_c only.
//     192 = 6 generic + 186 dedicated papers (70 pairs + 116 singles = 256 targets).
// Request u (paper D of column c): order the generic sheets for D's generic holes, dig column c until
// D is its top and move D to the very top; every handle hole of D must then show A_u, by fillers
// (column papers placed just below the generic layer, showing on an interval of handles) or by
// digging the columns. Unlike the cyclic columns of clean-base, every paper moved out of the way or
// back into a column goes to the depth of least expected future cost (adaptive_insert).
//
// Design:
//   assign_windows   which windows are generic, and the pair of sheets and colors of each (annealing
//                    on the compatible pairs of targets, until 0.45 s)
//   Design::initialize / anneal   the pairs of targets, their columns and the handle order
//                    (annealing on a model of the moves, until 1.10 s)
//   Design::filler_climb   exchanges of units between columns for better fillers (until 1.15 s)
// Requests (Solver::process): every combination of the plan options is simulated on a copy of the
// state and the plan of least cost (moves + 0.8 per paper left out of its column + 0.6 times the
// expected cost of the next request) is kept. Safety nets: retries with fewer generic windows, a
// design with one white and one black sheet per window, and a light plan once 1.55 s of CPU time is
// used.
#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <iostream>
#include <memory>
#include <numeric>
#include <random>
#include <string>
#include <utility>
#include <vector>

using u64 = std::uint64_t;

namespace {

constexpr int N = 64, K = 192, P = 256;

// Every clock reading is multiplied by CLOCK_SCALE (CLAUDE.md, the clock scale): the local
// evaluation compiles with -DCLOCK_SCALE=1.1 so that it searches as much as the judge.
#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
const auto kStartTime = std::chrono::steady_clock::now();
double elapsed_sec() {
    return CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() - kStartTime).count();
}

// Fixed iteration counts for experiments (MAP_ITERS, ANNEAL_ITERS, CLIMB_ITERS; 0 or unset: until
// the time limits; CLIMB_ITERS = -1: no climb). The output then does not depend on the machine.
int env_int(const char* name) {
    const char* s = std::getenv(name);
    return s ? std::atoi(s) : 0;
}

u64 low_bits(int n) { return n == 64 ? ~0ULL : (1ULL << n) - 1; }  // bits 0..n-1

// xorshift (7, 9); `mod` and `below` are the two mappings to [0, n) of the two original generators.
struct XorShift {
    u64 x;
    u64 next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    int mod(int n) { return int(next() % n); }
    int below(int n) { return int(((unsigned __int128)next() * unsigned(n)) >> 64); }
    double real() { return (next() >> 11) * 0x1.0p-53; }
};

// The generic layer. Generic window j compares the sheets edge[j] = (a, b): a has color polarity[j]
// there, b the other color, and the other sheets have a hole, so the window shows the color of the
// upper of a and b. With every pair of sheets compared (complete), every sheet but the bottom one is
// visible somewhere.
struct Comparator {
    int M = 0, G = 0;
    bool complete = false;
    std::vector<std::pair<int, int>> edge;
    std::vector<int> polarity;
    std::vector<u64> opq, black;  // per sheet

    void init(int m, int g, std::mt19937_64& rng) {  // random pairs (each used about equally)
        M = m;
        G = g;
        std::vector<std::pair<int, int>> all;
        for (int a = 0; a < M; ++a)
            for (int b = a + 1; b < M; ++b) all.emplace_back(a, b);
        std::shuffle(all.begin(), all.end(), rng);
        edge.resize(G);
        polarity.resize(G);
        for (int j = 0; j < G; ++j) {
            edge[j] = all[j % all.size()];
            polarity[j] = int(rng() & 1);
        }
        rebuild();
    }

    // The sheets' patterns from edge / polarity.
    void rebuild() {
        assert(1 < M && M <= 12 && 0 < G && G <= 64);
        assert(int(edge.size()) == G && int(polarity.size()) == G);
        opq.assign(M, 0);
        black.assign(M, 0);
        std::array<unsigned, 12> adj{};
        for (int j = 0; j < G; ++j) {
            auto [a, b] = edge[j];
            assert(a != b && 0 <= a && a < M && 0 <= b && b < M);
            u64 bit = 1ULL << j;
            opq[a] |= bit;
            opq[b] |= bit;
            black[polarity[j] ? a : b] |= bit;
            adj[a] |= 1U << b;
            adj[b] |= 1U << a;
        }
        complete = true;
        for (int i = 0; i < M; ++i) complete &= (adj[i] | (1U << i)) == (1U << M) - 1;
    }

    // Transitive closure of the relations asked for by the colors `target` on the windows `holes`:
    // bit b of reach[a] means that a must be above b. A bit on the diagonal: impossible.
    std::array<unsigned, 12> closure(u64 target, u64 holes) const {
        std::array<unsigned, 12> reach{};
        holes &= low_bits(G);
        while (holes) {
            int j = __builtin_ctzll(holes);
            holes &= holes - 1;
            auto [a, b] = edge[j];
            if (int((target >> j) & 1) != polarity[j]) std::swap(a, b);
            reach[a] |= 1U << b;
        }
        for (int k = 0; k < M; ++k)
            for (int a = 0; a < M; ++a)
                if ((reach[a] >> k) & 1) reach[a] |= reach[k];
        return reach;
    }

    // Can a paper with holes where a and b differ serve both? (The relations for b are those for a
    // reversed, so one acyclicity test suffices.)
    bool compatible(u64 a, u64 b) const {
        auto reach = closure(a, a ^ b);
        for (int i = 0; i < M; ++i)
            if ((reach[i] >> i) & 1) return false;
        return true;
    }

    // Expected moves to show a partial display (generic estimate of the design): the mean over the
    // M! orders of the sheets of the distance (the least number of moves, M - longest common
    // subsequence) to the nearest order satisfying the relations. Tables built once (orders: perms;
    // below[s][a]: the sheets below a in order s; dist).
    std::vector<std::vector<int>> perms;
    std::vector<std::vector<unsigned>> below;
    std::vector<uint8_t> dist;
    void build_tables() {
        if (!perms.empty()) return;
        std::vector<int> o(M);
        std::iota(o.begin(), o.end(), 0);
        do perms.push_back(o);
        while (std::next_permutation(o.begin(), o.end()));
        const int n = perms.size();
        below.assign(n, std::vector<unsigned>(M, 0));
        for (int t = 0; t < n; t++)
            for (int i = M - 1, acc = 0; i >= 0; i--) {
                below[t][perms[t][i]] = acc;
                acc |= 1 << perms[t][i];
            }
        dist.resize(n * n);
        std::vector<int> dp((M + 1) * (M + 1));
        for (int a = 0; a < n; a++)
            for (int b = 0; b < n; b++) {
                for (int i = 1; i <= M; i++)
                    for (int j = 1; j <= M; j++)
                        dp[i * (M + 1) + j] = perms[a][i - 1] == perms[b][j - 1]
                                                  ? dp[(i - 1) * (M + 1) + j - 1] + 1
                                                  : std::max(dp[(i - 1) * (M + 1) + j], dp[i * (M + 1) + j - 1]);
                dist[a * n + b] = M - dp[M * (M + 1) + M];
            }
    }
    double mean_moves(u64 target, u64 holes) {
        build_tables();
        auto reach = closure(target, holes);
        const int n = perms.size();
        std::vector<int> sat;
        for (int t = 0; t < n; t++) {
            bool ok = true;
            for (int a = 0; a < M && ok; a++) ok = !(reach[a] & ~below[t][a]);
            if (ok) sat.push_back(t);
        }
        if (sat.empty()) return 0.0;
        double sum = 0;
        for (int s = 0; s < n; s++) {
            int m = M;
            for (int t : sat) m = std::min<int>(m, dist[s * n + t]);
            sum += m;
        }
        return sum / n;
    }

    // Moves (sheet, depth within the layer) taking the layer from the order `current` (top first) to an
    // order showing `target` on `holes`, keeping the largest subsequence of the sheets that is already
    // consistent and moving the others; {{-1, -1}} if impossible. The caller keeps the generic sheets
    // contiguous with no opaque paper above them while applying the moves.
    std::vector<std::pair<int, int>> plan(const std::vector<int>& current, u64 target, u64 holes) const {
        if (!complete || int(current.size()) != M) return {{-1, -1}};
        auto reach = closure(target, holes);
        for (int i = 0; i < M; ++i)
            if ((reach[i] >> i) & 1) return {{-1, -1}};
        bool satisfied = true;
        for (int i = 0; i < M; ++i)
            for (int j = 0; j < i; ++j)
                if ((reach[current[i]] >> current[j]) & 1) satisfied = false;
        if (satisfied) return {};

        std::array<unsigned, 12> conflict{};
        for (int i = 0; i < M; ++i)
            for (int j = 0; j < i; ++j)
                if ((reach[current[i]] >> current[j]) & 1) {
                    conflict[current[i]] |= 1U << current[j];
                    conflict[current[j]] |= 1U << current[i];
                }

        // A kept subsequence is compatible iff it has no inversion of the closure. If it keeps the bottom
        // sheet, every moved sheet is visible until its move; otherwise a moved witness must end below
        // every kept sheet and below the old bottom sheet, exposing that sheet before its move.
        std::array<unsigned char, 1 << 12> valid{};
        valid[0] = 1;
        unsigned kept = 0;
        int best_count = -1, witness = -1;
        const int bottom = current.back();
        const unsigned bottom_bit = 1U << bottom;
        const unsigned end = 1U << M;
        for (unsigned mask = 1; mask < end; ++mask) {
            unsigned rest = mask & (mask - 1);
            int a = __builtin_ctz(mask);
            valid[mask] = valid[rest] && !(rest & conflict[a]);
            if (!valid[mask]) continue;
            int count = __builtin_popcount(mask);
            if (count <= best_count) continue;
            bool legal = mask & bottom_bit;
            int w = -1;
            if (!legal) {
                for (int b = 0; b < M; ++b) {
                    if ((mask >> b & 1) || b == bottom) continue;
                    if (!(reach[b] & (mask | bottom_bit))) {
                        w = b;
                        legal = true;
                        break;
                    }
                }
            }
            if (legal) {
                kept = mask;
                best_count = count;
                witness = w;
            }
        }
        if (best_count < 0) return {{-1, -1}};

        auto required = reach;
        int last = -1;
        for (int a : current)
            if (kept >> a & 1) {
                if (last >= 0) required[last] |= 1U << a;
                last = a;
            }
        if (witness >= 0) {
            required[last] |= 1U << witness;
            required[bottom] |= 1U << witness;
        }
        std::array<unsigned, 12> pred{};
        for (int a = 0; a < M; ++a)
            for (int b = 0; b < M; ++b)
                if (required[a] >> b & 1) pred[b] |= 1U << a;

        std::vector<int> goal;
        unsigned placed = 0;
        for (int step = 0; step < M; ++step) {
            int next = -1;
            for (int a : current)
                if (!(placed >> a & 1) && !(pred[a] & ~placed)) {
                    next = a;
                    break;
                }
            if (next < 0) return {{-1, -1}};
            goal.push_back(next);
            placed |= 1U << next;
        }

        std::vector<int> order = current;
        std::vector<std::pair<int, int>> moves;
        for (int a : current)
            if (!(kept >> a & 1)) {
                u64 covered = 0;
                bool visible = false;
                for (int b : order) {
                    if (b == a) {
                        visible = (opq[a] & ~covered) != 0;
                        break;
                    }
                    covered |= opq[b];
                }
                if (!visible) return {{-1, -1}};
                int successor = -1;
                bool passed = false;
                for (int b : goal) {
                    if (passed && (kept >> b & 1)) {
                        successor = b;
                        break;
                    }
                    if (b == a) passed = true;
                }
                int old = int(std::find(order.begin(), order.end(), a) - order.begin());
                order.erase(order.begin() + old);
                int depth =
                    successor < 0 ? M - 1 : int(std::find(order.begin(), order.end(), successor) - order.begin());
                order.insert(order.begin() + depth, a);
                if (old != depth) moves.emplace_back(a, depth);
                kept |= 1U << a;
            }
        if (order != goal) return {{-1, -1}};
        return moves;
    }
};

// Which windows are generic and the pair of sheets and colors of each generic window (`edge`,
// `polarity` in and out), by annealing until `seconds` (or `fixed_iters` iterations). On return the
// windows are renumbered so that the generic ones are 0..g-1: A is rewritten, and permutation[j] is
// the original window of internal window j.
// Objective: sum over the targets u of (degree_u + 0.2)^0.7, where degree_u sums, over the targets v
// at distance <= 28 that u can share a paper with (Comparator::compatible), the weight
// exp(0.35 (center - |A_u ^ A_v| + 0.3 |generic differences|)): close partners, mostly at the handles,
// for every target. The relations of a pair are kept as a bit matrix (bit 8a + b: a above b) and
// recomputed only for the pairs that differ on a changed window.
// Moves: exchange a generic window with a handle window (kWindowRate of the time), flip the
// colors of a window, exchange the pairs of two windows, give a window to another pair of sheets.
struct WindowStats {
    int iterations = 0;
    double score = 0;
};
WindowStats assign_windows(std::vector<u64>& A, int m, int g, std::vector<std::pair<int, int>>& edges,
                           std::vector<int>& polarity, std::vector<int>& permutation, double seconds, int fixed_iters) {
    constexpr int kCutoff = 28;
    constexpr double kStrength = 0.7, kGenericWeight = 0.70, kWindowRate = 0.6;
    WindowStats stats;
    if (m > 8 || m < 2 || g >= 64 || g < m * (m - 1) / 2) return stats;
    const auto start = std::chrono::steady_clock::now();
    XorShift rng{0x71eb2566be932e31ULL};
    const int n = int(A.size());
    std::vector<std::pair<int, int>> ep;  // the pairs of sheets
    int index[8][8];
    std::memset(index, -1, sizeof(index));
    for (int a = 0; a < m; a++)
        for (int b = a + 1; b < m; b++) {
            index[a][b] = index[b][a] = int(ep.size());
            ep.push_back({a, b});
        }
    const int ne = int(ep.size());
    std::vector<u64> mask(ne), fwd(ne), rev(ne);  // windows of each pair; its relation bits
    std::vector<int> which(64, -1), counts(ne), order(64);
    std::iota(order.begin(), order.end(), 0);
    u64 pol = 0;  // window j: 1 if the first sheet of its pair is black
    for (int e = 0; e < ne; e++) {
        auto [a, b] = ep[e];
        fwd[e] = 1ULL << (8 * a + b);
        rev[e] = 1ULL << (8 * b + a);
    }
    for (int j = 0; j < g; j++) {
        auto [a, b] = edges[j];
        int e = index[a][b];
        which[j] = e;
        mask[e] |= 1ULL << j;
        counts[e]++;
        int c = polarity[j];
        if (a > b) c ^= 1;
        if (c) pol |= 1ULL << j;
    }
    for (int c : counts)
        if (!c) return stats;
    // closure of the relation bit matrix (sheets < 8)
    auto closure8 = [m](u64 r) {
        for (int k = 0; k < m; k++) r |= ((r >> k) & 0x0101010101010101ULL) * ((r >> (8 * k)) & 255);
        return r;
    };
    constexpr u64 kDiagonal = 0x8040201008040201ULL;
    struct Pair {
        u64 au, diff, dir;
        int u, v;
        double base, w;
    };
    std::vector<Pair> pairs;
    std::vector<double> degree(n);
    double bfactor[3];  // base factor when a window swap moves a difference into / out of G
    for (int d = -1; d <= 1; d++) bfactor[d + 1] = std::exp(0.35 * (1 - kGenericWeight) * d);
    const double center = 24 * (1 - (1 - kGenericWeight) * g / 64.0);
    for (int u = 0; u < n; u++)
        for (int v = u + 1; v < n; v++) {
            u64 d = A[u] ^ A[v];
            int h = __builtin_popcountll(d);
            if (h > kCutoff) continue;
            u64 r = 0, z = A[u] ^ pol;
            for (int e = 0; e < ne; e++) {
                u64 q = d & mask[e];
                if (q & ~z) r |= fwd[e];
                if (q & z) r |= rev[e];
            }
            bool ok = !(closure8(r) & kDiagonal);
            int hg = __builtin_popcountll(d & ((1ULL << g) - 1));
            double base = std::exp((center - h + (1 - kGenericWeight) * hg) * 0.35);
            double w = ok ? base : 0;
            pairs.push_back({A[u], d, r, u, v, base, w});
            degree[u] += w;
            degree[v] += w;
        }
    auto value = [&](double d) { return std::pow(d + 0.2, kStrength); };
    double score = 0;
    for (double d : degree) score += value(d);
    double best = score;
    auto best_mask = mask;
    auto best_order = order;
    u64 best_pol = pol;
    const int np = int(pairs.size());
    std::vector<u64> ndir(np);
    std::vector<double> nbase(np), nw(np), delta(n);
    std::vector<int> changed;
    changed.reserve(np);
    double elapsed = 0;
    for (int it = 0;; it++) {
        if ((it & 15) == 0) {
            elapsed = CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
            if (elapsed >= seconds || (fixed_iters > 0 && it >= fixed_iters)) break;
        }
        stats.iterations++;
        double progress = fixed_iters ? double(it) / fixed_iters : elapsed / seconds;
        int ia = rng.mod(g), ib = rng.mod(g), a = order[ia], b = order[ib];
        bool swindow = rng.real() < kWindowRate;
        if (swindow) {
            ib = g + rng.mod(64 - g);
            b = order[ib];
        }
        int kind = rng.mod(10), ea = which[a], eb = swindow ? ea : which[b];
        u64 olda = mask[ea], oldb = mask[eb], oldpol = pol, affected = 0;
        int transfer = -1;
        if (swindow) {  // generic window a <-> handle window b
            mask[ea] ^= (1ULL << a) | (1ULL << b);
            pol = (pol & ~(1ULL << b)) | (((oldpol >> a) & 1) << b);
            affected = (1ULL << a) | (1ULL << b);
        } else if (kind < 3) {  // flip the colors of a
            pol ^= 1ULL << a;
            affected = 1ULL << a;
            eb = ea;
            oldb = olda;
        } else if (kind < 8) {  // exchange the pairs of a and b
            if (ea == eb) continue;
            mask[ea] ^= (1ULL << a) | (1ULL << b);
            mask[eb] ^= (1ULL << a) | (1ULL << b);
            affected = (1ULL << a) | (1ULL << b);
        } else {  // window a to another pair
            if (counts[ea] < 2) continue;
            eb = rng.mod(ne);
            if (ea == eb) continue;
            oldb = mask[eb];
            mask[ea] ^= 1ULL << a;
            mask[eb] |= 1ULL << a;
            transfer = eb;
            affected = 1ULL << a;
        }
        const u64 erase = fwd[ea] | rev[ea] | fwd[eb] | rev[eb];
        std::fill(delta.begin(), delta.end(), 0);
        changed.clear();
        for (int p = 0; p < np; p++) {
            auto& q = pairs[p];
            if (!(q.diff & affected)) continue;
            u64 r = q.dir & ~erase, z = q.au ^ pol;
            u64 d = q.diff & mask[ea];
            if (d & ~z) r |= fwd[ea];
            if (d & z) r |= rev[ea];
            d = q.diff & mask[eb];
            if (d & ~z) r |= fwd[eb];
            if (d & z) r |= rev[eb];
            double base = q.base;
            if (swindow) {
                int dh = int((q.diff >> b) & 1) - int((q.diff >> a) & 1);
                base *= bfactor[dh + 1];
            }
            if (r == q.dir && base == q.base) continue;
            bool ok = !(closure8(r) & kDiagonal);
            double w = ok ? base : 0;
            ndir[p] = r;
            nbase[p] = base;
            nw[p] = w;
            changed.push_back(p);
            double dw = w - q.w;
            delta[q.u] += dw;
            delta[q.v] += dw;
        }
        double ds = 0;
        for (int u = 0; u < n; u++)
            if (std::abs(delta[u]) > 1e-9) ds += value(std::max(0.0, degree[u] + delta[u])) - value(degree[u]);
        double temp = 0.2 * std::pow(0.005 / 0.2, progress);
        if (ds >= 0 || rng.real() < std::exp(ds / temp)) {
            score += ds;
            for (int p : changed) {
                pairs[p].dir = ndir[p];
                pairs[p].base = nbase[p];
                pairs[p].w = nw[p];
            }
            for (int u = 0; u < n; u++) degree[u] = std::max(0.0, degree[u] + delta[u]);
            if (swindow) {
                which[a] = -1;
                which[b] = ea;
                std::swap(order[ia], order[ib]);
            } else {
                if (kind >= 3 && kind < 8) std::swap(which[a], which[b]);
                if (transfer >= 0) {
                    counts[ea]--;
                    counts[eb]++;
                    which[a] = eb;
                }
            }
            if (score > best) {
                best = score;
                best_mask = mask;
                best_pol = pol;
                best_order = order;
            }
        } else {
            mask[ea] = olda;
            mask[eb] = oldb;
            pol = oldpol;
        }
    }
    for (int j = 0; j < g; j++) {
        int x = best_order[j], e = 0;
        while (e < ne && !(best_mask[e] >> x & 1)) e++;
        assert(e < ne);
        edges[j] = ep[e];
        polarity[j] = (best_pol >> x) & 1;
    }
    auto oldperm = permutation;
    for (int j = 0; j < 64; j++) permutation[j] = oldperm[best_order[j]];
    for (u64& a : A) {
        u64 b = 0;
        for (int j = 0; j < 64; j++) b |= ((a >> best_order[j]) & 1) << j;
        a = b;
    }
    stats.score = best;
    return stats;
}

// The dedicated papers: units (a pair of targets a, b or a single target a, b = -1) in columns c, and
// the handle order (handle[j]: window of h_j; hb[t]: colors of target t at h_0..h_{H-1}).
// Model of the moves per request, summed over the targets (cur):
//   - column c (colcost): the digs nt (nc - 1) / 2 of a cyclic column (nt targets on nc papers), less
//     kRankPriority of the saving of keeping the pairs (asked twice as often) near the top with both
//     handle colors near the top (alt); 5 imb^2 for an unbalanced column, 1e5 without both colors;
//   - handle hole h_j (hcost): kHoleWeight 4 n0 n1 / (n0 + n1) for n0 / n1 holes of color 0 / 1 (the
//     top of column j keeps the color of the last request with a hole there: persistence);
//   - generic layer of a pair (gc): twice the mean number of moves of the generic layer from a uniform
//     order of the sheets (gcost, Comparator::mean_moves).
struct Design {
    struct Unit {
        int a = -1, b = -1, c = -1;
    };
    static constexpr double kHoleWeight = 0.50, kRankPriority = 0.85;
    XorShift rng{0x6176abcd1349ULL};
    int M, G, H, U, need;
    std::vector<u64> A, hb;
    std::vector<int> handle, owner;  // owner[t]: unit of target t
    std::vector<Unit> unit;
    std::vector<std::vector<int>> partners;  // compatible targets
    std::array<std::array<uint8_t, 256>, 256> ok{};
    std::array<std::array<float, 256>, 256> gcost{};
    std::vector<int> nc, nt, n1, pairOne;  // per column: units, targets, units / pairs of color 1
    std::vector<std::array<int, 2>> hn;    // per handle: holes of color 0 and 1
    double cur = 0;
    int anneal_iters = 0, climb_iters = 0, climb_accepted = 0;
    double proxy_before = 0, proxy_after = 0;

    static int pc(u64 x) { return __builtin_popcountll(x); }
    Design(const std::vector<u64>& a, int m, int g) : M(m), G(g), H(64 - g), U(192 - m), need(256 - U), A(a) {
        handle.resize(H);
        std::iota(handle.begin(), handle.end(), G);
        hb.resize(256);
        for (int i = 0; i < 256; i++) hb[i] = A[i] >> G;
        owner.assign(256, -1);
        partners.resize(256);
        nc.resize(H);
        nt.resize(H);
        n1.resize(H);
        pairOne.resize(H);
        hn.resize(H);
    }
    bool valid(const Unit& u, int c) const { return u.b < 0 || (((hb[u.a] ^ hb[u.b]) >> c) & 1) == 0; }
    int color(const Unit& u, int c) const { return hb[u.a] >> c & 1; }
    int weight(const Unit& u) const { return u.b < 0 ? 1 : 2; }
    u64 holes(const Unit& u) const {
        u64 d = u.b < 0 ? 0 : hb[u.a] ^ hb[u.b];
        return (low_bits(H) & ~low_bits(u.c + 1)) | d;
    }
    double colcost(int c) const {
        int imb = std::max(0, std::abs(nc[c] - 2 * n1[c]) - 1);
        int p = nt[c] - nc[c], p1 = pairOne[c], p0 = p - p1;
        double base = nt[c] * (nc[c] - 1) * 0.5;
        int firstPair = n1[c] > nc[c] - n1[c] ? p1 : n1[c] < nc[c] - n1[c] ? p0 : std::max(p0, p1);
        double alt = nc[c] * (nc[c] - 1) * 0.5 + p0 * p0 + p1 * p1 - firstPair;
        double retrieval = base - kRankPriority * std::max(0.0, base - alt);
        return retrieval + 5.0 * imb * imb + ((n1[c] == 0 || n1[c] == nc[c]) ? 100000.0 : 0.0);
    }
    double hcost(int j) const {
        static const std::array<double, 257 * 257> table = [] {  // 4 x y / (x + y)
            std::array<double, 257 * 257> t{};
            for (int x = 0; x <= 256; x++)
                for (int y = 0; y <= 256; y++)
                    if (x + y) t[x * 257 + y] = 4.0 * x * y / (x + y);
            return t;
        }();
        return kHoleWeight * table[hn[j][0] * 257 + hn[j][1]];
    }
    double gc(const Unit& u) const { return u.b < 0 ? 0 : gcost[u.a][u.b] * 2; }
    void update(const Unit& u, int sgn) {
        cur -= colcost(u.c);
        nc[u.c] += sgn;
        nt[u.c] += sgn * weight(u);
        n1[u.c] += sgn * color(u, u.c);
        if (u.b >= 0) pairOne[u.c] += sgn * color(u, u.c);
        cur += colcost(u.c);
        u64 hs = holes(u);
        for (u64 s = hs; s; s &= s - 1) {
            int j = __builtin_ctzll(s);
            cur -= hcost(j);
            hn[j][hb[u.a] >> j & 1] += sgn;
            if (u.b >= 0) hn[j][hb[u.b] >> j & 1] += sgn;
            cur += hcost(j);
        }
        cur += sgn * gc(u);
    }
    void rebuild() {
        std::fill(nc.begin(), nc.end(), 0);
        std::fill(nt.begin(), nt.end(), 0);
        std::fill(n1.begin(), n1.end(), 0);
        std::fill(pairOne.begin(), pairOne.end(), 0);
        std::fill(hn.begin(), hn.end(), std::array<int, 2>{0, 0});
        cur = 0;
        for (int j = 0; j < H; j++) cur += colcost(j);
        for (const auto& u : unit) update(u, 1);
        for (int x = 0; x < U; x++) {
            owner[unit[x].a] = x;
            if (unit[x].b >= 0) owner[unit[x].b] = x;
        }
    }
    // Units and columns. Pairs: a greedy matching of the compatible pairs by 0.65 handle differences +
    // 2 gcost + 0.04 differences, completed by augmenting paths of length 3 (one pair replaced by
    // two); the rest are singles. Columns: both colors in every column (singles first), then sizes
    // about proportional to c + 1.5 (even), filled from the deepest column, pairs first; leftovers
    // where cheapest. false if impossible (or expired).
    template <class Compatible, class Estimate, class Expired>
    bool initialize(Compatible compatible, Estimate estimate, Expired expired) {
        struct E {
            double w;
            int a, b;
        };
        std::vector<E> edges;
        for (int a = 0; a < 256; a++)
            for (int b = a + 1; b < 256; b++) {
                if ((b & 31) == 0 && expired()) return false;
                if (!compatible(A[a], A[b])) continue;
                ok[a][b] = ok[b][a] = 1;
                partners[a].push_back(b);
                partners[b].push_back(a);
                u64 d = A[a] ^ A[b];
                gcost[a][b] = gcost[b][a] = estimate(A[a], A[b]);
                edges.push_back({0.65 * pc(d >> G) + 2 * gcost[a][b] + 0.04 * pc(d), a, b});
            }
        std::sort(edges.begin(), edges.end(), [](const E& a, const E& b) { return a.w < b.w; });
        std::vector<char> used(256, 0);
        for (const auto& e : edges) {
            if (int(unit.size()) == need) break;
            if (used[e.a] || used[e.b]) continue;
            used[e.a] = used[e.b] = 1;
            unit.push_back({e.a, e.b, -1});
        }
        // Greedy matching can get stuck despite an adequate compatibility
        // graph.  A length-three augmenting path replaces one pair by two.
        auto edgeCost = [&](int a, int b) {
            u64 d = A[a] ^ A[b];
            return 0.65 * pc(d >> G) + 2 * gcost[a][b] + 0.04 * pc(d);
        };
        while (int(unit.size()) < need) {
            double best = 1e100;
            int bx = -1, bu = -1, bv = -1, flip = 0;
            for (int x = 0; x < int(unit.size()); x++)
                for (int f = 0; f < 2; f++) {
                    if (expired()) return false;
                    int a = f ? unit[x].b : unit[x].a, b = f ? unit[x].a : unit[x].b;
                    for (int u : partners[a])
                        if (!used[u])
                            for (int v : partners[b])
                                if (!used[v] && u != v) {
                                    double c = edgeCost(a, u) + edgeCost(b, v) - edgeCost(a, b);
                                    if (c < best) {
                                        best = c;
                                        bx = x;
                                        bu = u;
                                        bv = v;
                                        flip = f;
                                    }
                                }
                }
            if (bx < 0) break;
            int a = flip ? unit[bx].b : unit[bx].a, b = flip ? unit[bx].a : unit[bx].b;
            unit[bx] = {a, bu, -1};
            unit.push_back({b, bv, -1});
            used[bu] = used[bv] = 1;
        }
        if (int(unit.size()) < need) return false;
        for (int a = 0; a < 256; a++)
            if (!used[a]) unit.push_back({a, -1, -1});
        // Reserve both colors of every column using single-target papers first.
        std::vector<int> perm(U);
        std::iota(perm.begin(), perm.end(), 0);
        for (int i = U - 1; i > 0; i--) std::swap(perm[i], perm[rng.below(i + 1)]);
        auto take = [&](int c, int colorWanted, bool pairFirst) {
            for (int pass = 0; pass < 2; pass++)
                for (int x : perm) {
                    auto& u = unit[x];
                    if (u.c >= 0 || (u.b >= 0) != (pairFirst ^ (pass != 0)) || !valid(u, c) ||
                        color(u, c) != colorWanted)
                        continue;
                    u.c = c;
                    nc[c]++;
                    n1[c] += colorWanted;
                    return true;
                }
            return false;
        };
        for (int c = 0; c < H; c++)
            for (int v = 0; v < 2; v++)
                if (!take(c, v, false)) return false;
        std::vector<int> cap(H, 2);
        int tot = H * 2;
        while (tot + 2 <= U) {
            int best = 0;
            double val = 1e100;
            for (int c = 0; c < H; c++) {
                double q = (cap[c] + 1.0) / (c + 1.5);
                if (q < val) val = q, best = c;
            }
            cap[best] += 2;
            tot += 2;
        }
        for (int c = H - 1; c >= 0; c--)
            while (nc[c] < cap[c]) {
                int v = 2 * n1[c] < nc[c] ? 1 : 0;
                if (!take(c, v, true) && !take(c, v ^ 1, true)) break;
            }
        for (auto& u : unit)
            if (u.c < 0) {
                int best = -1;
                double cost = 1e100;
                for (int c = 0; c < H; c++)
                    if (valid(u, c)) {
                        double q = weight(u) * (nc[c] * 0.5 + 0.5 * (H - 1 - c)) + nc[c] * 0.5 +
                                   3 * std::abs(nc[c] + 1 - 2 * (n1[c] + color(u, c)));
                        if (q < cost) cost = q, best = c;
                    }
                if (best < 0) return false;
                u.c = best;
                nc[best]++;
                n1[best] += color(u, best);
            }
        rebuild();
        return true;
    }
    // Annealing of the pairing (exchange a target between two units, mostly towards a compatible
    // partner), the columns (exchange, move one unit, move two units of opposite colors) and the
    // handle order (exchange two handles: recount), until `seconds` (or fixedIterations); keeps the
    // best state.
    void anneal(double seconds, int fixedIterations = 0) {
        auto start = std::chrono::steady_clock::now();
        double progress = 0, temp = 2.0;
        static std::array<double, 16384> logs = []() {
            std::array<double, 16384> a{};
            for (int i = 0; i < 16384; i++) a[i] = -std::log((i + 0.5) / 16384);
            return a;
        }();
        auto accept = [&](double d) { return d <= 0 || d < temp * logs[rng.next() & 16383]; };
        std::vector<Unit> best = unit;
        std::vector<int> bestHandle = handle;
        double bestCost = cur;
        auto mutate = [&](int x, int y, Unit nx, Unit ny) {
            if (!valid(nx, nx.c) || !valid(ny, ny.c)) return;
            if ((nx.b >= 0 && !ok[nx.a][nx.b]) || (ny.b >= 0 && !ok[ny.a][ny.b])) return;
            Unit ox = unit[x], oy = unit[y];
            double old = cur;
            update(ox, -1);
            update(oy, -1);
            update(nx, 1);
            update(ny, 1);
            if (accept(cur - old)) {
                unit[x] = nx;
                unit[y] = ny;
                owner[nx.a] = x;
                if (nx.b >= 0) owner[nx.b] = x;
                owner[ny.a] = y;
                if (ny.b >= 0) owner[ny.b] = y;
            } else {
                update(nx, -1);
                update(ny, -1);
                update(ox, 1);
                update(oy, 1);
                cur = old;
            }
        };
        for (int it = 0;; it++) {
            anneal_iters = it;
            if ((it & 255) == 0) {
                double elapsed =
                    CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
                progress = fixedIterations > 0 ? double(it) / fixedIterations : elapsed / seconds;
                if (progress >= 1 || elapsed >= seconds) break;
                temp = 2.0 * std::pow(0.015 / 2.0, progress);
            }
            int type = rng.below(1000);
            if (type < 5) {
                int a = rng.below(H), b = rng.below(H);
                if (a == b) continue;
                bool validSwap = true;
                for (const auto& u : unit)
                    if (u.b >= 0 && (u.c == a || u.c == b)) {
                        int j = u.c == a ? b : a;
                        if ((hb[u.a] ^ hb[u.b]) >> j & 1) {
                            validSwap = false;
                            break;
                        }
                    }
                if (!validSwap) continue;
                double old = cur;
                auto sw = [&]() {
                    std::swap(handle[a], handle[b]);
                    for (auto& h : hb)
                        if (((h >> a) ^ (h >> b)) & 1) h ^= (u64(1) << a) | (u64(1) << b);
                };
                sw();
                rebuild();
                if (!accept(cur - old)) {
                    sw();
                    rebuild();
                }
            } else {
                int x = rng.below(U), y = rng.below(U);
                if (x == y) continue;
                Unit nx = unit[x], ny = unit[y];
                if (type < 430) {
                    if (nx.b < 0) {
                        std::swap(x, y);
                        nx = unit[x];
                        ny = unit[y];
                        if (nx.b < 0) continue;
                    }
                    int ix = rng.below(2), iy = ny.b < 0 ? 0 : rng.below(2);
                    if (type < 380) {
                        int fixed = ix == 0 ? nx.b : nx.a;
                        const auto& p = partners[fixed];
                        if (p.empty()) continue;
                        int newTarget = p[rng.below(p.size())];
                        y = owner[newTarget];
                        if (x == y) continue;
                        ny = unit[y];
                        iy = ny.a == newTarget ? 0 : 1;
                    }
                    int& a = ix == 0 ? nx.a : nx.b;
                    int& b = iy == 0 ? ny.a : ny.b;
                    std::swap(a, b);
                } else if (type < 750) {
                    if (nx.c == ny.c) continue;
                    std::swap(nx.c, ny.c);
                } else if (type < 900) {
                    if (nx.c == ny.c || nc[nx.c] <= 2) continue;
                    nx.c = ny.c;
                } else {
                    int c = nx.c, d = ny.c;
                    if (c == d || nc[c] <= 2) continue;
                    int z = -1;
                    for (int t = 0; t < 16; t++) {
                        int j = rng.below(U);
                        if (j != x && unit[j].c == c && color(unit[j], c) != color(nx, c)) {
                            z = j;
                            break;
                        }
                    }
                    if (z < 0) continue;
                    y = z;
                    ny = unit[y];
                    nx.c = ny.c = d;
                }
                mutate(x, y, nx, ny);
            }
            if (cur < bestCost - 1e-7) {
                bestCost = cur;
                best = unit;
                bestHandle = handle;
            }
        }
        unit = best;
        handle = bestHandle;
        for (int i = 0; i < 256; i++) {
            hb[i] = 0;
            for (int j = 0; j < H; j++) hb[i] |= ((A[i] >> handle[j]) & 1) << j;
        }
        rebuild();
    }
    // Persistence-weighted handle holes of a target (colors tb at the handles, column l) that the
    // paper of a unit (colors yb, pair differences dy) of column c > l would cover as a filler, at
    // the level just past its deepest mismatch with the target (h_c excluded), minus kT, at least 0.
    // q[j] = sum over the handles m < j of 2 (1 - p_m(color of the target at h_m)): the fixes a
    // covered hole saves relative to an unbiased handle. (solutions/clean-base)
    static double filler_gain(u64 tb, int l, u64 yb, u64 dy, int c, const double* q) {
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
    // Hill climbing after the annealing (solutions/clean-base filler_climb, pool-climb): exchanges
    // two units of the same kind between two columns, with the same colors at both handles (the
    // column costs and the generic costs do not change), when the model cost minus kW times the
    // filler proxy decreases:
    //   proxy(t) = sum over the columns c deeper than t's of the mean over the units y of c of
    //              filler_gain(t, paper of y).
    // Incremental: a target outside x and y only sees the sums of the columns a and b change.
    void filler_climb(double seconds, int fixedIterations = 0) {
        constexpr double kW = 0.3;
        auto start = std::chrono::steady_clock::now();
        std::vector<u64> diffb(U, 0);
        for (int x = 0; x < U; x++)
            if (unit[x].b >= 0) diffb[x] = hb[unit[x].a] ^ hb[unit[x].b];
        std::vector<std::vector<double>> pq(256, std::vector<double>(H + 1, 0.0));
        for (int t = 0; t < 256; t++)
            for (int m = 0; m < H; m++) {
                int n = hn[m][0] + hn[m][1];
                double p1 = n ? double(hn[m][1]) / n : 0.5, pc = (hb[t] >> m & 1) ? p1 : 1 - p1;
                pq[t][m + 1] = pq[t][m] + 2 * (1 - pc);
            }
        std::vector<std::vector<int>> colm(H);
        for (int x = 0; x < U; x++) colm[unit[x].c].push_back(x);
        auto tcol = [&](int t) { return unit[owner[t]].c; };
        auto gval = [&](int t, int l, int y, int c) {
            return filler_gain(hb[t], l, hb[unit[y].a], diffb[y], c, pq[t].data());
        };
        std::vector<std::vector<double>> colsum(256, std::vector<double>(H, 0.0));
        auto recompute = [&](int t) {
            int l = tcol(t);
            for (int c = 0; c < H; c++) {
                colsum[t][c] = 0;
                if (c <= l) continue;
                for (int y : colm[c]) colsum[t][c] += gval(t, l, y, c);
            }
        };
        for (int t = 0; t < 256; t++) recompute(t);
        auto proxy = [&](int t) {
            int l = tcol(t);
            double s = 0;
            for (int c = l + 1; c < H; c++)
                if (!colm[c].empty()) s += colsum[t][c] / colm[c].size();
            return s;
        };
        proxy_before = 0;
        for (int t = 0; t < 256; t++) proxy_before += proxy(t);
        std::vector<int> others, moved;
        std::vector<std::array<double, 2>> dlt;
        std::vector<std::vector<double>> saved;
        for (int it = 0;; it++) {
            if (fixedIterations > 0
                    ? it >= fixedIterations
                    : ((it & 63) == 0 &&
                       CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() >=
                           seconds))
                break;
            climb_iters = it + 1;
            int x = rng.below(U), y = rng.below(U);
            int a = unit[x].c, b = unit[y].c;
            if (a == b || (unit[x].b >= 0) != (unit[y].b >= 0)) continue;
            Unit nx = unit[x], ny = unit[y];
            nx.c = b;
            ny.c = a;
            if (!valid(nx, b) || !valid(ny, a)) continue;
            if (color(nx, b) != color(unit[y], b) || color(ny, a) != color(unit[x], a)) continue;
            double old = cur;
            Unit ox = unit[x], oy = unit[y];
            update(ox, -1);
            update(oy, -1);
            update(nx, 1);
            update(ny, 1);
            double dmodel = cur - old;
            const double na = colm[a].size(), nb = colm[b].size();
            const int hi = std::max(a, b);
            double dproxy = 0;
            others.clear();
            dlt.clear();
            for (int t = 0; t < 256; t++) {
                int o = owner[t];
                if (o == x || o == y) continue;
                int l = tcol(t);
                if (l >= hi) continue;
                double da = 0, db = 0;
                if (a > l) da = gval(t, l, y, a) - gval(t, l, x, a);
                if (b > l) db = gval(t, l, x, b) - gval(t, l, y, b);
                if (da || db) {
                    others.push_back(t);
                    dlt.push_back({da, db});
                    dproxy += da / na + db / nb;
                }
            }
            moved.clear();
            for (int t : {ox.a, ox.b, oy.a, oy.b})
                if (t >= 0) moved.push_back(t);
            saved.resize(moved.size());
            for (size_t i = 0; i < moved.size(); i++) {
                dproxy -= proxy(moved[i]);
                saved[i] = colsum[moved[i]];
            }
            auto apply = [&](int cx, int cy) {
                auto& ma = colm[unit[x].c];
                ma.erase(std::find(ma.begin(), ma.end(), x));
                auto& mb = colm[unit[y].c];
                mb.erase(std::find(mb.begin(), mb.end(), y));
                unit[x].c = cx;
                unit[y].c = cy;
                colm[cx].push_back(x);
                colm[cy].push_back(y);
            };
            apply(b, a);
            for (int t : moved) {
                recompute(t);
                dproxy += proxy(t);
            }
            if (dmodel - kW * dproxy < -1e-9) {
                climb_accepted++;
                for (size_t i = 0; i < others.size(); i++) {
                    colsum[others[i]][a] += dlt[i][0];
                    colsum[others[i]][b] += dlt[i][1];
                }
            } else {
                apply(a, b);
                for (size_t i = 0; i < moved.size(); i++) colsum[moved[i]] = saved[i];
                update(nx, -1);
                update(ny, -1);
                update(ox, 1);
                update(oy, 1);
                cur = old;
            }
        }
        proxy_after = 0;
        for (int t = 0; t < 256; t++) proxy_after += proxy(t);
        rebuild();
    }
};

struct Paper {
    u64 opaque = 0, black = 0;
};

// The papers and the request processing (clean-base's plan search with the generic layer replaced by
// the comparator and the cyclic columns replaced by adaptive_insert). The generic sheets are papers
// 0..M-1.
struct Solver {
    int M = 6, G = 36, H = 28;
    Comparator comparator;
    std::vector<u64> A;
    std::vector<int> handle, hidx;  // window of h_j; handle index of each window (-1: generic)
    u64 gmask = 0, hmask = 0;       // generic windows, handle windows
    std::vector<Paper> paper;
    std::vector<u64> h_opq, h_blk;  // per paper: opaque / black handles, by handle index
    std::vector<int> col_of, ded;   // column of each dedicated paper (-1: generic); paper of each target
    // (Inherited from clean-base, where it was the base paper F: here generic sheet 0. Papers above it
    // count as above the generic layer in gen_harm and move_to_level.)
    static constexpr int base_paper = 0;

    // State of the stack.
    std::vector<int> order;  // top first
    int top_d = -1;          // dedicated paper lifted to the top, -1 if none
    // Fillers: column papers out of their column, showing on the handles h_lvl..h_hi (hi = their
    // column).
    struct Filler {
        int paper;
        int lvl = 0, hi = 0;
    };
    std::vector<Filler> fillers;
    std::vector<std::pair<int, int>> ops;  // moves (paper, depth) of the plan being simulated
    explicit Solver(std::vector<u64> a) : A(std::move(a)) {}

    u64 handle_bits(u64 windows) const {  // the window set by handle index (bit j = window h_j)
        u64 r = 0;
        for (int j = 0; j < H; j++) r |= (windows >> handle[j] & 1) << j;
        return r;
    }

    // Orders the generic sheets (contiguous in the stack) so that the generic holes `holes` of the
    // paper of u show A_u (Comparator::plan).
    void set_generic(int u, u64 holes) {
        holes &= gmask;
        if (!holes) return;
        int offset = -1;
        for (int i = 0; i < K; i++)
            if (order[i] < M) {
                offset = i;
                break;
            }
        if (offset < 0 || offset + M > K) {
            invalid = true;
            return;
        }
        std::vector<int> local;
        for (int i = 0; i < M; i++) {
            int k = order[offset + i];
            if (k < 0 || k >= M) {
                invalid = true;
                return;
            }
            local.push_back(k);
        }
        auto path = comparator.plan(local, A[u], holes);
        for (auto [k, d] : path) {
            if (k < 0 || k >= M || d < 0 || d >= M) {
                invalid = true;
                return;
            }
            move(k, offset + d);
            if (invalid) return;
        }
    }

    // Adaptive columns: a paper moved out of the way (dig) or back into its column (return_paper)
    // goes to the depth of least expected future cost: weighted depths (a pair's paper is asked twice
    // as often) / P + for each handle color the depth of the first paper of that color times the
    // share of the requests with a hole of that color at the handle (adaptive_holes); a dig never
    // inserts above its barrier (the paper being dug for), so the current dig is not lengthened.
    int adaptive_request = -1;
    bool adaptive_initialized = false;
    std::vector<double> adaptive_weights;
    std::vector<std::array<double, 2>> adaptive_holes;
    static constexpr double kTopPenalty = 0.35, kEndWeight = 0.6;
    bool fast_mode = false;
    long long fast_requests = 0, plan_failures = 0;
    void init_adaptive() {  // (once)
        if (adaptive_initialized) return;
        adaptive_initialized = true;
        adaptive_weights.assign(K, 0.0);
        adaptive_holes.assign(H, {0.0, 0.0});
        for (int u = 0; u < P; u++) {
            int d = ded[u];
            if (d < 0) continue;
            adaptive_weights[d] += 1.0;
            for (int c = 0; c < H; c++)
                if (!(paper[d].opaque >> handle[c] & 1)) adaptive_holes[c][A[u] >> handle[c] & 1] += 1.0 / P;
        }
    }
    // Expected cost of the next request from the stack left (weighted depths and handle colors).
    double adaptive_next_cost() const {
        std::vector<int> rank(H, 0);
        std::vector<std::array<int, 2>> first(H);
        std::vector<std::array<bool, 2>> available(H, {false, false});
        for (auto& f : first) f = {-1, -1};
        double cost = 0;
        for (int k : order) {
            int c = col_of[k];
            if (c < 0) continue;
            int color = paper[k].black >> handle[c] & 1;
            if (k == top_d || is_filler(k)) {
                available[c][color] = true;
                continue;
            }
            if (first[c][color] < 0) first[c][color] = rank[c];
            cost += adaptive_weights[k] * rank[c] / P;
            rank[c]++;
        }
        for (int c = 0; c < H; c++)
            for (int color = 0; color < 2; color++) {
                int fixes = available[c][color] ? 0 : first[c][color];
                if (fixes < 0) fixes = rank[c];
                cost += adaptive_holes[c][color] * fixes;
            }
        return cost;
    }
    // Puts paper x into its column at the best depth below `barrier`; mode 1 adds kTopPenalty for the
    // very top. With u, a handle of x's column that the paper of u leaves as a hole adds the digs to
    // set it for u (when not digging).
    void adaptive_insert(int x, int u, int barrier = -1, int mode = 2) {
        const int c = col_of[x], cx = paper[x].black >> handle[c] & 1;
        std::vector<int> v;
        for (int k : order)
            if (k != x && in_column(k, c)) v.push_back(k);
        const int n = v.size();
        int lo = 0;
        if (barrier >= 0) {
            auto it = std::find(v.begin(), v.end(), barrier);
            if (it == v.end()) {
                invalid = true;
                return;
            }
            lo = int(it - v.begin()) + 1;
        }
        std::vector<double> suffix(n + 1, 0.0);
        std::array<int, 2> first = {n, n};
        for (int i = n - 1; i >= 0; i--) {
            suffix[i] = suffix[i + 1] + adaptive_weights[v[i]];
            first[paper[v[i]].black >> handle[c] & 1] = i;
        }
        int requested = u >= 0 ? ded[u] : -1;
        bool need = requested >= 0 && c != col_of[requested] && !(paper[requested].opaque >> handle[c] & 1);
        int desired = u >= 0 ? (A[u] >> handle[c] & 1) : 0;
        double best = 1e100;
        int gap = n;
        for (int i = lo; i <= n; i++) {
            std::array<int, 2> fc;
            for (int color = 0; color < 2; color++) {
                fc[color] = first[color] + (first[color] >= i);
                if (color == cx) fc[color] = std::min(fc[color], i);
            }
            double rank = adaptive_weights[x] * i + suffix[i];
            double value = rank / P + adaptive_holes[c][0] * fc[0] + adaptive_holes[c][1] * fc[1];
            if (need && barrier < 0) value += fc[desired];
            if (mode == 1 && i == 0 && n) value += kTopPenalty;
            value += 1e-7 * (n - i);
            if (value < best) {
                best = value;
                gap = i;
            }
        }
        if (x == top_d) top_d = -1;
        drop_filler(x);
        if (!n) {
            int anchor = -1;
            for (int k : order) {
                if (k == x || k == top_d || is_filler(k)) continue;
                if (k < M || (col_of[k] >= 0 && col_of[k] < c)) anchor = k;
            }
            if (anchor < 0)
                move(x, 0);
            else
                move_after(x, anchor);
        } else if (gap < n) {
            int from = index_of(x), to = index_of(v[gap]);
            move(x, from < to ? to - 1 : to);
        } else
            move_after(x, v.back());
    }
    // ------------------------------------------------------------------------------------------
    // The stack

    int index_of(int k) const {
        for (int i = 0; i < K; i++)
            if (order[i] == k) return i;
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
    bool check_vis = false, invalid = false;
    // Moves paper k so that d papers are above it (no move if it is there already). While plans are
    // simulated (check_vis), a move of an invisible paper marks the plan invalid.
    void move(int k, int d) {
        int i = index_of(k);
        if (i == d) return;
        if (check_vis && !visible(k)) invalid = true;
        order.erase(order.begin() + i);
        order.insert(order.begin() + d, k);
        ops.push_back({k, d});
    }
    // Moves paper k just below paper x.
    void move_after(int k, int x) {
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
        for (auto& f : fillers)
            if (f.paper == k) return true;
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
        for (int k : order)
            if (in_column(k, l)) return k;
        return -1;
    }
    // One dig of column l: its top paper goes back into the column below `barrier` (the paper dug
    // for; -1: below the column bottom), at the best depth (adaptive_insert).
    void dig(int l, int barrier = -1) {
        int t = column_top(l);
        if (t < 0) {
            invalid = true;
            return;
        }
        if (barrier < 0) {
            for (int k : order)
                if (in_column(k, l)) barrier = k;
        }
        if (t != barrier) adaptive_insert(t, adaptive_request, barrier, 2);
    }
    // Digs the column of d until d is its top, and moves d to the very top.
    void lift(int d) {
        int c = col_of[d];
        for (int it = 0; column_top(c) != d; it++) {
            if (it >= K || invalid) {
                invalid = true;
                return;
            }
            dig(c, d);
        }
        move(d, 0);
        top_d = d;
    }
    // Digs column l until its handle shows `color` (until the first paper of that color is on top).
    void set_handle(int l, int color) {
        int barrier = -1;
        for (int k : order)
            if (in_column(k, l) && int(paper[k].black >> handle[l] & 1) == color) {
                barrier = k;
                break;
            }
        if (barrier < 0) {
            invalid = true;
            return;
        }
        for (int it = 0; column_top(l) != barrier; it++) {
            if (it >= K || invalid) {
                invalid = true;
                return;
            }
            dig(l, barrier);
        }
    }
    void fix_handles(int u, u64 hh) {
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
    std::vector<int> fix_costs(int u, u64 hh) const {
        std::vector<int> fix(H, 0);
        for (int j = 0; j < H; j++)
            if (hh >> handle[j] & 1) fix[j] = handle_fix_cost(j, A[u] >> handle[j] & 1);
        return fix;
    }
    // The level just past the deepest handle of the windows `wrong`.
    int level_past(u64 wrong) const {
        int lvl = 0;
        for (u64 x = wrong; x; x &= x - 1) lvl = std::max(lvl, hidx[__builtin_ctzll(x)] + 1);
        return lvl;
    }
    // The handle windows a filler shows on.
    u64 shown_by(const Filler& f) const {
        u64 m = 0;
        for (int j = f.lvl; j <= f.hi; j++)
            if (paper[f.paper].opaque >> handle[j] & 1) m |= 1ULL << handle[j];
        return m;
    }
    // A filler [lvl, c] placed now would sit above a filler of a deeper level that it reaches.
    static bool reaches_deeper(int lvl, int c, const std::vector<Filler>& placed) {
        for (auto& f : placed)
            if (f.lvl > lvl && c >= f.lvl) return true;
        return false;
    }
    // Paper x to level lvl: just above the first paper in place of a column >= lvl, i.e. below the
    // generic layer, the columns 0..lvl-1 and the fillers of lower levels. lazy: no move if x is
    // already between the last paper in place of a column < lvl (or base_paper, below_generic) and
    // that position.
    void move_to_level(int x, int lvl, bool lazy = false, bool below_generic = false) {
        int q = K, last_above = -1;
        for (int i = 0; i < K; i++) {
            int k = order[i];
            if (below_generic && k == base_paper) last_above = i;
            if (k == x || col_of[k] < 0 || !in_column(k, col_of[k])) continue;
            if (col_of[k] < lvl)
                last_above = i;
            else if (q == K)
                q = i;
        }
        int xi = index_of(x);
        if (lazy && xi < q && xi > last_above) return;
        move(x, xi < q ? q - 1 : q);
    }
    // The paper at depth `depth` of column c (the papers above it dug out first) placed as a filler
    // at level lvl; the handles it shows leave hh.
    void place_filler(int c, int depth, int lvl, u64& hh) {
        std::vector<int> top;
        column_tops(c, depth + 1, top);
        if (depth < 0 || depth >= int(top.size())) {
            invalid = true;
            return;
        }
        int x = top[depth];
        for (int it = 0; column_top(c) != x; it++) {
            if (it >= K || invalid) {
                invalid = true;
                return;
            }
            dig(c, x);
        }
        move_to_level(x, lvl);
        fillers.push_back({x, lvl, c});
        hh &= ~shown_by(fillers.back());
    }
    // An out-of-place paper x (the lifted paper or a filler) goes back to its column at the best
    // depth (adaptive_insert; mode 1 adds the top penalty).
    void return_paper(int x, int u, int mode) { adaptive_insert(x, u, -1, mode); }

    // ------------------------------------------------------------------------------------------
    // Plans of a request

    // Options of a plan (process tries the combinations):
    //   ret_mode   the previous lifted paper: 1 / 2 back to its column (with / without the top
    //              penalty), 3 re-used as a filler, 4 left in place under the new paper (a filler of
    //              level 0);
    //   fret_mode  the old fillers: 1 / 2 all back (with / without the top penalty), 3 moved to a new
    //              level if they save at least 2 digs, else back, 4 also left in place if harmless,
    //              5 everything chosen by one interval DP (run_joint);
    //   use_filler new fillers from the column tops; keep: the requested paper is already on top and
    //              stays there; fret_ret: the returns of fret_mode 3..5 with (1) / without (0) the
    //              top penalty.
    struct PlanOpt {
        int ret_mode = 0;
        int fret_mode = 0;
        bool use_filler = false;
        bool keep = false;
        int fret_ret = 1;
    };
    struct FillerPick {
        int c = -1, depth = 0, lvl = 0;
        bool post = false;
    };
    // A candidate interval [lvl, c] of handles for the interval DPs.
    struct Cand {
        int lvl;
        double gain;
        int c, depth;
        int kind = 0;
        int idx = -1;
        bool post = false;
    };
    // Weighted interval scheduling over the handle indices (cand[c]: the candidates ending at c): the
    // best set of disjoint intervals, deepest first. Disjoint intervals never cover each other's
    // column handles, so their gains add up.
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
    // A filler from a column costs 1 move (+ depth) now and is charged at most 1 more for its return,
    // but papers left out are often re-used or left in place: one that saves 2 + depth digs is worth
    // taking.
    static constexpr int kFillerDepth = 3, kFillerCost = 1, kMaxFillers = 8;
    // Fillers when D (column l) is already on top (kept plans): the papers at depth <= kFillerDepth of
    // the columns whose handle is a hole of D, at the level just past their deepest wrong handle.
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

    // Level for an out-of-place paper x (the previous lifted paper or an old filler) to serve as a
    // filler for D (column l, handle holes hh): just past its deepest wrong handle, and below D's
    // column when x would cover h_l (it must not hide D's column top). -1 if it covers nothing there.
    // cov receives the covered holes.
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
    // An old filler above base_paper (the previous lifted paper left under the new one by the stay
    // plan) may show its colors on the generic holes of the next paper D; where they differ from A_u
    // it cannot stay there: re-leveling moves it below the generic layer, and it is not harmless in
    // place.
    bool gen_harm(int x, int d, int u) const {
        if (d < 0 || index_of(x) > index_of(base_paper)) return false;
        return (paper[x].opaque & gmask & ~paper[d].opaque & (paper[x].black ^ A[u])) != 0;
    }
    // Old fillers (olds) that can cover holes of D = ded[u] not yet covered (pre_cov) move straight to
    // their new level if that saves at least 2 digs (no move if they already sit at that level); with
    // keep_harmless, the others stay where they are when they do not hide D's column top and show A_u
    // on the holes they cover; the rest go back to their columns (mode). `placed` holds the fillers of
    // this request so far.
    void refill_or_return(int u, const std::vector<Filler>& olds, u64& pre_cov, std::vector<Filler>& placed, int mode,
                          bool keep_harmless) {
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
            placed.push_back({x, lvl, cf});
            pre_cov |= cov;
        }
    }
    static constexpr double kRelevel = 0.5, kStay = 0.8;
    int depth_in_column(int x) const {
        int i = 0;
        for (int k : order) {
            if (k == x) return i;
            if (in_column(k, col_of[x])) i++;
        }
        return -1;
    }
    // Joint choice (fret_mode 5) of the papers out of their columns (the previous lifted paper x0 and
    // the old fillers) and of the new fillers from the column tops: one weighted interval scheduling
    // over the handles, every candidate an interval [lvl, c] that a paper of column c shows on
    // (matching A_u on all the holes of D it covers):
    //   - a new filler, the paper at depth p <= kFillerDepth of column c: gain = saved digs - 1 - p
    //     (taken only if at least kFillerCost);
    //   - an old paper moved to a new level: gain = saved digs - kRelevel;
    //   - an old filler left where it is: gain = saved digs + 1 - kStay;
    // all also at narrower levels. Old papers not chosen go back to their columns. Saved digs are the
    // handle_fix_cost of the covered holes before any move. The requested paper D, when it is an old
    // filler, is lifted straight from there (no dig).
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
        const bool d_out = is_filler(d);
        std::vector<Filler> olds;
        for (auto& f : fillers)
            if (f.paper != d) olds.push_back(f);
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
        auto add_old = [&](int x, int idx, int L, bool is_x0) {
            int c = col_of[x];
            int lvl = mism_level(x);
            if (!is_x0 && gen_harm(x, d, u)) L = -2;
            if (!d_out && c >= l && (paper[x].opaque >> handle[l] & 1)) lvl = std::max(lvl, l + 1);
            if (lvl <= c) {
                int sv = saved(x, lvl, c, false);
                double g = sv - kRelevel;
                if (!is_x0 && lvl == L) g = sv + 1 - kStay;
                if (g > 0) cand[c].push_back({lvl, g, c, 0, is_x0 ? 3 : (lvl == L ? 2 : 1), idx});
            }
            if (!is_x0 && L > lvl && L <= c) {
                bool harm = !d_out && L <= l && l <= c && (paper[x].opaque >> handle[l] & 1);
                double g = saved(x, L, c, false) + 1 - kStay;
                if (!harm && g > 0) cand[c].push_back({L, g, c, 0, 2, idx});
            }
            for (int lv = lvl + 1; lv <= c; lv++) {
                if (!covers(x, lv) || (!is_x0 && lv == L)) continue;
                double g = saved(x, lv, c, false) - kRelevel;
                if (g > 0) cand[c].push_back({lv, g, c, 0, is_x0 ? 3 : 1, idx});
            }
        };
        for (int i = 0; i < (int)olds.size(); i++) add_old(olds[i].paper, i, olds[i].lvl, false);
        if (x0 >= 0) add_old(x0, -1, -1, true);
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
        std::vector<int> old_dec(olds.size(), 0), old_lvl(olds.size(), -1);
        int x0_lvl = -1;
        for (auto& cd : picks) {
            if (cd.kind == 1 || cd.kind == 2) old_dec[cd.idx] = cd.kind, old_lvl[cd.idx] = cd.lvl;
            if (cd.kind == 3) x0_lvl = cd.lvl;
        }
        Filler fd{d};
        for (auto& f : fillers)
            if (f.paper == d) fd = f;
        fillers = olds;
        if (d_out) fillers.push_back(fd);
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
                fillers.push_back({x0, x0_lvl, col_of[x0]});
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
        for (auto& f : fillers)
            if (f.paper != d) hh &= ~shown_by(f);
        set_generic(u, hole_all);
        for (auto& cd : picks)
            if (cd.kind == 0 && !cd.post) place_filler(cd.c, depth_in_column(cd.idx), cd.lvl, hh);
        if (d_out) {
            drop_filler(d);
            move(d, 0);
            top_d = d;
        } else {
            lift(d);
        }
        for (auto& cd : picks)
            if (cd.kind == 0 && cd.post) place_filler(cd.c, depth_in_column(cd.idx), cd.lvl, hh);
        fix_handles(u, hh);
    }
    // One plan: the previous lifted paper and the old fillers (PlanOpt), the generic layer, new
    // fillers (chosen with every column top visible: those that do not reach D's handle go in before
    // the dig and the lift, the others after), the lift of D and the digs of the remaining handle
    // holes.
    void run_plan(int u, const PlanOpt& opt) {
        if (opt.fret_mode == 5) {
            run_joint(u, opt);
            return;
        }
        const bool kept = opt.keep && top_d >= 0 && ded[u] == top_d;
        u64 pre_cov = 0;
        int stay = -1;
        if (opt.ret_mode == 4) {
            int d = ded[u];
            if (top_d < 0 || kept || d < 0 || d == top_d || (gmask & ~paper[d].opaque & paper[top_d].opaque)) {
                invalid = true;
                return;
            }
            stay = top_d;
            top_d = -1;
        }
        if (top_d >= 0 && !kept && opt.ret_mode == 3) {
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
            std::vector<Filler> placed = {{x, lvl, lp}};
            pre_cov |= cov0;
            auto put_back = [&](const std::vector<Filler>& olds) {
                if (opt.fret_mode >= 3)
                    refill_or_return(u, olds, pre_cov, placed, opt.fret_ret, opt.fret_mode == 4);
                else
                    for (int i = (int)olds.size() - 1; i >= 0; i--) return_paper(olds[i].paper, u, opt.fret_mode);
            };
            put_back(vis_old);
            move_to_level(x, lvl);
            top_d = -1;
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
            fillers.push_back({stay, 0, col_of[stay]});
            pre_cov |= shown_by(fillers.back());
        }
        if (ded[u] < 0) {
            set_generic(u, gmask);
            for (int l = 0; l < H; l++) set_handle(l, A[u] >> handle[l] & 1);
            return;
        }
        const int d = ded[u];
        const u64 holes = (gmask | hmask) & ~paper[d].opaque;
        set_generic(u, holes);
        u64 hh = holes & ~gmask & ~pre_cov;
        if (!kept && opt.use_filler) {
            auto picks = choose_fillers_prelift(u, d, hh);
            for (auto& pk : picks)
                if (!pk.post) place_filler(pk.c, pk.depth, pk.lvl, hh);
            lift(d);
            for (auto& pk : picks)
                if (pk.post) place_filler(pk.c, pk.depth, pk.lvl, hh);
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
    // Fillers chosen before D (column l, in place) is lifted: candidates are the top papers of every
    // column c != l whose handle is not covered by a filler already placed, at the level just past
    // their deepest wrong handle and at the narrower levels lv whose handle h_lv is a hole they cover.
    // A candidate of a column c > l whose interval reaches h_l would hide D's column top: it is placed
    // after the lift (post). A candidate of a column c < l whose handle D covers can only be placed
    // before the lift.
    // Stacks: two papers at one level a, U (column cU) placed first and L (column cL > cU) next,
    // which inserts L just below U. U shows on its opaque handles in [a, cU], L on the holes of U
    // there and on (cU, cL]; L may be wrong where U masks it.
    std::vector<FillerPick> choose_fillers_prelift(int u, int d, u64 hh) const {
        const int l = col_of[d];
        const u64 hole_all = hmask & ~paper[d].opaque;
        u64 covered = 0;
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
        struct PC {
            int c, depth;
            u64 opq, shown, bad;
            bool hole_c;
            int fsum;
        };
        struct Stack {
            int cU, dU, cL, dL;
            bool postU, postL;
        };
        std::vector<Stack> stacks;
        auto hib = [](u64 x) { return x ? 63 - __builtin_clzll(x) : -1; };
        auto upto = [](int b) -> u64 { return b < 0 ? 0 : b >= 63 ? ~0ULL : (1ULL << (b + 1)) - 1; };
        const u64 hh_i = handle_bits(hh), au_i = handle_bits(A[u]);
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
            if (!L.bad) continue;
            for (int ui = first_of[std::max(hib(L.bad), 0)]; ui < first_of[L.c]; ui++) {
                const PC& U = pcs[ui];
                if (U.fsum + L.fsum < 2 * kFillerCost + U.depth + L.depth + 2) continue;
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
            if (cd.depth < 0) {
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
    // Peephole on the moves of a plan. A plan sometimes moves a paper twice (an old filler goes back
    // and its column is then dug past it, or it goes back and is placed again, or the requested paper
    // is returned and then lifted). Moving it at the first step straight to where the second step puts
    // it (the same depth after the second step, or just below the paper the second step puts it
    // under), or dropping the first move, often keeps every move legal and gives the same final
    // order: each candidate is checked by replaying the moves.
    void merge_double_moves(const std::vector<int>& start, std::vector<std::pair<int, int>>& mvs) const {
        bool dup = false;
        for (size_t i = 0; i < mvs.size() && !dup; i++)
            for (size_t j = i + 1; j < mvs.size() && !dup; j++) dup = mvs[i].first == mvs[j].first;
        if (!dup) return;
        struct M {
            int k, anchor, pos;
        };
        auto apply = [](std::vector<int>& ord, const M& m) {
            ord.erase(std::find(ord.begin(), ord.end(), m.k));
            if (m.anchor == -2)
                ord.insert(ord.begin() + m.pos, m.k);
            else if (m.anchor < 0)
                ord.insert(ord.begin(), m.k);
            else
                ord.insert(std::find(ord.begin(), ord.end(), m.anchor) + 1, m.k);
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
                    std::vector<int> st = start;
                    for (int t = 0; t < i; t++) apply(st, mv[t]);
                    std::vector<int> s2 = st;
                    for (int t = i; t <= j; t++) apply(s2, mv[t]);
                    int pj = std::find(s2.begin(), s2.end(), k) - s2.begin();
                    st.erase(std::find(st.begin(), st.end(), k));
                    int pa =
                        mv[j].anchor < 0 ? 0 : (int)(std::find(st.begin(), st.end(), mv[j].anchor) - st.begin()) + 1;
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
                    if (!again && replay_ok(mv, i)) {
                        mv.erase(mv.begin() + i);
                        again = true;
                    }
                    break;
                }
        }
        std::vector<int> ord = start;
        mvs.clear();
        for (auto& m : mv) {
            int before = std::find(ord.begin(), ord.end(), m.k) - ord.begin();
            apply(ord, m);
            int after = std::find(ord.begin(), ord.end(), m.k) - ord.begin();
            if (after != before) mvs.push_back({m.k, after});
        }
    }

    // The records of the papers out of their columns rebuilt from the order after every request.
    // Walking up from the bottom, a paper of column c <= cur (cur = column of the nearest paper in
    // place below) is in place, one of a column > cur is out (a filler of level cur), and a column
    // paper above a generic sheet is out (level 0); the paper on the very top is the lifted one.
    void canonicalize() {
        std::vector<char> inpl(K, 0);
        std::vector<int> lv(K, -1);
        int cur = H;
        bool gen_seen = false;
        for (int i = K - 1; i >= 0; i--) {
            int k = order[i], c = col_of[k];
            if (c < 0) {
                if (k < M) gen_seen = true;
                continue;
            }
            if (!gen_seen && c <= cur) {
                cur = c;
                inpl[k] = 1;
            } else
                lv[k] = gen_seen ? 0 : std::min(cur, c);
        }
        int ntop = -1;
        std::vector<Filler> nf;
        for (int i = 0; i < K; i++) {
            int k = order[i];
            if (col_of[k] < 0 || inpl[k]) continue;
            if (i == 0)
                ntop = k;
            else
                nf.push_back({k, lv[k], col_of[k]});
        }
        std::vector<Filler> res;
        for (auto& f : fillers)
            for (auto& g : nf)
                if (g.paper == f.paper) res.push_back(g);
        for (auto& g : nf)
            if (!is_filler(g.paper)) res.push_back(g);
        top_d = ntop;
        fillers = res;
    }
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
    // A paper left out costs its return later but is often re-used instead (kFillerCharge), and the
    // state left is valued by kEndWeight times adaptive_next_cost.
    static constexpr double kFillerCharge = 0.8;
    // The moves for request u: every combination of the plan options simulated on a copy of the
    // state, the cheapest valid one kept (display A_u, at most 2K moves, fillers reachable). In
    // fast_mode, or when no plan is valid, the plain plan.
    std::vector<std::pair<int, int>> process(int u) {
        init_adaptive();
        adaptive_request = u;
        if (fast_mode) {
            fast_requests++;
            ops.clear();
            invalid = false;
            check_vis = true;
            run_plan(u, PlanOpt{});
            check_vis = false;
            canonicalize();
            return ops;
        }
        const State st0 = save();
        const int top0 = top_d, d = ded[u];
        const bool prev_ok = top0 >= 0 && d >= 0 && d != top0;
        // without old fillers, their options are all the same
        const bool any_out = !fillers.empty();
        const std::vector<int> fms = any_out ? std::vector<int>{1, 2, 3, 4} : std::vector<int>{1};
        const std::vector<int> frets = any_out ? std::vector<int>{1, 0} : std::vector<int>{1};
        auto frets_of = [&](int fm) { return fm >= 3 ? frets : std::vector<int>{1}; };
        std::vector<PlanOpt> opts;
        for (int rm = 1; rm <= (prev_ok ? 3 : 2); rm++)
            for (int fm : fms)
                for (int kp = 0; kp < ((top0 >= 0 && d == top0) ? 2 : 1); kp++)
                    for (int fr : frets_of(fm)) opts.push_back({rm, fm, true, kp == 1, fr});
        if (d >= 0 && d != top0)
            for (int rm = 1; rm <= 2; rm++)
                for (int fr : frets) opts.push_back({rm, 5, true, false, fr});
        if (prev_ok)
            for (int fm : fms)
                for (int fr : frets_of(fm)) opts.push_back({4, fm, true, false, fr});
        double best = 1e18;
        std::vector<std::pair<int, int>> best_ops;
        State best_state;
        check_vis = true;
        for (const PlanOpt& o : opts) {
            restore(st0);
            ops.clear();
            invalid = false;
            run_plan(u, o);
            if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) continue;
            merge_double_moves(st0.order, ops);
            double future = kEndWeight * adaptive_next_cost();
            double cost = ops.size() + kFillerCharge * fillers.size() + future;
            if (cost < best) best = cost, best_ops = ops, best_state = save();
        }
        check_vis = false;
        if (best > 1e17) {
            plan_failures++;
            restore(st0);
            ops.clear();
            invalid = false;
            run_plan(u, PlanOpt{});
            return ops;
        }
        restore(best_state);
        canonicalize();
        return best_ops;
    }
};

// Emergency design (no design found in time): one white and one black sheet per window; moving the
// visible sheet of a window to the bottom flips it, so any request takes at most 64 moves.
int emergency_design(const std::vector<u64>& A, int R) {
    std::string output;
    for (int k = 0; k < K; k++) {
        std::string row(N, '.');
        if (k < 128) row[k % 64] = k < 64 ? '0' : '1';
        output += row + '\n';
    }
    std::cout << output << std::flush;
    u64 current = 0;
    long long total = 0;
    for (int r = 0; r < R; r++) {
        int u;
        if (!(std::cin >> u) || u == -1) return 0;
        u64 different = current ^ A[u];
        output = std::to_string(__builtin_popcountll(different)) + '\n';
        for (u64 s = different; s; s &= s - 1) {
            int j = __builtin_ctzll(s), k = j + ((current >> j & 1) ? 64 : 0);
            output += std::to_string(k) + " 191\n";
            total++;
        }
        current = A[u];
        std::cout << output << std::flush;
    }
    std::cerr << "total_moves = " << total << "\nemergency_design = 1\n";
    return 0;
}

}  // namespace

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    int n, k, p, R;
    if (!(std::cin >> n >> k >> p >> R)) return 0;
    std::vector<u64> A(P);
    for (auto& a : A) {
        std::string s;
        std::cin >> s;
        a = 0;
        for (int j = 0; j < N; j++)
            if (s[j] == '1') a |= 1ULL << j;
    }
    if (n != N || k != K || p != P) return 0;
    const auto originalA = A;
#ifdef FORCE_EMERGENCY_DESIGN
    return emergency_design(originalA, R);
#endif
    // Window assignment until kMapEnd, annealing until kAnnealEnd, climb until kClimbEnd (scaled s).
    constexpr double kMapEnd = 0.45, kAnnealEnd = 1.10, kClimbEnd = 1.15, kFastAfter = 1.70;
    const int map_iters = env_int("MAP_ITERS"), anneal_iters = env_int("ANNEAL_ITERS");
    const int climb_iters = env_int("CLIMB_ITERS");
    std::vector<int> permutation(64);  // original window of each internal window
    int M = 6, G = 36;
    Comparator comp;
    std::mt19937_64 rng(779879);
    std::unique_ptr<Design> des;
    int map_total = 0;
    // A design may fail (no matching of compatible pairs, or no column with both colors): retry with
    // fewer generic windows (32, then 28, without a new assignment the third time), then fall back.
    for (int attempt = 0;; attempt++) {
        A = originalA;
        std::iota(permutation.begin(), permutation.end(), 0);
        comp.init(M, G, rng);
        if (attempt < 2) {
            const double seconds = map_iters ? 1e9 : attempt == 0 ? kMapEnd - elapsed_sec() : 0.18;
            map_total += assign_windows(A, M, G, comp.edge, comp.polarity, permutation, seconds, map_iters).iterations;
        }
        comp.rebuild();
        des = std::make_unique<Design>(A, M, G);
        // gcost: the exact mean number of moves of the generic layer from a uniform order
        auto estimate = [&](u64 a, u64 b) { return comp.mean_moves(a, a ^ b); };
        const bool untimed = map_iters > 0;
        if (des->initialize([&](u64 a, u64 b) { return comp.compatible(a, b); }, estimate,
                            [&]() { return !untimed && elapsed_sec() > 0.90; }))
            break;
        if (attempt >= 2 || (!untimed && elapsed_sec() > 0.85)) return emergency_design(originalA, R);
        G = attempt == 0 ? 32 : 28;
    }
    std::cerr << "map_iters = " << map_total << "\nmap_end_sec = " << elapsed_sec() << '\n';
    if (elapsed_sec() > 1.05 && !anneal_iters) return emergency_design(originalA, R);
    if (anneal_iters)
        des->anneal(1e9, anneal_iters);
    else
        des->anneal(std::max(0.005, kAnnealEnd - elapsed_sec()), 0);
    std::cerr << "anneal_iters = " << des->anneal_iters << "\nanneal_end_sec = " << elapsed_sec() << '\n';
    if (climb_iters >= 0) {
        if (climb_iters)
            des->filler_climb(1e9, climb_iters);
        else
            des->filler_climb(std::max(0.0, kClimbEnd - elapsed_sec()), 0);
    }
    std::cerr << "climb_iters = " << des->climb_iters << "\nclimb_accepted = " << des->climb_accepted
              << "\nproxy_before = " << des->proxy_before / P << "\nproxy_after = " << des->proxy_after / P
              << "\nclimb_end_sec = " << elapsed_sec() << '\n';

    // Papers: the generic sheets, then the columns 0, 1, ... (in each column the colors alternate,
    // the more numerous first; singles before pairs within a color).
    std::vector<Paper> papers(K);
    std::vector<int> columns(K, -1), ded(P, -1);
    for (int i = 0; i < M; i++) papers[i] = {comp.opq[i], comp.black[i]};
    u64 opaque = low_bits(G);
    int next = M;
    for (int c = 0; c < des->H; c++) {
        opaque |= 1ULL << des->handle[c];
        std::array<std::vector<int>, 2> members;
        for (int x = 0; x < des->U; x++)
            if (des->unit[x].c == c) members[des->color(des->unit[x], c)].push_back(x);
        for (auto& group : members)
            std::stable_sort(group.begin(), group.end(),
                             [&](int x, int y) { return des->weight(des->unit[x]) < des->weight(des->unit[y]); });
        while (!members[0].empty() || !members[1].empty()) {
            int color = members[1].size() > members[0].size();
            int x = members[color].back();
            members[color].pop_back();
            const auto& u = des->unit[x];
            u64 mask = opaque;
            if (u.b >= 0) mask &= ~(A[u.a] ^ A[u.b]);
            papers[next] = {mask, A[u.a] & mask};
            columns[next] = c;
            ded[u.a] = next;
            if (u.b >= 0) ded[u.b] = next;
            next++;
        }
    }
    if (next != K || std::find(ded.begin(), ded.end(), -1) != ded.end()) return emergency_design(originalA, R);
    Solver solver(A);
    solver.M = M;
    solver.G = G;
    solver.H = des->H;
    solver.comparator = comp;
    solver.paper = papers;
    solver.col_of = columns;
    solver.ded = ded;
    solver.handle = des->handle;
    solver.hidx.assign(64, -1);
    for (int c = 0; c < des->H; c++) solver.hidx[solver.handle[c]] = c;
    solver.gmask = low_bits(G);
    solver.hmask = ~solver.gmask;
    solver.h_opq.resize(K);
    solver.h_blk.resize(K);
    for (int x = 0; x < K; x++) {
        solver.h_opq[x] = solver.handle_bits(papers[x].opaque);
        solver.h_blk[x] = solver.handle_bits(papers[x].black);
    }
    solver.order.resize(K);
    std::iota(solver.order.begin(), solver.order.end(), 0);
    solver.init_adaptive();
#ifdef SIM_HARNESS
    // Experiments only (-DSIM_HARNESS): SIM_SEQS=n random request sequences (as the generator:
    // uniform, never the same target twice in a row) on copies of the solver; prints the mean moves
    // per request and exits.
    if (int ns = env_int("SIM_SEQS"); ns > 0) {
        double tot = 0;
        long long wr = 0;
        for (int q = 0; q < ns; q++) {
            Solver sim = solver;
            std::mt19937_64 rr(1000003ULL * (q + 1));
            int prev = rr() % P;
            for (int t = 0; t < R; t++) {
                int u = t == 0 ? prev : int(rr() % (P - 1));
                if (t > 0 && u >= prev) u++;
                prev = u;
                tot += sim.process(u).size();
                wr += sim.display() != A[u];
            }
        }
        std::cerr << "sim_moves = " << tot / (double(ns) * R) << "\nsim_wrong = " << double(wr) / ns << '\n';
        return 0;
    }
#endif

    std::string output;
    for (const auto& pp : papers) {
        std::string row(N, '.');
        for (int j = 0; j < N; j++) row[permutation[j]] = !(pp.opaque >> j & 1) ? '.' : (pp.black >> j & 1) ? '1' : '0';
        output += row + '\n';
    }
    std::cout << output << std::flush;
    long long total = 0, generic = 0, wrong = 0;
    double req_sec = 0;  // time spent planning the requests (without waiting for them)
    for (int r = 0; r < R; r++) {
        int u;
        if (!(std::cin >> u) || u == -1) return 0;
        const double t_req = elapsed_sec();
        // Safety net against a slow machine: the light plan from kFastAfter on.
        if (t_req > kFastAfter) solver.fast_mode = true;
#ifdef FORCE_FAST_MODE
        solver.fast_mode = true;
#endif
        auto moves = solver.process(u);
        req_sec += elapsed_sec() - t_req;
        wrong += solver.display() != A[u];
        output = std::to_string(moves.size()) + '\n';
        for (auto [x, d] : moves) {
            output += std::to_string(x) + ' ' + std::to_string(d) + '\n';
            generic += x < M;
        }
        std::cout << output << std::flush;
        total += moves.size();
    }
    std::cerr << "self_wrong = " << wrong << "\ngeneric_moves = " << generic << "\ntotal_moves = " << total
              << "\nG = " << G << "\nplan_failures = " << solver.plan_failures
              << "\nfast_requests = " << solver.fast_requests << "\nreq_sec = " << req_sec
              << "\nend_sec = " << elapsed_sec() << '\n';
    return 0;
}
