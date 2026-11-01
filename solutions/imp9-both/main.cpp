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
    std::vector<uint8_t> dist;
    int order_index(const std::vector<int>& o) const {
        return int(std::lower_bound(perms.begin(), perms.end(), o) - perms.begin());
    }
    int distance(int a, int b) const { return dist[a * perms.size() + b]; }
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

// Closure of a relation bit matrix of m <= 8 sheets (bit 8a + b: a above b).
u64 closure8(u64 r, int m) {
    for (int k = 0; k < m; k++) r |= ((r >> k) & 0x0101010101010101ULL) * ((r >> (8 * k)) & 255);
    return r;
}
constexpr u64 kDiagonal = 0x8040201008040201ULL;

// The sums of the 720 legal distances (those of Comparator::build_tables: the bottom sheet never
// moves) from every order of the 6 generic sheets to the nearest order satisfying a closed relation
// (bit 8a + b: a above b), i.e. 720 Comparator::mean_moves (gpt6pro-09). The sum does not change when
// the sheets are relabeled, so kPosetClasses lists one closed relation of each of the 318 unlabeled
// partial orders of 6 elements with its sum (computed exhaustively offline; checked equal to
// Comparator::mean_moves); PosetSums expands them to the 130023 labeled ones in a hash table (a few
// ms, once).
struct PosetClass {
    u64 relation;
    int sum;
};
constexpr PosetClass kPosetClasses[318] = {
    {0x0ULL, 0}, {0x10101010100ULL, 600}, {0x10102020000ULL, 960}, {0x10202020000ULL, 900},
    {0x10204000000ULL, 1080}, {0x20202020000ULL, 576}, {0x20404000000ULL, 840}, {0x30102020000ULL, 1020},
    {0x30202020000ULL, 936}, {0x30301020000ULL, 1080}, {0x30302020000ULL, 1056}, {0x30303020000ULL, 1116},
    {0x30303030000ULL, 1152}, {0x30303030100ULL, 1176}, {0x30306020000ULL, 1394}, {0x30404000000ULL, 1000},
    {0x30505010100ULL, 1440}, {0x30506000000ULL, 1380}, {0x30604000000ULL, 1239}, {0x30606020000ULL, 1398},
    {0x30a02010000ULL, 1336}, {0x30a02020000ULL, 1278}, {0x30c00000000ULL, 1120}, {0x30c04000000ULL, 1300},
    {0x40404000000ULL, 540}, {0x40800000000ULL, 720}, {0x50204000000ULL, 1140}, {0x50505010100ULL, 1140},
    {0x50604000000ULL, 1214}, {0x50606000000ULL, 1324}, {0x50901010100ULL, 1320}, {0x50a02010000ULL, 1500},
    {0x60204000000ULL, 954}, {0x60404000000ULL, 892}, {0x60601000000ULL, 1240}, {0x60604000000ULL, 1010},
    {0x60606000000ULL, 1068}, {0x60606020000ULL, 1110}, {0x60800000000ULL, 900}, {0x60a02020000ULL, 1280},
    {0x60c04000000ULL, 1210}, {0x70204000000ULL, 1164}, {0x70303020000ULL, 1406}, {0x70304000000ULL, 1306},
    {0x70305010100ULL, 1524}, {0x70306020000ULL, 1481}, {0x70404000000ULL, 1004}, {0x70505010100ULL, 1452},
    {0x70506000000ULL, 1404}, {0x70604000000ULL, 1250}, {0x70606000000ULL, 1340}, {0x70606020000ULL, 1416},
    {0x70703020000ULL, 1516}, {0x70704000000ULL, 1332}, {0x70705010100ULL, 1560}, {0x70706000000ULL, 1436},
    {0x70706020000ULL, 1520}, {0x70707000000ULL, 1476}, {0x70707010100ULL, 1608}, {0x70707020000ULL, 1566},
    {0x70707030000ULL, 1632}, {0x70707030100ULL, 1680}, {0x70800000000ULL, 960}, {0x70901010100ULL, 1440},
    {0x70a02020000ULL, 1396}, {0x70b01020000ULL, 1558}, {0x70b02020000ULL, 1476}, {0x70b03020000ULL, 1639},
    {0x70b03030000ULL, 1720}, {0x70b03030100ULL, 1800}, {0x70c04000000ULL, 1316}, {0x70d05010100ULL, 1710},
    {0x70e04000000ULL, 1396}, {0x70e06000000ULL, 1544}, {0x70e06020000ULL, 1659}, {0x80800000000ULL, 480},
    {0x90901010100ULL, 1080}, {0xa0a02010000ULL, 1340}, {0xa0a02020000ULL, 1050}, {0xa0c00000000ULL, 1084},
    {0xb0301020000ULL, 1348}, {0xb0302020000ULL, 1308}, {0xb0601020000ULL, 1529}, {0xb0a02010000ULL, 1423},
    {0xb0a02020000ULL, 1316}, {0xb0b01020000ULL, 1458}, {0xb0b02020000ULL, 1402}, {0xb0b03020000ULL, 1514},
    {0xb0b03030000ULL, 1572}, {0xb0b03030100ULL, 1620}, {0xb0c00000000ULL, 1170}, {0xb0d01010100ULL, 1524},
    {0xb0e02020000ULL, 1481}, {0xc0800000000ULL, 810}, {0xc0c00000000ULL, 920}, {0xc0c04000000ULL, 1000},
    {0xd0604000000ULL, 1325}, {0xd0901010100ULL, 1350}, {0xd0d01010100ULL, 1440}, {0xd0d05010100ULL, 1560},
    {0xd0e00000000ULL, 1228}, {0xd0e04000000ULL, 1408}, {0xe0302020000ULL, 1398}, {0xe0304000000ULL, 1379},
    {0xe0604000000ULL, 1241}, {0xe0800000000ULL, 912}, {0xe0a02020000ULL, 1311}, {0xe0c00000000ULL, 1120},
    {0xe0c04000000ULL, 1252}, {0xe0e00000000ULL, 1188}, {0xe0e02020000ULL, 1400}, {0xe0e04000000ULL, 1334},
    {0xe0e06000000ULL, 1440}, {0xe0e06020000ULL, 1520}, {0xf0301020000ULL, 1456}, {0xf0302020000ULL, 1410},
    {0xf0304000000ULL, 1412}, {0xf0604000000ULL, 1340}, {0xf0703020000ULL, 1679}, {0xf0704000000ULL, 1432},
    {0xf0705010100ULL, 1746}, {0xf0706000000ULL, 1580}, {0xf0706020000ULL, 1693}, {0xf0800000000ULL, 966},
    {0xf0901010100ULL, 1452}, {0xf0a02010000ULL, 1568}, {0xf0a02020000ULL, 1411}, {0xf0b01020000ULL, 1603},
    {0xf0b02020000ULL, 1515}, {0xf0b03020000ULL, 1684}, {0xf0b03030000ULL, 1760}, {0xf0b03030100ULL, 1836},
    {0xf0c00000000ULL, 1192}, {0xf0c04000000ULL, 1340}, {0xf0d01010100ULL, 1560}, {0xf0d05010100ULL, 1752},
    {0xf0e00000000ULL, 1260}, {0xf0e02020000ULL, 1518}, {0xf0e04000000ULL, 1440}, {0xf0e06000000ULL, 1592},
    {0xf0e06020000ULL, 1704}, {0xf0f00000000ULL, 1296}, {0xf0f01010100ULL, 1608}, {0xf0f01020000ULL, 1668},
    {0xf0f02020000ULL, 1564}, {0xf0f03020000ULL, 1754}, {0xf0f03030000ULL, 1840}, {0xf0f03030100ULL, 1920},
    {0xf0f04000000ULL, 1484}, {0xf0f05010100ULL, 1824}, {0xf0f06000000ULL, 1652}, {0xf0f06020000ULL, 1770},
    {0xf0f07000000ULL, 1728}, {0xf0f07010100ULL, 1920}, {0xf0f07020000ULL, 1856}, {0xf0f07030000ULL, 1960},
    {0xf0f07030100ULL, 2040}, {0x100000000000ULL, 360}, {0x110101010100ULL, 960}, {0x110102020000ULL, 1220},
    {0x120201020000ULL, 1220}, {0x120202020000ULL, 930}, {0x130102020000ULL, 1232}, {0x130201020000ULL, 1250},
    {0x130202020000ULL, 1050}, {0x130301020000ULL, 1336}, {0x130302020000ULL, 1278}, {0x130303020000ULL, 1394},
    {0x130303030000ULL, 1452}, {0x130303030100ULL, 1500}, {0x130306020000ULL, 1610}, {0x140402000000ULL, 1110},
    {0x140404000000ULL, 880}, {0x150402000000ULL, 1230}, {0x150503010100ULL, 1680}, {0x150505010100ULL, 1440},
    {0x160204000000ULL, 1140}, {0x160404000000ULL, 1000}, {0x160601000000ULL, 1380}, {0x160603020000ULL, 1624},
    {0x160604000000ULL, 1217}, {0x160605000000ULL, 1516}, {0x160606000000ULL, 1324}, {0x160606020000ULL, 1402},
    {0x170204000000ULL, 1242}, {0x170303020000ULL, 1514}, {0x170304000000ULL, 1408}, {0x170305010100ULL, 1710},
    {0x170306020000ULL, 1644}, {0x170404000000ULL, 1060}, {0x170505010100ULL, 1560}, {0x170506000000ULL, 1548},
    {0x170603020000ULL, 1653}, {0x170604000000ULL, 1330}, {0x170606000000ULL, 1436}, {0x170606020000ULL, 1518},
    {0x170703020000ULL, 1694}, {0x170704000000ULL, 1436}, {0x170705010100ULL, 1752}, {0x170706000000ULL, 1592},
    {0x170706020000ULL, 1696}, {0x170707000000ULL, 1644}, {0x170707010100ULL, 1824}, {0x170707020000ULL, 1763},
    {0x170707030000ULL, 1858}, {0x170707030100ULL, 1932}, {0x180000000000ULL, 600}, {0x180800000000ULL, 780},
    {0x190101010100ULL, 1080}, {0x190901010100ULL, 1320}, {0x1a0202010000ULL, 1340}, {0x1a0202020000ULL, 1050},
    {0x1a0a02010000ULL, 1540}, {0x1a0a02020000ULL, 1285}, {0x1b0102020000ULL, 1340}, {0x1b0202010000ULL, 1352},
    {0x1b0202020000ULL, 1110}, {0x1b0301020000ULL, 1456}, {0x1b0302020000ULL, 1398}, {0x1b0303020000ULL, 1514},
    {0x1b0303030000ULL, 1572}, {0x1b0303030100ULL, 1620}, {0x1b0a02010000ULL, 1569}, {0x1b0a02020000ULL, 1401},
    {0x1b0b01020000ULL, 1610}, {0x1b0b02020000ULL, 1517}, {0x1b0b03020000ULL, 1682}, {0x1b0b03030000ULL, 1766},
    {0x1b0b03030100ULL, 1830}, {0x1c0000000000ULL, 660}, {0x1c0404000000ULL, 1000}, {0x1c0800000000ULL, 900},
    {0x1c0c00000000ULL, 1080}, {0x1c0c04000000ULL, 1220}, {0x1d0101010100ULL, 1140}, {0x1d0505010100ULL, 1560},
    {0x1d0901010100ULL, 1440}, {0x1d0d01010100ULL, 1560}, {0x1d0d05010100ULL, 1740}, {0x1e0000000000ULL, 696},
    {0x1e0202020000ULL, 1110}, {0x1e0204000000ULL, 1230}, {0x1e0404000000ULL, 1060}, {0x1e0604000000ULL, 1331},
    {0x1e0606000000ULL, 1440}, {0x1e0606020000ULL, 1520}, {0x1e0800000000ULL, 960}, {0x1e0a02020000ULL, 1401},
    {0x1e0c00000000ULL, 1180}, {0x1e0c04000000ULL, 1330}, {0x1e0e00000000ULL, 1260}, {0x1e0e02020000ULL, 1520},
    {0x1e0e04000000ULL, 1442}, {0x1e0e06000000ULL, 1590}, {0x1e0e06020000ULL, 1695}, {0x1f0000000000ULL, 720},
    {0x1f0101010100ULL, 1176}, {0x1f0102020000ULL, 1400}, {0x1f0202020000ULL, 1146}, {0x1f0204000000ULL, 1290},
    {0x1f0301020000ULL, 1516}, {0x1f0302020000ULL, 1458}, {0x1f0303020000ULL, 1574}, {0x1f0303030000ULL, 1632},
    {0x1f0303030100ULL, 1680}, {0x1f0304000000ULL, 1472}, {0x1f0305010100ULL, 1800}, {0x1f0306020000ULL, 1734},
    {0x1f0404000000ULL, 1096}, {0x1f0505010100ULL, 1620}, {0x1f0506000000ULL, 1626}, {0x1f0604000000ULL, 1388},
    {0x1f0606000000ULL, 1496}, {0x1f0606020000ULL, 1578}, {0x1f0703020000ULL, 1769}, {0x1f0704000000ULL, 1492},
    {0x1f0705010100ULL, 1836}, {0x1f0706000000ULL, 1664}, {0x1f0706020000ULL, 1780}, {0x1f0707000000ULL, 1728},
    {0x1f0707010100ULL, 1920}, {0x1f0707020000ULL, 1856}, {0x1f0707030000ULL, 1960}, {0x1f0707030100ULL, 2040},
    {0x1f0800000000ULL, 996}, {0x1f0901010100ULL, 1500}, {0x1f0a02010000ULL, 1646}, {0x1f0a02020000ULL, 1459},
    {0x1f0b01020000ULL, 1681}, {0x1f0b02020000ULL, 1575}, {0x1f0b03020000ULL, 1762}, {0x1f0b03030000ULL, 1850},
    {0x1f0b03030100ULL, 1926}, {0x1f0c00000000ULL, 1228}, {0x1f0c04000000ULL, 1384}, {0x1f0d01010100ULL, 1620},
    {0x1f0d05010100ULL, 1830}, {0x1f0e00000000ULL, 1302}, {0x1f0e02020000ULL, 1578}, {0x1f0e04000000ULL, 1496},
    {0x1f0e06000000ULL, 1662}, {0x1f0e06020000ULL, 1779}, {0x1f0f00000000ULL, 1344}, {0x1f0f01010100ULL, 1680},
    {0x1f0f01020000ULL, 1764}, {0x1f0f02020000ULL, 1636}, {0x1f0f03020000ULL, 1862}, {0x1f0f03030000ULL, 1960},
    {0x1f0f03030100ULL, 2040}, {0x1f0f04000000ULL, 1552}, {0x1f0f05010100ULL, 1932}, {0x1f0f06000000ULL, 1746},
    {0x1f0f06020000ULL, 1872}, {0x1f0f07000000ULL, 1824}, {0x1f0f07010100ULL, 2040}, {0x1f0f07020000ULL, 1970},
    {0x1f0f07030000ULL, 2098}, {0x1f0f07030100ULL, 2190},
};
// The transpose of a relation bit matrix (8 x 8): "b above a" for "a above b".
u64 transpose8(u64 r) {
    u64 t = (r ^ (r >> 7)) & 0x00AA00AA00AA00AAULL;
    r ^= t ^ (t << 7);
    t = (r ^ (r >> 14)) & 0x0000CCCC0000CCCCULL;
    r ^= t ^ (t << 14);
    t = (r ^ (r >> 28)) & 0x00000000F0F0F0F0ULL;
    r ^= t ^ (t << 28);
    return r;
}
struct PosetSums {
    static constexpr unsigned kSize = 1U << 18;
    static constexpr u64 kEmpty = ~0ULL;
    std::vector<u64> keys;
    std::vector<uint16_t> one, both;  // the sum for the relation; for it plus for its transpose
    static unsigned hash(u64 x) {
        x ^= x >> 27;
        x *= 0x3c79ac492ba7b653ULL;
        x ^= x >> 33;
        return unsigned(x) & (kSize - 1);
    }
    // The slot of a closed acyclic relation of 6 sheets (always present).
    unsigned slot_of(u64 r) const {
        unsigned s = hash(r);
        while (keys[s] != r) {
            assert(keys[s] != kEmpty);
            s = (s + 1) & (kSize - 1);
        }
        return s;
    }
    PosetSums() : keys(kSize, kEmpty), one(kSize), both(kSize) {
        std::array<int, 6> p{0, 1, 2, 3, 4, 5};
        do
            for (const auto& c : kPosetClasses) {
                u64 r = 0;
                for (u64 x = c.relation; x; x &= x - 1) {
                    const int bit = __builtin_ctzll(x);
                    r |= 1ULL << (8 * p[bit >> 3] + p[bit & 7]);
                }
                unsigned s = hash(r);
                while (keys[s] != kEmpty && keys[s] != r) s = (s + 1) & (kSize - 1);
                keys[s] = r;
                one[s] = uint16_t(c.sum);
            }
        while (std::next_permutation(p.begin(), p.end()));
        for (unsigned s = 0; s < kSize; s++)
            if (keys[s] != kEmpty) both[s] = uint16_t(one[s] + one[slot_of(transpose8(keys[s]))]);
    }
    int both_of(u64 closed) const { return both[slot_of(closed)]; }
    static const PosetSums& get() {
        static const PosetSums table;
        return table;
    }
};

