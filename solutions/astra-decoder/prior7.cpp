// astra-research: seven generic sheets, exact legal-distance costs for all 7-element posets.
// imp-gla: solutions/imp-910 with the generic look-ahead (Solver::init_lookahead, set_generic; README).
// imp-seg: solutions/imp-s2hd with the design annealing in 4 segments restarted from the best state (README).
// astra-search4: solutions/imp-combo with a stricter screen and faster stall escapes in assign_windows (README).
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
// Design (times in scaled seconds):
//   assign_windows   which windows are generic, and the pair of sheets and colors of each: annealing
//                    on the cost of a greedy matching of 70 compatible close pairs of targets
//                    (distance <= 26; the pairs Design::initialize takes) until 0.50 s, then a climb
//                    on the same cost until 0.61 s
//   Design::initialize / anneal   the pairs of targets, their columns and the handle order:
//                    annealing on a model of the moves (digs, persistence-weighted handle holes,
//                    exact mean moves of the generic layer) until 1.425 s (Design::Annealer; moves:
//                    target exchanges, unit moves, handle exchanges, column swaps, pair replaces)
//   Design::filler_climb   exchanges of units between columns for better fillers (until 1.48 s)
// Requests (Solver::process): every combination of the plan options is simulated on a copy of the
// state and the plan of least cost (moves + 0.6 per paper left out of its column + 1.0 times the
// expected cost of the next request) is kept. Safety nets: retries with fewer generic windows, a
// design with one white and one black sheet per window, and a light plan from 1.80 s on (scaled,
// as every clock reading).
#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <immintrin.h>
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