// The close pairs of targets of assign_windows, one array per field, padded to a multiple of 4 by
// pairs without differences (no move changes them; they are not counted in n).
struct WindowPairs {
    int n = 0, n4 = 0;
    std::vector<u64> au, diff, dir;  // colors of the first target, differences, relations (bit 8a + b)
    std::vector<double> base, w;     // weight (> 0) if compatible; w = base if compatible, else 0
    std::vector<long long> rel;      // PosetSums::both_of the closure of dir if compatible, else 0
    std::vector<int> u, v;
    void push(u64 au_, u64 diff_, u64 dir_, int u_, int v_, double base_, double w_, long long rel_) {
        au.push_back(au_), diff.push_back(diff_), dir.push_back(dir_), u.push_back(u_), v.push_back(v_);
        base.push_back(base_), w.push_back(w_), rel.push_back(rel_);
        n++;
    }
    void pad() {
        const int real = n;
        while (n % 4) push(0, 0, 0, 0, 0, 1.0, 0.0, 0);
        n4 = n;
        n = real;
    }
};

// AVX2 for one function (the judge compiles with -march=native; the local evaluation without it).
#define AVX2_TARGET __attribute__((target("avx2,popcnt")))
AVX2_TARGET inline __m256i set1_u64(u64 x) { return _mm256_set1_epi64x((long long)x); }
// x != 0 ? f : 0 per lane
AVX2_TARGET inline __m256i pick_nonzero(__m256i x, __m256i f) {
    return _mm256_andnot_si256(_mm256_cmpeq_epi64(x, _mm256_setzero_si256()), f);
}

// One move of assign_windows evaluated on all the pairs, 4 at a time (AVX2). The move leaves the
// windows of the sheet pairs ea, eb as ma, mb (relation bits fa / ra, fb / rb; erase: all four) and
// the colors as pol; a window swap multiplies the base of a pair differing at a only by f0, at b only
// by f2 (other moves: f0 = f2 = 1). New relations: those of dir off ea, eb, and per sheet pair the
// directions of the differences in its windows. New weight: relations unchanged: as before;
// changed: 0 if they hold "a above b" and "b above a" (most pairs), else by the closure (and then
// rel = PosetSums::both_of the closure). A pair that does not differ at a or b comes out unchanged.
// Writes the new values of every pair (ndir, nbase, nw, nrel) and lists the changed pairs
// (relations or base) in order in `changed`. Returns the number of changed pairs.
AVX2_TARGET int evaluate_move(const WindowPairs& P, const PosetSums& sums, u64 pol, u64 erase, u64 ma, u64 mb,
                              u64 fa, u64 ra, u64 fb, u64 rb, int a, int b, double f0, double f2, u64* ndir,
                              double* nbase, double* nw, long long* nrel, int* changed) {
    const __m256i zero = _mm256_setzero_si256(), vpol = set1_u64(pol), vkeep = set1_u64(~erase),
                  vma = set1_u64(ma), vmb = set1_u64(mb), vfa = set1_u64(fa), vra = set1_u64(ra), vfb = set1_u64(fb),
                  vrb = set1_u64(rb), vbita = set1_u64(1ULL << a), vbitb = set1_u64(1ULL << b),
                  c7 = set1_u64(0x00AA00AA00AA00AAULL), c14 = set1_u64(0x0000CCCC0000CCCCULL),
                  c28 = set1_u64(0x00000000F0F0F0F0ULL);
    const __m256d one = _mm256_set1_pd(1.0), vf0 = _mm256_set1_pd(f0), vf2 = _mm256_set1_pd(f2),
                  zd = _mm256_setzero_pd();
    // lanes of each 4-bit mask, packed (the changed pairs of a block)
    static const std::array<std::array<int, 4>, 16> kLanes = [] {
        std::array<std::array<int, 4>, 16> t{};
        for (int s = 0; s < 16; s++)
            for (int l = 0, k = 0; l < 4; l++)
                if (s >> l & 1) t[s][k++] = l;
        return t;
    }();
    const u64 *const pau = P.au.data(), *const pdiff = P.diff.data(), *const pdir = P.dir.data();
    const double *const pbase = P.base.data(), *const pw = P.w.data();
    const long long* const prel = P.rel.data();
    const int n4 = P.n4;
    int nch = 0;
    for (int p = 0; p < n4; p += 4) {
        const __m256i au = _mm256_loadu_si256((const __m256i*)(pau + p));
        const __m256i diff = _mm256_loadu_si256((const __m256i*)(pdiff + p));
        const __m256i dir = _mm256_loadu_si256((const __m256i*)(pdir + p));
        const __m256i z = _mm256_xor_si256(au, vpol);
        const __m256i da = _mm256_and_si256(diff, vma), db = _mm256_and_si256(diff, vmb);
        __m256i r = _mm256_and_si256(dir, vkeep);
        r = _mm256_or_si256(r, pick_nonzero(_mm256_andnot_si256(z, da), vfa));
        r = _mm256_or_si256(r, pick_nonzero(_mm256_and_si256(z, da), vra));
        r = _mm256_or_si256(r, pick_nonzero(_mm256_andnot_si256(z, db), vfb));
        r = _mm256_or_si256(r, pick_nonzero(_mm256_and_si256(z, db), vrb));
        // no difference at a / at b
        const __m256i na = _mm256_cmpeq_epi64(_mm256_and_si256(diff, vbita), zero);
        const __m256i nb = _mm256_cmpeq_epi64(_mm256_and_si256(diff, vbitb), zero);
        const __m256d fa_only = _mm256_castsi256_pd(_mm256_andnot_si256(na, nb));  // differs at a only
        const __m256d fb_only = _mm256_castsi256_pd(_mm256_andnot_si256(nb, na));  // differs at b only
        const __m256d fac = _mm256_blendv_pd(_mm256_blendv_pd(one, vf0, fa_only), vf2, fb_only);
        const __m256d base = _mm256_loadu_pd(pbase + p), w = _mm256_loadu_pd(pw + p);
        const __m256d nbase4 = _mm256_mul_pd(base, fac);
        const __m256i rsame = _mm256_cmpeq_epi64(r, dir);
        const int chg = 15 & ~_mm256_movemask_pd(
                                 _mm256_and_pd(_mm256_castsi256_pd(rsame), _mm256_cmp_pd(nbase4, base, _CMP_EQ_OQ)));
        // "a above b" and "b above a": r & transpose(r) != 0
        __m256i t = _mm256_and_si256(_mm256_xor_si256(r, _mm256_srli_epi64(r, 7)), c7);
        __m256i x = _mm256_xor_si256(r, _mm256_xor_si256(t, _mm256_slli_epi64(t, 7)));
        t = _mm256_and_si256(_mm256_xor_si256(x, _mm256_srli_epi64(x, 14)), c14);
        x = _mm256_xor_si256(x, _mm256_xor_si256(t, _mm256_slli_epi64(t, 14)));
        t = _mm256_and_si256(_mm256_xor_si256(x, _mm256_srli_epi64(x, 28)), c28);
        x = _mm256_xor_si256(x, _mm256_xor_si256(t, _mm256_slli_epi64(t, 28)));
        const __m256i noboth = _mm256_cmpeq_epi64(_mm256_and_si256(r, x), zero);
        const int need = _mm256_movemask_pd(_mm256_castsi256_pd(_mm256_andnot_si256(rsame, noboth)));
        const __m256d ok = _mm256_and_pd(_mm256_castsi256_pd(rsame), _mm256_cmp_pd(w, zd, _CMP_GT_OQ));
        const __m256d nw4 = _mm256_and_pd(ok, nbase4);
        _mm256_storeu_si256((__m256i*)(ndir + p), r);
        _mm256_storeu_pd(nbase + p, nbase4);
        _mm256_storeu_pd(nw + p, nw4);
        _mm256_storeu_si256((__m256i*)(nrel + p),
                            _mm256_and_si256(rsame, _mm256_loadu_si256((const __m256i*)(prel + p))));
        for (int l = need; l; l &= l - 1) {  // changed relations without a contradiction: the closure
            const int i = p + __builtin_ctz(l);
            const u64 cl = closure8(ndir[i], 8);  // (as with m: the sheets >= m have no relations)
            if (!(cl & kDiagonal)) nw[i] = nbase[i], nrel[i] = sums.both_of(cl);
        }
        _mm_storeu_si128((__m128i*)(changed + nch),
                         _mm_add_epi32(_mm_set1_epi32(p), _mm_loadu_si128((const __m128i*)kLanes[chg].data())));
        nch += __builtin_popcount(chg);
    }
    return nch;
}