// Fixed iteration counts for experiments (MAP_ITERS, GOPT_STEPS, ANNEAL_ITERS, CLIMB_ITERS; 0 or
// unset: until the time limits; GOPT_STEPS / CLIMB_ITERS = -1: no climb). The output then does not
// depend on the machine.
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
    // M! orders of the sheets of the distance (the least number of moves, the bottom sheet fixed) to
    // the nearest order satisfying the relations. Tables built once (orders: perms;
    // below[s][a]: the sheets below a in order s; dist).
    std::vector<std::vector<int>> perms, next;
    std::vector<std::vector<unsigned>> below;
    std::vector<std::array<unsigned char, 7>> inverse7;
    std::vector<uint8_t> relative7;
    std::vector<std::vector<int>> previous7;
    std::vector<uint8_t> dist;
    int order_index(const std::vector<int>& o) const {
        return int(std::lower_bound(perms.begin(), perms.end(), o) - perms.begin());
    }
    int distance(int a, int b) const {
        if (M == 7) {
            unsigned code = 0;
            for (int j = 0; j < 7; j++) code |= unsigned(inverse7[a][perms[b][j]]) << (3 * j);
            return relative7[code];
        }
        return dist[a * perms.size() + b];
    }
    // Moves (sheet, position in the layer) of a shortest way from order a to order b.
    std::vector<std::pair<int, int>> path(int a, int b) const {
        std::vector<std::pair<int, int>> ans;
        while (a != b)
            for (int code = 0; code < M * M; code++) {
                const int y = next[a][code];
                if (y >= 0 && distance(y, b) + 1 == distance(a, b)) {
                    ans.push_back({perms[a][code / M], code % M});
                    a = y;
                    break;
                }
            }
        return ans;
    }
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
        if (M == 7) {
            // Relabeling sheets is an automorphism of the complete comparison
            // graph, including the rule that the current bottom cannot move.
            auto encode = [](const std::vector<int>& p) {
                unsigned code = 0;
                for (int j = 0; j < 7; j++) code |= unsigned(p[j]) << (3 * j);
                return code;
            };
            std::vector<int> index(1U << 21, -1);
            inverse7.resize(n);
            for (int s = 0; s < n; s++) {
                index[encode(perms[s])] = s;
                for (int j = 0; j < 7; j++) inverse7[s][perms[s][j]] = j;
            }
            next.assign(n, std::vector<int>(49, -1));
            previous7.assign(n, {});
            for (int a = 0; a < n; a++) {
                previous7[a].reserve(42);
                for (int pos = 0; pos < 6; pos++) for (int d = 0; d < 7; d++) if (pos != d) {
                    auto q = perms[a];
                    int k = q[pos]; q.erase(q.begin() + pos); q.insert(q.begin() + d, k);
                    int b = index[encode(q)];
                    next[a][pos * 7 + d] = b;
                    previous7[b].push_back(a);
                }
            }
            std::vector<unsigned char> ds(n, 255);
            std::vector<int> queue(n); int head = 0, tail = 0;
            ds[0] = 0; queue[tail++] = 0;
            while (head < tail) {
                int a = queue[head++];
                for (int b : next[a]) if (b >= 0 && ds[b] == 255) ds[b] = ds[a] + 1, queue[tail++] = b;
            }
            assert(tail == n);
            relative7.assign(1U << 21, 255);
            for (int s = 0; s < n; s++) relative7[encode(perms[s])] = ds[s];
            return;
        }
        // next[a][pos * M + d]: the order after the sheet at position pos (not the bottom one: it is
        // not visible) moves to position d; dist[a * n + b]: least moves from order a to order b, by a
        // BFS from every order
        next.assign(n, std::vector<int>(M * M, -1));
        for (int a = 0; a < n; a++)
            for (int pos = 0; pos < M - 1; pos++)
                for (int d = 0; d < M; d++)
                    if (pos != d) {
                        auto o2 = perms[a];
                        const int k = o2[pos];
                        o2.erase(o2.begin() + pos);
                        o2.insert(o2.begin() + d, k);
                        next[a][pos * M + d] = int(std::lower_bound(perms.begin(), perms.end(), o2) - perms.begin());
                    }
        dist.assign(n * n, 255);
        std::vector<int> q(n);
        for (int a = 0; a < n; a++) {
            uint8_t* da = &dist[a * n];
            int qb = 0, qe = 0;
            q[qe++] = a;
            da[a] = 0;
            while (qb < qe) {
                const int x = q[qb++];
                for (int y : next[x])
                    if (y >= 0 && da[y] == 255) da[y] = da[x] + 1, q[qe++] = y;
            }
        }
    }
    // The orders (indices of perms) showing `target` on `holes` (tables built).
    std::vector<int> satisfying(u64 target, u64 holes) const {
        const auto reach = closure(target, holes);
        std::vector<int> sat;
        for (int t = 0; t < (int)perms.size(); t++) {
            bool ok = true;
            for (int a = 0; a < M && ok; a++) ok = !(reach[a] & ~below[t][a]);
            if (ok) sat.push_back(t);
        }
        return sat;
    }
    std::vector<std::pair<u64, double>> memo;  // closure (6 rows of 6 bits) -> mean_moves, sorted
    double mean_moves(u64 target, u64 holes) {
        build_tables();
        auto reach = closure(target, holes);
        u64 key = 0;
        for (int a = 0; a < M; a++) key |= u64(reach[a]) << (6 * a);
        auto it = std::lower_bound(memo.begin(), memo.end(), std::make_pair(key, -1.0));
        if (it != memo.end() && it->first == key) return it->second;
        const int n = perms.size();
        std::vector<int> sat;
        for (int t = 0; t < n; t++) {
            bool ok = true;
            for (int a = 0; a < M && ok; a++) ok = !(reach[a] & ~below[t][a]);
            if (ok) sat.push_back(t);
        }
        double mean = 0;
        if (!sat.empty()) {
            double sum = 0;
            for (int s = 0; s < n; s++) {
                int m = M;
                for (int t : sat)
                    if ((m = std::min<int>(m, dist[s * n + t])) == 0) break;
                sum += m;
            }
            mean = sum / n;
        }
        memo.insert(it, {key, mean});
        return mean;
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

// Seven-sheet exact decoder costs. The embedded table is generated offline.
u64 closure8(u64 r, int m) {
    for(int k=0;k<m;k++)r|=((r>>k)&0x0101010101010101ULL)*((r>>(8*k))&255);
    return r;
}
constexpr u64 kDiagonal=0x8040201008040201ULL;
u64 transpose8(u64 r) {
    u64 t=(r^(r>>7))&0x00AA00AA00AA00AAULL;r^=t^(t<<7);
    t=(r^(r>>14))&0x0000CCCC0000CCCCULL;r^=t^(t<<14);
    t=(r^(r>>28))&0x00000000F0F0F0F0ULL;r^=t^(t<<28);return r;
}
struct PosetClass {u64 relation;int sum;};
u64 canonical7(u64 r) {
    unsigned out[7], in[7]{};
    int key[7], order[7];
    for (int a=0;a<7;a++) {
        out[a]=(r>>(8*a))&127;
        for (int b=0;b<7;b++) if(out[a]>>b&1) in[b]|=1U<<a;
    }
    for(int a=0;a<7;a++) key[a]=__builtin_popcount(out[a])*8+__builtin_popcount(in[a]);
    u64 best=~0ULL;
    auto dfs=[&](auto&& self,int k,unsigned used)->void {
        if(k==7) {
            u64 rr=0;
            for(int i=0;i<7;i++) for(int j=0;j<7;j++)
                if(out[order[i]]>>order[j]&1) rr|=1ULL<<(8*i+j);
            best=std::min(best,rr); return;
        }
        int smallest=1000;
        for(int a=0;a<7;a++)if(!(used>>a&1))smallest=std::min(smallest,key[a]);
        unsigned tried=0;
        for(int a=0;a<7;a++)if(!(used>>a&1)&&key[a]==smallest) {
            bool twin=false;
            for(int b=0;b<a;b++)if(tried>>b&1) twin|=out[a]==out[b]&&in[a]==in[b];
            if(twin)continue;
            tried|=1U<<a;order[k]=a;self(self,k+1,used|(1U<<a));
        }
    };
    dfs(dfs,0,0);return best;
}

// Generated by generate_posets.cpp; all 2045 unlabeled 7-element posets.
// Each cost is the sum over all 5040 source permutations of the shortest
// legal insertion distance to a linear extension of this relation.
constexpr PosetClass kPoset7Classes[2045] = {
{0x0ULL, 0},
{0x1010101010100ULL, 4320},
{0x1010202020000ULL, 7140},
{0x1020202020000ULL, 6552},
{0x1020404000000ULL, 8400},
{0x2020202020000ULL, 4200},
{0x2020404000000ULL, 6720},
{0x2040404000000ULL, 6300},
{0x2040800000000ULL, 7560},
{0x3010102020000ULL, 7560},
{0x3010202020000ULL, 7392},
{0x3020202020000ULL, 6720},
{0x3020404000000ULL, 8730},
{0x3030102020000ULL, 7812},
{0x3030202020000ULL, 7560},
{0x3030301020000ULL, 8064},
{0x3030302020000ULL, 7980},
{0x3030303020000ULL, 8232},
{0x3030303030000ULL, 8400},
{0x3030303030100ULL, 8520},
{0x3030306020000ULL, 10386},
{0x3030404000000ULL, 9400},
{0x3030505010100ULL, 11040},
{0x3030606020000ULL, 10816},
{0x3030a02010000ULL, 10140},
{0x3030a02020000ULL, 9976},
{0x3030c04000000ULL, 11280},
{0x3040404000000ULL, 7320},
{0x3040800000000ULL, 8580},
{0x3050204000000ULL, 9726},
{0x3050505010100ULL, 10620},
{0x3050604000000ULL, 10156},
{0x3050606000000ULL, 10616},
{0x3050901010100ULL, 11880},
{0x3050a02010000ULL, 11952},
{0x3060404000000ULL, 9078},
{0x3060604000000ULL, 9726},
{0x3060606020000ULL, 10416},
{0x3060a02020000ULL, 11556},
{0x3060c04000000ULL, 11275},
{0x30a0a02010000ULL, 10570},
{0x30a0a02020000ULL, 9996},
{0x30c0800000000ULL, 9090},
{0x30c0c00000000ULL, 9800},
{0x30c0c04000000ULL, 10480},
{0x3110102020000ULL, 9730},
{0x3120201020000ULL, 9730},
{0x3120202020000ULL, 9156},
{0x3140402000000ULL, 10590},
{0x3140404000000ULL, 9640},
{0x4040404000000ULL, 4032},
{0x4080800000000ULL, 5880},
{0x5020404000000ULL, 8604},
{0x5050505010100ULL, 8352},
{0x5050602000000ULL, 10122},
{0x5050606000000ULL, 10456},
{0x5060204000000ULL, 9355},
{0x5060404000000ULL, 8868},
{0x5060604000000ULL, 9666},
{0x5060606000000ULL, 10056},
{0x5060c04000000ULL, 11100},
{0x5090901010100ULL, 10200},
{0x50a0a02010000ULL, 12000},
{0x50a0c00000000ULL, 10454},
{0x5140402000000ULL, 10590},
{0x6010204000000ULL, 9078},
{0x6020404000000ULL, 7120},
{0x6040404000000ULL, 6522},
{0x6060104000000ULL, 9390},
{0x6060204000000ULL, 7528},
{0x6060404000000ULL, 7356},
{0x6060601000000ULL, 9756},
{0x6060604000000ULL, 7770},
{0x6060606000000ULL, 8016},
{0x6060606020000ULL, 8208},
{0x6060c04000000ULL, 9684},
{0x6080800000000ULL, 6960},
{0x60a0a02020000ULL, 10020},
{0x60a0c00000000ULL, 9546},
{0x60c0800000000ULL, 8593},
{0x60c0c04000000ULL, 9720},
{0x6140402000000ULL, 9300},
{0x6140404000000ULL, 8880},
{0x6180000000000ULL, 7680},
{0x6180800000000ULL, 9000},
{0x7010204000000ULL, 9504},
{0x7020404000000ULL, 8794},
{0x7030303020000ULL, 10428},
{0x7030306020000ULL, 11094},
{0x7030404000000ULL, 9616},
{0x7030505010100ULL, 11320},
{0x7030506000000ULL, 10896},
{0x7030604000000ULL, 10367},
{0x7030606020000ULL, 11108},
{0x7030a02010000ULL, 12034},
{0x7030a02020000ULL, 11761},
{0x7030c04000000ULL, 11746},
{0x7040404000000ULL, 7332},
{0x7050204000000ULL, 9904},
{0x7050505010100ULL, 10662},
{0x7050604000000ULL, 10242},
{0x7050606000000ULL, 10726},
{0x7060204000000ULL, 9442},
{0x7060404000000ULL, 9112},
{0x7060601000000ULL, 10360},
{0x7060604000000ULL, 9774},
{0x7060606000000ULL, 10116},
{0x7060606020000ULL, 10482},
{0x7060c04000000ULL, 11360},
{0x7070204000000ULL, 10120},
{0x7070303020000ULL, 11232},
{0x7070304000000ULL, 10644},
{0x7070305010100ULL, 11656},
{0x7070306020000ULL, 11438},
{0x7070404000000ULL, 9712},
{0x7070505010100ULL, 11460},
{0x7070506000000ULL, 11036},
{0x7070604000000ULL, 10482},
{0x7070606000000ULL, 10856},
{0x7070606020000ULL, 11260},
{0x7070703020000ULL, 11616},
{0x7070704000000ULL, 10788},
{0x7070705010100ULL, 11838},
{0x7070706000000ULL, 11196},
{0x7070706020000ULL, 11628},
{0x7070707000000ULL, 11376},
{0x7070707010100ULL, 12048},
{0x7070707020000ULL, 11832},
{0x7070707030000ULL, 12144},
{0x7070707030100ULL, 12384},
{0x7070b03020000ULL, 13202},
{0x7070c04000000ULL, 11932},
{0x7070d05010100ULL, 13560},
{0x7070e04000000ULL, 12136},
{0x7070e06000000ULL, 12668},
{0x7070e06020000ULL, 13252},
{0x7080800000000ULL, 7380},
{0x7090901010100ULL, 11040},
{0x70a0a02010000ULL, 12082},
{0x70a0a02020000ULL, 10840},
{0x70a0c00000000ULL, 10766},
{0x70b0301020000ULL, 12116},
{0x70b0302020000ULL, 11924},
{0x70b0a02010000ULL, 12649},
{0x70b0a02020000ULL, 12166},
{0x70b0b01020000ULL, 12888},
{0x70b0b02020000ULL, 12626},
{0x70b0b03020000ULL, 13270},
{0x70b0b03030000ULL, 13584},
{0x70b0b03030100ULL, 13980},
{0x70b0c00000000ULL, 11280},
{0x70b0d01010100ULL, 13182},
{0x70b0e02020000ULL, 12902},
{0x70c0800000000ULL, 9272},
{0x70c0c04000000ULL, 10520},
{0x70d0604000000ULL, 11698},
{0x70d0901010100ULL, 12433},
{0x70d0d05010100ULL, 13644},
{0x70d0e04000000ULL, 12448},
{0x70e0304000000ULL, 11948},
{0x70e0604000000ULL, 11525},
{0x70e0800000000ULL, 9914},
{0x70e0a02020000ULL, 12198},
{0x70e0c04000000ULL, 11784},
{0x70e0e04000000ULL, 12220},
{0x70e0e06000000ULL, 12816},
{0x70e0e06020000ULL, 13370},
{0x7130303020000ULL, 12430},
{0x7130306020000ULL, 12963},
{0x7140402000000ULL, 10770},
{0x7140404000000ULL, 9680},
{0x7150402000000ULL, 11125},
{0x7150503010100ULL, 13308},
{0x7150505010100ULL, 12804},
{0x7160204000000ULL, 10933},
{0x7160404000000ULL, 10248},
{0x7160601000000ULL, 11858},
{0x7160603020000ULL, 12988},
{0x7160604000000ULL, 11386},
{0x7160605000000ULL, 12455},
{0x7160606000000ULL, 11996},
{0x7160606020000ULL, 12540},
{0x7180000000000ULL, 8160},
{0x7180800000000ULL, 9450},
{0x7190101010100ULL, 11040},
{0x7190901010100ULL, 12720},
{0x71a0202010000ULL, 12082},
{0x71a0202020000ULL, 10840},
{0x71a0a02010000ULL, 13550},
{0x71a0a02020000ULL, 12476},
{0x71c0404000000ULL, 10520},
{0x71c0800000000ULL, 10120},
{0x71c0c04000000ULL, 12046},
{0x8080800000000ULL, 3780},
{0x8100000000000ULL, 5040},
{0x9090901010100ULL, 8100},
{0x90a0400000000ULL, 9468},
{0x90a0c00000000ULL, 10386},
{0x9110101010100ULL, 9360},
{0x9120201020000ULL, 11160},
{0xa040800000000ULL, 7950},
{0xa0a0a02010000ULL, 10170},
{0xa0a0a02020000ULL, 7956},
{0xa0c0800000000ULL, 8418},
{0xa0c0c00000000ULL, 9174},
{0xa120202010000ULL, 11160},
{0xa120202020000ULL, 9180},
{0xa140402000000ULL, 10440},
{0xb030301020000ULL, 10182},
{0xb030302020000ULL, 10060},
{0xb030a02010000ULL, 10848},
{0xb030a02020000ULL, 10579},
{0xb040800000000ULL, 8664},
{0xb050901010100ULL, 12090},
{0xb050a02010000ULL, 12567},
{0xb060a02020000ULL, 11837},
{0xb0a0a02010000ULL, 10862},
{0xb0a0a02020000ULL, 10110},
{0xb0b0301020000ULL, 10986},
{0xb0b0302020000ULL, 10826},
{0xb0b0601020000ULL, 12806},
{0xb0b0602020000ULL, 12424},
{0xb0b0a02010000ULL, 11192},
{0xb0b0a02020000ULL, 10846},
{0xb0b0b01020000ULL, 11370},
{0xb0b0b02020000ULL, 11172},
{0xb0b0b03020000ULL, 11646},
{0xb0b0b03030000ULL, 11892},
{0xb0b0b03030100ULL, 12132},
{0xb0b0e02020000ULL, 12638},
{0xb0c0800000000ULL, 9178},
{0xb0c0c00000000ULL, 9920},
{0xb0d0901010100ULL, 12258},
{0xb0d0d01010100ULL, 12930},
{0xb0d0e00000000ULL, 11610},
{0xb0e0302020000ULL, 12118},
{0xb0e0a02020000ULL, 12008},
{0xb0e0c00000000ULL, 11010},
{0xb0e0e02020000ULL, 12682},
{0xb110102020000ULL, 11365},
{0xb120201020000ULL, 11242},
{0xb120202010000ULL, 11365},
{0xb120202020000ULL, 10000},
{0xb130102020000ULL, 11447},
{0xb130202010000ULL, 11528},
{0xb130202020000ULL, 10568},
{0xb130301020000ULL, 12034},
{0xb130302020000ULL, 11761},
{0xb130303020000ULL, 12348},
{0xb130303030000ULL, 12744},
{0xb130303030100ULL, 13140},
{0xb140402000000ULL, 11265},
{0xb150402000000ULL, 11838},
{0xb150503010100ULL, 14400},
{0xb160603020000ULL, 13983},
{0xb1a0a02010000ULL, 12623},
{0xb1a0a02020000ULL, 11853},
{0xb1c0800000000ULL, 9918},
{0xb1c0c00000000ULL, 11152},
{0xc040800000000ULL, 6648},
{0xc080800000000ULL, 6204},
{0xc0c0200000000ULL, 8640},
{0xc0c0800000000ULL, 7020},
{0xc0c0c00000000ULL, 7416},
{0xc0c0c04000000ULL, 7740},
{0xc100000000000ULL, 6240},
{0xc140404000000ULL, 8880},
{0xc180800000000ULL, 8370},
{0xd030604000000ULL, 11599},
{0xd050901010100ULL, 10788},
{0xd060601000000ULL, 11480},
{0xd060604000000ULL, 10496},
{0xd060800000000ULL, 9607},
{0xd060c04000000ULL, 11401},
{0xd090901010100ULL, 10284},
{0xd0a0c00000000ULL, 10649},
{0xd0c0200000000ULL, 9720},
{0xd0d0301010100ULL, 12720},
{0xd0d0901010100ULL, 11040},
{0xd0d0d01010100ULL, 11376},
{0xd0d0d05010100ULL, 11880},
{0xd0e0304000000ULL, 12320},
{0xd0e0604000000ULL, 11747},
{0xd0e0800000000ULL, 9712},
{0xd0e0c00000000ULL, 10852},
{0xd0e0c04000000ULL, 11642},
{0xd0e0e00000000ULL, 11400},
{0xd0e0e04000000ULL, 12256},
{0xd110101010100ULL, 10200},
{0xd150505010100ULL, 12720},
{0xd160204000000ULL, 11469},
{0xd160404000000ULL, 10512},
{0xd160601000000ULL, 12661},
{0xd160604000000ULL, 11979},
{0xd160605000000ULL, 13354},
{0xd190901010100ULL, 12090},
{0xe030302020000ULL, 10816},
{0xe030604000000ULL, 11439},
{0xe030a02020000ULL, 11780},
{0xe030c00000000ULL, 10808},
{0xe030c04000000ULL, 11711},
{0xe040800000000ULL, 8118},
{0xe050604000000ULL, 11318},
{0xe060604000000ULL, 9770},
{0xe060800000000ULL, 9066},
{0xe060a02020000ULL, 10604},
{0xe060c04000000ULL, 10289},
{0xe080800000000ULL, 6988},
{0xe0a0a02020000ULL, 10106},
{0xe0a0c00000000ULL, 9720},
{0xe0c0800000000ULL, 8669},
{0xe0c0c00000000ULL, 9284},
{0xe0c0c04000000ULL, 9844},
{0xe0e0100000000ULL, 10116},
{0xe0e0302020000ULL, 12396},
{0xe0e0304000000ULL, 12128},
{0xe0e0504000000ULL, 11960},
{0xe0e0604000000ULL, 10532},
{0xe0e0800000000ULL, 9236},
{0xe0e0900000000ULL, 11156},
{0xe0e0a02020000ULL, 10858},
{0xe0e0c00000000ULL, 9944},
{0xe0e0c04000000ULL, 10564},
{0xe0e0e00000000ULL, 10224},
{0xe0e0e02020000ULL, 11196},
{0xe0e0e04000000ULL, 10884},
{0xe0e0e06000000ULL, 11340},
{0xe0e0e06020000ULL, 11700},
{0xe100000000000ULL, 6660},
{0xe110102020000ULL, 12000},
{0xe120202020000ULL, 10020},
{0xe130302020000ULL, 12396},
{0xe140402000000ULL, 10644},
{0xe140404000000ULL, 9696},
{0xe160204000000ULL, 10848},
{0xe160404000000ULL, 10260},
{0xe160604000000ULL, 11378},
{0xe160606000000ULL, 11928},
{0xe160606020000ULL, 12504},
{0xe180800000000ULL, 9108},
{0xe1a0a02020000ULL, 11882},
{0xe1c0800000000ULL, 9673},
{0xe1c0c00000000ULL, 10664},
{0xe1c0c04000000ULL, 11506},
{0xf030301020000ULL, 10980},
{0xf030302020000ULL, 10844},
{0xf030604000000ULL, 11670},
{0xf030a02010000ULL, 12282},
{0xf030a02020000ULL, 11946},
{0xf030c00000000ULL, 11104},
{0xf030c04000000ULL, 12088},
{0xf040800000000ULL, 8736},
{0xf050604000000ULL, 11500},
{0xf050901010100ULL, 12258},
{0xf050a02010000ULL, 13032},
{0xf060601000000ULL, 11572},
{0xf060604000000ULL, 10532},
{0xf060800000000ULL, 9828},
{0xf060a02020000ULL, 12036},
{0xf060c04000000ULL, 11588},
{0xf070304000000ULL, 12044},
{0xf070604000000ULL, 11773},
{0xf070703020000ULL, 13310},
{0xf070704000000ULL, 12236},
{0xf070705010100ULL, 13658},
{0xf070706000000ULL, 12768},
{0xf070706020000ULL, 13346},
{0xf070800000000ULL, 10224},
{0xf070901010100ULL, 12930},
{0xf070a02010000ULL, 13218},
{0xf070a02020000ULL, 12668},
{0xf070b01020000ULL, 13404},
{0xf070b02020000ULL, 13096},
{0xf070b03020000ULL, 13768},
{0xf070b03030000ULL, 14132},
{0xf070b03030100ULL, 14540},
{0xf070c04000000ULL, 12226},
{0xf070d05010100ULL, 14141},
{0xf070e04000000ULL, 12633},
{0xf070e06000000ULL, 13250},
{0xf070e06020000ULL, 13844},
{0xf080800000000ULL, 7392},
{0xf090901010100ULL, 11068},
{0xf0a0a02010000ULL, 12188},
{0xf0a0a02020000ULL, 10876},
{0xf0a0c00000000ULL, 10852},
{0xf0b0301020000ULL, 12392},
{0xf0b0302020000ULL, 12186},
{0xf0b0a02010000ULL, 12762},
{0xf0b0a02020000ULL, 12244},
{0xf0b0b01020000ULL, 13008},
{0xf0b0b02020000ULL, 12732},
{0xf0b0b03020000ULL, 13390},
{0xf0b0b03030000ULL, 13692},
{0xf0b0b03030100ULL, 14078},
{0xf0b0c00000000ULL, 11410},
{0xf0b0d01010100ULL, 13392},
{0xf0b0e02020000ULL, 13120},
{0xf0c0800000000ULL, 9308},
{0xf0c0c00000000ULL, 9976},
{0xf0c0c04000000ULL, 10580},
{0xf0d0604000000ULL, 12192},
{0xf0d0901010100ULL, 12503},
{0xf0d0d01010100ULL, 13028},
{0xf0d0d05010100ULL, 13756},
{0xf0d0e00000000ULL, 11796},
{0xf0d0e04000000ULL, 12696},
{0xf0e0302020000ULL, 12604},
{0xf0e0304000000ULL, 12473},
{0xf0e0604000000ULL, 11827},
{0xf0e0800000000ULL, 9966},
{0xf0e0a02020000ULL, 12286},
{0xf0e0c00000000ULL, 11108},
{0xf0e0c04000000ULL, 11899},
{0xf0e0e00000000ULL, 11520},
{0xf0e0e02020000ULL, 12804},
{0xf0e0e04000000ULL, 12366},
{0xf0e0e06000000ULL, 12972},
{0xf0e0e06020000ULL, 13512},
{0xf0f0301020000ULL, 12932},
{0xf0f0302020000ULL, 12700},
{0xf0f0304000000ULL, 12640},
{0xf0f0604000000ULL, 12300},
{0xf0f0703020000ULL, 14010},
{0xf0f0704000000ULL, 12832},
{0xf0f0705010100ULL, 14372},
{0xf0f0706000000ULL, 13456},
{0xf0f0706020000ULL, 14060},
{0xf0f0800000000ULL, 10284},
{0xf0f0901010100ULL, 13028},
{0xf0f0a02010000ULL, 13424},
{0xf0f0a02020000ULL, 12784},
{0xf0f0b01020000ULL, 13662},
{0xf0f0b02020000ULL, 13328},
{0xf0f0b03020000ULL, 14056},
{0xf0f0b03030000ULL, 14404},
{0xf0f0b03030100ULL, 14806},
{0xf0f0c00000000ULL, 11544},
{0xf0f0c04000000ULL, 12384},
{0xf0f0d01010100ULL, 13616},
{0xf0f0d05010100ULL, 14428},
{0xf0f0e00000000ULL, 12000},
{0xf0f0e02020000ULL, 13360},
{0xf0f0e04000000ULL, 12902},
{0xf0f0e06000000ULL, 13564},
{0xf0f0e06020000ULL, 14144},
{0xf0f0f00000000ULL, 12240},
{0xf0f0f01010100ULL, 13896},
{0xf0f0f01020000ULL, 13992},
{0xf0f0f02020000ULL, 13620},
{0xf0f0f03020000ULL, 14376},
{0xf0f0f03030000ULL, 14760},
{0xf0f0f03030100ULL, 15156},
{0xf0f0f04000000ULL, 13152},
{0xf0f0f05010100ULL, 14736},
{0xf0f0f06000000ULL, 13836},
{0xf0f0f06020000ULL, 14430},
{0xf0f0f07000000ULL, 14184},
{0xf0f0f07010100ULL, 15156},
{0xf0f0f07020000ULL, 14814},
{0xf0f0f07030000ULL, 15264},
{0xf0f0f07030100ULL, 15660},
{0xf100000000000ULL, 6912},
{0xf110101010100ULL, 10620},
{0xf110102020000ULL, 12082},
{0xf120201020000ULL, 12000},
{0xf120202020000ULL, 10430},
{0xf130102020000ULL, 12164},
{0xf130201020000ULL, 12205},
{0xf130202020000ULL, 11110},
{0xf130301020000ULL, 12792},
{0xf130302020000ULL, 12478},
{0xf130303020000ULL, 13188},
{0xf130303030000ULL, 13584},
{0xf130303030100ULL, 13980},
{0xf130306020000ULL, 14181},
{0xf140402000000ULL, 11349},
{0xf140404000000ULL, 10112},
{0xf150402000000ULL, 11929},
{0xf150503010100ULL, 14610},
{0xf150505010100ULL, 13560},
{0xf160204000000ULL, 11553},
{0xf160404000000ULL, 10788},
{0xf160601000000ULL, 12826},
{0xf160603020000ULL, 14202},
{0xf160604000000ULL, 12070},
{0xf160605000000ULL, 13557},
{0xf160606000000ULL, 12708},
{0xf160606020000ULL, 13298},
{0xf170204000000ULL, 12020},
{0xf170303020000ULL, 13776},
{0xf170304000000ULL, 13020},
{0xf170305010100ULL, 14820},
{0xf170306020000ULL, 14400},
{0xf170404000000ULL, 11120},
{0xf170505010100ULL, 14148},
{0xf170506000000ULL, 13760},
{0xf170604000000ULL, 12616},
{0xf170606000000ULL, 13248},
{0xf170606020000ULL, 13846},
{0xf170703020000ULL, 14693},
{0xf170704000000ULL, 13234},
{0xf170705010100ULL, 15128},
{0xf170706000000ULL, 14030},
{0xf170706020000ULL, 14733},
{0xf170707000000ULL, 14376},
{0xf170707010100ULL, 15576},
{0xf170707020000ULL, 15138},
{0xf170707030000ULL, 15724},
{0xf170707030100ULL, 16248},
{0xf180800000000ULL, 9504},
{0xf190901010100ULL, 12804},
{0xf1a0a02010000ULL, 13759},
{0xf1a0a02020000ULL, 12570},
{0xf1b0301020000ULL, 13387},
{0xf1b0302020000ULL, 13073},
{0xf1b0a02010000ULL, 13957},
{0xf1b0a02020000ULL, 13123},
{0xf1b0b01020000ULL, 14250},
{0xf1b0b02020000ULL, 13798},
{0xf1b0b03020000ULL, 14741},
{0xf1b0b03030000ULL, 15184},
{0xf1b0b03030100ULL, 15674},
{0xf1c0800000000ULL, 10176},
{0xf1c0c00000000ULL, 11256},
{0xf1c0c04000000ULL, 12168},
{0xf1d0901010100ULL, 13399},
{0xf1d0d01010100ULL, 14120},
{0xf1d0d05010100ULL, 15184},
{0xf1e0604000000ULL, 12654},
{0xf1e0800000000ULL, 10508},
{0xf1e0a02020000ULL, 13158},
{0xf1e0c00000000ULL, 11780},
{0xf1e0c04000000ULL, 12710},
{0xf1e0e00000000ULL, 12294},
{0xf1e0e02020000ULL, 13866},
{0xf1e0e04000000ULL, 13352},
{0xf1e0e06000000ULL, 14196},
{0xf1e0e06020000ULL, 14882},
{0x10100000000000ULL, 3360},
{0x11110101010100ULL, 7680},
{0x12120201010000ULL, 10160},
{0x12120201020000ULL, 9750},
{0x12120202020000ULL, 7536},
{0x13030102020000ULL, 9772},
{0x13030201020000ULL, 9814},
{0x13030202020000ULL, 9366},
{0x13050204000000ULL, 10918},
{0x13110102020000ULL, 10438},
{0x13120201020000ULL, 10333},
{0x13120202020000ULL, 9406},
{0x13130102020000ULL, 10576},
{0x13130201020000ULL, 10580},
{0x13130202020000ULL, 10016},
{0x13130301020000ULL, 10980},
{0x13130302020000ULL, 10816},
{0x13130303020000ULL, 11226},
{0x13130303030000ULL, 11472},
{0x13130303030100ULL, 11712},
{0x13130306020000ULL, 13188},
{0x131a0202010000ULL, 11735},
{0x131a0202020000ULL, 10592},
{0x131c0000000000ULL, 8560},
{0x14140402000000ULL, 9360},
{0x14140404000000ULL, 7320},
{0x14180000000000ULL, 7428},
{0x15060402000000ULL, 10125},
{0x15060404000000ULL, 9696},
{0x15140402000000ULL, 10884},
{0x15150503010100ULL, 13560},
{0x15150505010100ULL, 11460},
{0x15160402000000ULL, 11192},
{0x15160404000000ULL, 10298},
{0x15190101010100ULL, 10788},
{0x16030404000000ULL, 10204},
{0x16050204000000ULL, 10752},
{0x16050402000000ULL, 10794},
{0x16060204000000ULL, 9385},
{0x16060401000000ULL, 10827},
{0x16060404000000ULL, 9094},
{0x16140402000000ULL, 9913},
{0x16140404000000ULL, 9145},
{0x16160204000000ULL, 10148},
{0x16160401000000ULL, 11418},
{0x16160404000000ULL, 9742},
{0x16160601000000ULL, 12120},
{0x16160603020000ULL, 13236},
{0x16160604000000ULL, 10524},
{0x16160605000000ULL, 12698},
{0x16160606000000ULL, 10920},
{0x16160606020000ULL, 11280},
{0x16180000000000ULL, 8020},
{0x161a0202020000ULL, 10608},
{0x161c0404000000ULL, 10291},
{0x17030404000000ULL, 10442},
{0x17050204000000ULL, 10985},
{0x17050402000000ULL, 10992},
{0x17060204000000ULL, 10157},
{0x17060404000000ULL, 9794},
{0x17070204000000ULL, 11196},
{0x17070303020000ULL, 12688},
{0x17070304000000ULL, 11948},
{0x17070305010100ULL, 13399},
{0x17070306020000ULL, 13064},
{0x17070404000000ULL, 10500},
{0x17070505010100ULL, 13042},
{0x17070506000000ULL, 12550},
{0x17070603020000ULL, 13076},
{0x17070604000000ULL, 11639},
{0x17070606000000ULL, 12236},
{0x17070606020000ULL, 12769},
{0x170b0301020000ULL, 12874},
{0x170b0302020000ULL, 12601},
{0x170d0604000000ULL, 12518},
{0x170e0304000000ULL, 12855},
{0x170e0604000000ULL, 12161},
{0x17130303020000ULL, 12706},
{0x17130306020000ULL, 13582},
{0x17140402000000ULL, 11023},
{0x17140404000000ULL, 9814},
{0x17150402000000ULL, 11599},
{0x17150503010100ULL, 13945},
{0x17150505010100ULL, 13063},
{0x17160204000000ULL, 11251},
{0x17160404000000ULL, 10537},
{0x17160601000000ULL, 12418},
{0x17160603020000ULL, 13611},
{0x17160604000000ULL, 11712},
{0x17160605000000ULL, 13058},
{0x17160606000000ULL, 12310},
{0x17160606020000ULL, 12836},
{0x17170204000000ULL, 11686},
{0x17170303020000ULL, 13258},
{0x17170304000000ULL, 12560},
{0x17170305010100ULL, 14120},
{0x17170306020000ULL, 13772},
{0x17170404000000ULL, 10860},
{0x17170505010100ULL, 13630},
{0x17170506000000ULL, 13228},
{0x17170603020000ULL, 13778},
{0x17170604000000ULL, 12170},
{0x17170606000000ULL, 12812},
{0x17170606020000ULL, 13370},
{0x17170703020000ULL, 14042},
{0x17170704000000ULL, 12772},
{0x17170705010100ULL, 14400},
{0x17170706000000ULL, 13484},
{0x17170706020000ULL, 14080},
{0x17170707000000ULL, 13764},
{0x17170707010100ULL, 14736},
{0x17170707020000ULL, 14394},
{0x17170707030000ULL, 14844},
{0x17170707030100ULL, 15240},
{0x17180000000000ULL, 8358},
{0x17190101010100ULL, 11320},
{0x171a0202010000ULL, 12595},
{0x171a0202020000ULL, 11130},
{0x171b0102020000ULL, 12686},
{0x171b0201020000ULL, 12684},
{0x171b0202020000ULL, 11456},
{0x171b0301020000ULL, 13394},
{0x171b0302020000ULL, 13082},
{0x171b0303020000ULL, 13783},
{0x171b0303030000ULL, 14172},
{0x171b0303030100ULL, 14568},
{0x171c0404000000ULL, 10814},
{0x171d0505010100ULL, 14155},
{0x171e0204000000ULL, 12038},
{0x171e0404000000ULL, 11138},
{0x171e0604000000ULL, 12646},
{0x171e0606000000ULL, 13296},
{0x171e0606020000ULL, 13890},
{0x18100000000000ULL, 5610},
{0x18180000000000ULL, 6360},
{0x18180800000000ULL, 6960},
{0x19060800000000ULL, 9810},
{0x19110101010100ULL, 9570},
{0x19190101010100ULL, 10200},
{0x19190901010100ULL, 11040},
{0x1a030202010000ULL, 10570},
{0x1a030202020000ULL, 9996},
{0x1a0c0800000000ULL, 9180},
{0x1a120202010000ULL, 11397},
{0x1a120202020000ULL, 9394},
{0x1a1a0202010000ULL, 12000},
{0x1a1a0202020000ULL, 10020},
{0x1a1a0a02010000ULL, 12840},
{0x1a1a0a02020000ULL, 10860},
{0x1a1c0000000000ULL, 8416},
{0x1a1c0800000000ULL, 9746},
{0x1b030102020000ULL, 10570},
{0x1b030202010000ULL, 10598},
{0x1b030202020000ULL, 10080},
{0x1b070303020000ULL, 13270},
{0x1b070a02010000ULL, 13748},
{0x1b070a02020000ULL, 13022},
{0x1b0b0301020000ULL, 12305},
{0x1b0b0302020000ULL, 12032},
{0x1b0b0a02010000ULL, 12711},
{0x1b0b0a02020000ULL, 12095},
{0x1b0c0800000000ULL, 9594},
{0x1b0d0901010100ULL, 12930},
{0x1b0e0302020000ULL, 12984},
{0x1b0e0a02020000ULL, 12675},
{0x1b110102020000ULL, 11645},
{0x1b120201020000ULL, 11489},
{0x1b120202010000ULL, 11563},
{0x1b120202020000ULL, 10098},
{0x1b130102020000ULL, 11755},
{0x1b130201020000ULL, 11736},
{0x1b130202010000ULL, 11803},
{0x1b130202020000ULL, 10834},
{0x1b130301020000ULL, 12323},
{0x1b130302020000ULL, 12069},
{0x1b130303020000ULL, 12619},
{0x1b130303030000ULL, 13002},
{0x1b130303030100ULL, 13378},
{0x1b1a0202010000ULL, 12208},
{0x1b1a0202020000ULL, 10850},
{0x1b1a0a02010000ULL, 13215},
{0x1b1a0a02020000ULL, 12165},
{0x1b1b0102020000ULL, 12238},
{0x1b1b0202010000ULL, 12304},
{0x1b1b0202020000ULL, 11176},
{0x1b1b0301020000ULL, 12862},
{0x1b1b0302020000ULL, 12564},
{0x1b1b0303020000ULL, 13188},
{0x1b1b0303030000ULL, 13584},
{0x1b1b0303030100ULL, 13980},
{0x1b1b0a02010000ULL, 13382},
{0x1b1b0a02020000ULL, 12640},
{0x1b1b0b01020000ULL, 13646},
{0x1b1b0b02020000ULL, 13264},
{0x1b1b0b03020000ULL, 14028},
{0x1b1b0b03030000ULL, 14424},
{0x1b1b0b03030100ULL, 14820},
{0x1b1c0000000000ULL, 8788},
{0x1b1c0800000000ULL, 10224},
{0x1b1d0101010100ULL, 11656},
{0x1b1d0901010100ULL, 13406},
{0x1b1e0202020000ULL, 11466},
{0x1b1e0a02020000ULL, 13152},
{0x1c030404000000ULL, 10480},
{0x1c060404000000ULL, 9720},
{0x1c060800000000ULL, 9558},
{0x1c0c0800000000ULL, 8592},
{0x1c100000000000ULL, 6324},
{0x1c140404000000ULL, 9102},
{0x1c180000000000ULL, 7680},
{0x1c180800000000ULL, 8664},
{0x1c1c0000000000ULL, 8136},
{0x1c1c0404000000ULL, 9720},
{0x1c1c0800000000ULL, 9228},
{0x1c1c0c00000000ULL, 9960},
{0x1c1c0c04000000ULL, 10560},
{0x1d060404000000ULL, 10128},
{0x1d060800000000ULL, 10084},
{0x1d070505010100ULL, 13644},
{0x1d070901010100ULL, 13308},
{0x1d0d0901010100ULL, 12342},
{0x1d0e0800000000ULL, 10197},
{0x1d0e0c00000000ULL, 11406},
{0x1d0e0c04000000ULL, 12279},
{0x1d110101010100ULL, 10284},
{0x1d150505010100ULL, 12972},
{0x1d160404000000ULL, 10809},
{0x1d190101010100ULL, 11040},
{0x1d190901010100ULL, 12384},
{0x1d1d0101010100ULL, 11376},
{0x1d1d0505010100ULL, 13560},
{0x1d1d0901010100ULL, 12888},
{0x1d1d0d01010100ULL, 13560},
{0x1d1d0d05010100ULL, 14400},
{0x1d1e0000000000ULL, 9036},
{0x1d1e0404000000ULL, 11152},
{0x1d1e0800000000ULL, 10540},
{0x1d1e0c00000000ULL, 11812},
{0x1d1e0c04000000ULL, 12742},
{0x1e030202020000ULL, 10416},
{0x1e030404000000ULL, 10748},
{0x1e050204000000ULL, 11430},
{0x1e060204000000ULL, 10140},
{0x1e060404000000ULL, 9806},
{0x1e060800000000ULL, 9792},
{0x1e070204000000ULL, 11610},
{0x1e070404000000ULL, 10790},
{0x1e070604000000ULL, 12202},
{0x1e070606000000ULL, 12816},
{0x1e070606020000ULL, 13370},
{0x1e070800000000ULL, 10450},
{0x1e070a02020000ULL, 13047},
{0x1e070c04000000ULL, 12572},
{0x1e0b0a02020000ULL, 12679},
{0x1e0b0c00000000ULL, 11661},
{0x1e0c0800000000ULL, 9286},
{0x1e0d0604000000ULL, 12547},
{0x1e0e0604000000ULL, 11658},
{0x1e0e0800000000ULL, 9926},
{0x1e0e0a02020000ULL, 12136},
{0x1e0e0c00000000ULL, 10916},
{0x1e0e0c04000000ULL, 11747},
{0x1e100000000000ULL, 6702},
{0x1e120202020000ULL, 10106},
{0x1e130202020000ULL, 11122},
{0x1e140402000000ULL, 10920},
{0x1e140404000000ULL, 9802},
{0x1e150402000000ULL, 11951},
{0x1e160204000000ULL, 11162},
{0x1e160404000000ULL, 10531},
{0x1e160604000000ULL, 11692},
{0x1e160606000000ULL, 12210},
{0x1e160606020000ULL, 12760},
{0x1e180000000000ULL, 8172},
{0x1e180800000000ULL, 9274},
{0x1e1a0202020000ULL, 10860},
{0x1e1a0a02020000ULL, 12177},
{0x1e1c0000000000ULL, 8634},
{0x1e1c0404000000ULL, 10548},
{0x1e1c0800000000ULL, 9971},
{0x1e1c0c00000000ULL, 10992},
{0x1e1c0c04000000ULL, 11818},
{0x1e1e0000000000ULL, 8880},
{0x1e1e0202020000ULL, 11196},
{0x1e1e0204000000ULL, 11616},
{0x1e1e0404000000ULL, 10872},
{0x1e1e0604000000ULL, 12174},
{0x1e1e0606000000ULL, 12760},
{0x1e1e0606020000ULL, 13340},
{0x1e1e0800000000ULL, 10280},
{0x1e1e0a02020000ULL, 12674},
{0x1e1e0c00000000ULL, 11400},
{0x1e1e0c04000000ULL, 12274},
{0x1e1e0e00000000ULL, 11916},
{0x1e1e0e02020000ULL, 13340},
{0x1e1e0e04000000ULL, 12870},
{0x1e1e0e06000000ULL, 13580},
{0x1e1e0e06020000ULL, 14170},
{0x1f030102020000ULL, 10990},
{0x1f030202020000ULL, 10458},
{0x1f030404000000ULL, 10880},
{0x1f050204000000ULL, 11536},
{0x1f060204000000ULL, 10554},
{0x1f060404000000ULL, 10176},
{0x1f060800000000ULL, 10218},
{0x1f070204000000ULL, 11738},
{0x1f070303020000ULL, 13378},
{0x1f070304000000ULL, 12648},
{0x1f070305010100ULL, 14148},
{0x1f070306020000ULL, 13808},
{0x1f070404000000ULL, 10928},
{0x1f070505010100ULL, 13742},
{0x1f070506000000ULL, 13268},
{0x1f070604000000ULL, 12315},
{0x1f070606000000ULL, 12916},
{0x1f070606020000ULL, 13464},
{0x1f070800000000ULL, 10632},
{0x1f070901010100ULL, 13560},
{0x1f070a02010000ULL, 14028},
{0x1f070a02020000ULL, 13279},
{0x1f070c04000000ULL, 12800},
{0x1f0b0301020000ULL, 12995},
{0x1f0b0302020000ULL, 12722},
{0x1f0b0a02010000ULL, 13438},
{0x1f0b0a02020000ULL, 12786},
{0x1f0b0c00000000ULL, 11880},
{0x1f0c0800000000ULL, 9656},
{0x1f0d0604000000ULL, 12778},
{0x1f0d0901010100ULL, 13042},
{0x1f0e0302020000ULL, 13236},
{0x1f0e0304000000ULL, 13127},
{0x1f0e0604000000ULL, 12313},
{0x1f0e0800000000ULL, 10342},
{0x1f0e0a02020000ULL, 12808},
{0x1f0e0c00000000ULL, 11540},
{0x1f0e0c04000000ULL, 12404},
{0x1f0f0301020000ULL, 13646},
{0x1f0f0302020000ULL, 13332},
{0x1f0f0304000000ULL, 13320},
{0x1f0f0604000000ULL, 12892},
{0x1f0f0703020000ULL, 14981},
{0x1f0f0704000000ULL, 13520},
{0x1f0f0705010100ULL, 15408},
{0x1f0f0706000000ULL, 14338},
{0x1f0f0706020000ULL, 15032},
{0x1f0f0800000000ULL, 10692},
{0x1f0f0901010100ULL, 13658},
{0x1f0f0a02010000ULL, 14267},
{0x1f0f0a02020000ULL, 13397},
{0x1f0f0b01020000ULL, 14533},
{0x1f0f0b02020000ULL, 14065},
{0x1f0f0b03020000ULL, 15012},
{0x1f0f0b03030000ULL, 15460},
{0x1f0f0b03030100ULL, 15940},
{0x1f0f0c00000000ULL, 12016},
{0x1f0f0c04000000ULL, 12956},
{0x1f0f0d01010100ULL, 14372},
{0x1f0f0d05010100ULL, 15443},
{0x1f0f0e00000000ULL, 12528},
{0x1f0f0e02020000ULL, 14096},
{0x1f0f0e04000000ULL, 13589},
{0x1f0f0e06000000ULL, 14436},
{0x1f0f0e06020000ULL, 15119},
{0x1f100000000000ULL, 6936},
{0x1f110101010100ULL, 10662},
{0x1f110102020000ULL, 12228},
{0x1f120201020000ULL, 12106},
{0x1f120202020000ULL, 10478},
{0x1f130102020000ULL, 12324},
{0x1f130201020000ULL, 12339},
{0x1f130202020000ULL, 11256},
{0x1f130301020000ULL, 12926},
{0x1f130302020000ULL, 12638},
{0x1f130303020000ULL, 13309},
{0x1f130303030000ULL, 13692},
{0x1f130303030100ULL, 14078},
{0x1f130306020000ULL, 14471},
{0x1f140402000000ULL, 11497},
{0x1f140404000000ULL, 10174},
{0x1f150402000000ULL, 12176},
{0x1f150503010100ULL, 14904},
{0x1f150505010100ULL, 13672},
{0x1f160204000000ULL, 11725},
{0x1f160404000000ULL, 10945},
{0x1f160601000000ULL, 13112},
{0x1f160603020000ULL, 14501},
{0x1f160604000000ULL, 12242},
{0x1f160605000000ULL, 13852},
{0x1f160606000000ULL, 12862},
{0x1f160606020000ULL, 13433},
{0x1f170204000000ULL, 12270},
{0x1f170303020000ULL, 14035},
{0x1f170304000000ULL, 13312},
{0x1f170305010100ULL, 15128},
{0x1f170306020000ULL, 14715},
{0x1f170404000000ULL, 11316},
{0x1f170505010100ULL, 14407},
{0x1f170506000000ULL, 14078},
{0x1f170603020000ULL, 14713},
{0x1f170604000000ULL, 12866},
{0x1f170606000000ULL, 13528},
{0x1f170606020000ULL, 14124},
{0x1f170703020000ULL, 15006},
{0x1f170704000000ULL, 13526},
{0x1f170705010100ULL, 15436},
{0x1f170706000000ULL, 14356},
{0x1f170706020000ULL, 15056},
{0x1f170707000000ULL, 14700},
{0x1f170707010100ULL, 15870},
{0x1f170707020000ULL, 15448},
{0x1f170707030000ULL, 16022},
{0x1f170707030100ULL, 16528},
{0x1f180000000000ULL, 8460},
{0x1f180800000000ULL, 9612},
{0x1f190101010100ULL, 11460},
{0x1f190901010100ULL, 12958},
{0x1f1a0202010000ULL, 12840},
{0x1f1a0202020000ULL, 11274},
{0x1f1a0a02010000ULL, 14050},
{0x1f1a0a02020000ULL, 12732},
{0x1f1b0102020000ULL, 12924},
{0x1f1b0202010000ULL, 12936},
{0x1f1b0202020000ULL, 11642},
{0x1f1b0301020000ULL, 13639},
{0x1f1b0302020000ULL, 13313},
{0x1f1b0303020000ULL, 14028},
{0x1f1b0303030000ULL, 14424},
{0x1f1b0303030100ULL, 14820},
{0x1f1b0a02010000ULL, 14262},
{0x1f1b0a02020000ULL, 13369},
{0x1f1b0b01020000ULL, 14555},
{0x1f1b0b02020000ULL, 14084},
{0x1f1b0b03020000ULL, 15039},
{0x1f1b0b03030000ULL, 15490},
{0x1f1b0b03030100ULL, 15975},
{0x1f1c0000000000ULL, 8928},
{0x1f1c0404000000ULL, 10964},
{0x1f1c0800000000ULL, 10358},
{0x1f1c0c00000000ULL, 11452},
{0x1f1c0c04000000ULL, 12346},
{0x1f1d0101010100ULL, 11838},
{0x1f1d0505010100ULL, 14400},
{0x1f1d0901010100ULL, 13637},
{0x1f1d0d01010100ULL, 14400},
{0x1f1d0d05010100ULL, 15478},
{0x1f1e0000000000ULL, 9192},
{0x1f1e0202020000ULL, 11652},
{0x1f1e0204000000ULL, 12268},
{0x1f1e0404000000ULL, 11330},
{0x1f1e0604000000ULL, 12888},
{0x1f1e0606000000ULL, 13548},
{0x1f1e0606020000ULL, 14146},
{0x1f1e0800000000ULL, 10716},
{0x1f1e0a02020000ULL, 13395},
{0x1f1e0c00000000ULL, 12016},
{0x1f1e0c04000000ULL, 12959},
{0x1f1e0e00000000ULL, 12558},
{0x1f1e0e02020000ULL, 14146},
{0x1f1e0e04000000ULL, 13636},
{0x1f1e0e06000000ULL, 14502},
{0x1f1e0e06020000ULL, 15190},
{0x1f1f0000000000ULL, 9360},
{0x1f1f0101010100ULL, 12048},
{0x1f1f0102020000ULL, 13232},
{0x1f1f0202020000ULL, 11856},
{0x1f1f0204000000ULL, 12556},
{0x1f1f0301020000ULL, 13968},
{0x1f1f0302020000ULL, 13628},
{0x1f1f0303020000ULL, 14364},
{0x1f1f0303030000ULL, 14760},
{0x1f1f0303030100ULL, 15156},
{0x1f1f0304000000ULL, 13664},
{0x1f1f0305010100ULL, 15576},
{0x1f1f0306020000ULL, 15144},
{0x1f1f0404000000ULL, 11536},
{0x1f1f0505010100ULL, 14736},
{0x1f1f0506000000ULL, 14480},
{0x1f1f0604000000ULL, 13182},
{0x1f1f0606000000ULL, 13856},
{0x1f1f0606020000ULL, 14460},
{0x1f1f0703020000ULL, 15424},
{0x1f1f0704000000ULL, 13868},
{0x1f1f0705010100ULL, 15870},
{0x1f1f0706000000ULL, 14760},
{0x1f1f0706020000ULL, 15486},
{0x1f1f0707000000ULL, 15144},
{0x1f1f0707010100ULL, 16360},
{0x1f1f0707020000ULL, 15924},
{0x1f1f0707030000ULL, 16528},
{0x1f1f0707030100ULL, 17060},
{0x1f1f0800000000ULL, 10920},
{0x1f1f0901010100ULL, 13952},
{0x1f1f0a02010000ULL, 14666},
{0x1f1f0a02020000ULL, 13690},
{0x1f1f0b01020000ULL, 14946},
{0x1f1f0b02020000ULL, 14426},
{0x1f1f0b03020000ULL, 15446},
{0x1f1f0b03030000ULL, 15924},
{0x1f1f0b03030100ULL, 16430},
{0x1f1f0c00000000ULL, 12280},
{0x1f1f0c04000000ULL, 13248},
{0x1f1f0d01010100ULL, 14736},
{0x1f1f0d05010100ULL, 15898},
{0x1f1f0e00000000ULL, 12828},
{0x1f1f0e02020000ULL, 14460},
{0x1f1f0e04000000ULL, 13944},
{0x1f1f0e06000000ULL, 14860},
{0x1f1f0e06020000ULL, 15574},
{0x1f1f0f00000000ULL, 13152},
{0x1f1f0f01010100ULL, 15156},
{0x1f1f0f01020000ULL, 15460},
{0x1f1f0f02020000ULL, 14856},
{0x1f1f0f03020000ULL, 15994},
{0x1f1f0f03030000ULL, 16528},
{0x1f1f0f03030100ULL, 17060},
{0x1f1f0f04000000ULL, 14320},
{0x1f1f0f05010100ULL, 16458},
{0x1f1f0f06000000ULL, 15320},
{0x1f1f0f06020000ULL, 16074},
{0x1f1f0f07000000ULL, 15780},
{0x1f1f0f07010100ULL, 17060},
{0x1f1f0f07020000ULL, 16608},
{0x1f1f0f07030000ULL, 17264},
{0x1f1f0f07030100ULL, 17830},
{0x20000000000000ULL, 2520},
{0x21010101010100ULL, 6840},
{0x21010202020000ULL, 8910},
{0x22020101020000ULL, 9320},
{0x22020102020000ULL, 8910},
{0x22020202020000ULL, 6696},
{0x22020404000000ULL, 8520},
{0x23010102020000ULL, 9404},
{0x23010202020000ULL, 8952},
{0x23020102020000ULL, 9120},
{0x23020202020000ULL, 7536},
{0x23020404000000ULL, 9360},
{0x23030102020000ULL, 9730},
{0x23030202020000ULL, 9156},
{0x23030301020000ULL, 10140},
{0x23030302020000ULL, 9976},
{0x23030303020000ULL, 10386},
{0x23030303030000ULL, 10632},
{0x23030303030100ULL, 10872},
{0x23030306020000ULL, 12348},
{0x23030404000000ULL, 10320},
{0x23030505010100ULL, 12720},
{0x23030606020000ULL, 12396},
{0x23030a02010000ULL, 11952},
{0x23030a02020000ULL, 11556},
{0x23030c04000000ULL, 12300},
{0x24040102000000ULL, 10170},
{0x24040204000000ULL, 8520},
{0x24040404000000ULL, 6480},
{0x25040204000000ULL, 9360},
{0x25050305010100ULL, 12720},
{0x25050505010100ULL, 10620},
{0x25050602000000ULL, 11480},
{0x25050606000000ULL, 11944},
{0x26020104000000ULL, 10380},
{0x26020404000000ULL, 8604},
{0x26040204000000ULL, 8730},
{0x26040404000000ULL, 7320},
{0x26060104000000ULL, 10779},
{0x26060204000000ULL, 9314},
{0x26060303020000ULL, 12422},
{0x26060304000000ULL, 11314},
{0x26060305000000ULL, 12296},
{0x26060306020000ULL, 12419},
{0x26060404000000ULL, 8902},
{0x26060504000000ULL, 11170},
{0x26060506000000ULL, 11891},
{0x26060601000000ULL, 11388},
{0x26060604000000ULL, 9695},
{0x26060606000000ULL, 10088},
{0x26060606020000ULL, 10444},
{0x26060c04000000ULL, 11172},
{0x27010204000000ULL, 10548},
{0x27020404000000ULL, 9388},
{0x27030303020000ULL, 11226},
{0x27030306020000ULL, 12578},
{0x27030404000000ULL, 10400},
{0x27030505010100ULL, 12804},
{0x27030506000000ULL, 12386},
{0x27030604000000ULL, 11565},
{0x27030606020000ULL, 12490},
{0x27030a02010000ULL, 12792},
{0x27030a02020000ULL, 12396},
{0x27030c04000000ULL, 12494},
{0x27040204000000ULL, 9444},
{0x27040404000000ULL, 7740},
{0x27050204000000ULL, 10980},
{0x27050305010100ULL, 12930},
{0x27050505010100ULL, 11460},
{0x27050604000000ULL, 11390},
{0x27050606000000ULL, 12034},
{0x27060204000000ULL, 10124},
{0x27060303020000ULL, 12504},
{0x27060304000000ULL, 11548},
{0x27060306020000ULL, 12624},
{0x27060404000000ULL, 9710},
{0x27060506000000ULL, 12111},
{0x27060601000000ULL, 11588},
{0x27060604000000ULL, 10499},
{0x27060606000000ULL, 10888},
{0x27060606020000ULL, 11264},
{0x27060c04000000ULL, 11954},
{0x27070204000000ULL, 11228},
{0x27070303020000ULL, 12656},
{0x27070304000000ULL, 11974},
{0x27070305010100ULL, 13406},
{0x27070306020000ULL, 13080},
{0x27070404000000ULL, 10500},
{0x27070505010100ULL, 12958},
{0x27070506000000ULL, 12566},
{0x27070604000000ULL, 11699},
{0x27070606000000ULL, 12196},
{0x27070606020000ULL, 12676},
{0x27070703020000ULL, 13302},
{0x27070704000000ULL, 12134},
{0x27070705010100ULL, 13637},
{0x27070706000000ULL, 12766},
{0x27070706020000ULL, 13323},
{0x27070707000000ULL, 13020},
{0x27070707010100ULL, 13952},
{0x27070707020000ULL, 13620},
{0x27070707030000ULL, 14048},
{0x27070707030100ULL, 14428},
{0x27070b03020000ULL, 14461},
{0x27070c04000000ULL, 12698},
{0x27070d05010100ULL, 14904},
{0x27070e04000000ULL, 13062},
{0x27070e06000000ULL, 13818},
{0x27070e06020000ULL, 14524},
{0x28080400000000ULL, 7740},
{0x28080800000000ULL, 6120},
{0x29090501010100ULL, 11880},
{0x29090901010100ULL, 10200},
{0x2a080400000000ULL, 8580},
{0x2a0a0302010000ULL, 12101},
{0x2a0a0302020000ULL, 11616},
{0x2a0a0502010000ULL, 13410},
{0x2a0a0602020000ULL, 11670},
{0x2a0a0a02010000ULL, 12054},
{0x2a0a0a02020000ULL, 10027},
{0x2b030301020000ULL, 10980},
{0x2b030302020000ULL, 10816},
{0x2b030a02010000ULL, 12195},
{0x2b030a02020000ULL, 11785},
{0x2b080400000000ULL, 9000},
{0x2b090501010100ULL, 12720},
{0x2b090601020000ULL, 13608},
{0x2b0a0302010000ULL, 12183},
{0x2b0a0302020000ULL, 11821},
{0x2b0a0602020000ULL, 12462},
{0x2b0a0a02010000ULL, 12259},
{0x2b0a0a02020000ULL, 10847},
{0x2b0b0301020000ULL, 12335},
{0x2b0b0302020000ULL, 12110},
{0x2b0b0601020000ULL, 13888},
{0x2b0b0602020000ULL, 13254},
{0x2b0b0701020000ULL, 14028},
{0x2b0b0702020000ULL, 13617},
{0x2b0b0703020000ULL, 14519},
{0x2b0b0703030000ULL, 14952},
{0x2b0b0703030100ULL, 15450},
{0x2b0b0a02010000ULL, 12715},
{0x2b0b0a02020000ULL, 12123},
{0x2b0b0b01020000ULL, 12937},
{0x2b0b0b02020000ULL, 12603},
{0x2b0b0b03020000ULL, 13297},
{0x2b0b0b03030000ULL, 13662},
{0x2b0b0b03030100ULL, 14029},
{0x2b0b0e02020000ULL, 13633},
{0x2c040800000000ULL, 7950},
{0x2c080800000000ULL, 6960},
{0x2c0c0200000000ULL, 9600},
{0x2c0c0300000000ULL, 10920},
{0x2c0c0304000000ULL, 11960},
{0x2c0c0604000000ULL, 11265},
{0x2c0c0800000000ULL, 8454},
{0x2c0c0a00000000ULL, 10471},
{0x2c0c0c00000000ULL, 9168},
{0x2c0c0c04000000ULL, 9744},
{0x2d050901010100ULL, 12090},
{0x2d090901010100ULL, 11040},
{0x2d0c0200000000ULL, 10140},
{0x2d0c0604000000ULL, 12005},
{0x2d0c0a00000000ULL, 11180},
{0x2d0d0301010100ULL, 13560},
{0x2d0d0705010100ULL, 14967},
{0x2d0d0901010100ULL, 12384},
{0x2d0d0b01010100ULL, 13945},
{0x2d0d0d01010100ULL, 12888},
{0x2d0d0d05010100ULL, 13644},
{0x2e040800000000ULL, 8664},
{0x2e060304000000ULL, 12117},
{0x2e060504000000ULL, 11954},
{0x2e060604000000ULL, 10525},
{0x2e060800000000ULL, 9780},
{0x2e060900000000ULL, 11400},
{0x2e060a02020000ULL, 11880},
{0x2e060c04000000ULL, 11409},
{0x2e080800000000ULL, 7380},
{0x2e0a0302020000ULL, 12410},
{0x2e0a0a02020000ULL, 10861},
{0x2e0a0c00000000ULL, 10691},
{0x2e0c0304000000ULL, 12476},
{0x2e0c0604000000ULL, 11467},
{0x2e0c0800000000ULL, 9229},
{0x2e0c0c00000000ULL, 9946},
{0x2e0c0c04000000ULL, 10553},
{0x2e0e0100000000ULL, 10620},
{0x2e0e0302020000ULL, 13236},
{0x2e0e0304000000ULL, 13027},
{0x2e0e0504000000ULL, 12768},
{0x2e0e0604000000ULL, 11753},
{0x2e0e0704000000ULL, 13143},
{0x2e0e0706000000ULL, 13964},
{0x2e0e0706020000ULL, 14645},
{0x2e0e0800000000ULL, 9964},
{0x2e0e0900000000ULL, 11814},
{0x2e0e0a02020000ULL, 12177},
{0x2e0e0b02020000ULL, 13672},
{0x2e0e0c00000000ULL, 10996},
{0x2e0e0c04000000ULL, 11772},
{0x2e0e0d00000000ULL, 12134},
{0x2e0e0d04000000ULL, 13184},
{0x2e0e0e00000000ULL, 11352},
{0x2e0e0e02020000ULL, 12678},
{0x2e0e0e04000000ULL, 12233},
{0x2e0e0e06000000ULL, 12882},
{0x2e0e0e06020000ULL, 13426},
{0x2f030301020000ULL, 11400},
{0x2f030302020000ULL, 11236},
{0x2f030604000000ULL, 12231},
{0x2f030a02010000ULL, 12899},
{0x2f030a02020000ULL, 12489},
{0x2f030c00000000ULL, 11576},
{0x2f030c04000000ULL, 12688},
{0x2f040800000000ULL, 9042},
{0x2f050604000000ULL, 12044},
{0x2f050901010100ULL, 12804},
{0x2f050a02010000ULL, 13842},
{0x2f060304000000ULL, 12221},
{0x2f060601000000ULL, 12182},
{0x2f060604000000ULL, 10929},
{0x2f060800000000ULL, 10206},
{0x2f060a02020000ULL, 12563},
{0x2f060c04000000ULL, 12075},
{0x2f070304000000ULL, 12654},
{0x2f070604000000ULL, 12334},
{0x2f070703020000ULL, 14054},
{0x2f070704000000ULL, 12840},
{0x2f070705010100ULL, 14407},
{0x2f070706000000ULL, 13494},
{0x2f070706020000ULL, 14086},
{0x2f070800000000ULL, 10674},
{0x2f070901010100ULL, 13644},
{0x2f070a02010000ULL, 14062},
{0x2f070a02020000ULL, 13358},
{0x2f070b01020000ULL, 14248},
{0x2f070b02020000ULL, 13821},
{0x2f070b03020000ULL, 14691},
{0x2f070b03030000ULL, 15164},
{0x2f070b03030100ULL, 15660},
{0x2f070c04000000ULL, 12842},
{0x2f070d05010100ULL, 15135},
{0x2f070e04000000ULL, 13299},
{0x2f070e06000000ULL, 14080},
{0x2f070e06020000ULL, 14778},
{0x2f080800000000ULL, 7632},
{0x2f090901010100ULL, 11460},
{0x2f0a0302010000ULL, 12877},
{0x2f0a0302020000ULL, 12492},
{0x2f0a0a02010000ULL, 12871},
{0x2f0a0a02020000ULL, 11271},
{0x2f0a0c00000000ULL, 11290},
{0x2f0b0301020000ULL, 12987},
{0x2f0b0302020000ULL, 12746},
{0x2f0b0703020000ULL, 14721},
{0x2f0b0a02010000ULL, 13445},
{0x2f0b0a02020000ULL, 12804},
{0x2f0b0b01020000ULL, 13684},
{0x2f0b0b02020000ULL, 13334},
{0x2f0b0b03020000ULL, 14066},
{0x2f0b0b03030000ULL, 14436},
{0x2f0b0b03030100ULL, 14827},
{0x2f0b0c00000000ULL, 11942},
{0x2f0b0d01010100ULL, 14141},
{0x2f0b0e02020000ULL, 13850},
{0x2f0c0304000000ULL, 12680},
{0x2f0c0604000000ULL, 12101},
{0x2f0c0800000000ULL, 9620},
{0x2f0c0c00000000ULL, 10344},
{0x2f0c0c04000000ULL, 10962},
{0x2f0d0604000000ULL, 12867},
{0x2f0d0705010100ULL, 15163},
{0x2f0d0901010100ULL, 13063},
{0x2f0d0d01010100ULL, 13630},
{0x2f0d0d05010100ULL, 14435},
{0x2f0d0e00000000ULL, 12326},
{0x2f0d0e04000000ULL, 13379},
{0x2f0e0302020000ULL, 13318},
{0x2f0e0304000000ULL, 13178},
{0x2f0e0604000000ULL, 12355},
{0x2f0e0704000000ULL, 13321},
{0x2f0e0706000000ULL, 14140},
{0x2f0e0706020000ULL, 14826},
{0x2f0e0800000000ULL, 10350},
{0x2f0e0a02020000ULL, 12828},
{0x2f0e0b02020000ULL, 13851},
{0x2f0e0c00000000ULL, 11572},
{0x2f0e0c04000000ULL, 12414},
{0x2f0e0e00000000ULL, 11994},
{0x2f0e0e02020000ULL, 13386},
{0x2f0e0e04000000ULL, 12920},
{0x2f0e0e06000000ULL, 13598},
{0x2f0e0e06020000ULL, 14176},
{0x2f0f0301020000ULL, 13702},
{0x2f0f0302020000ULL, 13428},
{0x2f0f0304000000ULL, 13404},
{0x2f0f0604000000ULL, 12992},
{0x2f0f0703020000ULL, 15017},
{0x2f0f0704000000ULL, 13582},
{0x2f0f0705010100ULL, 15443},
{0x2f0f0706000000ULL, 14392},
{0x2f0f0706020000ULL, 15087},
{0x2f0f0800000000ULL, 10740},
{0x2f0f0901010100ULL, 13756},
{0x2f0f0a02010000ULL, 14334},
{0x2f0f0a02020000ULL, 13491},
{0x2f0f0b01020000ULL, 14579},
{0x2f0f0b02020000ULL, 14119},
{0x2f0f0b03020000ULL, 15052},
{0x2f0f0b03030000ULL, 15490},
{0x2f0f0b03030100ULL, 15975},
{0x2f0f0c00000000ULL, 12108},
{0x2f0f0c04000000ULL, 13034},
{0x2f0f0d01010100ULL, 14428},
{0x2f0f0d05010100ULL, 15492},
{0x2f0f0e00000000ULL, 12576},
{0x2f0f0e02020000ULL, 14150},
{0x2f0f0e04000000ULL, 13636},
{0x2f0f0e06000000ULL, 14468},
{0x2f0f0e06020000ULL, 15154},
{0x2f0f0f00000000ULL, 12816},
{0x2f0f0f01010100ULL, 14736},
{0x2f0f0f01020000ULL, 14972},
{0x2f0f0f02020000ULL, 14438},
{0x2f0f0f03020000ULL, 15466},
{0x2f0f0f03030000ULL, 15960},
{0x2f0f0f03030100ULL, 16458},
{0x2f0f0f04000000ULL, 13914},
{0x2f0f0f05010100ULL, 15905},
{0x2f0f0f06000000ULL, 14820},
{0x2f0f0f06020000ULL, 15533},
{0x2f0f0f07000000ULL, 15246},
{0x2f0f0f07010100ULL, 16458},
{0x2f0f0f07020000ULL, 16027},
{0x2f0f0f07030000ULL, 16630},
{0x2f0f0f07030100ULL, 17158},
{0x30000000000000ULL, 4080},
{0x30100000000000ULL, 5400},
{0x31010101010100ULL, 7680},
{0x31110101010100ULL, 9360},
{0x32020201010000ULL, 10160},
{0x32020201020000ULL, 9750},
{0x32020202020000ULL, 7536},
{0x32120201010000ULL, 11500},
{0x32120201020000ULL, 11295},
{0x32120202020000ULL, 9198},
{0x33010102020000ULL, 10188},
{0x33010201020000ULL, 10160},
{0x33010202020000ULL, 9750},
{0x33020201020000ULL, 9834},
{0x33020202020000ULL, 7956},
{0x33030102020000ULL, 10570},
{0x33030201020000ULL, 10570},
{0x33030202020000ULL, 9996},
{0x33030301020000ULL, 10980},
{0x33030302020000ULL, 10816},
{0x33030303020000ULL, 11226},
{0x33030303030000ULL, 11472},
{0x33030303030100ULL, 11712},
{0x33030306020000ULL, 13188},
{0x33110102020000ULL, 11582},
{0x33120201020000ULL, 11500},
{0x33120202020000ULL, 10018},
{0x33130102020000ULL, 11734},
{0x33130201020000ULL, 11789},
{0x33130202020000ULL, 10838},
{0x33130301020000ULL, 12306},
{0x33130302020000ULL, 12026},
{0x33130303020000ULL, 12627},
{0x33130303030000ULL, 12948},
{0x33130303030100ULL, 13266},
{0x33130306020000ULL, 14379},
{0x34040402000000ULL, 9360},
{0x34040404000000ULL, 7320},
{0x34140402000000ULL, 10740},
{0x34140404000000ULL, 8940},
{0x35040402000000ULL, 9780},
{0x35050503010100ULL, 13560},
{0x35050505010100ULL, 11460},
{0x35140402000000ULL, 11430},
{0x35150503010100ULL, 14820},
{0x35150505010100ULL, 12930},
{0x36020401000000ULL, 11010},
{0x36020404000000ULL, 9360},
{0x36040402000000ULL, 9444},
{0x36040404000000ULL, 7740},
{0x36060204000000ULL, 10141},
{0x36060401000000ULL, 11457},
{0x36060404000000ULL, 9724},
{0x36060601000000ULL, 12120},
{0x36060603020000ULL, 13236},
{0x36060604000000ULL, 10524},
{0x36060605000000ULL, 12698},
{0x36060606000000ULL, 10920},
{0x36060606020000ULL, 11280},
{0x36140402000000ULL, 10935},
{0x36140404000000ULL, 9740},
{0x36160204000000ULL, 11212},
{0x36160401000000ULL, 12174},
{0x36160404000000ULL, 10547},
{0x36160601000000ULL, 13050},
{0x36160603020000ULL, 14445},
{0x36160604000000ULL, 11686},
{0x36160605000000ULL, 13799},
{0x36160606000000ULL, 12250},
{0x36160606020000ULL, 12725},
{0x37010204000000ULL, 11094},
{0x37020404000000ULL, 9780},
{0x37030303020000ULL, 11646},
{0x37030306020000ULL, 13282},
{0x37030404000000ULL, 10862},
{0x37030505010100ULL, 13560},
{0x37030506000000ULL, 13096},
{0x37030603020000ULL, 13208},
{0x37030604000000ULL, 12153},
{0x37030606020000ULL, 13241},
{0x37040402000000ULL, 9822},
{0x37040404000000ULL, 7992},
{0x37050204000000ULL, 11545},
{0x37050402000000ULL, 11538},
{0x37050503010100ULL, 13644},
{0x37050505010100ULL, 11880},
{0x37050604000000ULL, 11978},
{0x37050606000000ULL, 12723},
{0x37060204000000ULL, 10549},
{0x37060404000000ULL, 10130},
{0x37060601000000ULL, 12200},
{0x37060603020000ULL, 13318},
{0x37060604000000ULL, 10926},
{0x37060605000000ULL, 12788},
{0x37060606000000ULL, 11320},
{0x37060606020000ULL, 11690},
{0x37070204000000ULL, 11756},
{0x37070303020000ULL, 13318},
{0x37070304000000ULL, 12596},
{0x37070305010100ULL, 14155},
{0x37070306020000ULL, 13815},
{0x37070404000000ULL, 10920},
{0x37070505010100ULL, 13672},
{0x37070506000000ULL, 13268},
{0x37070603020000ULL, 13809},
{0x37070604000000ULL, 12252},
{0x37070606000000ULL, 12856},
{0x37070606020000ULL, 13394},
{0x37070703020000ULL, 14042},
{0x37070704000000ULL, 12772},
{0x37070705010100ULL, 14400},
{0x37070706000000ULL, 13484},
{0x37070706020000ULL, 14080},
{0x37070707000000ULL, 13764},
{0x37070707010100ULL, 14736},
{0x37070707020000ULL, 14394},
{0x37070707030000ULL, 14844},
{0x37070707030100ULL, 15240},
{0x37130303020000ULL, 13301},
{0x37130306020000ULL, 14535},
{0x37140402000000ULL, 11505},
{0x37140404000000ULL, 10140},
{0x37150402000000ULL, 12249},
{0x37150503010100ULL, 14967},
{0x37150505010100ULL, 13658},
{0x37160204000000ULL, 11747},
{0x37160404000000ULL, 10947},
{0x37160601000000ULL, 13166},
{0x37160603020000ULL, 14585},
{0x37160604000000ULL, 12245},
{0x37160605000000ULL, 13944},
{0x37160606000000ULL, 12882},
{0x37160606020000ULL, 13419},
{0x37170204000000ULL, 12350},
{0x37170303020000ULL, 14063},
{0x37170304000000ULL, 13344},
{0x37170305010100ULL, 15184},
{0x37170306020000ULL, 14772},
{0x37170404000000ULL, 11354},
{0x37170505010100ULL, 14435},
{0x37170506000000ULL, 14155},
{0x37170603020000ULL, 14791},
{0x37170604000000ULL, 12889},
{0x37170606000000ULL, 13572},
{0x37170606020000ULL, 14152},
{0x37170703020000ULL, 15069},
{0x37170704000000ULL, 13548},
{0x37170705010100ULL, 15478},
{0x37170706000000ULL, 14432},
{0x37170706020000ULL, 15108},
{0x37170707000000ULL, 14760},
{0x37170707010100ULL, 15898},
{0x37170707020000ULL, 15495},
{0x37170707030000ULL, 16050},
{0x37170707030100ULL, 16535},
{0x38000000000000ULL, 4500},
{0x38080800000000ULL, 6960},
{0x38100000000000ULL, 6240},
{0x38180000000000ULL, 7440},
{0x38180800000000ULL, 8460},
{0x39010101010100ULL, 8100},
{0x39090901010100ULL, 11040},
{0x39110101010100ULL, 10200},
{0x39190101010100ULL, 11040},
{0x39190901010100ULL, 12300},
{0x3a020202010000ULL, 10170},
{0x3a020202020000ULL, 7956},
{0x3a0a0a02010000ULL, 12840},
{0x3a0a0a02020000ULL, 10860},
{0x3a120202010000ULL, 12027},
{0x3a120202020000ULL, 10024},
{0x3a1a0202010000ULL, 12840},
{0x3a1a0202020000ULL, 10860},
{0x3a1a0a02010000ULL, 13965},
{0x3a1a0a02020000ULL, 12104},
{0x3b010102020000ULL, 10580},
{0x3b010202020000ULL, 10170},
{0x3b020202010000ULL, 10212},
{0x3b020202020000ULL, 8208},
{0x3b030102020000ULL, 10990},
{0x3b030202010000ULL, 10990},
{0x3b030202020000ULL, 10416},
{0x3b030301020000ULL, 11400},
{0x3b030302020000ULL, 11236},
{0x3b030303020000ULL, 11646},
{0x3b030303030000ULL, 11892},
{0x3b030303030100ULL, 12132},
{0x3b030a02010000ULL, 12825},
{0x3b030a02020000ULL, 12415},
{0x3b0a0a02010000ULL, 12922},
{0x3b0a0a02020000ULL, 11270},
{0x3b0b0301020000ULL, 12935},
{0x3b0b0302020000ULL, 12662},
{0x3b0b0a02010000ULL, 13413},
{0x3b0b0a02020000ULL, 12714},
{0x3b0b0b01020000ULL, 13646},
{0x3b0b0b02020000ULL, 13264},
{0x3b0b0b03020000ULL, 14028},
{0x3b0b0b03030000ULL, 14424},
{0x3b0b0b03030100ULL, 14820},
{0x3b110102020000ULL, 12191},
{0x3b120201020000ULL, 12084},
{0x3b120202010000ULL, 12109},
{0x3b120202020000ULL, 10434},
{0x3b130102020000ULL, 12301},
{0x3b130201020000ULL, 12331},
{0x3b130202010000ULL, 12363},
{0x3b130202020000ULL, 11254},
{0x3b130301020000ULL, 12918},
{0x3b130302020000ULL, 12615},
{0x3b130303020000ULL, 13249},
{0x3b130303030000ULL, 13632},
{0x3b130303030100ULL, 14008},
{0x3b1a0202010000ULL, 12922},
{0x3b1a0202020000ULL, 11270},
{0x3b1a0a02010000ULL, 14105},
{0x3b1a0a02020000ULL, 12705},
{0x3b1b0102020000ULL, 12959},
{0x3b1b0202010000ULL, 13032},
{0x3b1b0202020000ULL, 11680},
{0x3b1b0301020000ULL, 13667},
{0x3b1b0302020000ULL, 13320},
{0x3b1b0303020000ULL, 14028},
{0x3b1b0303030000ULL, 14424},
{0x3b1b0303030100ULL, 14820},
{0x3b1b0a02010000ULL, 14311},
{0x3b1b0a02020000ULL, 13376},
{0x3b1b0b01020000ULL, 14589},
{0x3b1b0b02020000ULL, 14084},
{0x3b1b0b03020000ULL, 15032},
{0x3b1b0b03030000ULL, 15512},
{0x3b1b0b03030100ULL, 15968},
{0x3c000000000000ULL, 4752},
{0x3c040404000000ULL, 7740},
{0x3c040800000000ULL, 8580},
{0x3c080800000000ULL, 7380},
{0x3c0c0800000000ULL, 9222},
{0x3c0c0c00000000ULL, 9960},
{0x3c0c0c04000000ULL, 10560},
{0x3c100000000000ULL, 6660},
{0x3c140404000000ULL, 9732},
{0x3c180000000000ULL, 8100},
{0x3c180800000000ULL, 9210},
{0x3c1c0000000000ULL, 8640},
{0x3c1c0404000000ULL, 10560},
{0x3c1c0800000000ULL, 9984},
{0x3c1c0c00000000ULL, 10980},
{0x3c1c0c04000000ULL, 11760},
{0x3d010101010100ULL, 8352},
{0x3d050505010100ULL, 11880},
{0x3d050901010100ULL, 12720},
{0x3d090901010100ULL, 11460},
{0x3d0d0901010100ULL, 12972},
{0x3d0d0d01010100ULL, 13560},
{0x3d0d0d05010100ULL, 14400},
{0x3d110101010100ULL, 10620},
{0x3d150505010100ULL, 13602},
{0x3d190101010100ULL, 11460},
{0x3d190901010100ULL, 12930},
{0x3d1d0101010100ULL, 11880},
{0x3d1d0505010100ULL, 14400},
{0x3d1d0901010100ULL, 13644},
{0x3d1d0d01010100ULL, 14400},
{0x3d1d0d05010100ULL, 15450},
{0x3e000000000000ULL, 4920},
{0x3e020202020000ULL, 8208},
{0x3e020404000000ULL, 9780},
{0x3e040404000000ULL, 7992},
{0x3e040800000000ULL, 9000},
{0x3e060204000000ULL, 10560},
{0x3e060404000000ULL, 10142},
{0x3e060604000000ULL, 10944},
{0x3e060606000000ULL, 11340},
{0x3e060606020000ULL, 11700},
{0x3e060800000000ULL, 10212},
{0x3e060a02020000ULL, 12500},
{0x3e060c04000000ULL, 12024},
{0x3e080800000000ULL, 7632},
{0x3e0a0a02020000ULL, 11280},
{0x3e0a0c00000000ULL, 11216},
{0x3e0c0800000000ULL, 9622},
{0x3e0c0c00000000ULL, 10356},
{0x3e0c0c04000000ULL, 10968},
{0x3e0e0604000000ULL, 12274},
{0x3e0e0800000000ULL, 10346},
{0x3e0e0a02020000ULL, 12757},
{0x3e0e0c00000000ULL, 11482},
{0x3e0e0c04000000ULL, 12345},
{0x3e0e0e00000000ULL, 11916},
{0x3e0e0e02020000ULL, 13340},
{0x3e0e0e04000000ULL, 12870},
{0x3e0e0e06000000ULL, 13580},
{0x3e0e0e06020000ULL, 14170},
{0x3e100000000000ULL, 6912},
{0x3e120202020000ULL, 10442},
{0x3e140402000000ULL, 11466},
{0x3e140404000000ULL, 10138},
{0x3e160204000000ULL, 11708},
{0x3e160404000000ULL, 10951},
{0x3e160604000000ULL, 12237},
{0x3e160606000000ULL, 12830},
{0x3e160606020000ULL, 13385},
{0x3e180000000000ULL, 8424},
{0x3e180800000000ULL, 9582},
{0x3e1a0202020000ULL, 11280},
{0x3e1a0a02020000ULL, 12722},
{0x3e1c0000000000ULL, 8928},
{0x3e1c0404000000ULL, 10968},
{0x3e1c0800000000ULL, 10363},
{0x3e1c0c00000000ULL, 11472},
{0x3e1c0c04000000ULL, 12338},
{0x3e1e0000000000ULL, 9216},
{0x3e1e0202020000ULL, 11700},
{0x3e1e0204000000ULL, 12288},
{0x3e1e0404000000ULL, 11376},
{0x3e1e0604000000ULL, 12916},
{0x3e1e0606000000ULL, 13580},
{0x3e1e0606020000ULL, 14170},
{0x3e1e0800000000ULL, 10756},
{0x3e1e0a02020000ULL, 13421},
{0x3e1e0c00000000ULL, 12036},
{0x3e1e0c04000000ULL, 12977},
{0x3e1e0e00000000ULL, 12564},
{0x3e1e0e02020000ULL, 14170},
{0x3e1e0e04000000ULL, 13654},
{0x3e1e0e06000000ULL, 14518},
{0x3e1e0e06020000ULL, 15199},
{0x3f000000000000ULL, 5040},
{0x3f010101010100ULL, 8520},
{0x3f010102020000ULL, 10832},
{0x3f010202020000ULL, 10422},
{0x3f010204000000ULL, 11430},
{0x3f020202020000ULL, 8376},
{0x3f020404000000ULL, 10032},
{0x3f030102020000ULL, 11242},
{0x3f030202020000ULL, 10668},
{0x3f030301020000ULL, 11652},
{0x3f030302020000ULL, 11488},
{0x3f030303020000ULL, 11898},
{0x3f030303030000ULL, 12144},
{0x3f030303030100ULL, 12384},
{0x3f030306020000ULL, 13618},
{0x3f030404000000ULL, 11132},
{0x3f030505010100ULL, 13980},
{0x3f030506000000ULL, 13506},
{0x3f030604000000ULL, 12558},
{0x3f030606020000ULL, 13656},
{0x3f030a02010000ULL, 13235},
{0x3f030a02020000ULL, 12825},
{0x3f030c00000000ULL, 11880},
{0x3f030c04000000ULL, 13042},
{0x3f040404000000ULL, 8160},
{0x3f040800000000ULL, 9252},
{0x3f050204000000ULL, 11872},
{0x3f050505010100ULL, 12132},
{0x3f050604000000ULL, 12378},
{0x3f050606000000ULL, 13128},
{0x3f050901010100ULL, 13140},
{0x3f050a02010000ULL, 14292},
{0x3f060204000000ULL, 10806},
{0x3f060404000000ULL, 10386},
{0x3f060601000000ULL, 12540},
{0x3f060604000000ULL, 11186},
{0x3f060606000000ULL, 11580},
{0x3f060606020000ULL, 11946},
{0x3f060800000000ULL, 10470},
{0x3f060a02020000ULL, 12896},
{0x3f060c04000000ULL, 12408},
{0x3f070204000000ULL, 12074},
{0x3f070303020000ULL, 13714},
{0x3f070304000000ULL, 13006},
{0x3f070305010100ULL, 14568},
{0x3f070306020000ULL, 14223},
{0x3f070404000000ULL, 11180},
{0x3f070505010100ULL, 14078},
{0x3f070506000000ULL, 13678},
{0x3f070604000000ULL, 12652},
{0x3f070606000000ULL, 13256},
{0x3f070606020000ULL, 13802},
{0x3f070703020000ULL, 14462},
{0x3f070704000000ULL, 13192},
{0x3f070705010100ULL, 14820},
{0x3f070706000000ULL, 13904},
{0x3f070706020000ULL, 14500},
{0x3f070707000000ULL, 14184},
{0x3f070707010100ULL, 15156},
{0x3f070707020000ULL, 14814},
{0x3f070707030000ULL, 15264},
{0x3f070707030100ULL, 15660},
{0x3f070800000000ULL, 10926},
{0x3f070901010100ULL, 13980},
{0x3f070a02010000ULL, 14491},
{0x3f070a02020000ULL, 13691},
{0x3f070b01020000ULL, 14690},
{0x3f070b02020000ULL, 14212},
{0x3f070b03020000ULL, 15189},
{0x3f070b03030000ULL, 15688},
{0x3f070b03030100ULL, 16220},
{0x3f070c04000000ULL, 13172},
{0x3f070d05010100ULL, 15660},
{0x3f070e04000000ULL, 13687},
{0x3f070e06000000ULL, 14570},
{0x3f070e06020000ULL, 15303},
{0x3f080800000000ULL, 7800},
{0x3f090901010100ULL, 11712},
{0x3f0a0a02010000ULL, 13260},
{0x3f0a0a02020000ULL, 11526},
{0x3f0a0c00000000ULL, 11584},
{0x3f0b0301020000ULL, 13331},
{0x3f0b0302020000ULL, 13058},
{0x3f0b0a02010000ULL, 13827},
{0x3f0b0a02020000ULL, 13122},
{0x3f0b0b01020000ULL, 14066},
{0x3f0b0b02020000ULL, 13684},
{0x3f0b0b03020000ULL, 14448},
{0x3f0b0b03030000ULL, 14844},
{0x3f0b0b03030100ULL, 15240},
{0x3f0b0c00000000ULL, 12226},
{0x3f0b0d01010100ULL, 14540},
{0x3f0b0e02020000ULL, 14247},
{0x3f0c0800000000ULL, 9866},
{0x3f0c0c00000000ULL, 10600},
{0x3f0c0c04000000ULL, 11216},
{0x3f0d0604000000ULL, 13189},
{0x3f0d0901010100ULL, 13378},
{0x3f0d0d01010100ULL, 13980},
{0x3f0d0d05010100ULL, 14820},
{0x3f0d0e00000000ULL, 12648},
{0x3f0d0e04000000ULL, 13764},
{0x3f0e0302020000ULL, 13656},
{0x3f0e0304000000ULL, 13538},
{0x3f0e0604000000ULL, 12647},
{0x3f0e0800000000ULL, 10594},
{0x3f0e0a02020000ULL, 13142},
{0x3f0e0c00000000ULL, 11850},
{0x3f0e0c04000000ULL, 12727},
{0x3f0e0e00000000ULL, 12300},
{0x3f0e0e02020000ULL, 13736},
{0x3f0e0e04000000ULL, 13260},
{0x3f0e0e06000000ULL, 13968},
{0x3f0e0e06020000ULL, 14566},
{0x3f0f0301020000ULL, 14066},
{0x3f0f0302020000ULL, 13752},
{0x3f0f0304000000ULL, 13762},
{0x3f0f0604000000ULL, 13306},
{0x3f0f0703020000ULL, 15491},
{0x3f0f0704000000ULL, 13942},
{0x3f0f0705010100ULL, 15940},
{0x3f0f0706000000ULL, 14838},
{0x3f0f0706020000ULL, 15563},
{0x3f0f0800000000ULL, 10986},
{0x3f0f0901010100ULL, 14078},
{0x3f0f0a02010000ULL, 14761},
{0x3f0f0a02020000ULL, 13812},
{0x3f0f0b01020000ULL, 15013},
{0x3f0f0b02020000ULL, 14494},
{0x3f0f0b03020000ULL, 15518},
{0x3f0f0b03030000ULL, 15996},
{0x3f0f0b03030100ULL, 16507},
{0x3f0f0c00000000ULL, 12384},
{0x3f0f0c04000000ULL, 13350},
{0x3f0f0d01010100ULL, 14806},
{0x3f0f0d05010100ULL, 15975},
{0x3f0f0e00000000ULL, 12882},
{0x3f0f0e02020000ULL, 14528},
{0x3f0f0e04000000ULL, 14003},
{0x3f0f0e06000000ULL, 14916},
{0x3f0f0e06020000ULL, 15640},
{0x3f0f0f00000000ULL, 13152},
{0x3f0f0f01010100ULL, 15156},
{0x3f0f0f01020000ULL, 15460},
{0x3f0f0f02020000ULL, 14856},
{0x3f0f0f03020000ULL, 15994},
{0x3f0f0f03030000ULL, 16528},
{0x3f0f0f03030100ULL, 17060},
{0x3f0f0f04000000ULL, 14320},
{0x3f0f0f05010100ULL, 16458},
{0x3f0f0f06000000ULL, 15320},
{0x3f0f0f06020000ULL, 16074},
{0x3f0f0f07000000ULL, 15780},
{0x3f0f0f07010100ULL, 17060},
{0x3f0f0f07020000ULL, 16608},
{0x3f0f0f07030000ULL, 17264},
{0x3f0f0f07030100ULL, 17830},
{0x3f100000000000ULL, 7080},
{0x3f110101010100ULL, 10872},
{0x3f110102020000ULL, 12536},
{0x3f120201020000ULL, 12442},
{0x3f120202020000ULL, 10688},
{0x3f130102020000ULL, 12632},
{0x3f130201020000ULL, 12675},
{0x3f130202020000ULL, 11508},
{0x3f130301020000ULL, 13262},
{0x3f130302020000ULL, 12946},
{0x3f130303020000ULL, 13645},
{0x3f130303030000ULL, 14028},
{0x3f130303030100ULL, 14414},
{0x3f130306020000ULL, 14990},
{0x3f140402000000ULL, 11805},
{0x3f140404000000ULL, 10384},
{0x3f150402000000ULL, 12568},
{0x3f150503010100ULL, 15450},
{0x3f150505010100ULL, 14008},
{0x3f160204000000ULL, 12033},
{0x3f160404000000ULL, 11197},
{0x3f160601000000ULL, 13540},
{0x3f160603020000ULL, 15042},
{0x3f160604000000ULL, 12555},
{0x3f160605000000ULL, 14358},
{0x3f160606000000ULL, 13202},
{0x3f160606020000ULL, 13771},
{0x3f170204000000ULL, 12662},
{0x3f170303020000ULL, 14455},
{0x3f170304000000ULL, 13740},
{0x3f170305010100ULL, 15674},
{0x3f170306020000ULL, 15239},
{0x3f170404000000ULL, 11610},
{0x3f170505010100ULL, 14827},
{0x3f170506000000ULL, 14589},
{0x3f170603020000ULL, 15254},
{0x3f170604000000ULL, 13259},
{0x3f170606000000ULL, 13948},
{0x3f170606020000ULL, 14544},
{0x3f170703020000ULL, 15540},
{0x3f170704000000ULL, 13948},
{0x3f170705010100ULL, 15975},
{0x3f170706000000ULL, 14876},
{0x3f170706020000ULL, 15588},
{0x3f170707000000ULL, 15228},
{0x3f170707010100ULL, 16430},
{0x3f170707020000ULL, 16000},
{0x3f170707030000ULL, 16600},
{0x3f170707030100ULL, 17123},
{0x3f180000000000ULL, 8628},
{0x3f180800000000ULL, 9810},
{0x3f190101010100ULL, 11712},
{0x3f190901010100ULL, 13266},
{0x3f1a0202010000ULL, 13260},
{0x3f1a0202020000ULL, 11526},
{0x3f1a0a02010000ULL, 14544},
{0x3f1a0a02020000ULL, 13043},
{0x3f1b0102020000ULL, 13316},
{0x3f1b0202010000ULL, 13356},
{0x3f1b0202020000ULL, 11936},
{0x3f1b0301020000ULL, 14059},
{0x3f1b0302020000ULL, 13705},
{0x3f1b0303020000ULL, 14448},
{0x3f1b0303030000ULL, 14844},
{0x3f1b0303030100ULL, 15240},
{0x3f1b0a02010000ULL, 14756},
{0x3f1b0a02020000ULL, 13761},
{0x3f1b0b01020000ULL, 15042},
{0x3f1b0b02020000ULL, 14504},
{0x3f1b0b03020000ULL, 15526},
{0x3f1b0b03030000ULL, 16024},
{0x3f1b0b03030100ULL, 16514},
{0x3f1c0000000000ULL, 9120},
{0x3f1c0404000000ULL, 11216},
{0x3f1c0800000000ULL, 10598},
{0x3f1c0c00000000ULL, 11744},
{0x3f1c0c04000000ULL, 12650},
{0x3f1d0101010100ULL, 12132},
{0x3f1d0505010100ULL, 14820},
{0x3f1d0901010100ULL, 14029},
{0x3f1d0d01010100ULL, 14820},
{0x3f1d0d05010100ULL, 15968},
{0x3f1e0000000000ULL, 9408},
{0x3f1e0202020000ULL, 11946},
{0x3f1e0204000000ULL, 12632},
{0x3f1e0404000000ULL, 11624},
{0x3f1e0604000000ULL, 13278},
{0x3f1e0606000000ULL, 13968},
{0x3f1e0606020000ULL, 14566},
{0x3f1e0800000000ULL, 10998},
{0x3f1e0a02020000ULL, 13785},
{0x3f1e0c00000000ULL, 12362},
{0x3f1e0c04000000ULL, 13332},
{0x3f1e0e00000000ULL, 12906},
{0x3f1e0e02020000ULL, 14566},
{0x3f1e0e04000000ULL, 14040},
{0x3f1e0e06000000ULL, 14962},
{0x3f1e0e06020000ULL, 15679},
{0x3f1f0000000000ULL, 9600},
{0x3f1f0101010100ULL, 12384},
{0x3f1f0102020000ULL, 13708},
{0x3f1f0202020000ULL, 12192},
{0x3f1f0204000000ULL, 13004},
{0x3f1f0301020000ULL, 14472},
{0x3f1f0302020000ULL, 14104},
{0x3f1f0303020000ULL, 14868},
{0x3f1f0303030000ULL, 15264},
{0x3f1f0303030100ULL, 15660},
{0x3f1f0304000000ULL, 14176},
{0x3f1f0305010100ULL, 16248},
{0x3f1f0306020000ULL, 15794},
{0x3f1f0404000000ULL, 11872},
{0x3f1f0505010100ULL, 15240},
{0x3f1f0506000000ULL, 15092},
{0x3f1f0604000000ULL, 13652},
{0x3f1f0606000000ULL, 14356},
{0x3f1f0606020000ULL, 14962},
{0x3f1f0703020000ULL, 16060},
{0x3f1f0704000000ULL, 14360},
{0x3f1f0705010100ULL, 16528},
{0x3f1f0706000000ULL, 15370},
{0x3f1f0706020000ULL, 16135},
{0x3f1f0707000000ULL, 15780},
{0x3f1f0707010100ULL, 17060},
{0x3f1f0707020000ULL, 16608},
{0x3f1f0707030000ULL, 17264},
{0x3f1f0707030100ULL, 17830},
{0x3f1f0800000000ULL, 11244},
{0x3f1f0901010100ULL, 14428},
{0x3f1f0a02010000ULL, 15265},
{0x3f1f0a02020000ULL, 14161},
{0x3f1f0b01020000ULL, 15531},
{0x3f1f0b02020000ULL, 14925},
{0x3f1f0b03020000ULL, 16057},
{0x3f1f0b03030000ULL, 16586},
{0x3f1f0b03030100ULL, 17123},
{0x3f1f0c00000000ULL, 12684},
{0x3f1f0c04000000ULL, 13692},
{0x3f1f0d01010100ULL, 15240},
{0x3f1f0d05010100ULL, 16535},
{0x3f1f0e00000000ULL, 13224},
{0x3f1f0e02020000ULL, 14962},
{0x3f1f0e04000000ULL, 14422},
{0x3f1f0e06000000ULL, 15430},
{0x3f1f0e06020000ULL, 16194},
{0x3f1f0f00000000ULL, 13536},
{0x3f1f0f01010100ULL, 15660},
{0x3f1f0f01020000ULL, 16074},
{0x3f1f0f02020000ULL, 15358},
{0x3f1f0f03020000ULL, 16669},
{0x3f1f0f03030000ULL, 17264},
{0x3f1f0f03030100ULL, 17830},
{0x3f1f0f04000000ULL, 14804},
{0x3f1f0f05010100ULL, 17158},
{0x3f1f0f06000000ULL, 15940},
{0x3f1f0f06020000ULL, 16750},
{0x3f1f0f07000000ULL, 16434},
{0x3f1f0f07010100ULL, 17830},
{0x3f1f0f07020000ULL, 17345},
{0x3f1f0f07030000ULL, 18104},
{0x3f1f0f07030100ULL, 18733},
};


struct Poset7Costs {
    static constexpr unsigned CS=1U<<19;
    std::vector<u64> keys;
    std::vector<int> values;
    std::array<int,2045> both{};
    long long misses=0;
    static unsigned hash(u64 r) {
        r^=r>>27;r*=0x3c79ac492ba7b653ULL;r^=r>>33;
        return unsigned(r)&(CS-1);
    }
    static int find(u64 c) {
        auto it=std::lower_bound(std::begin(kPoset7Classes),std::end(kPoset7Classes),c,
            [](const PosetClass& x,u64 r){return x.relation<r;});
        assert(it!=std::end(kPoset7Classes)&&it->relation==c);
        return int(it-std::begin(kPoset7Classes));
    }
    Poset7Costs():keys(CS,~0ULL),values(CS) {
        for(int i=0;i<2045;i++)both[i]=kPoset7Classes[i].sum+
            kPoset7Classes[find(canonical7(transpose8(kPoset7Classes[i].relation)))].sum;
    }
    // 0 for impossible, otherwise 1 + sum of the distances for both target colors.
    int cost(u64 raw) {
        unsigned h=hash(raw);
        if(keys[h]==raw)return values[h];
        int value=0;
        if(!(raw&transpose8(raw))) {
            u64 closed=closure8(raw,7);
            if(!(closed&kDiagonal)) {
                misses++;
                value=1+both[find(canonical7(closed))];
            }
        }
        keys[h]=raw;values[h]=value;return value;
    }
    static Poset7Costs& get(){static Poset7Costs p;return p;}
};

// The seven-sheet graph has 21 unordered comparisons, exceeding the 16-bit
// direction encoding of astra-search4. Keep the exact 8-by-8 relation matrix.
struct WindowStats {
    int iterations=0;double score=0,gobj_before=0,gobj_after=0;int climb_steps=0;
};
WindowStats assign_windows(std::vector<u64>& A,int m,int g,
    std::vector<std::pair<int,int>>& edges,std::vector<int>& polarity,
    std::vector<int>& permutation,double seconds,int fixed_iters,int climb_steps,double climb_seconds) {
    assert(m==7&&g>=21&&g<64);
    auto& costs=Poset7Costs::get();
    const double start=elapsed_sec();
    constexpr int need=71;
    XorShift rng{0x71eb2566be932e31ULL};
    std::vector<std::pair<int,int>> ep;
    int index[7][7];std::memset(index,-1,sizeof(index));
    for(int a=0;a<7;a++)for(int b=a+1;b<7;b++)index[a][b]=index[b][a]=ep.size(),ep.push_back({a,b});
    std::array<u64,21> masks{},forward{},reverse{};
    std::array<int,64> which{},order{};which.fill(-1);std::iota(order.begin(),order.end(),0);
    std::array<int,21> counts{};
    u64 pol=0,hm=~low_bits(g);
    for(int e=0;e<21;e++)forward[e]=1ULL<<(8*ep[e].first+ep[e].second),reverse[e]=1ULL<<(8*ep[e].second+ep[e].first);
    for(int j=0;j<g;j++) {
        auto[a,b]=edges[j];int e=index[a][b];masks[e]|=1ULL<<j;counts[e]++;which[j]=e;
        if(polarity[j]^(a>b))pol|=1ULL<<j;
    }
    struct Pair {u64 a,d,r;int u,v,dist,rel;};
    std::vector<Pair> pairs;
    auto relation=[&](u64 a,u64 d) {
        u64 z=a^pol,r=0;
        for(int e=0;e<21;e++){u64 x=d&masks[e];if(x&~z)r|=forward[e];if(x&z)r|=reverse[e];}
        return r;
    };
    for(int u=0;u<256;u++)for(int v=u+1;v<256;v++) {
        u64 d=A[u]^A[v];int hd=__builtin_popcountll(d);
        if(hd>26)continue;
        u64 r=relation(A[u],d);pairs.push_back({A[u],d,r,u,v,hd,costs.cost(r)});
    }
    const int np=pairs.size();
    std::vector<u64> nr(np);std::vector<int> nc(np),selected,newselected;
    std::vector<std::pair<int,int>> sorted;sorted.reserve(np);
    auto matching=[&](u64 handles,bool next,std::vector<int>& matching)->double {
        sorted.clear();
        for(int p=0;p<np;p++) {
            int c=next?nc[p]:pairs[p].rel;if(!c)continue;
            const auto& x=pairs[p];
            // 50400 times (0.65 handle differences + both legal means + 0.04 all differences).
            int key=32760*__builtin_popcountll(x.d&handles)+10*(c-1)+2016*x.dist;
            sorted.emplace_back(key,p);
        }
        std::sort(sorted.begin(),sorted.end());
        std::array<unsigned char,256> used{};matching.clear();long long sum=0;
        for(auto[key,p]:sorted) {
            const auto& x=pairs[p];if(used[x.u]||used[x.v])continue;
            used[x.u]=used[x.v]=1;matching.push_back(p);sum+=key;
            if(int(matching.size())==need)break;
        }
        return double(sum)/(50400*need)+10.0*(need-int(matching.size()));
    };
    double current=matching(hm,false,selected),best=current;
    auto best_masks=masks;auto best_order=order;u64 best_pol=pol;
    WindowStats stats;stats.gobj_before=current;
    long long full=0,escapes=0;unsigned generation=1;
    std::array<unsigned,32768> seen{};
    int no_accept=0;
    double escape_score=1e100;auto escape_masks=masks;auto escape_order=order;u64 escape_pol=pol;
    auto restore_state=[&](const auto& mm,const auto& oo,u64 pp) {
        masks=mm;order=oo;pol=pp;hm=0;which.fill(-1);
        for(int j=g;j<64;j++)hm|=1ULL<<order[j];
        for(int e=0;e<21;e++) {
            counts[e]=__builtin_popcountll(masks[e]);
            for(u64 s=masks[e];s;s&=s-1)which[__builtin_ctzll(s)]=e;
        }
        for(auto& p:pairs)p.r=relation(p.a,p.d),p.rel=costs.cost(p.r);
        current=matching(hm,false,selected);generation++;no_accept=0;escape_score=1e100;
    };
    auto stage=[&](double duration,int iterations,bool climb) {
        const double st=elapsed_sec();double now=st;
        for(int it=0;;it++) {
            if((it&31)==0) {
                now=elapsed_sec();
                if(iterations>0?it>=iterations:now-st>=duration)break;
            }
            if(climb)stats.climb_steps++;else stats.iterations++;
            no_accept++;
            if(no_accept>=(climb?2048:1024)&&escape_score<1e50) {
                auto mm=escape_masks;auto oo=escape_order;u64 pp=escape_pol;restore_state(mm,oo,pp);
                escapes++;
                if(current<best)best=current,best_masks=masks,best_pol=pol,best_order=order;
            }
            int ia=rng.mod(g),ib=rng.mod(g),a=order[ia],b=order[ib];
            bool swap_window=rng.real()<0.6;
            if(swap_window)ib=g+rng.mod(64-g),b=order[ib];
            int kind=rng.mod(10),ea=which[a],eb=swap_window?ea:which[b],transfer=-1;
            int memo=0;
            if(swap_window)memo=a*64+b;
            else if(kind<3)memo=4096+a;
            else if(kind<8) {
                if(ea==eb)continue;memo=8192+std::min(a,b)*64+std::max(a,b);
            } else {
                if(counts[ea]<2)continue;eb=rng.mod(21);if(ea==eb)continue;
                transfer=eb;memo=16384+a*32+eb;
            }
            if(seen[memo]==generation)continue;seen[memo]=generation;
            const u64 olda=masks[ea],oldb=masks[eb],oldpol=pol;
            if(swap_window) {
                masks[ea]^=(1ULL<<a)|(1ULL<<b);
                pol=(pol&~(1ULL<<b))|(((oldpol>>a)&1)<<b);
            } else if(kind<3)pol^=1ULL<<a;
            else if(kind<8)masks[ea]^=(1ULL<<a)|(1ULL<<b),masks[eb]^=(1ULL<<a)|(1ULL<<b);
            else masks[ea]^=1ULL<<a,masks[eb]|=1ULL<<a;
            u64 erase=forward[ea]|reverse[ea]|forward[eb]|reverse[eb];
            auto changed_relation=[&](const Pair& x) {
                u64 r=x.r&~erase,z=x.a^pol,da=x.d&masks[ea],db=x.d&masks[eb];
                if(da&~z)r|=forward[ea];if(da&z)r|=reverse[ea];
                if(db&~z)r|=forward[eb];if(db&z)r|=reverse[eb];return r;
            };
            int lost=0;
            for(int p:selected) {
                u64 r=changed_relation(pairs[p]);
                if(r!=pairs[p].r&&(closure8(r,7)&kDiagonal)) {
                    if(++lost>=3)break;
                }
            }
            if(lost>=3) {masks[ea]=olda;masks[eb]=oldb;pol=oldpol;continue;}
            full++;
            for(int p=0;p<np;p++) {
                nr[p]=changed_relation(pairs[p]);
                nc[p]=nr[p]==pairs[p].r?pairs[p].rel:costs.cost(nr[p]);
            }
            u64 nhm=swap_window?hm^((1ULL<<a)|(1ULL<<b)):hm;
            double next=matching(nhm,true,newselected);
            double progress=iterations>0?double(it)/iterations:(now-st)/duration;
            double temp=climb?0.0:0.05*std::pow(0.025,progress);
            bool accept=next<=current||(!climb&&rng.real()<std::exp((current-next)/temp));
            if(next<escape_score) {
                escape_score=next;escape_masks=masks;escape_pol=pol;escape_order=order;
                if(swap_window)std::swap(escape_order[ia],escape_order[ib]);
            }
            if(accept) {
                for(int p=0;p<np;p++)pairs[p].r=nr[p],pairs[p].rel=nc[p];
                hm=nhm;selected.swap(newselected);current=next;
                if(swap_window)which[a]=-1,which[b]=ea,std::swap(order[ia],order[ib]);
                else if(kind>=3&&kind<8)std::swap(which[a],which[b]);
                else if(transfer>=0)counts[ea]--,counts[eb]++,which[a]=eb;
                generation++;no_accept=0;escape_score=1e100;
                if(current<best)best=current,best_masks=masks,best_pol=pol,best_order=order;
            } else {
                masks[ea]=olda;masks[eb]=oldb;pol=oldpol;
            }
        }
    };
    stage(std::max(0.0,seconds-(elapsed_sec()-start)),fixed_iters,false);
    restore_state(best_masks,best_order,best_pol);
    if(climb_steps>0||climb_seconds>0)stage(climb_seconds,climb_steps,true);
    masks=best_masks;order=best_order;pol=best_pol;
    for(int j=0;j<g;j++) {
        int x=order[j],e=0;while(e<21&&!(masks[e]>>x&1))e++;
        assert(e<21);edges[j]=ep[e];polarity[j]=(pol>>x)&1;
    }
    auto oldperm=permutation;
    for(int j=0;j<64;j++)permutation[j]=oldperm[order[j]];
    for(u64& a:A){u64 b=0;for(int j=0;j<64;j++)b|=((a>>order[j])&1)<<j;a=b;}
    stats.score=best;stats.gobj_after=best;
    std::cerr<<"map_escapes = "<<escapes<<"\nmap_full_evaluations = "<<full<<"\nposet7_cache_misses = "<<costs.misses<<'\n';
    return stats;
}
#define AVX2_TARGET __attribute__((target("avx2,popcnt")))

// kBitLanes[v][i]: bit i of v as 0.0f / 1.0f (8 float lanes of a byte of a bit mask; Design::Annealer)
alignas(32) const std::array<std::array<float, 8>, 256> kBitLanes = [] {
    std::array<std::array<float, 8>, 256> a{};
    for (int v = 0; v < 256; v++)
        for (int i = 0; i < 8; i++) a[v][i] = float(v >> i & 1);
    return a;
}();

// The dedicated papers: units (a pair of targets a, b or a single target a, b = -1) in columns c, and
// the handle order (handle[j]: window of h_j; hb[t]: colors of target t at h_0..h_{H-1}).
// Model of the moves per request, summed over the targets (cur):
//   - column c (colcost; from solutions/gpt6pro-10-01-filler-chain): (1 - kRankPriority) times the
//     digs nt (nc - 1) / 2 of a cyclic column (nt targets on nc papers) plus kRankPriority times the
//     least weighted depth W of the column with the pairs (asked twice as often) first, under the
//     condition that the top two papers have both handle colors; 0.1 imb^2 for an unbalanced
//     column, 1e5 without both colors;
//   - handle hole h_j (hcost): kHoleWeight 4 n0 n1 / (n0 + n1) for n0 / n1 holes of color 0 / 1 (the
//     top of column j keeps the color of the last request with a hole there: persistence);
//   - generic layer of a pair (gc): the mean number of moves of the generic layer from a uniform
//     order of the sheets for each of its two targets, summed (2 gcost; PosetSums).
struct Design {
    struct Unit {
        int a = -1, b = -1, c = -1;
    };
    static constexpr double kHoleWeight = 0.40, kRankPriority = 0.85;
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
    std::vector<double> cval;              // colcost of the current counts
    double cur = 0;
    int anneal_iters = 0, climb_iters = 0, climb_accepted = 0;
    int colswap_tried = 0, colswap_accepted = 0, replace_tried = 0, replace_accepted = 0;  // (anneal)
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
    // valid without branches: the pair differences of u (0 for a single) at column c
    int invalid_bit(const Unit& u, int c) const {
        return int(((hb[u.a] ^ hb[u.b & 255]) & (u64(0) - u64(u.b >= 0))) >> c & 1);
    }
    int color(const Unit& u, int c) const { return hb[u.a] >> c & 1; }
    int weight(const Unit& u) const { return u.b < 0 ? 1 : 2; }
    u64 holes(const Unit& u) const {
        u64 d = u.b < 0 ? 0 : hb[u.a] ^ hb[u.b];
        return (low_bits(H) & ~low_bits(u.c + 1)) | d;
    }
    // colcost of a column with nc units, nt targets, n1 units and p1 pairs of color 1 at its handle.
    // W (doubled: minimum2) is the least sum of the depths weighted by the targets (a pair counts
    // twice) with the np pairs on top: nc (nc - 1) / 2 + np (np - 1) / 2, plus np - 1 when the pairs
    // all have one handle color (a single of the other color must then be second, below the first
    // pair). The balance term is weak (0.1 imb^2): the top two papers already carry both colors.
    // Written without branches (the annealing evaluates it twice per move, on random counts).
    // always_inline: Annealer (AVX2) must not call SSE code.
    __attribute__((always_inline)) static double colcost_of(int nc, int nt, int n1, int p1) {
        const int imb = std::max(0, std::abs(nc - 2 * n1) - 1);
        const int np = nt - nc, p0 = np - p1;
        const int correction = std::max(0, np - 1) * int((p0 == 0) | (p1 == 0));
        const int base2 = nt * (nc - 1);
        const int minimum2 = nc * (nc - 1) + np * (np - 1) + 2 * correction;
        const double retrieval = (1.0 - kRankPriority) * base2 * 0.5 + kRankPriority * minimum2 * 0.5;
        return retrieval + 0.1 * (imb * imb) + 100000.0 * int((n1 == 0) | (n1 == nc));
    }
    double colcost(int c) const { return colcost_of(nc[c], nt[c], n1[c], pairOne[c]); }
    // 40 colcost_of in integers (exact; kRankPriority = 17 / 20): 0.15 / 2 * 40 = 3,
    // 0.85 / 2 * 40 = 17, 0.1 * 40 = 4, for the annealing
    static_assert(kRankPriority == 0.85);
    __attribute__((always_inline)) static int colcost40(int nc, int nt, int n1, int p1) {
        const int imb = std::max(0, std::abs(nc - 2 * n1) - 1);
        const int np = nt - nc, p0 = np - p1;
        const int correction = std::max(0, np - 1) * int((p0 == 0) | (p1 == 0));
        const int base2 = nt * (nc - 1);
        const int minimum2 = nc * (nc - 1) + np * (np - 1) + 2 * correction;
        return 3 * base2 + 17 * minimum2 + 4 * (imb * imb) + 4000000 * int((n1 == 0) | (n1 == nc));
    }
    // hcost of x holes of color 0 and y of color 1: hole_table()[x * 257 + y] = kHoleWeight 4 x y / (x + y)
    static const std::array<double, 257 * 257>& hole_table() {
        static const std::array<double, 257 * 257> table = [] {
            std::array<double, 257 * 257> t{};
            for (int x = 0; x <= 256; x++)
                for (int y = 0; y <= 256; y++)
                    if (x + y) t[x * 257 + y] = kHoleWeight * (4.0 * x * y / (x + y));
            return t;
        }();
        return table;
    }
    double hcost(int j) const { return hole_table()[hn[j][0] * 257 + hn[j][1]]; }
    double gc(const Unit& u) const { return u.b < 0 ? 0 : gcost[u.a][u.b] * 2; }
    void update(const Unit& u, int sgn) {
        cur -= cval[u.c];
        nc[u.c] += sgn;
        nt[u.c] += sgn * weight(u);
        n1[u.c] += sgn * color(u, u.c);
        if (u.b >= 0) pairOne[u.c] += sgn * color(u, u.c);
        cur += cval[u.c] = colcost(u.c);
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
        cval.assign(H, 0.0);
        for (int j = 0; j < H; j++) cur += cval[j] = colcost(j);
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
    // partner; pair replaces), the columns (exchange, move one unit, move two units of opposite
    // colors) and the handle order (exchange two handles, 15% of the moves; column swaps with their
    // handle windows), until `seconds` (or fixedIterations);
    // keeps the best state. The moves, the model and the acceptance are those of cmp-speed; the state
    // is kept in a form that evaluates a move quickly (Annealer).
    // The schedule in kAnnealSegments segments, each a new Annealer from the best state so far (run
    // keeps the best state on return), with the temperatures of its slice of the whole schedule.
    static constexpr int kAnnealSegments = 4;
    void anneal(double seconds, int fixedIterations = 0) {
        const auto t0 = std::chrono::steady_clock::now();
        int total = 0;
        for (int s = 0; s < kAnnealSegments; s++) {
            const double used = CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
            const double sec = fixedIterations ? 1e9 : std::max(0.0, seconds * (s + 1) / kAnnealSegments - used);
            const int fi = fixedIterations ? fixedIterations / kAnnealSegments : 0;
            const double p0 = double(s) / kAnnealSegments, p1 = double(s + 1) / kAnnealSegments;
            if (H <= 32)
                Annealer<4>(*this).run(sec, fi, p0, p1);
            else
                Annealer<5>(*this).run(sec, fi, p0, p1);
            total += anneal_iters;
        }
        anneal_iters = total;
    }
    static const std::array<double, 16384>& anneal_logs() {  // -log of a uniform (0, 1), quantized
        static const std::array<double, 16384> logs = []() {
            std::array<double, 16384> a{};
            for (int i = 0; i < 16384; i++) a[i] = -std::log((i + 0.5) / 16384);
            return a;
        }();
        return logs;
    }
    // The state of the annealing, NR registers of 8 float lanes covering the handles (H <= 8 NR):
    //   - a move is evaluated without changing the state and applied only if accepted (a rejection
    //     restores nothing);
    //   - per handle j, the hole counts n0[j], n1[j] and q[j] = n0 n1 / max(n0 + n1, 1) as float lanes
    //     (hcost = kHoleWeight 4 q). A move adds per lane its sign times its weight to n0 or n1 (from
    //     the bit masks of the handles, kBitLanes), and its cost change is the sum of the new q minus
    //     the old q, computed for all the handles at once (AVX2, no branches);
    //   - per column c and handle j, the targets / units / pairs of color 1 there and the pairs that
    //     differ there (rows[c].t1 / u1 / p1 / pd, float lanes, updated on acceptance), so that a
    //     handle exchange a <-> b is counted by sums over the columns a..b-1 instead of their units;
    //   - key[x] = column * 2 + color at its handle of unit x (the partner of the two-unit move).
#define ANNEAL_TARGET __attribute__((target("avx2,fma,bmi,bmi2,popcnt")))
    template <int NR>
    struct Annealer {
        static constexpr int L = 8 * NR;
        static constexpr double kHoleScale = 4 * kHoleWeight;
        struct ColRow {
            alignas(32) float t1[L], u1[L], p1[L], pd[L];
        };
        Design& D;
        const int H, U;
        alignas(32) float n0[L] = {}, n1[L] = {}, hq[L] = {};
        std::vector<ColRow> rows;
        std::array<int, 64> cnc{}, cnt{}, cn1{}, cp1{};
        std::array<int, 64> cv{};  // colcost40
        std::vector<int> key;
        double cur = 0, temp = 2.0;
        const double* const logs = anneal_logs().data();

        // Four independent integer lanes use exactly the scalar colcost40 formula. Callers
        // use two lanes; unused lanes cannot affect the result. All possible counts fit int32.
        ANNEAL_TARGET static __m128i colcost_pair(__m128i nc, __m128i nt, __m128i n1, __m128i p1) {
            const __m128i z = _mm_setzero_si128(), one = _mm_set1_epi32(1);
            const __m128i imbalance = _mm_abs_epi32(_mm_sub_epi32(nc, _mm_slli_epi32(n1, 1)));
            const __m128i imb = _mm_max_epi32(z, _mm_sub_epi32(imbalance, one));
            const __m128i np = _mm_sub_epi32(nt, nc), p0 = _mm_sub_epi32(np, p1);
            const __m128i same = _mm_or_si128(_mm_cmpeq_epi32(p0, z), _mm_cmpeq_epi32(p1, z));
            const __m128i correction = _mm_and_si128(_mm_max_epi32(z, _mm_sub_epi32(np, one)), same);
            const __m128i nm = _mm_sub_epi32(nc, one);
            const __m128i base2 = _mm_mullo_epi32(nt, nm);
            const __m128i minimum2 = _mm_add_epi32(
                _mm_add_epi32(_mm_mullo_epi32(nc, nm), _mm_mullo_epi32(np, _mm_sub_epi32(np, one))),
                _mm_slli_epi32(correction, 1));
            const __m128i retrieval = _mm_add_epi32(
                _mm_add_epi32(base2, _mm_slli_epi32(base2, 1)),
                _mm_add_epi32(minimum2, _mm_slli_epi32(minimum2, 4)));
            const __m128i balance = _mm_slli_epi32(_mm_mullo_epi32(imb, imb), 2);
            const __m128i penalty = _mm_and_si128(_mm_set1_epi32(4000000),
                _mm_or_si128(_mm_cmpeq_epi32(n1, z), _mm_cmpeq_epi32(n1, nc)));
            return _mm_add_epi32(_mm_add_epi32(retrieval, balance), penalty);
        }
        static const float* bit_lanes(unsigned v) { return kBitLanes[v].data(); }
        ANNEAL_TARGET static float qf(float a, float b) {  // the same operations as eval_holes per lane
            const float s = a + b;
            return a * b / (s > 1.0f ? s : 1.0f);
        }
        ANNEAL_TARGET static float hsum(__m256 v) {
            __m128 x = _mm_add_ps(_mm256_castps256_ps128(v), _mm256_extractf128_ps(v, 1));
            x = _mm_add_ps(x, _mm_movehl_ps(x, x));
            x = _mm_add_ss(x, _mm_shuffle_ps(x, x, 1));
            return _mm_cvtss_f32(x);
        }
        // Explicitly unroll these fixed-size loops: GCC -O2 otherwise spills the temporary
        // vector arrays to the stack. Arithmetic order within each lane and hsum stays intact.
        // acc[lane j] += k for every bit j of m
        ANNEAL_TARGET static void add_bits(__m256* acc, u64 m, float k) {
            const __m256 kv = _mm256_set1_ps(k);
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++)
                acc[r] = _mm256_fmadd_ps(_mm256_load_ps(bit_lanes((m >> (8 * r)) & 255)), kv, acc[r]);
        }
        ANNEAL_TARGET static void add_bits(float* row, u64 m, float k) {
            const __m256 kv = _mm256_set1_ps(k);
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++)
                _mm256_store_ps(row + 8 * r, _mm256_add_ps(_mm256_load_ps(row + 8 * r),
                                                           _mm256_mul_ps(_mm256_load_ps(bit_lanes((m >> (8 * r)) & 255)), kv)));
        }
        // New counts N0 = n0 + d0, N1 = n1 + d1 and their q; returns the sum of the changes of q.
        ANNEAL_TARGET float eval_holes(const __m256* d0, const __m256* d1, __m256* N0, __m256* N1, __m256* Q) const {
            const __m256 one = _mm256_set1_ps(1.0f);
            __m256 dif[NR];
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++) {
                N0[r] = _mm256_add_ps(_mm256_load_ps(n0 + 8 * r), d0[r]);
                N1[r] = _mm256_add_ps(_mm256_load_ps(n1 + 8 * r), d1[r]);
                const __m256 s = _mm256_max_ps(_mm256_add_ps(N0[r], N1[r]), one);
                Q[r] = _mm256_div_ps(_mm256_mul_ps(N0[r], N1[r]), s);
                dif[r] = _mm256_sub_ps(Q[r], _mm256_load_ps(hq + 8 * r));
            }
            __m256 acc = _mm256_add_ps(_mm256_add_ps(dif[0], dif[1]), _mm256_add_ps(dif[2], dif[3]));
            if constexpr (NR == 5) acc = _mm256_add_ps(acc, dif[4]);
            static_assert(NR == 4 || NR == 5);
            return hsum(acc);
        }
        ANNEAL_TARGET void commit_holes(const __m256* N0, const __m256* N1, const __m256* Q) {
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++) {
                _mm256_store_ps(n0 + 8 * r, N0[r]);
                _mm256_store_ps(n1 + 8 * r, N1[r]);
                _mm256_store_ps(hq + 8 * r, Q[r]);
            }
        }
        // The rows of column u.c: the unit u added (sgn 1) or removed (-1).
        ANNEAL_TARGET void unit_rows(const Unit& u, float sgn) {
            auto& row = rows[u.c];
            const u64 ha = D.hb[u.a];
            add_bits(row.t1, ha, sgn);
            add_bits(row.u1, ha, sgn);
            if (u.b >= 0) {
                add_bits(row.t1, D.hb[u.b], sgn);
                add_bits(row.p1, ha, sgn);
                add_bits(row.pd, ha ^ D.hb[u.b], sgn);
            }
        }
        int unit_key(const Unit& u) const { return u.c * 2 + D.color(u, u.c); }
        bool accept(double d) {
            return d <= 0 || d < temp * logs[D.rng.next() & 16383];
        }

        explicit Annealer(Design& d) : D(d), H(d.H), U(d.U), rows(d.H), key(d.U) {
            std::memset(static_cast<void*>(rows.data()), 0, rows.size() * sizeof(ColRow));
            for (int j = 0; j < H; j++) n0[j] = float(D.hn[j][0]), n1[j] = float(D.hn[j][1]), hq[j] = qf(n0[j], n1[j]);
            for (int c = 0; c < H; c++)
                cnc[c] = D.nc[c], cnt[c] = D.nt[c], cn1[c] = D.n1[c], cp1[c] = D.pairOne[c];
            for (int c = 0; c < H; c++) cv[c] = colcost40(cnc[c], cnt[c], cn1[c], cp1[c]);
            for (const auto& u : D.unit) unit_rows(u, 1.0f);
            for (int x = 0; x < U; x++) key[x] = unit_key(D.unit[x]);
            cur = D.cur;
        }

        // Units x, y moved between the columns P = ox.c and Q = nx.c (!= P): x to Q, y to the other
        // column (ny.c != oy.c) or not (ny.c == oy.c; its terms then cancel). Applied if accepted.
        ANNEAL_TARGET void column_move(int x, int y, const Unit& ox, const Unit& oy, const Unit& nx, const Unit& ny) {
            const int P = ox.c, Q = nx.c;
            // x always moves P -> Q. y either stays, follows x, or moves Q -> P.
            const int sy = ny.c == oy.c ? 0 : (oy.c == P ? -1 : 1);
            const int px = ox.b >= 0, py = oy.b >= 0, wx = 1 + px, wy = 1 + py;
            const int cxP = D.color(ox, P), cxQ = D.color(ox, Q);
            const int cyP = D.color(oy, P), cyQ = D.color(oy, Q);
            const int dn = -1 + sy, dt = -wx + sy * wy;
            int dnc[2] = {dn, -dn}, dnt[2] = {dt, -dt};
            int dn1[2] = {-cxP + sy * cyP, cxQ - sy * cyQ};
            int dp1[2] = {-px * cxP + sy * py * cyP, px * cxQ - sy * py * cyQ};
            const __m128i costs = colcost_pair(
                _mm_setr_epi32(cnc[P]+dnc[0],cnc[Q]+dnc[1],0,0),
                _mm_setr_epi32(cnt[P]+dnt[0],cnt[Q]+dnt[1],0,0),
                _mm_setr_epi32(cn1[P]+dn1[0],cn1[Q]+dn1[1],0,0),
                _mm_setr_epi32(cp1[P]+dp1[0],cp1[Q]+dp1[1],0,0));
            const int cvP = _mm_cvtsi128_si32(costs), cvQ = _mm_extract_epi32(costs,1);
            // The handles between the two columns stop (moving deeper) or start being holes of the
            // unit, except its pair differences (always holes); a pair's targets agree there.
            __m256 d0[NR], d1[NR];
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            const u64 interval = low_bits(P + 1) ^ low_bits(Q + 1);
            const int sign = Q > P ? -1 : 1;
            const u64 hx = D.hb[ox.a], dx = px ? hx ^ D.hb[ox.b] : 0;
            const u64 mx = interval & ~dx;
            add_bits(d1, mx & hx, float(sign * wx));
            add_bits(d0, mx & ~hx, float(sign * wx));
            if (sy) {
                const u64 hy = D.hb[oy.a], dy = py ? hy ^ D.hb[oy.b] : 0;
                const u64 my = interval & ~dy;
                add_bits(d1, my & hy, float(-sy * sign * wy));
                add_bits(d0, my & ~hy, float(-sy * sign * wy));
            }
            __m256 N0[NR], N1[NR], Qv[NR];
            const float dq = eval_holes(d0, d1, N0, N1, Qv);
            const double delta = ((cvP - cv[P]) + (cvQ - cv[Q])) * (1.0 / 40) + kHoleScale * dq;
            if (!accept(delta)) return;
            cur += delta;
            commit_holes(N0, N1, Qv);
            cnc[P] += dnc[0], cnt[P] += dnt[0], cn1[P] += dn1[0], cp1[P] += dp1[0], cv[P] = cvP;
            cnc[Q] += dnc[1], cnt[Q] += dnt[1], cn1[Q] += dn1[1], cp1[Q] += dp1[1], cv[Q] = cvQ;
            unit_rows(ox, -1.0f);
            unit_rows(nx, 1.0f);
            D.unit[x] = nx;
            key[x] = unit_key(nx);
            if (ny.c != oy.c) {
                unit_rows(oy, -1.0f);
                unit_rows(ny, 1.0f);
                D.unit[y] = ny;
                key[y] = unit_key(ny);
            }
        }
        // An exchange of targets between units x and y (both keep their columns). Applied if accepted.
        ANNEAL_TARGET void target_move(int x, int y, const Unit& ox, const Unit& oy, const Unit& nx, const Unit& ny) {
            const int cx = ox.c, cy = oy.c, iy = cx == cy ? 0 : 1;
            int dnt[2] = {0, 0}, dn1[2] = {0, 0}, dp1[2] = {0, 0};  // [0]: column of x, [1]: of y (if other)
            __m256 d0[NR], d1[NR];
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            _Pragma("GCC unroll 4")
            for (const auto& [u, i, sgn] : {std::tuple<const Unit&, int, int>{ox, 0, -1}, std::tuple<const Unit&, int, int>{nx, 0, 1},
                                            std::tuple<const Unit&, int, int>{oy, iy, -1}, std::tuple<const Unit&, int, int>{ny, iy, 1}}) {
                const int cl = D.color(u, u.c);
                dnt[i] += sgn * D.weight(u), dn1[i] += sgn * cl, dp1[i] += sgn * (u.b >= 0) * cl;
                const u64 hs = D.holes(u);
                _Pragma("GCC unroll 2")
                for (int t : {u.a, u.b}) {
                    if (t < 0) continue;
                    add_bits(d1, hs & D.hb[t], float(sgn));
                    add_bits(d0, hs & ~D.hb[t], float(sgn));
                }
            }
            const __m128i costs = colcost_pair(_mm_setr_epi32(cnc[cx],cnc[cy],0,0),
                _mm_setr_epi32(cnt[cx]+dnt[0],cnt[cy]+dnt[1],0,0),
                _mm_setr_epi32(cn1[cx]+dn1[0],cn1[cy]+dn1[1],0,0),
                _mm_setr_epi32(cp1[cx]+dp1[0],cp1[cy]+dp1[1],0,0));
            const int cvx = _mm_cvtsi128_si32(costs), cvy = iy ? _mm_extract_epi32(costs,1) : 0;
            __m256 N0[NR], N1[NR], Qv[NR];
            const float dq = eval_holes(d0, d1, N0, N1, Qv);
            const double dcol = ((cvx - cv[cx]) + (iy ? cvy - cv[cy] : 0)) * (1.0 / 40);
            const double delta = dcol + kHoleScale * dq + ((D.gc(nx) + D.gc(ny)) - (D.gc(ox) + D.gc(oy)));
            if (!accept(delta)) return;
            cur += delta;
            commit_holes(N0, N1, Qv);
            cnt[cx] += dnt[0], cn1[cx] += dn1[0], cp1[cx] += dp1[0], cv[cx] = cvx;
            if (iy) cnt[cy] += dnt[1], cn1[cy] += dn1[1], cp1[cy] += dp1[1], cv[cy] = cvy;
            unit_rows(ox, -1.0f);
            unit_rows(oy, -1.0f);
            unit_rows(nx, 1.0f);
            unit_rows(ny, 1.0f);
            D.unit[x] = nx;
            D.unit[y] = ny;
            key[x] = unit_key(nx);
            key[y] = unit_key(ny);
            D.owner[nx.a] = x;
            if (nx.b >= 0) D.owner[nx.b] = x;
            D.owner[ny.a] = y;
            if (ny.b >= 0) D.owner[ny.b] = y;
        }
        ANNEAL_TARGET void mutate(int x, int y, const Unit& nx, const Unit& ny) {
            if (D.invalid_bit(nx, nx.c) | D.invalid_bit(ny, ny.c)) return;  // (one branch for both)
            const Unit ox = D.unit[x], oy = D.unit[y];
            if (nx.a == ox.a && nx.b == ox.b && ny.a == oy.a && ny.b == oy.b) {  // only the columns change
                column_move(x, y, ox, oy, nx, ny);  // (the pairs are compatible)
            } else {
                if ((nx.b >= 0 && !D.ok[nx.a][nx.b]) || (ny.b >= 0 && !D.ok[ny.a][ny.b])) return;
                target_move(x, y, ox, oy, nx, ny);
            }
        }
        // Exchange the handles at positions a < b. The units of the columns < a and >= b see h_a and
        // h_b exchanged, so the new hole counts are the old ones of the other handle, corrected for
        // the targets of the columns a..b-1 (b deeper, a only a pair difference: one hole of each
        // color); the colors at the handles of the columns a and b change. Applied if accepted.
        ANNEAL_TARGET void handle_swap(int a, int b) {
            if (rows[a].pd[b] != 0 || rows[b].pd[a] != 0) return;  // a pair must agree at the new handle of its column
            const int n1a = int(rows[a].u1[b]), n1b = int(rows[b].u1[a]), pa = int(rows[a].p1[b]), pb = int(rows[b].p1[a]);
            int tot = 0;
            float mb_old1 = 0, mb_new1 = 0, ma_old = 0, ma_new = 0;  // (small integers: exact)
            for (int c = a; c < b; c++) {
                tot += cnt[c];
                mb_old1 += rows[c].t1[b];
                mb_new1 += rows[c].t1[a];
                ma_old += rows[c].pd[a];
                ma_new += rows[c].pd[b];
            }
            const float na0 = n0[b] - (float(tot) - mb_old1) + ma_new, na1 = n1[b] - mb_old1 + ma_new;
            const float nb0 = n0[a] - ma_old + (float(tot) - mb_new1), nb1 = n1[a] - ma_old + mb_new1;
            const float qa = qf(na0, na1), qb = qf(nb0, nb1);
            const __m128i costs = colcost_pair(_mm_setr_epi32(cnc[a],cnc[b],0,0),
                _mm_setr_epi32(cnt[a],cnt[b],0,0),_mm_setr_epi32(n1a,n1b,0,0),_mm_setr_epi32(pa,pb,0,0));
            const int cva = _mm_cvtsi128_si32(costs), cvb = _mm_extract_epi32(costs,1);
            const double delta = kHoleScale * ((qa - hq[a]) + (qb - hq[b])) + ((cva + cvb) - (cv[a] + cv[b])) * (1.0 / 40);
            if (!accept(delta)) return;
            cur += delta;
            std::swap(D.handle[a], D.handle[b]);
            for (auto& h : D.hb) {
                const u64 t = ((h >> a) ^ (h >> b)) & 1;
                h ^= (t << a) | (t << b);
            }
            for (auto& row : rows) {
                std::swap(row.t1[a], row.t1[b]);
                std::swap(row.u1[a], row.u1[b]);
                std::swap(row.p1[a], row.p1[b]);
                std::swap(row.pd[a], row.pd[b]);
            }
            n0[a] = na0, n1[a] = na1, hq[a] = qa, n0[b] = nb0, n1[b] = nb1, hq[b] = qb;
            cn1[a] = n1a, cn1[b] = n1b, cp1[a] = pa, cp1[b] = pb, cv[a] = cva, cv[b] = cvb;
            for (int x = 0; x < U; x++) key[x] = unit_key(D.unit[x]);
        }
        // Exchange the columns at positions a < b together with their handle windows (the column
        // swap of solutions/gpt6pro-08-01-colswap and gpt6pro-06-02-regroup). Every unit keeps its
        // own handle window, so the validity and every column cost stay; only hole counts change.
        // With the new positions (h_a's window moves to position b, h_b's to a):
        //   - position a (window of old h_b): the old counts of h_b, less the holes there of the
        //     columns a..b-1 (old column a is now deeper, the columns a+1..b-1 are above it);
        //   - position b (window of old h_a): the old counts of h_a, plus the holes there of the
        //     columns a+1..b (old column b is now at position a, the columns a+1..b-1 are above it);
        //   - positions a < j < b: old column a stops being a hole there, old column b starts;
        // always except the pair differences (holes anyway). Without its pair differences, a column c
        // has t1 - pd holes of color 1 and nt - t1 - pd of color 0 at a handle (a differing pair counts
        // one target of each color in t1). Applied if accepted.
        ANNEAL_TARGET void column_swap(int a, int b) {
            ++D.colswap_tried;
            float T = 0, X1 = 0, Xd = 0;  // columns a..b-1 at h_b (small integers: exact)
            for (int c = a; c < b; c++) T += float(cnt[c]), X1 += rows[c].t1[b], Xd += rows[c].pd[b];
            float T2 = 0, Y1 = 0, Yd = 0;  // columns a+1..b at h_a
            for (int c = a + 1; c <= b; c++) T2 += float(cnt[c]), Y1 += rows[c].t1[a], Yd += rows[c].pd[a];
            __m256 d0[NR], d1[NR];
            if (b - a > 1) {
                const u64 mid = low_bits(b) & ~low_bits(a + 1);
                const __m256 ta = _mm256_set1_ps(float(cnt[a])), tb = _mm256_set1_ps(float(cnt[b]));
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++) {
                    const __m256 m = _mm256_load_ps(bit_lanes((mid >> (8 * r)) & 255));
                    const __m256 a1 = _mm256_sub_ps(_mm256_load_ps(rows[a].t1 + 8 * r), _mm256_load_ps(rows[a].pd + 8 * r));
                    const __m256 b1 = _mm256_sub_ps(_mm256_load_ps(rows[b].t1 + 8 * r), _mm256_load_ps(rows[b].pd + 8 * r));
                    const __m256 a0 = _mm256_sub_ps(_mm256_sub_ps(ta, _mm256_load_ps(rows[a].t1 + 8 * r)), _mm256_load_ps(rows[a].pd + 8 * r));
                    const __m256 b0 = _mm256_sub_ps(_mm256_sub_ps(tb, _mm256_load_ps(rows[b].t1 + 8 * r)), _mm256_load_ps(rows[b].pd + 8 * r));
                    d1[r] = _mm256_mul_ps(m, _mm256_sub_ps(b1, a1));
                    d0[r] = _mm256_mul_ps(m, _mm256_sub_ps(b0, a0));
                }
            } else {
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            }
            const u64 ba = u64(1) << a, bb = u64(1) << b;
            add_bits(d0, ba, (n0[b] - n0[a]) - (T - X1 - Xd));
            add_bits(d1, ba, (n1[b] - n1[a]) - (X1 - Xd));
            add_bits(d0, bb, (n0[a] - n0[b]) + (T2 - Y1 - Yd));
            add_bits(d1, bb, (n1[a] - n1[b]) + (Y1 - Yd));
            __m256 N0[NR], N1[NR], Qv[NR];
            const float dq = eval_holes(d0, d1, N0, N1, Qv);
            const double delta = kHoleScale * dq;
            if (!accept(delta)) return;
            ++D.colswap_accepted;
            cur += delta;
            commit_holes(N0, N1, Qv);
            std::swap(cnc[a], cnc[b]), std::swap(cnt[a], cnt[b]), std::swap(cn1[a], cn1[b]);
            std::swap(cp1[a], cp1[b]), std::swap(cv[a], cv[b]);
            std::swap(D.handle[a], D.handle[b]);
            // bits a and b of every target exchanged, without branches (vectorized; a branch per
            // target would be mispredicted half of the time)
            for (auto& h : D.hb) {
                const u64 t = ((h >> a) ^ (h >> b)) & 1;
                h ^= (t << a) | (t << b);
            }
            for (auto& row : rows) {
                std::swap(row.t1[a], row.t1[b]);
                std::swap(row.u1[a], row.u1[b]);
                std::swap(row.p1[a], row.p1[b]);
                std::swap(row.pd[a], row.pd[b]);
            }
            std::swap(rows[a], rows[b]);
            for (int x = 0; x < U; x++) {
                auto& u = D.unit[x];
                if (u.c == a || u.c == b) {
                    u.c ^= a ^ b;
                    key[x] = unit_key(u);
                }
            }
        }
        // Pair replace (solutions/gpt6pro-07-02-replace; the pair shift of gpt6pro-06-02-regroup is
        // one of its outcomes): units xs[0..k-1] become nu[0..k-1] (any targets and columns). The
        // column counts are summed per distinct column, the hole counts per target as in
        // target_move. Applied if accepted.
        ANNEAL_TARGET void multi_move(int k, const int* xs, const Unit* nu) {
            int cols[6], dnc[6], dnt[6], dn1[6], dp1[6], ncols = 0;
            __m256 d0[NR], d1[NR];
            _Pragma("GCC unroll 5")
            for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            _Pragma("GCC unroll 3")
            for (int i = 0; i < k; i++)
                _Pragma("GCC unroll 2")
                for (int sgn = -1; sgn <= 1; sgn += 2) {
                    const Unit& u = sgn < 0 ? D.unit[xs[i]] : nu[i];
                    int ci = 0;
                    while (ci < ncols && cols[ci] != u.c) ci++;
                    if (ci == ncols) cols[ncols] = u.c, dnc[ncols] = dnt[ncols] = dn1[ncols] = dp1[ncols] = 0, ncols++;
                    const int cl = D.color(u, u.c);
                    dnc[ci] += sgn, dnt[ci] += sgn * D.weight(u), dn1[ci] += sgn * cl, dp1[ci] += sgn * (u.b >= 0) * cl;
                    const u64 hs = D.holes(u);
                _Pragma("GCC unroll 2")
                for (int t : {u.a, u.b}) {
                        if (t < 0) continue;
                        add_bits(d1, hs & D.hb[t], float(sgn));
                        add_bits(d0, hs & ~D.hb[t], float(sgn));
                    }
                }
            int ncv[6], dcol = 0;
            for (int i = 0; i < ncols; i++) {
                const int c = cols[i];
                ncv[i] = colcost40(cnc[c] + dnc[i], cnt[c] + dnt[i], cn1[c] + dn1[i], cp1[c] + dp1[i]);
                dcol += ncv[i] - cv[c];
            }
            double dg = 0;
            for (int i = 0; i < k; i++) dg += D.gc(nu[i]) - D.gc(D.unit[xs[i]]);
            __m256 N0[NR], N1[NR], Qv[NR];
            const float dq = eval_holes(d0, d1, N0, N1, Qv);
            const double delta = dcol * (1.0 / 40) + kHoleScale * dq + dg;
            if (!accept(delta)) return;
            ++D.replace_accepted;
            cur += delta;
            commit_holes(N0, N1, Qv);
            for (int i = 0; i < ncols; i++) {
                const int c = cols[i];
                cnc[c] += dnc[i], cnt[c] += dnt[i], cn1[c] += dn1[i], cp1[c] += dp1[i], cv[c] = ncv[i];
            }
            for (int i = 0; i < k; i++) unit_rows(D.unit[xs[i]], -1.0f);
            for (int i = 0; i < k; i++) {
                unit_rows(nu[i], 1.0f);
                D.unit[xs[i]] = nu[i];
                key[xs[i]] = unit_key(nu[i]);
                D.owner[nu[i].a] = xs[i];
                if (nu[i].b >= 0) D.owner[nu[i].b] = xs[i];
            }
        }

        // p0, p1: the slice of the whole schedule (progress) that this run covers
        ANNEAL_TARGET void run(double seconds, int fixedIterations, double p0 = 0, double p1 = 1) {
            auto start = std::chrono::steady_clock::now();
            double progress = 0;
            // Handle exchanges, column swaps (distances 1..kColSwapDist) and pair replaces, per mille
            // of the moves (then target exchanges until 430, column exchanges until 750, unit moves
            // until 900, two-unit moves).
            constexpr int kHandleSwapRate = 150, kColSwapRate = 20, kColSwapDist = 4, kReplaceRate = 100;
            constexpr int kColSwapEnd = kHandleSwapRate + kColSwapRate, kReplaceEnd = kColSwapEnd + kReplaceRate;
            auto& rng = D.rng;
            auto& unit = D.unit;
            // The units that are pairs / singles: no move changes it (a pair replace keeps the pair
            // in the unit that was a pair; the units exchange columns instead).
            std::vector<int> pairUnits, singleUnits;
            for (int x = 0; x < U; x++) (unit[x].b >= 0 ? pairUnits : singleUnits).push_back(x);
            std::vector<Unit> best = unit;
            std::vector<int> bestHandle = D.handle;
            double bestCost = cur;
            for (int it = 0;; it++) {
                D.anneal_iters = it;
                if ((it & 255) == 0) {
                    double elapsed =
                        CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
                    progress = fixedIterations > 0 ? double(it) / fixedIterations : elapsed / seconds;
                    if (progress >= 1 || elapsed >= seconds) break;
                    temp = 2.0 * std::pow(0.015 / 2.0, p0 + (p1 - p0) * progress);
                }
                int type = rng.below(1000);
                if (type < kHandleSwapRate) {
                    int a = rng.below(H), b = rng.below(H);
                    if (a == b) continue;
                    if (a > b) std::swap(a, b);
                    handle_swap(a, b);
                } else if (type < kColSwapEnd) {
                    const int d = 1 + rng.below(std::min(kColSwapDist, H - 1));
                    const int a = rng.below(H - d);
                    column_swap(a, a + d);
                } else if (type < kReplaceEnd) {
                    // The pair x = (a, b), a single y = c and a single z = d compatible with c become
                    // the pair (c, d) in x and the singles a, b in y, z (in random order); the pair
                    // takes a random one of the three columns where it is valid (the other two units
                    // take the other two columns).
                    if (pairUnits.empty() || singleUnits.size() < 2) continue;
                    const int x = pairUnits[rng.below(pairUnits.size())];
                    const int y = singleUnits[rng.below(singleUnits.size())];
                    const auto& ps = D.partners[unit[y].a];
                    if (ps.empty()) continue;
                    int z = -1;
                    for (int t = 0; t < 4; t++) {
                        const int cand = D.owner[ps[rng.below(ps.size())]];
                        if (cand != y && unit[cand].b < 0) {
                            z = cand;
                            break;
                        }
                    }
                    if (z < 0) continue;
                    const Unit ox = unit[x], oy = unit[y], oz = unit[z];
                    Unit nu[3] = {{oy.a, oz.a, ox.c}, {ox.a, -1, oy.c}, {ox.b, -1, oz.c}};
                    if (rng.below(2)) std::swap(nu[1].a, nu[2].a);
                    int choice[3], nch = 0;
                    for (int i = 0; i < 3; i++)
                        if (!D.invalid_bit(nu[0], nu[i].c)) choice[nch++] = i;
                    if (!nch) continue;
                    const int ch = choice[rng.below(nch)];
                    if (ch) std::swap(nu[0].c, nu[ch].c);
                    ++D.replace_tried;
                    const int xs[3] = {x, y, z};
                    multi_move(3, xs, nu);
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
                            const auto& p = D.partners[fixed];
                            if (p.empty()) continue;
                            int newTarget = p[rng.below(p.size())];
                            y = D.owner[newTarget];
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
                        if (nx.c == ny.c || cnc[nx.c] <= 2) continue;
                        nx.c = ny.c;
                    } else {
                        int c = nx.c, d = ny.c;
                        if (c == d || cnc[c] <= 2) continue;
                        // a unit of column c with the other color at h_c (x itself never matches)
                        const int want = 2 * c + 1 - D.color(nx, c);
                        int z = -1;
                        for (int t = 0; t < 16; t++) {
                            int j = rng.below(U);
                            if (key[j] == want) {
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
                    bestHandle = D.handle;
                }
            }
            unit = best;
            D.handle = bestHandle;
            for (int i = 0; i < 256; i++) {
                D.hb[i] = 0;
                for (int j = 0; j < H; j++) D.hb[i] |= ((D.A[i] >> D.handle[j]) & 1) << j;
            }
            D.rebuild();
        }
    };
#undef ANNEAL_TARGET
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

// Helpers inside the generic layer (from solutions/gpt6pro-08-01-colswap): a dedicated paper x of
// another column placed between the generic sheets shows its colors on the generic windows that the
// sheets above it leave as holes, hides the sheets below it there, and also shows on the handle holes
// of the requested paper D. The 720 orders s of the 6 generic sheets (states) and their distances are
// those of the Comparator (the bottom sheet of the layer never moves). For a target u, helpers[u]
// lists the papers x (not of D's column, the
// same colors as A_u on their opaque handle holes of D, opaque on some generic hole of D) with the
// goals (s, t) such that order s with x inserted under the t upper sheets shows A_u on D's generic
// holes (the deepest t per s).
struct Interleave {
    static constexpr int GM = 6;
    struct Goal {
        uint16_t state;
        uint8_t depth;
    };
    struct Helper {
        int paper;
        std::vector<Goal> goals;
    };
    struct Pick {
        int paper, goal, depth, distance;
    };
    const Comparator* comp = nullptr;  // the orders of the generic sheets and their distances
    std::vector<std::vector<Helper>> helpers;
    std::vector<u64> display;                     // generic display of order s
    std::vector<std::array<u64, GM + 1>> prefix;  // windows covered by the t upper sheets of s
    bool ready = false;
    long long helper_papers = 0;
    // Builds the tables (comparator c with its tables built); stops (ready stays false) after the
    // scaled time `limit`.
    void init(const Comparator& c, const std::vector<Paper>& paper, const std::vector<u64>& A,
              const std::vector<int>& ded, const std::vector<int>& col_of, u64 gmask, u64 hmask, double limit) {
        comp = &c;
        const int NS = c.perms.size();
        display.assign(NS, 0);
        prefix.assign(NS, {});
        for (int s = 0; s < NS; s++) {
            u64 cov = 0, b = 0;
            for (int j = 0; j < GM; j++) {
                const int k = c.perms[s][j];
                b |= paper[k].black & gmask & ~cov;
                cov |= paper[k].opaque & gmask;
                prefix[s][j + 1] = cov;
            }
            display[s] = b;
        }
        helpers.assign(A.size(), {});
        for (int u = 0; u < (int)A.size(); u++) {
            if (ded[u] < 0) continue;
            const u64 holes = ~paper[ded[u]].opaque, gh = holes & gmask, hh = holes & hmask;
            if (!gh) continue;
            for (int x = GM; x < (int)paper.size(); x++) {
                if ((x & 15) == 0 && elapsed_sec() > limit) return;
                if (x == ded[u] || col_of[x] == col_of[ded[u]]) continue;
                const auto& pp = paper[x];
                if ((pp.black ^ A[u]) & pp.opaque & hh) continue;
                if (!(pp.opaque & gh)) continue;
                Helper h{x, {}};
                for (int s = 0; s < NS; s++)
                    for (int t = GM; t >= 0; t--) {
                        const u64 y = (display[s] & (prefix[s][t] | ~pp.opaque)) | (pp.black & ~prefix[s][t]);
                        if (!((y ^ A[u]) & gh)) {
                            h.goals.push_back({(uint16_t)s, (uint8_t)t});
                            break;
                        }
                    }
                if (!h.goals.empty()) helper_papers++, helpers[u].push_back(std::move(h));
            }
        }
        ready = true;
    }
    int state(const std::vector<int>& order) const {  // the order of the generic sheets in the stack
        std::vector<int> p;
        for (int k : order)
            if (k < GM) p.push_back(k);
        return comp->order_index(p);
    }
    Pick best(int s, const Helper& h) const {  // the nearest goal (deeper on ties)
        Pick b{h.paper, -1, 0, 255};
        for (auto g : h.goals) {
            const int d = comp->distance(s, g.state);
            if (d < b.distance || (d == b.distance && g.depth > b.depth)) b = {h.paper, g.state, g.depth, d};
        }
        return b;
    }
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
        std::vector<std::pair<int, int>> path;
        if (!future.empty() && holes == (gmask & ~paper[ded[u]].opaque) && !sat[u].empty()) {
            // the satisfying order of least moves, ties broken by the expected moves of the next request
            const int s0 = comparator.order_index(local);
            int best = -1, bd = 1 << 30;
            double bv = 1e18;
            for (int t : sat[u]) {
                const int dd = comparator.distance(s0, t);
                if (dd < bd || (dd == bd && future[t] < bv)) bd = dd, bv = future[t], best = t;
            }
            path = comparator.path(s0, best);
        } else
            path = comparator.plan(local, A[u], holes);
        for (auto [k, d] : path) {
            if (k < 0 || k >= M || d < 0 || d >= M) {
                invalid = true;
                return;
            }
            move(k, offset + d);
            if (invalid) return;
        }
    }

    // Generic look-ahead (from the [ChatGPT] report of hitonanode/ahc074 PR 49): sat[u] lists the
    // orders of the generic sheets that show A_u on the generic holes of its paper, and future[s] is
    // the mean over the targets with generic holes of the least moves from order s to one of theirs
    // (the generic moves of the next such request; the requests in between leave the layer as it is).
    // set_generic goes to a satisfying order of least moves, ties broken by future (init_lookahead;
    // without it, Comparator::plan).
    std::vector<std::vector<int>> sat;
    std::vector<double> future;
    void init_lookahead() {
        const int n = comparator.perms.size();
        sat.assign(P, {});
        future.assign(n, 0.0);
        int cnt = 0;
        for (int u = 0; u < P; u++) {
            const u64 gh = gmask & ~paper[ded[u]].opaque;
            if (!gh) continue;
            sat[u] = comparator.satisfying(A[u], gh);
            if (sat[u].empty()) continue;
            cnt++;
            if (M == 7) {
                // Directed reverse BFS: distance FROM each start TO this target set.
                std::vector<unsigned char> ds(n, 255);
                std::vector<int> queue(n); int head = 0, tail = 0;
                for (int s : sat[u]) ds[s] = 0, queue[tail++] = s;
                while (head < tail) {
                    int s = queue[head++];
                    for (int t : comparator.previous7[s]) if (ds[t] == 255)
                        ds[t] = ds[s] + 1, queue[tail++] = t;
                }
                assert(tail == n);
                for (int s = 0; s < n; s++) future[s] += ds[s];
                continue;
            }
            for (int s = 0; s < n; s++) {
                int m = 255;
                for (int t : sat[u])
                    if ((m = std::min(m, comparator.distance(s, t))) == 0) break;
                future[s] += m;
            }
        }
        if (cnt)
            for (auto& f : future) f /= cnt;
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
    static constexpr double kTopPenalty = 0.35, kEndWeight = 1.0;
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
    // depth (adaptive_insert; mode 1 adds the top penalty); below u's paper if that paper is still in
    // place in the same column (the column is dug for it in this request).
    void return_paper(int x, int u, int mode) {
        const int d = u >= 0 ? ded[u] : -1;
        adaptive_insert(x, u, d >= 0 && d != x && col_of[d] == col_of[x] && in_column(d, col_of[x]) ? d : -1, mode);
    }
    // Returns the fillers olds to their columns (return_paper), each time the last one in the list
    // that is visible (from solutions/gpt6pro-10-01-filler-chain): fillers may hide each other
    // (fillers_reachable), and an invisible paper cannot move. The order is the reverse list order
    // when nothing is hidden. Invalid if at some point none of the fillers left is visible.
    void return_visible_fillers(const std::vector<Filler>& olds, int u, int mode) {
        std::vector<char> done(olds.size(), 0);
        for (int left = olds.size(); left > 0; left--) {
            int chosen = -1;
            for (int i = (int)olds.size() - 1; i >= 0; i--)
                if (!done[i] && visible(olds[i].paper)) {
                    chosen = i;
                    break;
                }
            if (chosen < 0) {
                invalid = true;
                return;
            }
            done[chosen] = 1;
            return_paper(olds[chosen].paper, u, mode);
            if (invalid) return;
        }
    }

    // ------------------------------------------------------------------------------------------
    // Plans of a request

    // Options of a plan (process tries the combinations):
    //   ret_mode   the previous lifted paper: 1 / 2 back to its column (with / without the top
    //              penalty), 3 re-used as a filler, 4 left in place under the new paper (a filler of
    //              level 0);
    //   fret_mode  the old fillers: 0 / 1 all back (without / with the top penalty), 4 moved to a new
    //              level if they save at least 2 digs, else left in place if harmless, else back
    //              (refill_or_return), 5 everything chosen by one interval DP (run_joint);
    //   use_filler new fillers from the column tops (choose_fillers_prelift).
    struct PlanOpt {
        int ret_mode = 0;
        int fret_mode = 0;
        bool use_filler = false;
    };
    struct FillerPick {
        int c = -1, depth = 0, lvl = 0;
        bool post = false;
        int chain_id = -1, chain_rank = -1;  // a paper of chain placement_chains[chain_id] at rank (0: top)
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
    // their new level if that saves at least 2 digs (no move if they already sit at that level); the
    // others stay where they are when they do not hide D's column top and show A_u on the holes they
    // cover; the rest go back to their columns (with the top penalty). `placed` holds the fillers of
    // this request so far.
    // The old fillers are taken from the top of the stack down (fillers may hide each other); one
    // left in place need not be visible (fillers_reachable checks at the end that all the fillers can
    // still be removed one by one).
    void refill_or_return(int u, std::vector<Filler> olds, u64& pre_cov, std::vector<Filler>& placed) {
        int d = ded[u];
        std::sort(olds.begin(), olds.end(),
                  [&](const Filler& a, const Filler& b) { return index_of(a.paper) > index_of(b.paper); });
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
            if (!use && d >= 0 && x != d) {
                int L = olds[i].lvl, l = col_of[d];
                bool harm = (L <= l && l <= cf && (paper[x].opaque >> handle[l] & 1)) || reaches_deeper(L, cf, placed);
                u64 hcov = 0;
                for (int j = L; j <= cf; j++) hcov |= 1ULL << handle[j];
                hcov &= paper[x].opaque & hmask & ~paper[d].opaque & ~pre_cov;
                if ((paper[x].black ^ A[u]) & hcov || gen_harm(x, d, u)) harm = true;
                if (!harm) {
                    drop_filler(x);
                    placed.push_back(olds[i]);
                    pre_cov |= hcov;
                    continue;
                }
            }
            if (!use) {
                return_paper(x, u, 1);
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
        // the visible ones first, each time the last visible one in the list (a filler may be hidden
        // by another one, visible once that one is back)
        for (;;) {
            int chosen = -1;
            for (int i = (int)olds.size() - 1; i >= 0; i--)
                if (old_dec[i] == 0 && !done[i] && visible(olds[i].paper)) {
                    chosen = i;
                    break;
                }
            if (chosen < 0) break;
            return_paper(olds[chosen].paper, u, 1);
            done[chosen] = 1;
            if (invalid) return;
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
            if (old_dec[i] == 0 && !done[i]) return_paper(olds[i].paper, u, 1);
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
        u64 pre_cov = 0;
        int stay = -1;
        if (opt.ret_mode == 4) {
            int d = ded[u];
            if (top_d < 0 || d == top_d || (gmask & ~paper[d].opaque & paper[top_d].opaque)) {
                invalid = true;
                return;
            }
            stay = top_d;
            top_d = -1;
        }
        if (top_d >= 0 && opt.ret_mode == 3) {
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
                if (opt.fret_mode == 4)
                    refill_or_return(u, olds, pre_cov, placed);
                else
                    return_visible_fillers(olds, u, opt.fret_mode);
            };
            put_back(vis_old);
            move_to_level(x, lvl);
            top_d = -1;
            put_back(def_old);
            for (auto& f : placed) fillers.push_back(f);
        } else {
            if (top_d >= 0) return_paper(top_d, u, opt.ret_mode);
            if (opt.fret_mode == 4) {
                std::vector<Filler> olds = fillers, placed;
                refill_or_return(u, olds, pre_cov, placed);
                for (auto& f : placed) fillers.push_back(f);
            } else {
                const auto olds = fillers;
                return_visible_fillers(olds, u, opt.fret_mode);
            }
        }
        if (stay >= 0) {
            fillers.push_back({stay, 0, col_of[stay]});
            pre_cov |= shown_by(fillers.back());
        }
        if (!tail_cache_on || invalid) {
            run_plan_tail(u, opt, pre_cov);
            return;
        }
        // the rest of the plan depends only on the state reached and on (pre_cov, use_filler)
        u64 h = 1469598103934665603ULL ^ pre_cov ^ (u64(opt.use_filler) << 2) ^ (u64(top_d + 1) << 3);
        for (int k : order) h = (h ^ u64(k)) * 1099511628211ULL;
        for (const auto& f : fillers) h = (h ^ u64(f.paper * 4096 + f.lvl * 64 + f.hi)) * 1099511628211ULL;
        for (const auto& e : tail_cache)
            if (e.hash == h && e.pre_cov == pre_cov && e.use_filler == opt.use_filler &&
                e.top_d == top_d && e.order == order && same_fillers(e.fillers, fillers)) {
                tail_hits++;
                order = e.out_order;
                top_d = e.out_top;
                fillers = e.out_fillers;
                ops.insert(ops.end(), e.out_ops.begin(), e.out_ops.end());
                invalid = e.out_invalid;
                return;
            }
        TailEntry e{h, order, top_d, fillers, pre_cov, opt.use_filler, {}, -1, {}, {}, false};
        const size_t prefix = ops.size();
        run_plan_tail(u, opt, pre_cov);
        e.out_order = order;
        e.out_top = top_d;
        e.out_fillers = fillers;
        e.out_ops.assign(ops.begin() + prefix, ops.end());
        e.out_invalid = invalid;
        tail_cache.push_back(std::move(e));
    }
    // Plans that reach the same state after their first part (the previous lifted paper and the old
    // fillers handled) share the rest (from solutions/gpt6pro-06-02-regroup): while process tries
    // the plan options (tail_cache_on), the result of run_plan_tail is kept per request and re-used
    // (the same moves appended, the same state). The output is unchanged.
    struct TailEntry {
        u64 hash;
        std::vector<int> order;
        int top_d;
        std::vector<Filler> fillers;
        u64 pre_cov;
        bool use_filler;
        std::vector<int> out_order;
        int out_top;
        std::vector<Filler> out_fillers;
        std::vector<std::pair<int, int>> out_ops;
        bool out_invalid;
    };
    std::vector<TailEntry> tail_cache;
    bool tail_cache_on = false;
    long long tail_hits = 0;
    static bool same_fillers(const std::vector<Filler>& a, const std::vector<Filler>& b) {
        if (a.size() != b.size()) return false;
        for (size_t i = 0; i < a.size(); i++)
            if (a[i].paper != b[i].paper || a[i].lvl != b[i].lvl || a[i].hi != b[i].hi) return false;
        return true;
    }
    // The second part of run_plan: the generic layer, the new fillers, the lift of D and the digs of
    // the handle holes left.
    void run_plan_tail(int u, const PlanOpt& opt, u64 pre_cov) {
        const int d = ded[u];
        const u64 holes = (gmask | hmask) & ~paper[d].opaque;
        set_generic(u, holes);
        u64 hh = holes & ~gmask & ~pre_cov;
        if (opt.use_filler) {
            auto picks = choose_fillers_prelift(u, d, hh);
            // the chain search picked no chain: the same plan as without it (process has it already)
            if (beam_enabled && placement_chains.empty()) {
                invalid = true;
                return;
            }
            for (auto& pk : picks)
                if (!pk.post) place_picked_filler(pk, hh);
            lift(d);
            for (auto& pk : picks)
                if (pk.post) place_picked_filler(pk, hh);
        } else
            lift(d);
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
    // With beam_enabled, chains of up to 4 papers (append_wide_chains) are candidates too.
    std::vector<FillerPick> choose_fillers_prelift(int u, int d, u64 hh) {
        placement_chains.clear();
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
        std::vector<std::vector<FillerPick>> wide_chains;
        if (beam_enabled) append_wide_chains(u, d, hh, fix, cand, wide_chains);
        std::vector<FillerPick> res;
        for (auto& cd : best_intervals(cand)) {
            if (cd.kind == 7) {
                // a chain: its papers taken in increasing column order (res is reversed below), each
                // placed at its rank among those of the chain already placed (place_picked_filler)
                auto chain = wide_chains[cd.idx];
                const int chain_id = placement_chains.size();
                placement_chains.emplace_back(chain.size(), -1);
                for (int i = 0; i < (int)chain.size(); i++) chain[i].chain_id = chain_id, chain[i].chain_rank = i;
                std::sort(chain.begin(), chain.end(), [](const FillerPick& a, const FillerPick& b) { return a.c > b.c; });
                for (const auto& pick : chain) res.push_back(pick);
            } else if (cd.depth < 0) {
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

    // Chains of fillers (from solutions/gpt6pro-10-01-filler-chain): up to kChainLength papers of
    // distinct columns (at most kChainDepth deep in their column) stacked at one level, the first of
    // the path on top. Walking down the path, the opaque handles O of the papers so far and the
    // wrong ones B (shown with a color other than A_u on a hole of D, not masked by a paper above)
    // are updated; the level is just past the deepest wrong handle and must not exceed the least
    // column. The gain is the digs (fix) of the holes of D covered from the level on, less 1 + depth
    // per paper; a beam of kBeamWidth paths per length, pruned when the cost reaches the digs left
    // from the level on (suffixFix: an upper bound of the saving). A chain is an interval candidate
    // [level, deepest column] (kind 7, idx: its index in chains). Papers of columns deeper than D's
    // are placed after the lift (D must not cover their handle, or their column top is hidden).
    static constexpr int kChainDepth = 2, kChainLength = 4, kBeamWidth = 24;
    long long chain_trials = 0, chain_selected = 0, chain_papers = 0;
    bool beam_enabled = false;                       // choose_fillers_prelift searches chains
    std::vector<std::vector<int>> placement_chains;  // per chain of the plan: the paper placed at each rank
    void append_wide_chains(int u, int d, u64 hh, const std::vector<int>& fix, std::vector<std::vector<Cand>>& cand,
                            std::vector<std::vector<FillerPick>>& chains) const {
        const int totalFix = std::accumulate(fix.begin(), fix.end(), 0);
        if (totalFix < 3) return;
        std::vector<int> suffixFix(H + 1, 0);
        for (int j = H - 1; j >= 0; j--) suffixFix[j] = suffixFix[j + 1] + fix[j];
        struct PC {
            int c, depth;
            u64 opaque, bad;  // by handle index
        };
        const int l = col_of[d];
        const u64 hh_i = handle_bits(hh), au_i = handle_bits(A[u]);
        u64 covered = 0;
        for (const auto& f : fillers) covered |= shown_by(f);
        std::vector<PC> pool;
        std::vector<int> top;
        for (int c = 0; c < H; c++) {
            if (c == l || (covered >> handle[c] & 1)) continue;
            column_tops(c, std::min(kFillerDepth, kChainDepth) + 1, top);
            for (int depth = 0; depth < (int)top.size(); depth++) {
                const int k = top[depth];
                pool.push_back({c, depth, h_opq[k], h_opq[k] & hh_i & (h_blk[k] ^ au_i)});
            }
        }
        struct BeamState {
            std::array<int, kChainLength> path{};
            int length = 0, minc = 0, maxc = 0, cost = 0, level = 0, gain = 0;
            u64 opaque = 0, bad = 0;
        };
        auto evaluate = [&](BeamState& b) {
            if (b.cost >= totalFix) return false;
            b.level = b.bad ? 64 - __builtin_clzll(b.bad) : 0;
            if (b.level > b.minc || reaches_deeper(b.level, b.maxc, fillers)) return false;
            if (b.cost >= suffixFix[b.level]) return false;
            int saved = 0;
            for (u64 x = b.opaque & hh_i & ~low_bits(b.level); x; x &= x - 1) saved += fix[__builtin_ctzll(x)];
            b.gain = saved - b.cost;
            return true;
        };
        auto add = [&](const BeamState& b) {
            if (b.gain <= 0) return;
            std::vector<FillerPick> chain;
            for (int j = 0; j < b.length; j++) {
                const auto& p = pool[b.path[j]];
                const bool post = p.c > l;
                if (post && (paper[d].opaque >> handle[p.c] & 1)) return;
                chain.push_back({p.c, p.depth, b.level, post});
            }
            const int index = chains.size();
            chains.push_back(std::move(chain));
            cand[b.maxc].push_back({b.level, double(b.gain), b.maxc, 0, 7, index});
        };
        std::vector<BeamState> current;
        for (int i = 0; i < (int)pool.size(); i++) {
            const auto& p = pool[i];
            BeamState b;
            b.path[0] = i;
            b.length = 1;
            b.minc = b.maxc = p.c;
            b.cost = kFillerCost + p.depth;
            b.opaque = p.opaque;
            b.bad = p.bad;
            if (evaluate(b)) current.push_back(b);
        }
        for (int length = 2; length <= std::min(kChainLength, totalFix - 1); length++) {
            std::vector<BeamState> next;
            for (const auto& b : current) {
                for (int i = 0; i < (int)pool.size(); i++) {
                    const auto& p = pool[i];
                    if (b.cost + kFillerCost + p.depth >= suffixFix[b.level]) continue;
                    bool duplicate_column = false;
                    for (int j = 0; j < b.length; j++)
                        if (pool[b.path[j]].c == p.c) duplicate_column = true;
                    if (duplicate_column) continue;
                    BeamState nb = b;
                    nb.path[nb.length++] = i;
                    nb.minc = std::min(nb.minc, p.c);
                    nb.maxc = std::max(nb.maxc, p.c);
                    nb.cost += kFillerCost + p.depth;
                    nb.bad |= p.bad & ~b.opaque;
                    nb.opaque |= p.opaque;
                    if (!evaluate(nb)) continue;
                    add(nb);
                    next.push_back(nb);
                }
            }
            std::sort(next.begin(), next.end(), [](const BeamState& a, const BeamState& b) { return a.gain > b.gain; });
            if ((int)next.size() > kBeamWidth) next.resize(kBeamWidth);
            current = std::move(next);
        }
    }
    // place_filler, and for a paper of a chain: just above the nearest paper of the chain below it
    // that is placed already, else just below the nearest one above it, else at the level.
    void place_picked_filler(const FillerPick& pick, u64& hh) {
        if (pick.chain_id < 0) {
            place_filler(pick.c, pick.depth, pick.lvl, hh);
            return;
        }
        std::vector<int> top;
        column_tops(pick.c, pick.depth + 1, top);
        if (pick.depth < 0 || pick.depth >= (int)top.size()) {
            invalid = true;
            return;
        }
        const int x = top[pick.depth];
        for (int it = 0; column_top(pick.c) != x; it++) {
            if (it >= K || invalid) {
                invalid = true;
                return;
            }
            dig(pick.c, x);
        }
        auto& placed = placement_chains[pick.chain_id];
        int successor = -1, predecessor = -1;
        for (int i = pick.chain_rank + 1; i < (int)placed.size(); i++)
            if (placed[i] >= 0) {
                successor = placed[i];
                break;
            }
        for (int i = pick.chain_rank - 1; i >= 0; i--)
            if (placed[i] >= 0) {
                predecessor = placed[i];
                break;
            }
        if (successor >= 0) {
            const int from = index_of(x), to = index_of(successor);
            move(x, from < to ? to - 1 : to);
        } else if (predecessor >= 0) {
            move_after(x, predecessor);
        } else {
            move_to_level(x, pick.lvl);
        }
        placed[pick.chain_rank] = x;
        fillers.push_back({x, pick.lvl, pick.c});
        hh &= ~shown_by(fillers.back());
    }

    // The fillers can be removed one by one with the lifted paper set aside (it goes back first at
    // the next request): each time one of those left is visible once the removed ones are gone
    // (from solutions/gpt6pro-10-01-filler-chain; fillers may hide each other). Removing a paper
    // never hides another, so taking any visible one (here the topmost) decides it.
    bool fillers_reachable() const {
        std::array<bool, K> removed{}, pending{};
        if (top_d >= 0) removed[top_d] = true;
        for (const auto& f : fillers) {
            if (pending[f.paper]) return false;
            pending[f.paper] = true;
        }
        for (int left = fillers.size(); left > 0; left--) {
            int chosen = -1;
            u64 covered = 0;
            for (int k : order) {
                if (removed[k]) continue;
                if (pending[k] && (paper[k].opaque & ~covered)) {
                    chosen = k;
                    break;
                }
                covered |= paper[k].opaque;
            }
            if (chosen < 0) return false;
            removed[chosen] = true;
            pending[chosen] = false;
        }
        return true;
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
    static constexpr double kFillerCharge = 0.6;
    // Helper plans (Interleave; from solutions/gpt6pro-08-01-colswap), tried after the plan options
    // from the state with the lifted paper and the old fillers back in their columns (the generic
    // layer then on top): the generic sheets go to a goal order (Interleave::path), the helper is dug
    // out of its column and inserted at the goal depth of the layer (a filler of level 0), D is
    // lifted, and the remaining handle holes are covered as in run_plan (fillers of the interval DP,
    // digs). A pair of helpers x (upper) and y (lower, of a deeper column) inserted at depths tu <= tl
    // of the same goal order: best_interleave_pair (goals of distance < limit, the nearest first).
    std::shared_ptr<Interleave> interleave;
    long long interleave_trials = 0, interleave_selected = 0;
    struct PairHelperPick {
        int upper, lower, goal, tu, tl, distance;
    };
    PairHelperPick best_interleave_pair(int source, int u, int x, int y, int limit) const {
        const u64 gh = gmask & ~paper[ded[u]].opaque;
        for (int distance = 0; distance < limit; distance++)
            for (int state = 0; state < (int)comparator.perms.size(); state++) {
                if (comparator.distance(source, state) != distance) continue;
                for (int tl = M; tl >= 0; tl--) {
                    const u64 py = interleave->prefix[state][tl];
                    const u64 b = (interleave->display[state] & (py | ~paper[y].opaque)) | (paper[y].black & ~py);
                    for (int tu = tl; tu >= 0; tu--) {
                        const u64 px = interleave->prefix[state][tu];
                        const u64 z = (b & (px | ~paper[x].opaque)) | (paper[x].black & ~px);
                        if (!((z ^ A[u]) & gh)) return {x, y, state, tu, tl, distance};
                    }
                }
            }
        return {x, y, -1, 0, 0, limit};
    }
    // The remaining handle holes hh (not shown by the helpers): fillers of the interval DP and digs.
    void finish_handles(int u, int d, u64 hh) {
        for (auto& pk : choose_fillers_dp(u, d, hh)) {
            if ((int)fillers.size() >= kMaxFillers) break;
            place_filler(pk.c, pk.depth, pk.lvl, hh);
        }
        fix_handles(u, hh);
    }
    void run_interleave(int u, const Interleave::Pick& pk) {
        const int d = ded[u], c = col_of[pk.paper], l = col_of[d];
        const int s = interleave->state(order);
        for (auto [k, depth] : comparator.path(s, pk.goal)) move(k, depth);
        auto get_helper = [&](bool after_target) {
            for (int it = 0; column_top(c) != pk.paper; it++) {
                if (it >= K || invalid) {
                    invalid = true;
                    return;
                }
                dig(c, pk.paper);
            }
            move(pk.paper, pk.depth + (after_target ? 1 : 0));
            fillers.push_back({pk.paper, 0, c});
        };
        if (c < l) get_helper(false);  // digging a shallower column first does not hide D's column
        lift(d);
        if (c > l) get_helper(true);
        if (invalid) return;
        finish_handles(u, d, hmask & ~paper[d].opaque & ~paper[pk.paper].opaque);
    }
    void run_interleave_pair(int u, const PairHelperPick& pk) {
        const int d = ded[u], l = col_of[d];
        const int s = interleave->state(order);
        for (auto [k, depth] : comparator.path(s, pk.goal)) move(k, depth);
        int placed = 0;
        bool lifted = false;
        auto get = [&](int x, int depth) {
            const int c = col_of[x];
            if (c > l && !lifted) lift(d), lifted = true;
            for (int it = 0; column_top(c) != x; it++) {
                if (it >= K || invalid) {
                    invalid = true;
                    return;
                }
                dig(c, x);
            }
            move(x, depth + placed + (lifted ? 1 : 0));
            fillers.push_back({x, 0, c});
            placed++;
        };
        get(pk.upper, pk.tu);
        get(pk.lower, pk.tl);
        if (!lifted) lift(d);
        if (invalid) return;
        finish_handles(u, d, hmask & ~paper[d].opaque & ~paper[pk.upper].opaque & ~paper[pk.lower].opaque);
    }
    // The helper plans of request u from st0 (cost as in process); updates best / best_ops / best_state.
    template <class Keep>
    void try_helpers(int u, const State& st0, Keep keep) {
        const int d = ded[u];
        restore(st0);
        ops.clear();
        invalid = false;
        if (top_d >= 0) return_paper(top_d, u, 1);
        const auto olds = fillers;
        return_visible_fillers(olds, u, 1);
        if (invalid) return;
        for (int i = 0; i < M; i++)
            if (order[i] >= M) return;
        const State clean = save();
        const auto clean_ops = ops;
        const int s = interleave->state(order);
        std::vector<int> current(order.begin(), order.begin() + M);
        const int base_generic = comparator.plan(current, A[u], ~paper[d].opaque & gmask).size();
        const auto fixes = fix_costs(u, ~paper[d].opaque & hmask);
        // single helpers: at most 5 deep in their column, fewer generic moves than without; the 4 of
        // least distance + depth + 1.8 + digs of the handle holes they do not cover
        std::vector<std::pair<double, Interleave::Pick>> picks;
        for (const auto& h : interleave->helpers[u]) {
            const int dep = depth_in_column(h.paper);
            if (dep < 0 || dep > 5) continue;
            auto pk = interleave->best(s, h);
            if (pk.distance >= base_generic) continue;
            double score = pk.distance + dep + 1.8;
            for (int c = 0; c < H; c++)
                if (!(paper[h.paper].opaque >> handle[c] & 1)) score += fixes[c];
            picks.push_back({score, pk});
        }
        std::sort(picks.begin(), picks.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
        if (picks.size() > 4) picks.resize(4);
        // pairs: a helper x at most 3 deep and a paper y of a deeper column (not D's) at most 3 deep
        // that is right on the handle holes of D that x leaves; the 12 of least estimate, then the 4
        // of least estimate + distance
        struct PP {
            double estimate;
            int x, y;
        };
        std::vector<PP> pairs;
        std::vector<int> available, depths(K, -1), ranks(H, 0);
        for (int k : order)
            if (col_of[k] >= 0 && in_column(k, col_of[k])) {
                const int c = col_of[k];
                depths[k] = ranks[c]++;
                if (k != d && c != col_of[d] && depths[k] <= 3) available.push_back(k);
            }
        const u64 hh = ~paper[d].opaque & hmask;
        for (const auto& h : interleave->helpers[u]) {
            const int x = h.paper;
            if (depths[x] < 0 || depths[x] > 3) continue;
            for (int y : available) {
                if (col_of[y] <= col_of[x]) continue;
                if ((paper[y].black ^ A[u]) & paper[y].opaque & hh & ~paper[x].opaque) continue;
                double estimate = depths[x] + depths[y] + 3.6;
                for (int c = 0; c < H; c++)
                    if (!((paper[x].opaque | paper[y].opaque) >> handle[c] & 1)) estimate += fixes[c];
                pairs.push_back({estimate, x, y});
            }
        }
        std::sort(pairs.begin(), pairs.end(), [](const PP& a, const PP& b) { return a.estimate < b.estimate; });
        if (pairs.size() > 12) pairs.resize(12);
        std::vector<std::pair<double, PairHelperPick>> pair_picks;
        for (auto pp : pairs) {
            auto pk = best_interleave_pair(s, u, pp.x, pp.y, base_generic);
            if (pk.goal >= 0) pair_picks.push_back({pp.estimate + pk.distance, pk});
        }
        std::sort(pair_picks.begin(), pair_picks.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
        if (pair_picks.size() > 4) pair_picks.resize(4);
        auto finish = [&]() {
            if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) return;
            keep(ops.size() + kFillerCharge * fillers.size() + kEndWeight * adaptive_next_cost());
        };
        for (const auto& item : pair_picks) {
            restore(clean);
            ops = clean_ops;
            invalid = false;
            interleave_trials++;
            run_interleave_pair(u, item.second);
            finish();
        }
        for (const auto& item : picks) {
            restore(clean);
            ops = clean_ops;
            invalid = false;
            interleave_trials++;
            run_interleave(u, item.second);
            finish();
        }
    }

    // Post-processing of the chosen plan (from solutions/gpt6pro-07-02-replace): the plan is a list
    // of edits "paper k goes just below paper anchor" (anchor -1: the top), replayed from the start
    // with the depths recomputed. A request only needs the display A_u, not one final order, so an
    // edited list is kept when every move is legal (the paper is visible), the display is A_u, the
    // fillers are reachable (after canonicalize; the generic sheets may be split by column papers,
    // fillers of level 0 that the next request returns before it orders the generic sheets) and the
    // cost of process (moves + kFillerCharge fillers + kEndWeight adaptive_next_cost) decreases.
    // Edits tried: delete one edit (repeated), and move the anchor of an old filler / the old lifted
    // paper / a paper moved twice.
    long long post_saved = 0;
    std::vector<std::pair<int, int>> post_optimize(const State& initial, std::vector<std::pair<int, int>> input_ops,
                                                   int u) {
        if (input_ops.empty()) return input_ops;
        struct Edit {
            int paper, anchor;
        };
        auto anchorize = [&](const std::vector<std::pair<int, int>>& path) {
            std::vector<int> ord = initial.order;
            std::vector<Edit> edits;
            edits.reserve(path.size());
            for (auto [k, d] : path) {
                ord.erase(std::find(ord.begin(), ord.end(), k));
                edits.push_back({k, d ? ord[d - 1] : -1});
                ord.insert(ord.begin() + d, k);
            }
            return edits;
        };
        auto edits = anchorize(input_ops);
        std::array<bool, K> initial_extra{};  // the old lifted paper and old fillers
        if (initial.top_d >= 0) initial_extra[initial.top_d] = true;
        for (const auto& f : initial.fillers) initial_extra[f.paper] = true;
        // Every candidate rebuilds its records from the same saved state (canonicalize keeps the
        // priority of the fillers listed there).
        const State seed = save();
        State best_state = seed;
        auto best_ops = input_ops;
        auto score = [&](size_t count) {
            return count + kFillerCharge * fillers.size() + kEndWeight * adaptive_next_cost();
        };
        double best_score = score(best_ops.size());
        // Keeps the trial if valid and better (best_ops / best_state / best_score). No-op edits are
        // dropped.
        auto evaluate = [&](const std::vector<Edit>& trial) {
            std::vector<int> ord = initial.order;
            std::vector<std::pair<int, int>> path;
            for (auto [k, a] : trial) {
                if (a == k) return false;
                const int p = int(std::find(ord.begin(), ord.end(), k) - ord.begin());
                int dest = a < 0 ? 0 : int(std::find(ord.begin(), ord.end(), a) - ord.begin()) + 1;
                if (p < dest) dest--;
                if (p == dest) continue;
                u64 covered = 0;
                for (int i = 0; i < p; i++) covered |= paper[ord[i]].opaque;
                if (!(paper[k].opaque & ~covered)) return false;
                ord.erase(ord.begin() + p);
                ord.insert(ord.begin() + dest, k);
                path.push_back({k, dest});
            }
            u64 covered = 0, shown = 0;
            for (int k : ord) {
                shown |= paper[k].black & ~covered;
                covered |= paper[k].opaque;
            }
            if (shown != A[u]) return false;
            restore(seed);
            order = std::move(ord);
            canonicalize();
            if (!fillers_reachable()) return false;
            const double value = score(path.size());
            if (value + 1e-8 >= best_score) return false;
            best_score = value;
            best_ops = std::move(path);
            best_state = save();
            return true;
        };
        auto delete_singles = [&]() {
            bool any = false;
            for (int i = int(edits.size()) - 1; i >= 0; i--) {
                auto trial = edits;
                trial.erase(trial.begin() + i);
                if (evaluate(trial)) {
                    edits = anchorize(best_ops);
                    any = true;
                    i = std::min(i, int(edits.size()));  // other edits may have become no-ops
                }
            }
            return any;
        };
        for (int pass = 0; pass < 3; pass++)
            if (!delete_singles()) break;
        // Other anchors for an old lifted paper / old filler / a paper moved twice: the top, around
        // the papers of its column and the column boundaries (column papers), or around the other
        // papers out of the columns (a generic sheet).
        for (int i = int(edits.size()) - 1; i >= 0; i--) {
            const int k = edits[i].paper;
            if (!initial_extra[k]) {
                int repeats = 0;
                for (const auto& e : edits) repeats += e.paper == k;
                if (repeats < 2) continue;
            }
            std::vector<int> ord = initial.order;
            for (int t = 0; t < i; t++) {
                auto [x, a] = edits[t];
                ord.erase(std::find(ord.begin(), ord.end(), x));
                const int d = a < 0 ? 0 : int(std::find(ord.begin(), ord.end(), a) - ord.begin()) + 1;
                ord.insert(ord.begin() + d, x);
            }
            std::vector<int> anchors{-1};
            auto add = [&](int a) {
                if (a != k && std::find(anchors.begin(), anchors.end(), a) == anchors.end()) anchors.push_back(a);
            };
            int last = -1;
            std::array<bool, 64> seen{};
            for (int x : ord)
                if (x != k) {
                    if (col_of[k] < 0) {
                        if (col_of[x] < 0) add(last), add(x);
                    } else {
                        if (col_of[x] >= 0 && !seen[col_of[x]]) {
                            seen[col_of[x]] = true;
                            if (col_of[x] <= col_of[k]) add(last);
                        }
                        if (col_of[x] == col_of[k]) add(last), add(x);
                        if (col_of[x] < 0) add(x);
                    }
                    last = x;
                }
            for (int t = i + 1; t < int(edits.size()); t++)
                if (edits[t].paper == k) add(edits[t].anchor);
            auto chosen = edits;
            for (int a : anchors) {
                if (a == edits[i].anchor) continue;
                auto trial = edits;
                trial[i].anchor = a;
                if (evaluate(trial)) chosen = anchorize(best_ops);
            }
            edits = std::move(chosen);
            i = std::min(i, int(edits.size()));
        }
        delete_singles();
        post_saved += int(input_ops.size()) - int(best_ops.size());
        restore(best_state);
        return best_ops;
    }
    // The moves for request u: every combination of the plan options simulated on a copy of the
    // state, the cheapest valid one kept (display A_u, at most 2K moves, fillers reachable), and the
    // best plan without the joint choice again with the chain search (append_wide_chains). In
    // fast_mode, or when no plan is valid, the plain plan; if it is not legal either (it would move
    // an invisible paper, or more than 2K moves: fillers may hide each other), the full search, and
    // as the last resort no move at all (a wrong display, never an illegal output).
    long long unsafe_plans = 0;
    std::vector<std::pair<int, int>> process(int u) {
        init_adaptive();
        adaptive_request = u;
        const State st0 = save();
        if (fast_mode) {
            fast_requests++;
            ops.clear();
            invalid = false;
            check_vis = true;
            run_plan(u, PlanOpt{});
            check_vis = false;
            if (!invalid && ops.size() <= 2 * K) {
                canonicalize();
                return ops;
            }
            unsafe_plans++;
            restore(st0);
        }
        const int top0 = top_d, d = ded[u];
        const bool prev_ok = top0 >= 0 && d >= 0 && d != top0;
        // without old fillers, their options are all the same
        const bool any_out = !fillers.empty();
        const std::vector<int> fms = any_out ? std::vector<int>{1, 4} : std::vector<int>{1};
        std::vector<PlanOpt> opts;
        for (int rm = 1; rm <= (prev_ok ? 3 : 2); rm++)
            for (int fm : fms) opts.push_back({rm, fm, true});
        if (d != top0)
            for (int rm = 1; rm <= 2; rm++) opts.push_back({rm, 5, true});
        if (prev_ok)
            for (int fm : fms) opts.push_back({4, fm, true});
        double best = 1e18, best_normal = 1e18;
        std::vector<std::pair<int, int>> best_ops;
        State best_state;
        PlanOpt best_normal_opt;
        check_vis = true;
        tail_cache.clear();
        tail_cache_on = true;
        for (const PlanOpt& o : opts) {
            restore(st0);
            ops.clear();
            invalid = false;
            run_plan(u, o);
            if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) continue;
            double future = kEndWeight * adaptive_next_cost();
            double cost = ops.size() + kFillerCharge * fillers.size() + future;
            if (cost < best) best = cost, best_ops = ops, best_state = save();
            if (o.fret_mode != 5 && cost < best_normal) best_normal = cost, best_normal_opt = o;
        }
        tail_cache_on = false;
        int source = 0, chain_count = 0;  // the plan kept: 0 the options, 1 the chain search, 2 helpers
        if (best_normal < 1e17) {
            restore(st0);
            ops.clear();
            invalid = false;
            beam_enabled = true;
            run_plan(u, best_normal_opt);
            beam_enabled = false;
            if (!placement_chains.empty()) chain_trials++;
            for (const auto& ch : placement_chains) chain_count += ch.size();
            placement_chains.clear();
            if (!invalid && ops.size() <= 2 * K && display() == A[u] && fillers_reachable()) {
                double cost = ops.size() + kFillerCharge * fillers.size() + kEndWeight * adaptive_next_cost();
                if (cost < best) best = cost, best_ops = ops, best_state = save(), source = 1;
            }
        }
        if (interleave && interleave->ready && d >= 0 && d != top0 && !interleave->helpers[u].empty()) {
            bool used = false;
            try_helpers(u, st0, [&](double cost) {
                if (cost < best) best = cost, best_ops = ops, best_state = save(), used = true;
            });
            interleave_selected += used;
            if (used) source = 2;
        }
        if (source == 1) chain_selected++, chain_papers += chain_count;
        if (best > 1e17) {
            plan_failures++;
            restore(st0);
            ops.clear();
            invalid = false;
            run_plan(u, PlanOpt{});
            check_vis = false;
            if (invalid || ops.size() > 2 * K) {
                unsafe_plans++;
                restore(st0);
                ops.clear();
            }
            return ops;
        }
        check_vis = false;
        restore(best_state);
        canonicalize();
        return post_optimize(st0, std::move(best_ops), u);
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
    // Window assignment until kMapEnd and its greedy matching climb until kGoptEnd, annealing until
    // kAnnealEnd, climb until kClimbEnd (scaled s).
    constexpr double kMapEnd = 0.50, kGoptEnd = 0.61, kAnnealEnd = 1.305, kClimbEnd = 1.36, kFastAfter = 1.80;
    // A design not initialized by kInitExpiry (or failed after kInitGiveUp) falls back to the emergency design.
    constexpr double kInitGiveUp = 1.30, kInitExpiry = 1.35;
    // The helper tables (Interleave) are left unfinished (no helpers) after kHelperGiveUp.
    constexpr double kHelperGiveUp = 1.55;
    const int map_iters = env_int("MAP_ITERS"), anneal_iters = env_int("ANNEAL_ITERS");
    const int climb_iters = env_int("CLIMB_ITERS");
    std::vector<int> permutation(64);  // original window of each internal window
    #ifndef RESEARCH_G
#define RESEARCH_G 38
#endif
    int M = 7, G = RESEARCH_G;
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
            // the greedy matching climb (until kGoptEnd) on the first assignment only (GOPT_STEPS: fixed
            // steps, -1 none)
            const int gsteps = attempt ? 0 : std::max(0, env_int("GOPT_STEPS"));
            const double gsec = attempt || env_int("GOPT_STEPS") ? 0.0 : std::max(0.0, kGoptEnd - kMapEnd);
            auto ws = assign_windows(A, M, G, comp.edge, comp.polarity, permutation, seconds, map_iters, gsteps, gsec);
            map_total += ws.iterations;
            if (!attempt)
                std::cerr << "gobj_before = " << ws.gobj_before << "\ngobj_after = " << ws.gobj_after
                          << "\ngopt_steps = " << ws.climb_steps << '\n';
        }
        comp.rebuild();
        des = std::make_unique<Design>(A, M, G);
        // gcost: the exact mean number of moves of the generic layer from a uniform order, averaged over
        // the two targets of the pair (gpt6pro-09: the legal distance is not symmetric, and the
        // relations for b are those for a reversed): PosetSums::both_of / 1440 (= the mean of
        // Comparator::mean_moves for a and for b)
        auto estimate = [&](u64 a, u64 b) {
            const auto reach = comp.closure(a, a ^ b);
            u64 r = 0;
            for (int s = 0; s < M; s++) r |= u64(reach[s]) << (8 * s);
            return (Poset7Costs::get().cost(r) - 1) / 10080.0;
        };
        const bool untimed = map_iters > 0;
        if (des->initialize([&](u64 a, u64 b) { return comp.compatible(a, b); }, estimate,
                            [&]() { return !untimed && elapsed_sec() > kInitExpiry; }))
            break;
        if (attempt >= 2 || (!untimed && elapsed_sec() > kInitGiveUp)) return emergency_design(originalA, R);
        G = attempt == 0 ? 32 : 28;
    }
    std::cerr << "map_iters = " << map_total << "\nmap_end_sec = " << elapsed_sec() << '\n';
    if (anneal_iters)
        des->anneal(1e9, anneal_iters);
    else
        des->anneal(std::max(0.005, kAnnealEnd - elapsed_sec()), 0);
    std::cerr << "anneal_iters = " << des->anneal_iters << "\nanneal_end_sec = " << elapsed_sec() << '\n';
    std::cerr << "colswap_tried = " << des->colswap_tried << "\ncolswap_accepted = " << des->colswap_accepted
              << "\nreplace_tried = " << des->replace_tried << "\nreplace_accepted = " << des->replace_accepted
              << '\n';
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
    if (M == Interleave::GM && comp.complete) {
        solver.interleave = std::make_shared<Interleave>();
        solver.comparator.build_tables();
        solver.interleave->init(solver.comparator, papers, A, ded, columns, solver.gmask, solver.hmask, kHelperGiveUp);
        solver.init_lookahead();
    } else if (M == 7 && comp.complete) {
        solver.comparator.build_tables();
        solver.init_lookahead();
    }
    std::cerr << "helper_end_sec = " << elapsed_sec() << '\n';
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
              << "\nfast_requests = " << solver.fast_requests << "\npost_saved = " << solver.post_saved
              << "\nhelper_papers = " << (solver.interleave ? solver.interleave->helper_papers : 0)
              << "\ninterleave_trials = " << solver.interleave_trials
              << "\ninterleave_selected = " << solver.interleave_selected << "\ntail_hits = " << solver.tail_hits
              << "\nchain_trials = " << solver.chain_trials << "\nchain_selected = " << solver.chain_selected
              << "\nchain_papers = " << solver.chain_papers << "\nunsafe_plans = " << solver.unsafe_plans
              << "\nreq_sec = " << req_sec
              << "\nend_sec = " << elapsed_sec() << '\n';
    return 0;
}