// Which windows are generic and the pair of sheets and colors of each generic window (`edge`,
// `polarity` in and out), by annealing until `seconds` (or `fixed_iters` iterations), then a climb
// on the same objective (climb_steps steps, or for climb_seconds). On return the windows are
// renumbered so that the generic ones are 0..g-1: A is rewritten, and permutation[j] is the original
// window of internal window j. Needs m = 6 (PosetSums); otherwise nothing is changed.
// Objective (gpt6pro-09): the cost of the pairs of targets that share a paper, as Design::initialize
// takes them: a greedy matching (least cost first) of need = 70 vertex-disjoint pairs among the
// compatible close pairs (distance <= 26; Comparator::compatible), a pair costing 0.65 handle
// differences + the mean moves of the generic layer for both of its targets + 0.04 differences; the
// mean over the 70 pairs, + 10 per missing pair. The costs are integers in 1/3600 (2340 hd + 5 rel +
// 144 d, rel = PosetSums::both_of, 720 times the two means), sorted by a stable radix sort (two passes
// of 9 bits; ties in the order of the pairs). The relations of a pair are kept as a bit matrix
// (bit 8a + b: a above b); a move is evaluated on all the pairs at once (evaluate_move; it changes
// only the pairs that differ on a changed window), then the matching of the new values.
// Moves: exchange a generic window with a handle window (kWindowRate of the time), flip the
// colors of a window, exchange the pairs of two windows, give a window to another pair of sheets.
struct WindowStats {
    int iterations = 0;
    double score = 0, gobj_before = 0, gobj_after = 0;
    int climb_steps = 0;
};
WindowStats assign_windows(std::vector<u64>& A, int m, int g, std::vector<std::pair<int, int>>& edges,
                           std::vector<int>& polarity, std::vector<int>& permutation, double seconds, int fixed_iters,
                           int climb_steps, double climb_seconds) {
    constexpr int kCutoff = 26;
    constexpr double kGenericWeight = 0.70, kWindowRate = 0.6;
    WindowStats stats;
    if (m != 6 || g >= 64 || g < m * (m - 1) / 2) return stats;
    const auto start = std::chrono::steady_clock::now();
    const PosetSums& sums = PosetSums::get();
    XorShift rng{0x71eb2566be932e31ULL};
    const int n = int(A.size()), need = 256 - (192 - m);
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
    u64 pol = 0;               // window j: 1 if the first sheet of its pair is black
    u64 hm = ~low_bits(g);     // the handle windows (original numbering)
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
    // The relations, weight (> 0 if compatible; evaluate_move) and rel of every close pair under the
    // current mask / pol.
    WindowPairs pairs;
    double bfactor[3];  // base factor when a window swap moves a difference into / out of G
    for (int d = -1; d <= 1; d++) bfactor[d + 1] = std::exp(0.35 * (1 - kGenericWeight) * d);
    const double center = 24 * (1 - (1 - kGenericWeight) * g / 64.0);
    auto pair_state = [&](u64 au, u64 d, u64& r, double& base, double& w, long long& rel) {
        r = 0;
        const u64 z = au ^ pol;
        for (int e = 0; e < ne; e++) {
            u64 q = d & mask[e];
            if (q & ~z) r |= fwd[e];
            if (q & z) r |= rev[e];
        }
        const u64 cl = closure8(r, m);
        const bool ok = !(cl & kDiagonal);
        const int h = __builtin_popcountll(d), hg = __builtin_popcountll(d & ~hm);
        base = std::exp((center - h + (1 - kGenericWeight) * hg) * 0.35);
        w = ok ? base : 0;
        rel = ok ? sums.both_of(cl) : 0;
    };
    for (int u = 0; u < n; u++)
        for (int v = u + 1; v < n; v++) {
            const u64 d = A[u] ^ A[v];
            if (__builtin_popcountll(d) > kCutoff) continue;
            u64 r;
            double base, w;
            long long rel;
            pair_state(A[u], d, r, base, w, rel);
            pairs.push(A[u], d, r, u, v, base, w, rel);
        }
    pairs.pad();
    const int np = pairs.n, np4 = pairs.n4;
    std::vector<u64> ndir(np4);
    std::vector<double> nbase(np4), nw(np4);
    std::vector<long long> nrel(np4);
    std::vector<int> changed(np4 + 4);  // changed[0 .. nchanged - 1] (evaluate_move writes 4 at a time)
    std::vector<int> full144(np);       // 144 differences of each pair
    for (int p = 0; p < np; p++) full144[p] = 144 * __builtin_popcountll(pairs.diff[p]);
    int nchanged = 0;
    // The objective for the weights `valid`, the sums `rel` and the handle windows `handle_mask`.
    struct KeyPair {
        uint32_t key;
        int pair;
    };
    std::vector<KeyPair> keyed(np), tmp(np), sorted(np);
    auto matching_cost = [&](const double* valid, const long long* rel, u64 handle_mask) {
        std::array<int, 512> low{}, high{};
        int size = 0;
        for (int p = 0; p < np; p++)
            if (valid[p] > 0) {
                const int key = 2340 * __builtin_popcountll(pairs.diff[p] & handle_mask) + 5 * int(rel[p]) + full144[p];
                assert(key < (1 << 18));
                keyed[size++] = {uint32_t(key), p};
                low[key & 511]++;
                high[key >> 9]++;
            }
        for (int i = 0, l = 0, h = 0; i < 512; i++) {
            const int a = low[i], b = high[i];
            low[i] = l, high[i] = h;
            l += a, h += b;
        }
        for (int i = 0; i < size; i++) tmp[low[keyed[i].key & 511]++] = keyed[i];
        for (int i = 0; i < size; i++) sorted[high[tmp[i].key >> 9]++] = tmp[i];
        std::array<u64, 4> used{};
        int matched = 0;
        long long total = 0;
        for (int i = 0; i < size; i++) {
            const int p = sorted[i].pair, u = pairs.u[p], v = pairs.v[p];
            if ((used[u >> 6] >> (u & 63) & 1) || (used[v >> 6] >> (v & 63) & 1)) continue;
            used[u >> 6] |= 1ULL << (u & 63);
            used[v >> 6] |= 1ULL << (v & 63);
            total += sorted[i].key;
            if (++matched == need) break;
        }
        return double(total) / (need * 3600) + (need - matched) * 10.0;
    };
    // A move: its windows and sheet pairs; propose changes mask / pol and evaluates the move on all
    // the pairs (ndir, nbase, nw, nrel; `changed`); apply_move keeps it, undo_move restores mask / pol.
    struct Move {
        int ia, ib, a, b, kind, ea, eb, transfer;
        bool swindow;
        u64 olda, oldb, oldpol;
    };
    auto propose = [&](Move& mv) {
        int ia = rng.mod(g), ib = rng.mod(g), a = order[ia], b = order[ib];
        bool swindow = rng.real() < kWindowRate;
        if (swindow) {
            ib = g + rng.mod(64 - g);
            b = order[ib];
        }
        int kind = rng.mod(10), ea = which[a], eb = swindow ? ea : which[b];
        u64 olda = mask[ea], oldb = mask[eb], oldpol = pol;
        int transfer = -1;
        if (swindow) {  // generic window a <-> handle window b
            mask[ea] ^= (1ULL << a) | (1ULL << b);
            pol = (pol & ~(1ULL << b)) | (((oldpol >> a) & 1) << b);
        } else if (kind < 3) {  // flip the colors of a
            pol ^= 1ULL << a;
            eb = ea;
            oldb = olda;
        } else if (kind < 8) {  // exchange the pairs of a and b
            if (ea == eb) return false;
            mask[ea] ^= (1ULL << a) | (1ULL << b);
            mask[eb] ^= (1ULL << a) | (1ULL << b);
        } else {  // window a to another pair
            if (counts[ea] < 2) return false;
            eb = rng.mod(ne);
            if (ea == eb) return false;
            oldb = mask[eb];
            mask[ea] ^= 1ULL << a;
            mask[eb] |= 1ULL << a;
            transfer = eb;
        }
        mv = {ia, ib, a, b, kind, ea, eb, transfer, swindow, olda, oldb, oldpol};
        // on all the pairs (those that do not differ at a or b come out unchanged)
        nchanged = evaluate_move(pairs, sums, pol, fwd[ea] | rev[ea] | fwd[eb] | rev[eb], mask[ea], mask[eb], fwd[ea],
                                 rev[ea], fwd[eb], rev[eb], a, b, swindow ? bfactor[0] : 1.0,
                                 swindow ? bfactor[2] : 1.0, ndir.data(), nbase.data(), nw.data(), nrel.data(),
                                 changed.data());
        return true;
    };
    auto handles_after = [&](const Move& mv) { return hm ^ (mv.swindow ? (1ULL << mv.a) | (1ULL << mv.b) : 0); };
    auto apply_move = [&](const Move& mv) {
        for (int i = 0; i < nchanged; i++) {
            const int p = changed[i];
            pairs.dir[p] = ndir[p];
            pairs.base[p] = nbase[p];
            pairs.w[p] = nw[p];
            pairs.rel[p] = nrel[p];
        }
        if (mv.swindow) {
            which[mv.a] = -1;
            which[mv.b] = mv.ea;
            std::swap(order[mv.ia], order[mv.ib]);
            hm = handles_after(mv);
        } else {
            if (mv.kind >= 3 && mv.kind < 8) std::swap(which[mv.a], which[mv.b]);
            if (mv.transfer >= 0) {
                counts[mv.ea]--;
                counts[mv.eb]++;
                which[mv.a] = mv.eb;
            }
        }
    };
    auto undo_move = [&](const Move& mv) {
        mask[mv.ea] = mv.olda;
        mask[mv.eb] = mv.oldb;
        pol = mv.oldpol;
    };
    double cur = matching_cost(pairs.w.data(), pairs.rel.data(), hm), best = cur;
    auto best_mask = mask;
    auto best_order = order;
    u64 best_pol = pol;
    double elapsed = 0;
    Move mv;
    for (int it = 0;; it++) {
        if ((it & 15) == 0) {
            elapsed = CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
            if (elapsed >= seconds || (fixed_iters > 0 && it >= fixed_iters)) break;
        }
        stats.iterations++;
        double progress = fixed_iters ? double(it) / fixed_iters : elapsed / seconds;
        if (!propose(mv)) continue;
        const double candidate = matching_cost(nw.data(), nrel.data(), handles_after(mv));
        const double temp = 0.2 * std::pow(0.005 / 0.2, progress);
        if (candidate <= cur || rng.real() < std::exp((cur - candidate) / temp)) {
            apply_move(mv);
            cur = candidate;
            if (cur < best - 1e-9) {
                best = cur;
                best_mask = mask;
                best_pol = pol;
                best_order = order;
            }
        } else {
            undo_move(mv);
        }
    }
    // Climb on the same objective from the best state (gpt6pro-09: no floor on another objective).
    mask = best_mask, pol = best_pol, order = best_order;
    std::fill(which.begin(), which.end(), -1);
    hm = ~0ULL;
    for (int e = 0; e < ne; e++) {
        counts[e] = __builtin_popcountll(mask[e]);
        hm &= ~mask[e];
        for (u64 x = mask[e]; x; x &= x - 1) which[__builtin_ctzll(x)] = e;
    }
    for (int p = 0; p < np; p++)
        pair_state(pairs.au[p], pairs.diff[p], pairs.dir[p], pairs.base[p], pairs.w[p], pairs.rel[p]);
    cur = matching_cost(pairs.w.data(), pairs.rel.data(), hm);
    stats.gobj_before = cur;
    if (climb_steps > 0 || climb_seconds > 0) {
        const auto climb_start = std::chrono::steady_clock::now();
        for (int it = 0;; it++) {
            if (climb_steps > 0 ? it >= climb_steps
                                : (it & 15) == 0 &&
                                      CLOCK_SCALE * std::chrono::duration<double>(std::chrono::steady_clock::now() -
                                                                                  climb_start)
                                                        .count() >=
                                          climb_seconds)
                break;
            stats.climb_steps = it + 1;
            if (!propose(mv)) continue;
            const double candidate = matching_cost(nw.data(), nrel.data(), handles_after(mv));
            if (candidate <= cur) {
                apply_move(mv);
                cur = candidate;
            } else {
                undo_move(mv);
            }
        }
    }
    stats.gobj_after = cur;
    stats.score = -cur;
    for (int j = 0; j < g; j++) {
        int x = order[j], e = 0;
        while (e < ne && !(mask[e] >> x & 1)) e++;
        assert(e < ne);
        edges[j] = ep[e];
        polarity[j] = (pol >> x) & 1;
    }
    auto oldperm = permutation;
    for (int j = 0; j < 64; j++) permutation[j] = oldperm[order[j]];
    for (u64& a : A) {
        u64 b = 0;
        for (int j = 0; j < 64; j++) b |= ((a >> order[j]) & 1) << j;
        a = b;
    }
    return stats;
}

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
//   - column c (colcost): the digs nt (nc - 1) / 2 of a cyclic column (nt targets on nc papers), less
//     kRankPriority of the saving of keeping the pairs (asked twice as often) near the top with both
//     handle colors near the top (alt); 5 imb^2 for an unbalanced column, 1e5 without both colors;
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
    // Written without branches (the annealing evaluates it twice per move, on random counts): base and
    // alt are computed doubled in integers. always_inline: Annealer (AVX2) must not call SSE code.
    __attribute__((always_inline)) static double colcost_of(int nc, int nt, int n1, int p1) {
        const int imb = std::max(0, std::abs(nc - 2 * n1) - 1);
        const int p0 = nt - nc - p1;
        int firstPair = std::max(p0, p1);
        firstPair = 2 * n1 > nc ? p1 : firstPair;
        firstPair = 2 * n1 < nc ? p0 : firstPair;
        const int base2 = nt * (nc - 1), alt2 = nc * (nc - 1) + 2 * (p0 * p0 + p1 * p1 - firstPair);
        const double retrieval = base2 * 0.5 - kRankPriority * (std::max(0, base2 - alt2) * 0.5);
        return retrieval + 5.0 * (imb * imb) + 100000.0 * int((n1 == 0) | (n1 == nc));
    }
    double colcost(int c) const { return colcost_of(nc[c], nt[c], n1[c], pairOne[c]); }
    // 40 colcost_of in integers (exact; kRankPriority = 17 / 20), for the annealing
    static_assert(kRankPriority == 0.85);
    __attribute__((always_inline)) static int colcost40(int nc, int nt, int n1, int p1) {
        const int imb = std::max(0, std::abs(nc - 2 * n1) - 1);
        const int p0 = nt - nc - p1;
        int firstPair = std::max(p0, p1);
        firstPair = 2 * n1 > nc ? p1 : firstPair;
        firstPair = 2 * n1 < nc ? p0 : firstPair;
        const int base2 = nt * (nc - 1), alt2 = nc * (nc - 1) + 2 * (p0 * p0 + p1 * p1 - firstPair);
        return 20 * base2 - 17 * std::max(0, base2 - alt2) + 200 * (imb * imb) +
               4000000 * int((n1 == 0) | (n1 == nc));
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
    void anneal(double seconds, int fixedIterations = 0) {
        if (H <= 32)
            Annealer<4>(*this).run(seconds, fixedIterations);
        else
            Annealer<5>(*this).run(seconds, fixedIterations);
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
        // acc[lane j] += k for every bit j of m
        ANNEAL_TARGET static void add_bits(__m256* acc, u64 m, float k) {
            const __m256 kv = _mm256_set1_ps(k);
            for (int r = 0; r < NR; r++)
                acc[r] = _mm256_fmadd_ps(_mm256_load_ps(bit_lanes((m >> (8 * r)) & 255)), kv, acc[r]);
        }
        ANNEAL_TARGET static void add_bits(float* row, u64 m, float k) {
            const __m256 kv = _mm256_set1_ps(k);
            for (int r = 0; r < NR; r++)
                _mm256_store_ps(row + 8 * r, _mm256_add_ps(_mm256_load_ps(row + 8 * r),
                                                           _mm256_mul_ps(_mm256_load_ps(bit_lanes((m >> (8 * r)) & 255)), kv)));
        }
        // New counts N0 = n0 + d0, N1 = n1 + d1 and their q; returns the sum of the changes of q.
        ANNEAL_TARGET float eval_holes(const __m256* d0, const __m256* d1, __m256* N0, __m256* N1, __m256* Q) const {
            const __m256 one = _mm256_set1_ps(1.0f);
            __m256 dif[NR];
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
            int dnc[2] = {0, 0}, dnt[2] = {0, 0}, dn1[2] = {0, 0}, dp1[2] = {0, 0};  // [0]: P, [1]: Q
            for (const auto& [u, to] : {std::pair<const Unit&, int>{ox, nx.c}, std::pair<const Unit&, int>{oy, ny.c}}) {
                const int f = u.c == P ? 0 : 1, t = to == P ? 0 : 1;
                const int w = D.weight(u), cf = D.color(u, u.c), ct = D.color(u, to), pr = u.b >= 0;
                dnc[f]--, dnt[f] -= w, dn1[f] -= cf, dp1[f] -= pr * cf;
                dnc[t]++, dnt[t] += w, dn1[t] += ct, dp1[t] += pr * ct;
            }
            const int cvP = colcost40(cnc[P] + dnc[0], cnt[P] + dnt[0], cn1[P] + dn1[0], cp1[P] + dp1[0]);
            const int cvQ = colcost40(cnc[Q] + dnc[1], cnt[Q] + dnt[1], cn1[Q] + dn1[1], cp1[Q] + dp1[1]);
            // The handles between the two columns stop (moving deeper) or start being holes of the
            // unit, except its pair differences (always holes); a pair's targets agree there.
            __m256 d0[NR], d1[NR];
            for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            for (const auto& [u, to] : {std::pair<const Unit&, int>{ox, nx.c}, std::pair<const Unit&, int>{oy, ny.c}}) {
                const u64 ha = D.hb[u.a], d = u.b >= 0 ? ha ^ D.hb[u.b] : 0;
                const u64 m = (low_bits(u.c + 1) ^ low_bits(to + 1)) & ~d;
                const float k = float((to > u.c ? -1 : 1) * D.weight(u));
                add_bits(d1, m & ha, k);
                add_bits(d0, m & ~ha, k);
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
            for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            for (const auto& [u, i, sgn] : {std::tuple<const Unit&, int, int>{ox, 0, -1}, std::tuple<const Unit&, int, int>{nx, 0, 1},
                                            std::tuple<const Unit&, int, int>{oy, iy, -1}, std::tuple<const Unit&, int, int>{ny, iy, 1}}) {
                const int cl = D.color(u, u.c);
                dnt[i] += sgn * D.weight(u), dn1[i] += sgn * cl, dp1[i] += sgn * (u.b >= 0) * cl;
                const u64 hs = D.holes(u);
                for (int t : {u.a, u.b}) {
                    if (t < 0) continue;
                    add_bits(d1, hs & D.hb[t], float(sgn));
                    add_bits(d0, hs & ~D.hb[t], float(sgn));
                }
            }
            const int cvx = colcost40(cnc[cx], cnt[cx] + dnt[0], cn1[cx] + dn1[0], cp1[cx] + dp1[0]);
            const int cvy = iy ? colcost40(cnc[cy], cnt[cy] + dnt[1], cn1[cy] + dn1[1], cp1[cy] + dp1[1]) : 0;
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
            const int cva = colcost40(cnc[a], cnt[a], n1a, pa), cvb = colcost40(cnc[b], cnt[b], n1b, pb);
            const double delta = kHoleScale * ((qa - hq[a]) + (qb - hq[b])) + ((cva + cvb) - (cv[a] + cv[b])) * (1.0 / 40);
            if (!accept(delta)) return;
            cur += delta;
            std::swap(D.handle[a], D.handle[b]);
            for (auto& h : D.hb)
                if (((h >> a) ^ (h >> b)) & 1) h ^= (u64(1) << a) | (u64(1) << b);
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
            for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            for (int i = 0; i < k; i++)
                for (int sgn = -1; sgn <= 1; sgn += 2) {
                    const Unit& u = sgn < 0 ? D.unit[xs[i]] : nu[i];
                    int ci = 0;
                    while (ci < ncols && cols[ci] != u.c) ci++;
                    if (ci == ncols) cols[ncols] = u.c, dnc[ncols] = dnt[ncols] = dn1[ncols] = dp1[ncols] = 0, ncols++;
                    const int cl = D.color(u, u.c);
                    dnc[ci] += sgn, dnt[ci] += sgn * D.weight(u), dn1[ci] += sgn * cl, dp1[ci] += sgn * (u.b >= 0) * cl;
                    const u64 hs = D.holes(u);
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

        ANNEAL_TARGET void run(double seconds, int fixedIterations) {
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
                    temp = 2.0 * std::pow(0.015 / 2.0, progress);
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
    void refill_or_return(int u, const std::vector<Filler>& olds, u64& pre_cov, std::vector<Filler>& placed) {
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
            if (!use && d >= 0 && x != d) {
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
        for (int i = (int)olds.size() - 1; i >= 0; i--) {
            if (old_dec[i] != 0 || !visible(olds[i].paper)) continue;
            return_paper(olds[i].paper, u, 1);
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
                    for (int i = (int)olds.size() - 1; i >= 0; i--) return_paper(olds[i].paper, u, opt.fret_mode);
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
                while (!fillers.empty()) return_paper(fillers.back().paper, u, opt.fret_mode);
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
            for (auto& pk : picks)
                if (!pk.post) place_filler(pk.c, pk.depth, pk.lvl, hh);
            lift(d);
            for (auto& pk : picks)
                if (pk.post) place_filler(pk.c, pk.depth, pk.lvl, hh);
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
        while (!fillers.empty()) return_paper(fillers.back().paper, u, 1);
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
        const std::vector<int> fms = any_out ? std::vector<int>{1, 4} : std::vector<int>{1};
        std::vector<PlanOpt> opts;
        for (int rm = 1; rm <= (prev_ok ? 3 : 2); rm++)
            for (int fm : fms) opts.push_back({rm, fm, true});
        if (d != top0)
            for (int rm = 1; rm <= 2; rm++) opts.push_back({rm, 5, true});
        if (prev_ok)
            for (int fm : fms) opts.push_back({4, fm, true});
        double best = 1e18;
        std::vector<std::pair<int, int>> best_ops;
        State best_state;
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
        }
        tail_cache_on = false;
        if (interleave && interleave->ready && d >= 0 && d != top0 && !interleave->helpers[u].empty()) {
            bool used = false;
            try_helpers(u, st0, [&](double cost) {
                if (cost < best) best = cost, best_ops = ops, best_state = save(), used = true;
            });
            interleave_selected += used;
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
            return PosetSums::get().both_of(r) / 1440.0;
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
              << "\nreq_sec = " << req_sec
              << "\nend_sec = " << elapsed_sec() << '\n';
    return 0;
}
