// AHC074: six-sheet comparator, paired product papers, and visible access columns.
// The 63 active windows initially comprise 38 comparisons and 25 column handles;
// window 63 belongs to a fixed black cap. A partial target is feasible iff its comparisons form a DAG.
// A product paper serves one target or a compatible pair; disagreements become holes.
// Design: assign windows, anneal pairs/columns/handles, improve fillers, rematch, then perforate.
// Requests: choose return/filler/helper plans using moves plus a one-step/column-MDP state value;
// shorten them by legal replay, then explore one-to-one and two-to-two neutral rewrites.
// Defaults use fixed random seeds and iteration counts; no future order is read during design.
// V16 with target-specific Sobol shifts and exact mismatch control variates selects designs.
// Time-shortage fallback is intentionally absent (PR #117); restore it before the final submission
// (solutions/deval-vbranch-o3 has the light request modes and the design caps).
// Experiments: F3_* configures request search, COLMDP_* the column value model. ITER_SCALE scales
// design iterations; MAP_ITERS / GOPT_STEPS / ANNEAL_ITERS override individual stages; filler climbs are fixed.
// Profiling, heavy traces, POSET_VERIFY, SIM_HARNESS, and LOCAL_BENCH analysis remain available.
//
// Contents (section markers below):
//   Common: constants, clock, random numbers
//   Request profiling (COLFAST_PROFILE): inclusive and exclusive times
//   Analysis output (LOCAL_BENCH): move labels
//   Generic layer: the comparator of the six sheets
//   Generic layer: exact mean moves of a partial order (PosetSums)
//   Window assignment: pair relations and their fast evaluation
//   Window assignment: annealing and climb (assign_windows)
//   Window assignment: candidate screens and tables
//   Window assignment: ordinary moves
//   Window assignment: elite paths
//   Window assignment: acceptance and search loops
//   Design: units, columns and the cost model
//   Design annealing
//   Design annealing: move proposals
//   Filler climb: columns of the units for the filler value
//   Head-aware reassignment of the targets (Hungarian matching)
//   Helper tables: dedicated papers inside the generic layer (Interleave)
//   Column MDP: long-run values of the order of a column
//   Solver: papers, handles and the generic look-ahead
//   Solver: future-cost model of the stack
//   Solver: column MDP values in the future-cost model
//   Solver: stack operations (moves, digs, lifts, handle fixes)
//   Request plans: options, fillers and the joint interval DP
//   Request plans: one plan (run_plan) and its shared tail
//   Request plans: filler chains
//   Solver: canonical records of the stack
//   Request plans: helpers inside the generic layer
//   Post-processing: deletions and new anchors of the edits
//   Post-processing: two deletions and one repair (eject)
//   Post-processing: two deletions and two repairs (neutral rewrite)
//   Request processing (process)
//   Emergency design
//   Handle perforation
//   Design state: what the requests need from the design (DesignState, make_solver)
//   Initial column order
//   V: design-only expected moves
//   State
//   Donors
//   Cover expectation
//   V: compact fixed quadrature
//   Exact generic costs
//   Static design features
//   Filler features
//   Coefficients
//   Prediction
//   Adapter from the solver's DesignState
//   Design iteration counts
//   design_papers: window assignment and the initial design
//   design_papers: finish each candidate and select by V
//   design_papers: printing the papers
//   design_papers: handle perforation
//   design_papers: perforation-aware reassignment
//   Saving and loading the design state (LOCAL_BENCH: DesignStore)
//   Analysis output (LOCAL_BENCH): paper attributes
//   main: input
//   main: the design (designed, or loaded under LOCAL_BENCH)
//   main: helper tables and the generic look-ahead
//   main: simulation harness (SIM_HARNESS)
//   main: output of the papers
//   main: requests
//   main: statistics
#include <algorithm>
#include <initializer_list>
#include <bit>
#include <map>
#include <unordered_map>
#include <stdexcept>
#include <sstream>
#include <functional>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <immintrin.h>
#include <iostream>
#include <memory>
#include <numeric>
#include <random>
#include <string>
#include <tuple>
#include <utility>
#include <vector>
#ifdef LOCAL_BENCH
#include <cstdio>
#include <fstream>
#include <sstream>
#endif

using u64 = std::uint64_t;

namespace {

// ==== Common: constants, clock, random numbers ====

constexpr int N = 64, K = 192, P = 256;
constexpr int kCapWindow = 63, kCapPaper = 6;
constexpr u64 kCapBit = 1ULL << kCapWindow;
constexpr u64 kActiveWindows = kCapBit - 1;

// Every clock reading uses scaled_since and CLOCK_SCALE (1.1 locally, 1.0 on the judge).
#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
using Clock = std::chrono::steady_clock;
double scaled_since(Clock::time_point start) {
    return CLOCK_SCALE * std::chrono::duration<double>(Clock::now() - start).count();
}
#ifdef LOCAL_BENCH
// Not const in the local evaluation: a run that loads a saved design moves it (DesignStore::design_end).
auto kStartTime = Clock::now();
#else
const auto kStartTime = Clock::now();
#endif
double elapsed_sec() { return scaled_since(kStartTime); }

// ==== Request profiling (COLFAST_PROFILE): inclusive and exclusive times ====
#ifndef F3_PROFILE
#define F3_PROFILE 0
#endif
#if F3_PROFILE && defined(LOCAL_BENCH)
#define F3_DIAG(...) __VA_ARGS__
#else
#define F3_DIAG(...)
#endif
#ifndef COLFAST_PROFILE
#define COLFAST_PROFILE 0
#endif
#if COLFAST_PROFILE
struct CfProfile {
    const char* name;
    double inclusive = 0, exclusive = 0;
    long long calls = 0;
};
struct CfScope {
    static inline CfScope* current = nullptr;
    CfProfile& data;
    CfScope* parent;
    double start, children = 0;
    explicit CfScope(CfProfile& d) : data(d), parent(current), start(elapsed_sec()) { current = this; }
    ~CfScope() {
        const double dt = elapsed_sec() - start;
        data.inclusive += dt;
        data.exclusive += dt - children;
        data.calls++;
        if (parent) parent->children += dt;
        current = parent;
    }
};
CfProfile cf_process{"process"};
CfProfile cf_run_plan{"run_plan"};
CfProfile cf_run_joint{"run_joint"};
CfProfile cf_plan_tail{"plan_tail"};
CfProfile cf_next_cost{"next_cost"};
CfProfile cf_plan_cost{"plan_cost"};
CfProfile cf_filler_charge{"filler_charge"};
CfProfile cf_canonicalize{"canonicalize"};
CfProfile cf_reachable{"reachable"};
CfProfile cf_helpers{"helpers"};
CfProfile cf_post{"post"};
CfProfile cf_evaluate{"evaluate"};
CfProfile cf_eject{"eject"};
CfProfile cf_mdp_gaps{"mdp_gaps"};
CfProfile cf_insert{"insert"};
CfProfile cf_chains{"chains"};
CfProfile cf_neutral{"neutral"};
CfProfile cf_eval_filter{"eval_filter"};
CfProfile cf_eval_replay{"eval_replay"};
CfProfile cf_eval_value{"eval_value"};
CfProfile cf_choose_fillers{"choose_fillers"};
CfProfile cf_post_setup{"post_setup"};
CfProfile cf_single_helper{"single_helper"};
CfProfile cf_pair_helper{"pair_helper"};
CfProfile cf_neutral_edits{"neutral_edits"};
#define CF_SCOPE(name) CfScope cf_scope_##name(cf_##name)
void cf_report() {
    for (const auto* p : {&cf_process, &cf_run_plan, &cf_run_joint, &cf_plan_tail, &cf_next_cost,
                          &cf_plan_cost, &cf_filler_charge, &cf_canonicalize, &cf_reachable, &cf_helpers,
                          &cf_post, &cf_evaluate, &cf_eject, &cf_mdp_gaps, &cf_insert,
                          &cf_chains, &cf_neutral, &cf_eval_filter, &cf_eval_replay, &cf_eval_value,
                          &cf_choose_fillers, &cf_post_setup, &cf_single_helper, &cf_pair_helper, &cf_neutral_edits})
        std::cerr << "cfprof_" << p->name << "_inc = " << p->inclusive
                  << "\ncfprof_" << p->name << "_exc = " << p->exclusive
                  << "\ncfprof_" << p->name << "_calls = " << p->calls << '\n';
}

#else
#define CF_SCOPE(name) ((void)0)
void cf_report() {}
#endif

// Overrides of the fixed iteration counts for experiments (MAP_ITERS, GOPT_STEPS, ANNEAL_ITERS,
// CLIMB_ITERS; 0 or unset: the counts of Design iteration counts; GOPT_STEPS / CLIMB_ITERS = -1: no
// climb), and SIM_SEQS of the simulation harness (-DSIM_HARNESS).
int env_int(const char* name) {
    const char* s = std::getenv(name);
    return s ? std::atoi(s) : 0;
}

u64 low_bits(int n) { return n == 64 ? ~0ULL : (1ULL << n) - 1; }  // bits 0..n-1

// xorshift (7, 9); `mod` and `below` are the two mappings to [0, n) of the two original generators.
double env_real(const char* name,double fallback);
// Candidate salt is set only while constructing a design, never by requests.
u64 deval_salt=0;
u64 deval_seed_salt() { return deval_salt*0x9E3779B97F4A7C15ULL; }

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

// ==== Analysis output (LOCAL_BENCH): move labels ====

// LOCAL_BENCH labels track each move through planning and rewriting. They are never read by
// the search; OP_LABEL selects a scoped label and OP_TAG carries it with copied move lists.
#ifdef LOCAL_BENCH
enum OpLabel : uint8_t {
    kOpOther,    // no label set (a bug of the labels if it shows)
    kOpRet,      // the previous lifted paper back into its column
    kOpFret,     // an old filler back into its column
    kOpReuse,    // the previous lifted paper moved to a filler level
    kOpRelevel,  // an old filler moved to another level
    kOpGen,      // a generic sheet moved to order the generic layer
    kOpDig,      // a dig of the requested paper's column (its top paper back into the column)
    kOpLift,     // the requested paper to the top
    kOpFdig,     // a dig of a column to reach a new filler
    kOpFill,     // a new filler placed at its level
    kOpHdig,     // a dig of a column to reach a helper
    kOpHelp,     // a helper inserted into the generic layer
    kOpFix,      // a dig of a column until its handle shows the requested color
    kOpRepair,   // the repair move added by the eject pass of the post-processing
    kOpLabels
};
constexpr const char* kOpLabelName[kOpLabels] = {"other", "ret",  "fret", "reuse", "relevel", "gen",  "dig",
                                                 "lift",  "fdig", "fill", "hdig",  "help",    "fix", "repair"};
#define OP_TAG(...) __VA_ARGS__
#define OP_LABEL_CAT2(a, b) a##b
#define OP_LABEL_CAT(a, b) OP_LABEL_CAT2(a, b)
// Sets the label of the moves made in the rest of the enclosing scope (restored at its end).
#define OP_LABEL(label) const OpLabelScope OP_LABEL_CAT(op_label_scope_, __LINE__)(op_tag, label)
struct OpLabelScope {
    uint8_t& slot;
    uint8_t saved;
    OpLabelScope(uint8_t& s, uint8_t label) : slot(s), saved(s) { s = label; }
    ~OpLabelScope() { slot = saved; }
};
// `@ops <r> = ...` with runs of one label written as `<label>*<n>`.
void append_op_labels(std::string& out, int r, const std::vector<uint8_t>& tags) {
    out += "@ops " + std::to_string(r) + " =";
    for (size_t i = 0; i < tags.size();) {
        size_t j = i;
        while (j < tags.size() && tags[j] == tags[i]) j++;
        out += ' ';
        out += kOpLabelName[tags[i]];
        if (j - i > 1) out += '*' + std::to_string(j - i);
        i = j;
    }
    out += '\n';
}
#else
#define OP_TAG(...)
#define OP_LABEL(label)
#endif

#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC push_options
#pragma GCC optimize("O3")
#endif
// ==== Generic layer: the comparator of the six sheets ====

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

    // Tables of the M! orders of the sheets, built once by build_tables: perms (sorted), next (the
    // order after one move), below[s][a] (the sheets below a in order s) and dist (the least number
    // of moves between two orders; the bottom sheet of the layer never moves).
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
        // BFS and label symmetry
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
        // Renaming sheets preserves every legal move, including the immovable bottom
        // position. One BFS gives the identity row; all other rows are relabelings.
        int qb = 0, qe = 0;
        q[qe++] = 0;
        dist[0] = 0;
        while (qb < qe) {
            const int x = q[qb++];
            for (int y : next[x])
                if (y >= 0 && dist[y] == 255) dist[y] = dist[x] + 1, q[qe++] = y;
        }
        std::vector<std::vector<int>> renamed(M * M);
        for (int i = 0; i < M; ++i) for (int j = i + 1; j < M; ++j) {
            auto& index = renamed[i * M + j];
            index.resize(n);
            for (int b = 0; b < n; ++b) {
                auto r = perms[b];
                for (int& x : r) {
                    if (x == i) x = j;
                    else if (x == j) x = i;
                }
                index[b] = order_index(r);
            }
        }
        for (int a = 1; a < n; ++a) {
            int i = 0;
            while (perms[a][i] == i) ++i;
            // Earlier positions are fixed, so j > i. This swap makes the source
            // lexicographically smaller, and its distance row is already complete.
            const int j = perms[a][i];
            const auto& index = renamed[i * M + j];
            const int parent = index[a];
            assert(parent < a);
            for (int b = 0; b < n; ++b) dist[a * n + b] = dist[parent * n + index[b]];
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

// ==== Generic layer: exact mean moves of a partial order (PosetSums) ====

// The diagonal of a relation bit matrix (8 x 8, bit 8a + b: a above b); a closure with a bit there
// has a cycle.
constexpr u64 kDiagonal = 0x8040201008040201ULL;

// The sums of the 720 legal distances (those of Comparator::build_tables: the bottom sheet never
// moves) from every order of the 6 generic sheets to the nearest order satisfying a closed relation
// (bit 8a + b: a above b), i.e. 720 times the mean number of moves of the generic layer to show a
// partial display from a uniform order. The sum does not change when the sheets are
// relabeled, so kPosetClasses lists one closed relation of each of the 318 unlabeled partial orders
// of 6 elements with its sum (computed exhaustively offline from the Comparator tables); PosetSums
// expands them to the 130023 labeled ones in a hash table (a few ms, once).
struct PosetClass {
    u64 relation;
    int sum;
};
// clang-format off
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
// kPosetDual[i]: the class of the transposes of the relations of class i (its dual; computed
// offline from kPosetClasses by the least relabeling of each relation). both_of = the sum of the class plus
// that of its dual. (POSET_VERIFY checks every value against the table of climb4-fast.)
constexpr int kPosetDual[318] = {
    0, 255, 22, 62, 4, 239, 38, 90, 123, 100, 132, 136, 141, 302, 116, 15, 265, 17, 18, 186, 103, 184, 2, 159,
    229, 25, 26, 297, 41, 43, 259, 31, 79, 105, 34, 107, 109, 250, 6, 241, 176, 28, 119, 29, 270, 191, 46, 275,
    48, 49, 53, 197, 121, 50, 277, 55, 199, 57, 279, 201, 152, 313, 3, 257, 214, 65, 114, 127, 143, 304, 162, 288,
    80, 85, 224, 206, 293, 178, 248, 32, 72, 117, 82, 181, 193, 73, 194, 139, 150, 311, 7, 260, 217, 93, 94, 232,
    163, 271, 272, 300, 9, 165, 215, 20, 104, 33, 243, 35, 180, 36, 244, 182, 112, 253, 66, 115, 14, 81, 118, 42,
    274, 52, 196, 8, 261, 170, 218, 67, 185, 129, 145, 306, 10, 166, 262, 290, 11, 219, 167, 87, 226, 12, 263, 68,
    220, 130, 146, 307, 168, 291, 88, 227, 60, 282, 204, 155, 316, 157, 284, 23, 173, 246, 70, 96, 189, 101, 133, 138,
    148, 309, 125, 171, 231, 160, 286, 299, 40, 177, 77, 222, 108, 83, 111, 252, 21, 128, 19, 267, 188, 164, 289, 45,
    192, 84, 86, 225, 122, 51, 278, 56, 200, 59, 281, 203, 154, 315, 75, 207, 268, 294, 210, 242, 212, 249, 64, 102,
    216, 92, 126, 137, 144, 305, 179, 223, 74, 195, 140, 151, 312, 24, 230, 172, 95, 233, 258, 298, 287, 273, 301, 5,
    240, 39, 211, 106, 110, 251, 161, 247, 78, 213, 37, 245, 183, 113, 254, 1, 256, 63, 234, 30, 91, 124, 134, 142,
    303, 16, 266, 187, 208, 295, 44, 97, 98, 237, 120, 47, 276, 54, 198, 58, 280, 202, 153, 314, 158, 285, 174, 236,
    71, 190, 135, 149, 310, 76, 209, 269, 296, 27, 235, 175, 99, 238, 13, 264, 69, 221, 131, 147, 308, 169, 292, 89,
    228, 61, 283, 205, 156, 317,
};
// clang-format on
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
// The packed form of a closed relation c (bit 8a + b: a above b), as the relations of WindowRelations:
// bit e (the e-th pair (a, b), a < b, a outer) when a is above b, bit 16 + e when b is above a. The
// transpose of c packs to the two halves exchanged.
constexpr u64 kUpperPairs = 0x0000002030383c3eULL;  // the bits 8a + b, a < b < 6, in the order of e
__attribute__((target("bmi2"))) inline uint32_t pack_relation(u64 c) {
    return uint32_t(_pext_u64(c, kUpperPairs)) | uint32_t(_pext_u64(transpose8(c), kUpperPairs)) << 16;
}
// PosetSums is keyed by the canonical packed relation (the smaller of the packings of a
// relation and of its transpose, which have the same both_of): 65012 keys. The lookup is a displacement
// hash (CHD): the bucket of a key (kBucketBits bits of one hash) holds a displacement d, chosen when the
// table is built so that the keys of the bucket land on distinct free slots of `value` (kSlotBits bits
// of a second hash of key and d). It reads two 16-bit entries (32 KB and 256 KB tables) without a key
// comparison: every query is an acyclic closure, hence a key of the table.
// POSET_VERIFY checks the sums over all 130023 relations.
struct PosetSums {
    static constexpr unsigned kBucketBits = 14, kSlotBits = 17;
    std::vector<uint16_t> displacement, value, one;
    static uint32_t canonical(uint32_t k) { return std::min(k, (k >> 16) | (k << 16)); }
    static unsigned bucket(uint32_t key) {
        return unsigned((u64(key) * 0x9E3779B97F4A7C15ULL) >> (64 - kBucketBits));
    }
    static unsigned slot(uint32_t key, unsigned d) {
        u64 x = (u64(key) << 16 | d) * 0xBF58476D1CE4E5B9ULL;
        x ^= x >> 31;
        x *= 0x94D049BB133111EBULL;
        return unsigned(x >> (64 - kSlotBits));
    }
    // both_of of a canonical packed closed acyclic relation
    __attribute__((always_inline)) int lookup(uint32_t key) const { return value[slot(key, displacement[bucket(key)])]; }
    __attribute__((target("bmi2"))) int both_of(u64 closed) const {
        return lookup(canonical(pack_relation(closed)));
    }
    // Direction-specific expectation for V. The mapper still reads the original
    // sum of the two directions. Canonicalization tells which summand to use.
    __attribute__((target("bmi2"))) int one_of(u64 closed) const {
        const uint32_t packed=pack_relation(closed),key=canonical(packed);
        const unsigned i=slot(key,displacement[bucket(key)]);
        return packed==key?one[i]:value[i]-one[i];
    }
    // The canonical keys with their sums (kPosetDual), then the displacements, the largest buckets first.
    __attribute__((target("bmi2"))) void build() {
        // The classes one of each dual pair (and the self-dual ones): every relabeling of class i, by its
        // canonical key (a relabeling and the transpose of the dual's relabeling share it), once each
        // (seen: an open-addressing set of the keys of class i), with the sum of the class and of its dual.
        std::vector<uint32_t> all_keys;
        std::vector<uint16_t> all_sums, all_one;
        all_keys.reserve(65012);
        all_sums.reserve(65012);all_one.reserve(65012);
        constexpr unsigned kSeen = 2048;
        std::array<uint32_t, kSeen> seen_key{};
        std::array<int, kSeen> seen_class;
        seen_class.fill(-1);
        std::vector<std::array<int, 6>> perms;
        perms.reserve(720);
        std::array<int, 6> p{0, 1, 2, 3, 4, 5};
        do perms.push_back(p);
        while (std::next_permutation(p.begin(), p.end()));
        for (int i = 0; i < 318; i++) {
            if (kPosetDual[i] < i) continue;
            const uint16_t sum = uint16_t(kPosetClasses[i].sum + kPosetClasses[kPosetDual[i]].sum);
            for (const auto& q : perms) {
                u64 r = 0;
                for (u64 x = kPosetClasses[i].relation; x; x &= x - 1) {
                    const int bit = __builtin_ctzll(x);
                    r |= 1ULL << (8 * q[bit >> 3] + q[bit & 7]);
                }
                const uint32_t packed=pack_relation(r),key=canonical(packed);
                unsigned h = unsigned((u64(key) * 0x9E3779B97F4A7C15ULL) >> (64 - 11));
                while (seen_class[h] == i && seen_key[h] != key) h = (h + 1) & (kSeen - 1);
                if (seen_class[h] == i) continue;
                seen_class[h] = i;
                seen_key[h] = key;
                all_keys.push_back(key);
                all_sums.push_back(sum);
                all_one.push_back(uint16_t(packed==key?kPosetClasses[i].sum:kPosetClasses[kPosetDual[i]].sum));
            }
        }
        // the keys grouped by bucket (counting sort), with their sums
        constexpr unsigned kBuckets = 1U << kBucketBits;
        std::vector<int> start(kBuckets + 1, 0);
        for (uint32_t key : all_keys) start[bucket(key) + 1]++;
        for (unsigned b = 0; b < kBuckets; b++) start[b + 1] += start[b];
        std::vector<uint32_t> keys(start[kBuckets]);
        std::vector<uint16_t> sums(start[kBuckets]),ones(start[kBuckets]);
        {
            std::vector<int> at(start.begin(), start.end() - 1);
            for (size_t j = 0; j < all_keys.size(); j++) {
                const int i = at[bucket(all_keys[j])]++;
                keys[i] = all_keys[j];
                sums[i] = all_sums[j];ones[i]=all_one[j];
            }
        }
        // buckets by size (largest first; ties by index): a counting sort by size
        std::vector<int> order(kBuckets);
        {
            std::array<int, 66> by_size{};
            for (unsigned b = 0; b < kBuckets; b++) by_size[std::min(64, start[b + 1] - start[b])]++;
            for (int size = 64, at = 0; size >= 0; size--) {
                const int n = by_size[size];
                by_size[size] = at;
                at += n;
            }
            for (unsigned b = 0; b < kBuckets; b++) order[by_size[std::min(64, start[b + 1] - start[b])]++] = int(b);
        }
        displacement.assign(kBuckets, 0);
        value.assign(1U << kSlotBits, 0);one.assign(1U << kSlotBits,0);
        std::vector<uint8_t> used(1U << kSlotBits, 0);
        std::array<unsigned, 64> slots{};
        for (int b : order) {
            const int lo = start[b], n = start[b + 1] - lo;
            if (!n) break;
            assert(n <= 64);
            for (unsigned d = 0;; d++) {
                assert(d < 65536);
                bool ok = true;
                for (int i = 0; i < n && ok; i++) {
                    slots[i] = slot(keys[lo + i], d);
                    ok = !used[slots[i]];
                    for (int j = 0; j < i && ok; j++) ok = slots[j] != slots[i];
                }
                if (!ok) continue;
                displacement[b] = uint16_t(d);
                for (int i = 0; i < n; i++) {used[slots[i]]=1;value[slots[i]]=sums[lo+i];one[slots[i]]=ones[lo+i];}
                break;
            }
        }
    }
    PosetSums() { build(); }
    static const PosetSums& get() {
        static const PosetSums table;
        return table;
    }
};
#ifdef POSET_VERIFY
// Test only (-DPOSET_VERIFY: the first window assignment compares both_of with the table of climb4-fast on
// every closed relation, writes the result to stderr and exits).
struct PosetSumsReference {
    static constexpr unsigned kSize = 1U << 18;
    static constexpr u64 kEmpty = ~0ULL;
    std::vector<u64> keys;
    std::vector<uint16_t> one, both;
    static unsigned hash(u64 x) {
        x ^= x >> 27;
        x *= 0x3c79ac492ba7b653ULL;
        x ^= x >> 33;
        return unsigned(x) & (kSize - 1);
    }
    unsigned slot_of(u64 r) const {
        unsigned s = hash(r);
        while (keys[s] != r) s = (s + 1) & (kSize - 1);
        return s;
    }
    PosetSumsReference() : keys(kSize, kEmpty), one(kSize), both(kSize) {
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
};
int poset_verify() {
    const PosetSumsReference ref;
    const PosetSums& sums = PosetSums::get();
    long long checked = 0, wrong = 0, entries = 0;
    for (unsigned s = 0; s < PosetSumsReference::kSize; s++)
        if (ref.keys[s] != PosetSumsReference::kEmpty) {
            checked++;
            wrong += sums.both_of(ref.keys[s]) != ref.both[s];
        }
    for (uint16_t v : sums.value) entries += v != 0;
    std::cerr << "poset_verify_checked = " << checked << "\nposet_verify_wrong = " << wrong
              << "\nposet_verify_entries = " << entries << '\n';
    return wrong ? 1 : 0;
}
#endif

// ==== Window assignment: pair relations and their fast evaluation ====

// profiling of the window assignment (DESIGN_PROFILE, a macro of the source, 0 by default):
// 1 writes the cycles (rdtsc) and the calls of its parts as `dprof_<part>_mcyc` / `dprof_<part>_calls` to
// stderr at the end of assign_windows; 3 also the parts of evaluate_move / matching_cost and counts of the
// pairs (`dpc_*`). The measurement itself takes time: not for comparisons of speed.
#ifndef DESIGN_PROFILE
#define DESIGN_PROFILE 0
#endif
#if DESIGN_PROFILE
enum DpPart {
    dp_aw_total, dp_aw_setup, dp_aw_loop, dp_aw_final, dp_aw_propose, dp_aw_cross, dp_aw_windows, dp_aw_transfer,
    dp_aw_screen, dp_aw_evaluate, dp_aw_matching, dp_aw_apply, dp_win_refresh, dp_win_forbid, dp_win_loop,
    dp_ev_collect, dp_ev_simd, dp_ev_pending, dp_ev_lookup, dp_ev_valid, dp_mc_keys, dp_mc_sort, dp_mc_greedy, dp_aw_sums,
    dp_aw_pairs, dp_parts
};
constexpr const char* kDpName[dp_parts] = {
    "aw_total", "aw_setup", "aw_loop", "aw_final", "aw_propose", "aw_cross", "aw_windows", "aw_transfer",
    "aw_screen", "aw_evaluate", "aw_matching", "aw_apply", "win_refresh", "win_forbid", "win_loop",
    "ev_collect", "ev_simd", "ev_pending", "ev_lookup", "ev_valid", "mc_keys", "mc_sort", "mc_greedy", "aw_sums",
    "aw_pairs"};
unsigned long long dp_cycles[dp_parts];
long long dp_calls[dp_parts];
// DESIGN_PROFILE >= 3: the pairs whose relations change (with opposite arcs), skipped by their witness,
// pending (closures computed), acyclic among them; the valid pairs, the sorted and the scanned entries.
long long dp_changed, dp_changed_both, dp_skipped, dp_npending, dp_acyclic, dp_nvalid, dp_mc_size, dp_mc_scanned,
    dp_mc_count, dp_forbid_group, dp_forbid_lost;
struct DpScope {
    int part;
    unsigned long long start;
    explicit DpScope(int p) : part(p), start(__builtin_ia32_rdtsc()) {}
    ~DpScope() {
        dp_cycles[part] += __builtin_ia32_rdtsc() - start;
        dp_calls[part]++;
    }
};
#define DP_SCOPE(part) DpScope DP_SCOPE_CAT(dp_scope_, __LINE__)(dp_##part)
#define DP_SCOPE_CAT2(a, b) a##b
#define DP_SCOPE_CAT(a, b) DP_SCOPE_CAT2(a, b)
void dp_report() {
    std::cerr << "dpc_changed = " << dp_changed << "\ndpc_changed_both = " << dp_changed_both
              << "\ndpc_skipped = " << dp_skipped << "\ndpc_npending = " << dp_npending << "\ndpc_acyclic = " << dp_acyclic
              << "\ndpc_nvalid = " << dp_nvalid << "\ndpc_mc_size = " << dp_mc_size << "\ndpc_mc_scanned = " << dp_mc_scanned
              << "\ndpc_mc_count = " << dp_mc_count << "\ndpc_forbid_group = " << dp_forbid_group
              << "\ndpc_forbid_lost = " << dp_forbid_lost << '\n';
    for (int i = 0; i < dp_parts; i++)
        std::cerr << "dprof_" << kDpName[i] << "_mcyc = " << dp_cycles[i] * 1e-6 << "\ndprof_" << kDpName[i]
                  << "_calls = " << dp_calls[i] << '\n';
}
#else
#define DP_SCOPE(part) ((void)0)
#endif

// Close pairs used only by assign_windows. Padding pairs have no differences and remain invalid.
// zeros / ones: for each physical window, a bitset of differing pairs whose first target has that
// color. OR-ing the bitsets of an edge's windows produces its two possible relation directions.
struct WindowPairs {
    int n = 0, n8 = 0;
    int words = 0;
    std::vector<u64> zeros, ones;
    std::vector<u64> au, diff;
    std::vector<uint32_t> dir;  // first target, differences, packed relations (WindowRelations)
    // 0 means incompatible, otherwise 1 + PosetSums::both_of(closure(dir)).
    std::vector<int> rel;
    // a cycle of dir (WindowRelations::witness; all bits for a compatible pair), size n8
    std::vector<uint32_t> wit;
    std::vector<int> u, v;
    void push(u64 au_, u64 diff_, u64 dir_, int u_, int v_, int rel_) {
        au.push_back(au_), diff.push_back(diff_), dir.push_back(dir_), u.push_back(u_), v.push_back(v_);
        rel.push_back(rel_);
        n++;
    }
    void pad() {
        const int real = n;
        while (n % 8) push(0, 0, 0, 0, 0, 0);
        n8 = n;
        n = real;
        words = (n8 + 63) / 64;
        zeros.assign(64 * words, 0);
        ones.assign(64 * words, 0);
        for (int p = 0; p < n; ++p)
            for (u64 x = diff[p]; x; x &= x - 1) {
                const int j = __builtin_ctzll(x);
                (au[p] >> j & 1 ? ones : zeros)[j * words + (p >> 6)] |= 1ULL << (p & 63);
            }
    }
};

// Only assign_windows uses this representation: bit e means ep[e].first is above ep[e].second,
// bit 16+e means the reverse. Opposite arcs can be detected by r & (r >> 16).
// Reject cyclic relations before looking up their cost in the compact PosetSums table.
struct WindowRelations {
    const PosetSums& sums;
    std::array<std::array<u64, 256>, 4> expand{};
    // the 40 cycles of three sheets (a above b above c above a), as packed relations
    alignas(32) std::array<uint32_t, 40> triangles{};
    explicit WindowRelations(const PosetSums& sums_) : sums(sums_) {
        std::array<u64, 32> arcs{};
        int index[6][6];
        for (int a = 0, e = 0; a < 6; ++a)
            for (int b = a + 1; b < 6; ++b, ++e) {
                arcs[e] = 1ULL << (8 * a + b);
                arcs[16 + e] = 1ULL << (8 * b + a);
                index[a][b] = e;
                index[b][a] = 16 + e;  // b above a
            }
        for (int chunk = 0; chunk < 4; ++chunk)
            for (unsigned v = 1; v < 256; ++v)
                expand[chunk][v] = expand[chunk][v & (v - 1)] | arcs[8 * chunk + __builtin_ctz(v)];
        // arc x above y: bit index[x][y]
        int t = 0;
        for (int a = 0; a < 6; ++a)
            for (int b = a + 1; b < 6; ++b)
                for (int c = b + 1; c < 6; ++c) {
                    triangles[t++] = (1U << index[a][b]) | (1U << index[b][c]) | (1U << index[c][a]);
                    triangles[t++] = (1U << index[a][c]) | (1U << index[c][b]) | (1U << index[b][a]);
                }
    }
    // The first of the cycles of three sheets contained in the relations r, 0 if none.
    __attribute__((target("avx2,bmi2,popcnt"))) uint32_t triangle(uint32_t r) const {
        const __m256i rv = _mm256_set1_epi32(int(r));
        u64 found = 0;
        for (int i = 0; i < 5; i++) {
            const __m256i m = _mm256_load_si256((const __m256i*)(triangles.data() + 8 * i));
            const __m256i hit = _mm256_cmpeq_epi32(_mm256_and_si256(rv, m), m);
            found |= u64(unsigned(_mm256_movemask_ps(_mm256_castsi256_ps(hit)))) << (8 * i);
        }
        return found ? triangles[__builtin_ctzll(found)] : 0;
    }
    // A witness of the incompatibility of a pair with relations r (rel = 0): a set of arcs with a cycle,
    // so that any relations containing it have a cycle: the first cycle of three sheets in r, else r
    // itself; ~0 (never contained) for a compatible pair (rel > 0). assign_windows uses it to skip the
    // changed pairs that keep it (they stay incompatible). It decides only which closures are computed.
    __attribute__((target("avx2,bmi2,popcnt"))) uint32_t witness(uint32_t r, int rel) const {
        if (rel) return ~0U;
        const uint32_t t = triangle(r);
        return t ? t : r;
    }
    // The closed relation bit matrix (bit 8a + b: a above b) of the packed relations r.
    __attribute__((always_inline)) u64 closure(uint32_t r) const {
        u64 c = expand[0][r & 255] | expand[1][(r >> 8) & 255] | expand[2][(r >> 16) & 255] | expand[3][r >> 24];
        // Six fixed pivots: the other two rows and columns are always zero.
        c |= (c & 0x0101010101010101ULL) * (c & 255);
        c |= ((c >> 1) & 0x0101010101010101ULL) * ((c >> 8) & 255);
        c |= ((c >> 2) & 0x0101010101010101ULL) * ((c >> 16) & 255);
        c |= ((c >> 3) & 0x0101010101010101ULL) * ((c >> 24) & 255);
        c |= ((c >> 4) & 0x0101010101010101ULL) * ((c >> 32) & 255);
        c |= ((c >> 5) & 0x0101010101010101ULL) * ((c >> 40) & 255);
        return c;
    }
    // the closures of four packed relations (as closure, one per 64-bit lane): the relation
    // matrices from pdep (kUpperPairs: bit e to 8a + b, the reverse bits transposed), then the same six
    // pivot steps, a pivot k adding row k to every row i with bit (i, k) (byte masks instead of the
    // multiplication).
    __attribute__((target("avx2,bmi2,popcnt"))) __m256i closure4(uint32_t r0, uint32_t r1, uint32_t r2,
                                                                  uint32_t r3) const {
        const __m128i rs = _mm_set_epi32(int(r3),int(r2),int(r1),int(r0));
        const __m128i mask = _mm_set1_epi32(255);
        __m256i c = _mm256_i32gather_epi64((const long long*)expand[0].data(),_mm_and_si128(rs,mask),8);
        c = _mm256_or_si256(c,_mm256_i32gather_epi64((const long long*)expand[1].data(),_mm_and_si128(_mm_srli_epi32(rs,8),mask),8));
        c = _mm256_or_si256(c,_mm256_i32gather_epi64((const long long*)expand[2].data(),_mm_and_si128(_mm_srli_epi32(rs,16),mask),8));
        c = _mm256_or_si256(c,_mm256_i32gather_epi64((const long long*)expand[3].data(),_mm_srli_epi32(rs,24),8));
        const __m256i ones = _mm256_set1_epi8(1);
        _Pragma("GCC unroll 6") for (int k = 0; k < 6; k++) {
            const __m256i mask = _mm256_cmpeq_epi8(_mm256_and_si256(_mm256_srli_epi64(c, k), ones), ones);
            const __m256i row = _mm256_shuffle_epi8(
                c, _mm256_setr_epi8(k, k, k, k, k, k, k, k, 8 + k, 8 + k, 8 + k, 8 + k, 8 + k, 8 + k, 8 + k, 8 + k, k, k,
                                    k, k, k, k, k, k, 8 + k, 8 + k, 8 + k, 8 + k, 8 + k, 8 + k, 8 + k, 8 + k));
            c = _mm256_or_si256(c, _mm256_and_si256(mask, row));
        }
        return c;
    }
    // Whether the relations r have a cycle (cost(r) == 0).
    __attribute__((always_inline)) bool cyclic(uint32_t r) const {
        return (r & (r >> 16)) || (closure(r) & kDiagonal);
    }
    // 0 if the relations r have a cycle, else 1 + PosetSums::both_of of their closure.
    __attribute__((always_inline)) int cost(uint32_t r) const {
        if (r & (r >> 16)) return 0;
        const u64 c = closure(r);
        if (c & kDiagonal) return 0;
        return 1 + sums.both_of(c);
    }
};

// The arcs implied by a closed relation c of the 15 pairs e = (x, y), x < y, of the six sheets (in
// the order of WindowRelations): bit e of `forward` is set if c has y above x, bit e of `reverse` if
// c has x above y. (Used by assign_windows to tell which new arc would close a cycle.)
__attribute__((target("bmi2"))) inline void implied_arcs(u64 c, uint32_t& forward, uint32_t& reverse) {
    forward = _pext_u64(c, 0x0000010101010100ULL) | (_pext_u64(c, 0x0000020202020000ULL) << 5) |
              (_pext_u64(c, 0x0000040404000000ULL) << 9) | (_pext_u64(c, 0x0000080800000000ULL) << 12) |
              (((c >> 44) & 1) << 14);
    reverse = _pext_u64(c, 0x00002030383c3eULL);
}

// AVX2 for one function (the judge compiles with -march=native; the local evaluation without it).
#define AVX2_TARGET __attribute__((target("avx2,bmi2,popcnt")))

// Evaluate a move without changing the current pair state. First collect the directions on the
// one or two changed edges, then update all relation lanes in SIMD. Cache lookups are in a separate
// loop so that they do not spill the SIMD loop's registers. Finally list compatible pairs in their
// original order (including ties in matching_cost). Padding keeps rel = 0 and never enters the list.
// A one-edge move uses the same algorithm with the duplicate edge calculations compiled out.
template <bool TwoEdges>
AVX2_TARGET int evaluate_move(WindowPairs& P, const WindowRelations& relations, u64 pol, u64 erase, u64 ma, u64 mb,
                              u64 fa, u64 fb, uint32_t* ndir, int* nrel, int* valid, int* pending, u64* closures) {
    const __m256i zero = _mm256_setzero_si256(), vkeep = _mm256_set1_epi32(uint32_t(~erase));
    const uint32_t* const pdir = P.dir.data();
    const int* const prel = P.rel.data();
    uint32_t* const pwit = P.wit.data();
    const int n8 = P.n8;
    static const std::array<std::array<int, 8>, 256> lanes = [] {
        std::array<std::array<int, 8>, 256> t{};
        for (int s = 0; s < 256; ++s)
            for (int l = 0, k = 0; l < 8; ++l)
                if (s >> l & 1) t[s][k++] = l;
        return t;
    }();
    // Eight pair flags in one vector; forward and reverse flags are shifted independently.
    alignas(32) static const std::array<std::array<uint32_t, 8>, 256> directions = [] {
        std::array<std::array<uint32_t, 8>, 256> t{};
        for (int s = 0; s < 256; ++s)
            for (int l = 0; l < 8; ++l) t[s][l] = (s >> l) & 1;
        return t;
    }();
    // At most 256*255/2 pairs, hence at most 510 words. Only P.words entries are touched.
    u64 af[512], ar[512], bf[512], br[512];
#if DESIGN_PROFILE >= 3
    unsigned long long t0 = __builtin_ia32_rdtsc();
#endif
    auto collect = [&](u64 mask, u64* f, u64* r) {
        std::fill(f, f + P.words, 0);
        std::fill(r, r + P.words, 0);
        for (; mask; mask &= mask - 1) {
            const int j = __builtin_ctzll(mask), offset = j * P.words;
            const u64* first = ((pol >> j & 1) ? P.ones : P.zeros).data() + offset;
            const u64* second = ((pol >> j & 1) ? P.zeros : P.ones).data() + offset;
            for (int w = 0; w < P.words; ++w) {
                f[w] |= first[w];
                r[w] |= second[w];
            }
        }
    };
    collect(ma, af, ar);
    if constexpr (TwoEdges) collect(mb, bf, br);
#if DESIGN_PROFILE >= 3
    unsigned long long t1 = __builtin_ia32_rdtsc();
    dp_cycles[dp_ev_collect] += t1 - t0;
#endif
    const __m128i shift_a = _mm_cvtsi32_si128(__builtin_ctzll(fa));
    const __m128i shift_b = _mm_cvtsi32_si128(__builtin_ctzll(fb));
    int npending = 0;
    for (int block = 0; block < P.words; ++block) {
        u64 a_fwd = af[block], a_rev = ar[block], b_fwd = 0, b_rev = 0;
        if constexpr (TwoEdges) b_fwd = bf[block], b_rev = br[block];
        const int end = std::min(n8, (block + 1) * 64);
        for (int p = block * 64; p < end; p += 8) {
            const __m256i dir = _mm256_loadu_si256((const __m256i*)(pdir + p));
            __m256i r = _mm256_and_si256(dir, vkeep);
            const __m256i ar = _mm256_or_si256(
                _mm256_load_si256((const __m256i*)directions[a_fwd & 255].data()),
                _mm256_slli_epi32(_mm256_load_si256((const __m256i*)directions[a_rev & 255].data()), 16));
            a_fwd >>= 8;
            a_rev >>= 8;
            r = _mm256_or_si256(r, _mm256_sll_epi32(ar, shift_a));
            if constexpr (TwoEdges) {
                const __m256i br = _mm256_or_si256(
                    _mm256_load_si256((const __m256i*)directions[b_fwd & 255].data()),
                    _mm256_slli_epi32(_mm256_load_si256((const __m256i*)directions[b_rev & 255].data()), 16));
                b_fwd >>= 8;
                b_rev >>= 8;
                r = _mm256_or_si256(r, _mm256_sll_epi32(br, shift_b));
            }
            const __m256i rsame = _mm256_cmpeq_epi32(r, dir);
            const __m256i noboth = _mm256_cmpeq_epi32(_mm256_and_si256(r, _mm256_srli_epi32(r, 16)), zero);
            // a changed pair whose new relations keep the witness cycle stays incompatible
            // (rel 0, as kept below) without its closure
            const __m256i still = _mm256_cmpeq_epi32(
                _mm256_andnot_si256(r, _mm256_loadu_si256((const __m256i*)(pwit + p))), zero);
            const int need =
                _mm256_movemask_ps(_mm256_castsi256_ps(_mm256_andnot_si256(_mm256_or_si256(rsame, still), noboth)));
#if DESIGN_PROFILE >= 3
            dp_changed += 8 - __builtin_popcount(_mm256_movemask_ps(_mm256_castsi256_ps(rsame)));
            dp_changed_both += __builtin_popcount(_mm256_movemask_ps(
                _mm256_castsi256_ps(_mm256_andnot_si256(noboth, _mm256_andnot_si256(rsame, _mm256_set1_epi32(-1))))));
            dp_skipped += __builtin_popcount(
                _mm256_movemask_ps(_mm256_castsi256_ps(_mm256_andnot_si256(rsame, _mm256_and_si256(noboth, still)))));
#endif
            _mm256_storeu_si256((__m256i*)(ndir + p), r);
            const __m256i kept = _mm256_and_si256(rsame, _mm256_loadu_si256((const __m256i*)(prel + p)));
            _mm256_storeu_si256((__m256i*)(nrel + p), kept);
            _mm256_storeu_si256(
                (__m256i*)(pending + npending),
                _mm256_add_epi32(_mm256_set1_epi32(p), _mm256_loadu_si256((const __m256i*)lanes[need].data())));
            npending += __builtin_popcount(need);
        }
    }
#if DESIGN_PROFILE >= 3
    unsigned long long t2 = __builtin_ia32_rdtsc();
    dp_cycles[dp_ev_simd] += t2 - t1;
    dp_npending += npending;
#endif
    // the closures first, without a branch on their cycles (pending[] is compacted to the
    // acyclic pairs, their closures into closures[]; the cyclic pairs go to valid[] for the moment), then
    // the table lookups of the acyclic ones. The same values as relations.cost: the pending pairs have no
    // opposite arcs.
    // Four closures at a time in AVX2 (relations.closure4), the rest one by one.
    int nacyclic = 0, ncyclic = 0, k = 0;
    for (; k + 4 <= npending; k += 4) {
        const int p0 = pending[k], p1 = pending[k + 1], p2 = pending[k + 2], p3 = pending[k + 3];
        alignas(32) u64 c4[4];
        _mm256_store_si256((__m256i*)c4, relations.closure4(ndir[p0], ndir[p1], ndir[p2], ndir[p3]));
        const int ps[4] = {p0, p1, p2, p3};
        for (int l = 0; l < 4; l++) {
            const int acyclic = !(c4[l] & kDiagonal);
            closures[nacyclic] = c4[l];
            pending[nacyclic] = ps[l];
            nacyclic += acyclic;
            valid[ncyclic] = ps[l];
            ncyclic += acyclic ^ 1;
        }
    }
    for (; k < npending; ++k) {
        const int p = pending[k];
        const u64 c = relations.closure(ndir[p]);
        const int acyclic = !(c & kDiagonal);
        closures[nacyclic] = c;
        pending[nacyclic] = p;
        nacyclic += acyclic;
        valid[ncyclic] = p;
        ncyclic += acyclic ^ 1;
    }
    // A pair found incompatible here takes as its new witness a cycle of three sheets that its present
    // relations share with the new ones, if any (a cycle of the present relations that this move does
    // not break). A witness is any set of arcs with a cycle, so the replacement keeps the evaluation exact.
    for (int k = 0; k < ncyclic; ++k) {
        const int p = valid[k];
        const uint32_t t = relations.triangle(pdir[p] & ndir[p]);
        if (t) pwit[p] = t;
    }
#if DESIGN_PROFILE >= 3
    unsigned long long tl = __builtin_ia32_rdtsc();
#endif
    for (int k = 0; k < nacyclic; ++k) nrel[pending[k]] = 1 + relations.sums.both_of(closures[k]);
#if DESIGN_PROFILE >= 3
    dp_cycles[dp_ev_lookup] += __builtin_ia32_rdtsc() - tl;
    dp_acyclic += nacyclic;
#endif
#if DESIGN_PROFILE >= 3
    unsigned long long t3 = __builtin_ia32_rdtsc();
    dp_cycles[dp_ev_pending] += t3 - t2;
#endif
    int nvalid = 0;
    for (int p = 0; p < n8; p += 8) {
        const __m256i rel4 = _mm256_loadu_si256((const __m256i*)(nrel + p));
        const int good = _mm256_movemask_ps(_mm256_castsi256_ps(_mm256_cmpgt_epi32(rel4, zero)));
        _mm256_storeu_si256(
            (__m256i*)(valid + nvalid),
            _mm256_add_epi32(_mm256_set1_epi32(p), _mm256_loadu_si256((const __m256i*)lanes[good].data())));
        nvalid += __builtin_popcount(good);
    }
#if DESIGN_PROFILE >= 3
    dp_cycles[dp_ev_valid] += __builtin_ia32_rdtsc() - t3;
    dp_nvalid += nvalid;
#endif
    return nvalid;
}

// AS_PROFILE adds operator yield and cycle counts without changing proposals.
#ifndef AS_PROFILE
#define AS_PROFILE 0
#endif
#if AS_PROFILE
struct AssignProfile {
    long long proposed = 0, candidates = 0, memo = 0, accepted = 0, descending = 0, improved = 0;
    long long entering = 0, new_valid = 0;
    double descent = 0, best_gain = 0;
    unsigned long long propose_cycles = 0, matching_cycles = 0;
};
struct AssignScope {
    unsigned long long& total;
    unsigned long long start = __builtin_ia32_rdtsc();
    explicit AssignScope(unsigned long long& t) : total(t) {}
    ~AssignScope() { total += __builtin_ia32_rdtsc() - start; }
};
#endif

// ==== Window assignment: annealing and climb (assign_windows) ====

// Which windows are generic and the pair of sheets and colors of each generic window (`edge`,
// `polarity` in and out), by annealing until `seconds` (or `fixed_iters` iterations), then a climb
// on the same objective (climb_steps steps, or for climb_seconds). On return the windows are
// renumbered so that the generic ones are 0..g-1: A is rewritten, and permutation[j] is the original
// window of internal window j. Needs m = 6 (PosetSums); otherwise nothing is changed.
// Objective: a greedy matching of 71 compatible close pairs (distance <= 26),
// priced by 0.5 handle differences + both targets' mean generic moves + 0.04 differences.
// The mean pair cost has a penalty of 10 per missing pair. Integer keys in 1/3600
// (1800 hd + 5 PosetSums::both_of + 144 d) have stable ties by pair index.
// Moves change window roles, sheet pairs or polarity; evaluate_pairs updates the
// affected relations before the exact matching. A rejected move restores mask/pol.
struct WindowStats {
    int iterations = 0;
    double gobj_before = 0, gobj_after = 0;  // objective before / after the climb
    int climb_steps = 0;
};
WindowStats assign_windows(std::vector<u64>& A, int m, int g, std::vector<std::pair<int, int>>& edges,
                           std::vector<int>& polarity, std::vector<int>& permutation, double seconds, int fixed_iters,
                           int climb_steps, double climb_seconds) {
    constexpr int kCutoff = 26;
    constexpr int kRejectLoss = 3, kMemoSize = 1 << 18;
    constexpr double kWindowRate = 0.6;
    constexpr int kMapStall = 256, kClimbStall = 512, kTabuAccepted = 4;
    const int as_elite = std::getenv("AS_ELITE") ? env_int("AS_ELITE") : 1;
    const double as_work = std::getenv("AS_WORK") ? std::atof(std::getenv("AS_WORK")) : 1.0;
    fixed_iters = int(fixed_iters * as_work); climb_steps = int(climb_steps * as_work);
    constexpr int as_screen = 0;  // Its ordinary-move screen is no longer used.
    WindowStats stats;
    if (m != 6 || g >= 64 || g < m * (m - 1) / 2) return stats;
#ifdef POSET_VERIFY
    std::exit(poset_verify());  // (test only: any input)
#endif
#if DESIGN_PROFILE
    const unsigned long long dp_setup_start = __builtin_ia32_rdtsc();
#endif
    const auto start = Clock::now();
#if DESIGN_PROFILE
    const unsigned long long dp_sums_start = __builtin_ia32_rdtsc();
#endif
    const PosetSums& sums = PosetSums::get();
    WindowRelations relations(sums);
#if DESIGN_PROFILE
    dp_cycles[dp_aw_sums] += __builtin_ia32_rdtsc() - dp_sums_start;
#endif
    XorShift rng{0x71eb2566be932e31ULL};
    const int n = int(A.size()), need = 256 - (191 - m);
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
    // position[w] = the index of window w in order (instead of a search); select_bit(x, k) =
    // the k-th set bit of x (k < popcount(x)), as clearing the lowest bit k times
    std::array<int, 64> position;
    std::iota(position.begin(), position.end(), 0);
    auto select_bit = [](u64 x, int k) __attribute__((target("bmi2"))) { return __builtin_ctzll(_pdep_u64(1ULL << k, x)); };
    u64 pol = 0;                             // window j: 1 if the first sheet of its pair is black
    u64 hm = kActiveWindows & ~low_bits(g);  // cap is neither generic nor a handle
    for (int e = 0; e < ne; e++) {
        fwd[e] = 1ULL << e;
        rev[e] = 1ULL << (16 + e);
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
    // Packed relations and exact compatibility / costs under the current mask / pol.
    WindowPairs pairs;
    auto pair_state = [&](u64 au, u64 d, uint32_t& r, int& rel) {
        r = 0;
        const u64 z = au ^ pol;
        for (int e = 0; e < ne; e++) {
            u64 q = d & mask[e];
            if (q & ~z) r |= fwd[e];
            if (q & z) r |= rev[e];
        }
        rel = relations.cost(uint32_t(r));
    };
#if DESIGN_PROFILE
    const unsigned long long dp_pairs_start = __builtin_ia32_rdtsc();
#endif
    for (int u = 0; u < n; u++)
        for (int v = u + 1; v < n; v++) {
            const u64 d = A[u] ^ A[v];
            if (__builtin_popcountll(d) > kCutoff) continue;
            uint32_t r;
            int rel;
            pair_state(A[u], d, r, rel);
            pairs.push(A[u], d, r, u, v, rel);
        }
    pairs.pad();
#if DESIGN_PROFILE
    dp_cycles[dp_aw_pairs] += __builtin_ia32_rdtsc() - dp_pairs_start;
#endif

    const int np = pairs.n, np8 = pairs.n8;
    std::vector<uint32_t> ndir(np8);
    std::vector<int> nrel(np8);
    std::vector<int> valid(np8 + 8), pending(np8 + 8);
    std::vector<u64> closures(np8 + 8);  // evaluate_move's closures of the pending pairs
    // the witnesses of the pairs (WindowRelations::witness), all of them at the start and after
    // the annealing; evaluate_move replaces those that fail.
    pairs.wit.resize(np8);
    for (int p = 0; p < np8; p++) pairs.wit[p] = relations.witness(pairs.dir[p], pairs.rel[p]);
    int nvalid = 0;
    std::vector<int> full144(np);  // 144 differences of each pair
    for (int p = 0; p < np; p++) full144[p] = 144 * __builtin_popcountll(pairs.diff[p]);
    // Only `valid[0..nvalid)` is traversed here. A nonzero rel stores the original rel + 1.
    // a sort entry packs key << 32 | pair << 16 | u << 8 | v (pair_tail[p]: the low half), so
    // the ascending order of the entries is stable by key (ties in the order
    // of the pairs, as valid[] lists them) and the greedy reads the two targets from the entry.
    std::vector<uint32_t> pair_tail(np);
    for (int p = 0; p < np; p++) pair_tail[p] = uint32_t(p) << 16 | uint32_t(pairs.u[p]) << 8 | uint32_t(pairs.v[p]);
    std::vector<u64> keyed(np), tmp(np), sorted(np);
    std::vector<int> selected, candidate_selected;
    long long screen_rejected = 0, screen_checks = 0, accepted = 0;
    auto matching_cost = [&](const int* rel, u64 handle_mask) __attribute__((target("popcnt"))) {
#if DESIGN_PROFILE >= 3
        unsigned long long mt0 = __builtin_ia32_rdtsc();
#endif
        std::array<int, 512> high{};
        int min_high = 511, max_high = 0;
        const int size = nvalid;
        for (int i = 0; i < size; i++) {
            const int p = valid[i];
            const int key = 1800 * __builtin_popcountll(pairs.diff[p] & handle_mask) + 5 * int(rel[p] - 1) + full144[p];
            // hd <= 26, full144 <= 144*26, rel <= 4380: the key fits 17 bits.
            assert(key < (1 << 17));
            keyed[i] = u64(key) << 32 | pair_tail[p];
            high[key >> 8]++;
            min_high = std::min(min_high, key >> 8);
            max_high = std::max(max_high, key >> 8);
        }
#if DESIGN_PROFILE >= 3
        unsigned long long mt1 = __builtin_ia32_rdtsc();
        dp_cycles[dp_mc_keys] += mt1 - mt0;
#endif
        for (int i = min_high, h = 0; i <= max_high; ++i) {
            const int b = high[i];
            high[i] = h;
            h += b;
        }
        // Partition by the high key first. Each short bucket is ordered by
        // the complete integer key, including its original pair-index tie.
        for(int i=0;i<size;++i)sorted[high[keyed[i]>>40]++]=keyed[i];
        for(int bucket=min_high,begin=0;bucket<=max_high;++bucket) {
            const int end=high[bucket];
            std::sort(sorted.begin()+begin,sorted.begin()+end);
            begin=end;
        }
#if DESIGN_PROFILE >= 3
        unsigned long long mt2 = __builtin_ia32_rdtsc();
        dp_cycles[dp_mc_sort] += mt2 - mt1;
        int dp_last = size;
#endif
        // The greedy without branches on the targets: an entry is taken (ok) when both its targets are
        // free; out[matched] is overwritten until an entry is taken.
        candidate_selected.resize(need);
        int* const out = candidate_selected.data();
        std::array<unsigned char, 256> used{};
        int matched = 0;
        long long total = 0;
        for (int i = 0; i < size; i++) {
            const u64 x = sorted[i];
            const unsigned u = unsigned(x >> 8) & 255, v = unsigned(x) & 255;
            const int ok = (used[u] | used[v]) ^ 1;
            used[u] |= ok;
            used[v] |= ok;
            out[matched] = int(x >> 16) & 0xffff;
            total += ok ? (long long)(x >> 32) : 0LL;
            matched += ok;
            if (matched == need) {
#if DESIGN_PROFILE >= 3
                dp_last = i + 1;
#endif
                break;
            }
        }
        candidate_selected.resize(matched);
#if DESIGN_PROFILE >= 3
        dp_cycles[dp_mc_greedy] += __builtin_ia32_rdtsc() - mt2;
        dp_mc_size += size;
        dp_mc_scanned += dp_last;
        dp_mc_count++;
#endif
        return double(total) / (need * 3600) + (need - matched) * 10.0;
    };
    // ==== Window assignment: candidate screens and tables ====

    // A move: its windows and sheet pairs; propose changes mask / pol and evaluates the move on all
    // the pairs (ndir, nrel, valid); apply_move keeps it, undo_move restores mask / pol.
    struct Move {
        int ia, ib, a, b, kind, ea, eb, transfer;
        bool swindow;
        u64 olda, oldb, oldpol;
        bool elite = false;
    };
    auto undo_move = [&](const Move& mv) {
        mask[mv.ea] = mv.olda;
        mask[mv.eb] = mv.oldb;
        pol = mv.oldpol;
    };
    // A swap deletes window a and adds window b. For every selected pair, deletion leaves a DAG.
    // Its closure tells which of the two new arcs would create a cycle. Pack these prohibitions
    // for the selected pairs into two words, then count swap losses with two popcounts.
    using Bits = std::array<u64, 2>;
    using Colors = std::array<Bits, 2>;
    std::array<Colors, 64> match_colors{}, forbidden{};
    std::array<unsigned char, 64> forbidden_ready{};
    std::array<Colors, 15> group_forbidden{};
    std::array<unsigned char, 15> group_ready{};
    std::vector<u64> match_closed;
    std::vector<int> screen_selected, screen_pos(np, -1);
    std::vector<unsigned> screen_present(np, 0);
    std::vector<uint32_t> screen_dirs;
    unsigned screen_serial = 0;
    long long screen_color_pairs = 0, screen_refreshes = 0;
    bool screen_dirty = true;
    auto closure = [&](uint32_t r) { return relations.closure(r); };
    // The number of selected pairs (bit i of a Bits: the i-th of `selected`) that become incompatible
    // when the generic window mv.a leaves its pair of sheets and the handle window mv.b joins it with
    // the color pol gives b: forbidden[a][0 / 1] are the pairs whose closure without a forbids the
    // new arc in each direction, match_colors[b][color] the pairs that differ at b with that color of
    // their first target.
    auto refresh_screen = [&] __attribute__((target("avx2,bmi2,popcnt"))) {
        if (screen_dirty) {
#if DESIGN_PROFILE >= 3
            DP_SCOPE(win_refresh);
#endif
            ++screen_refreshes;
            auto toggle_colors = [&](int i, int p) {
                ++screen_color_pairs;
                const u64 bit = 1ULL << (i & 63);
                for (u64 q = pairs.diff[p]; q; q &= q - 1) {
                    const int j = __builtin_ctzll(q);
                    match_colors[j][(pairs.au[p] >> j) & 1][i >> 6] ^= bit;
                }
            };
            if (screen_selected.size() != selected.size()) {
                match_colors = {};
                std::fill(screen_pos.begin(), screen_pos.end(), -1);
                screen_selected = selected;
                for (int i = 0; i < int(selected.size()); ++i) {
                    screen_pos[selected[i]] = i;
                    toggle_colors(i, selected[i]);
                }
                // Four zero closures pad the four-lane reads of group_forbidden.
                match_closed.assign(selected.size() + 4, 0);
                screen_dirs.assign(selected.size(), ~0U);
            } else {
                // Keep surviving pairs in their bit positions. Only removed/new pairs
                // need color-bit updates, even when their matching cost order changes.
                ++screen_serial;
                for (int p : selected) screen_present[p] = screen_serial;
                std::array<int, 128> empty{};
                int count = 0;
                for (int i = 0; i < int(screen_selected.size()); ++i) {
                    const int p = screen_selected[i];
                    if (screen_present[p] == screen_serial) continue;
                    toggle_colors(i, p);
                    screen_pos[p] = -1;
                    empty[count++] = i;
                }
                for (int p : selected)
                    if (screen_pos[p] < 0) {
                        const int i = empty[--count];
                        screen_selected[i] = p;
                        screen_pos[p] = i;
                        toggle_colors(i, p);
                    }
                selected = screen_selected;
            }
            forbidden_ready = {};
            group_ready = {};
            for (int i = 0; i < int(selected.size()); ++i) {
                const uint32_t r = pairs.dir[selected[i]];
                if (screen_dirs[i] != r) {
                    screen_dirs[i] = r;
                    match_closed[i] = closure(r);
                }
            }
            screen_dirty = false;
        }
    };
    auto swap_losses = [&](const Move& mv) __attribute__((target("avx2,bmi2,popcnt"))) {
        refresh_screen();
        const int a = mv.a, e = mv.ea;
        if (!forbidden_ready[a]) {
#if DESIGN_PROFILE >= 3
            DP_SCOPE(win_forbid);
#endif
            const auto [x, y] = ep[e];
            if (!group_ready[e]) {
#if DESIGN_PROFILE >= 3
                dp_forbid_group++;
#endif
                group_forbidden[e] = {};
                // four closures at a time, the two bits moved to the sign bits of the lanes
                const __m128i to_sign0 = _mm_cvtsi32_si128(63 - (8 * y + x)), to_sign1 = _mm_cvtsi32_si128(63 - (8 * x + y));
                for (int i = 0; i < int(selected.size()); i += 4) {
                    const __m256i c = _mm256_loadu_si256((const __m256i*)(match_closed.data() + i));
                    const u64 b0 = unsigned(_mm256_movemask_pd(_mm256_castsi256_pd(_mm256_sll_epi64(c, to_sign0))));
                    const u64 b1 = unsigned(_mm256_movemask_pd(_mm256_castsi256_pd(_mm256_sll_epi64(c, to_sign1))));
                    group_forbidden[e][0][i >> 6] |= b0 << (i & 63);
                    group_forbidden[e][1][i >> 6] |= b1 << (i & 63);
                }
                group_ready[e] = 1;
            }
            forbidden[a] = group_forbidden[e];
            Colors remaining{};
            for (u64 q = mv.olda & ~(1ULL << a); q; q &= q - 1) {
                const int j = __builtin_ctzll(q), color = (mv.oldpol >> j) & 1;
                for (int w = 0; w < 2; ++w) {
                    remaining[0][w] |= match_colors[j][color][w];
                    remaining[1][w] |= match_colors[j][color ^ 1][w];
                }
            }
            const int color = (mv.oldpol >> a) & 1;
            for (int w = 0; w < 2; ++w) {
                const u64 lost_fwd = match_colors[a][color][w] & ~remaining[0][w];
                const u64 lost_rev = match_colors[a][color ^ 1][w] & ~remaining[1][w];
                // Only a pair losing its last arc in this direction needs a new closure.
                // without a new closure. The pair is compatible (selected), so its relations r
                // are acyclic and match_closed[i] is their closure C. Without the lost arc (x above y, or
                // y above x), the closure keeps no arc the other way (it is contained in C), and keeps this
                // one when another successor z of its upper sheet reaches its lower sheet in C (a path
                // from z never uses the lost arc: z would reach z).
                for (u64 q = lost_fwd | lost_rev; q; q &= q - 1) {
#if DESIGN_PROFILE >= 3
                    dp_forbid_lost++;
#endif
                    const int bit = __builtin_ctzll(q), i = 64 * w + bit;
                    const u64 flag = 1ULL << bit;
                    const uint32_t r = pairs.dir[selected[i]];
                    const bool is_fwd = lost_fwd & flag;
                    const int upper = is_fwd ? x : y, lower = is_fwd ? y : x;
                    const u64 matrix = _pdep_u64(r & 0x7fff, kUpperPairs) | transpose8(_pdep_u64((r >> 16) & 0x7fff, kUpperPairs));
                    const u64 successors = (matrix >> (8 * upper)) & 63 & ~(1ULL << lower);
                    const bool kept = _pdep_u64(successors, 0x0000010101010101ULL) & (match_closed[i] >> lower);
                    forbidden[a][0][w] &= ~flag;
                    forbidden[a][1][w] &= ~flag;
                    if (kept) forbidden[a][is_fwd ? 1 : 0][w] |= flag;
                }
            }
            forbidden_ready[a] = 1;
        }
        const int b = mv.b, c = (pol >> b) & 1;
        int lost = 0;
        for (int w = 0; w < 2; ++w)
            lost += __builtin_popcountll((match_colors[b][c][w] & forbidden[a][0][w]) |
                                         (match_colors[b][c ^ 1][w] & forbidden[a][1][w]));
        return lost;
    };
    long long direct_checks = 0, direct_rejects = 0;
    // Cache exact objective values of repeated neighbors while the current assignment is unchanged.
    // A cache hit can still be accepted by annealing; in that case rebuild its complete state.
    std::vector<unsigned> memo_epoch(kMemoSize, 0);
    std::vector<double> memo_value(kMemoSize);
    long long screen_hits = 0;
    unsigned epoch = 1;
    int move_key = 0;
    bool memo_hit = false;
    long long memo_hits = 0, exact_evals = 0;
    std::array<uint32_t, 64> transfer_options{};
    std::array<std::array<int, 30>, 64> transfer_priority{};
    std::array<unsigned, 64> transfer_epoch{};
    long long transfer_rows = 0, transfer_samples = 0;
    long long transfer_empty = 0, transfer_single = 0, transfer_many = 0;
    // The destinations of a transfer of the generic window a (pair of sheets ea) to another pair:
    // bit code of the result (code = e + 15 color) is the pair of sheets e with the new color of a,
    // kept when fewer than kRejectLoss selected pairs (those differing at a) become incompatible
    // (bit-sliced counters ones / twos / four / eight of the incompatible pairs per code), with the
    // increase of the PosetSums cost of the others in transfer_priority[a][code].
    auto make_transfer_options = [&](int a, int ea) __attribute__((target("avx2,bmi2,popcnt"))) {
        uint32_t ones = 0, twos = 0, four = 0, eight = 0;
        const uint32_t allowed = ((1U << 30) - 1) & ~((1U << ea) | (1U << (ea + 15)));
        struct Saved {
            u64 closure;
            uint32_t forward, reverse;
            int color;
        };
        std::array<Saved, 128> saved;
        int size = 0;
        const u64 rest = mask[ea] & ~(1ULL << a);
        const uint32_t keep = ~(fwd[ea] | rev[ea]);
        // the selected pairs that differ at a (in their order, without a branch), their new
        // relations, and their closures four at a time; then the same sequential pass as before
        std::array<int, 132> differing;
        std::array<uint32_t, 132> rs{};
        alignas(32) std::array<u64, 132> closed;
        int nd = 0;
        for (int p : selected) {
            differing[nd] = p;
            nd += int(pairs.diff[p] >> a & 1);
        }
        for (int i = 0; i < nd; i++) {
            const int p = differing[i];
            const u64 q = pairs.diff[p] & rest, z = pairs.au[p] ^ pol;
            uint32_t r = pairs.dir[p] & keep;
            if (q & ~z) r |= fwd[ea];
            if (q & z) r |= rev[ea];
            rs[i] = r;
        }
        for (int i = 0; i < nd; i += 4)
            _mm256_store_si256((__m256i*)(closed.data() + i), relations.closure4(rs[i], rs[i + 1], rs[i + 2], rs[i + 3]));
        for (int i = 0; i < nd; i++) {
            const int p = differing[i];
            const u64 c = closed[i];
            uint32_t forward, reverse;
            implied_arcs(c, forward, reverse);
            const int color = (pairs.au[p] >> a) & 1;
            const uint32_t bad = color ? reverse | (forward << 15) : forward | (reverse << 15);
            saved[size++] = {c, forward, reverse, color};
            const uint32_t carry = ones & bad;
            ones ^= bad;
            const uint32_t carry2 = twos & carry;
            twos ^= carry;
            eight |= four & carry2;
            four ^= carry2;
            // Once every destination meets the rejection threshold, later pairs cannot rescue it.
            if (!(allowed & ~(eight | four | (twos & ones)))) {
                ++transfer_empty;
                return 0U;
            }
        }
        const uint32_t available = allowed & ~(eight | four | (twos & ones));
        if (!(available & (available - 1))) {
            // With one destination there is no ranking to compute.
            transfer_priority[a][__builtin_ctz(available)] = 0;
            ++transfer_single;
            return available;
        }
        ++transfer_many;
        // Compute only the destinations surviving the loss screen.
        for (uint32_t options = available; options; options &= options - 1) {
            const int code = __builtin_ctz(options), e = code % 15;
            int cost = 0;
            for (int i = 0; i < size; ++i) {
                if ((saved[i].forward | saved[i].reverse) >> e & 1) continue;
                auto [x, y] = ep[e];
                if ((code / 15) ^ saved[i].color) std::swap(x, y);
                const u64 c = saved[i].closure;
                const u64 from = ((c >> x) & 0x010101010101ULL) | (1ULL << (8 * x));
                const u64 to = ((c >> (8 * y)) & 63) | (1ULL << y);
                cost += sums.both_of(c | (from * to)) - sums.both_of(c);
            }
            transfer_priority[a][code] = cost;
        }
        return available;
    };
    // the remainders by g and 63 - g with the divisors as constants for the generic window
    // counts of design_papers (38, 32, 28): the compiler divides by a multiplication (the same remainders).
    auto generic_index = [&] {
        const u64 x = rng.next();
        switch (g) {
            case 38: return int(x % 38);
            case 32: return int(x % 32);
            case 28: return int(x % 28);
            default: return int(x % g);
        }
    };
    auto handle_index = [&] {
        const u64 x = rng.next();
        switch (g) {
            case 38: return int(x % 25);
            case 32: return int(x % 31);
            case 28: return int(x % 35);
            default: return int(x % (63 - g));
        }
    };
    // Each row contains all handle/color replacements losing fewer than kRejectLoss pairs.
    // Consume a row without replacement in the current state; acceptance invalidates all rows.
    std::array<Bits, 64> window_options{};
    std::array<unsigned, 64> window_epoch{};
    long long window_rows = 0, window_samples = 0;
    auto prepare_windows = [&](int a, int ea) __attribute__((target("popcnt"))) {
        Move probe{};
        probe.a = a;
        probe.b = __builtin_ctzll(hm);
        probe.ea = ea;
        probe.olda = mask[ea];
        probe.oldpol = pol;
        swap_losses(probe);  // Refresh selected colors and the closure after removing a.
#if DESIGN_PROFILE >= 3
        DP_SCOPE(win_loop);
#endif
        Bits available{};
        for (u64 q = hm & kActiveWindows; q; q &= q - 1) {
            const int b = __builtin_ctzll(q);
            for (int color = 0; color < 2; ++color) {
                int loss = 0;
                for (int w = 0; w < 2; ++w)
                    loss += __builtin_popcountll((match_colors[b][color][w] & forbidden[a][0][w]) |
                                                 (match_colors[b][color ^ 1][w] & forbidden[a][1][w]));
                available[color] |= u64(loss < kRejectLoss) << b;
            }
        }
        ++window_rows;
        return available;
    };
    // Cross moves: the generic window a leaves its pair ea and a handle window b becomes generic in
    // another pair of sheets e with a new color (code = e + 15 color). cross_options[a][b]: the codes
    // that lose fewer than three selected pairs (rejected: three or more), split by their losses into
    // cross_zero (0) and cross_one (1); the others lose 2.
    std::array<std::array<uint32_t, 64>, 64> cross_options{};
    std::array<std::array<uint32_t, 64>, 64> cross_zero{}, cross_one{};
    std::array<unsigned, 64> cross_epoch{};
    long long cross_rows = 0, cross_samples = 0, cross_accepts = 0;
    auto prepare_cross = [&](int a, int ea) __attribute__((target("avx2,bmi2,popcnt"))) {
        std::array<uint32_t, 64> ones{}, twice{}, rejected{}, options{};
        const u64 rest = mask[ea] & ~(1ULL << a);
        const uint32_t keep = ~uint32_t(fwd[ea] | rev[ea]);
        // the relations of the selected pairs first, their closures four at a time
        const int ns = int(selected.size());
        alignas(32) std::array<u64, 132> closed;
        std::array<uint32_t, 132> rs{};
        for (int i = 0; i < ns; i++) {
            const int p = selected[i];
            const u64 q = pairs.diff[p] & rest, z = pairs.au[p] ^ pol;
            uint32_t r = pairs.dir[p] & keep;
            if (q & ~z) r |= fwd[ea];
            if (q & z) r |= rev[ea];
            rs[i] = r;
        }
        for (int i = 0; i < ns; i += 4)
            _mm256_store_si256((__m256i*)(closed.data() + i), relations.closure4(rs[i], rs[i + 1], rs[i + 2], rs[i + 3]));
        for (int i = 0; i < ns; i++) {
            const int p = selected[i];
            const u64 c = closed[i];
            uint32_t forward, reverse;
            implied_arcs(c, forward, reverse);
            for (u64 windows = pairs.diff[p] & hm; windows; windows &= windows - 1) {
                const int b = __builtin_ctzll(windows);
                const uint32_t bad = (pairs.au[p] >> b & 1) ? reverse | (forward << 15) : forward | (reverse << 15);
                // Parallel counters saturate when a third selected pair becomes incompatible.
                rejected[b] |= twice[b] & bad;
                twice[b] |= ones[b] & bad;
                ones[b] ^= bad;
            }
        }
        const uint32_t allowed = ((1U << 30) - 1) & ~((1U << ea) | (1U << (ea + 15)));
        for (u64 windows = hm; windows; windows &= windows - 1) {
            const int b = __builtin_ctzll(windows);
            options[b] = allowed & ~rejected[b];
            cross_zero[a][b] = options[b] & ~(ones[b] | twice[b]);
            cross_one[a][b] = options[b] & ones[b] & ~twice[b];
        }
        ++cross_rows;
        return options;
    };
    // The relations of all the pairs under the proposed mask / pol into ndir / nrel / valid (pairs
    // that differ neither on the windows of ea nor on those of eb come out unchanged).
    auto evaluate_pairs = [&](int ea, int eb) {
        if (ea == eb)
            nvalid = evaluate_move<false>(pairs, relations, pol, fwd[ea] | rev[ea], mask[ea], mask[ea], fwd[ea], fwd[ea],
                                          ndir.data(), nrel.data(), valid.data(), pending.data(), closures.data());
        else
            nvalid = evaluate_move<true>(pairs, relations, pol, fwd[ea] | rev[ea] | fwd[eb] | rev[eb], mask[ea],
                                         mask[eb], fwd[ea], fwd[eb], ndir.data(), nrel.data(), valid.data(),
                                         pending.data(), closures.data());
    };
    // Proposes a random move (changing mask / pol); false if there is none to evaluate (a rejected
    // or impossible move, already undone). Otherwise the move's pairs are evaluated (or memo_hit).
#if AS_PROFILE
    std::array<std::array<AssignProfile, 6>, 5> as_profile{};
    int as_phase = 0;
    auto as_kind = [](const Move& x) { return x.elite ? 5 : x.swindow ? (x.ea == x.eb ? 0 : 4) : x.kind < 3 ? 1 : x.kind < 8 ? 2 : 3; };
#endif
    // ==== Window assignment: ordinary moves ====

    auto propose = [&](Move& mv) {
        int ia = generic_index(), ib = generic_index(), a = order[ia], b = order[ib];
        bool swindow = rng.real() < kWindowRate;
        if (swindow) {
            ib = g + handle_index();
            b = order[ib];
        }
        int kind = rng.mod(10), ea = which[a], eb = swindow ? ea : which[b];
        u64 olda = mask[ea], oldb = mask[eb], oldpol = pol;
        int transfer = -1;
        const bool cross_move = swindow && counts[ea] >= 2 && selected.size() == unsigned(need) && rng.mod(16) == 0;
#if AS_PROFILE
        auto& ap = as_profile[as_phase][swindow ? (cross_move ? 4 : 0) : kind < 3 ? 1 : kind < 8 ? 2 : 3];
        ++ap.proposed;
        AssignScope as_time(ap.propose_cycles);
#endif
        // Retain the same proposal draws and budget for the remaining moves.
        // These slots used to propose ordinary generic flips/exchanges.
        if (!swindow && kind < 8) return false;
        if (cross_move) {  // generic window a -> handle, handle window b -> generic in another pair
            if (cross_epoch[a] != epoch) {
                DP_SCOPE(aw_cross);
                cross_options[a] = prepare_cross(a, ea);
                cross_epoch[a] = epoch;
            }
            std::array<int, 3> totals{};
            auto options_at = [&](int b, int level) {
                uint32_t bits = cross_options[a][b];
                if (level == 0) bits &= cross_zero[a][b];
                if (level == 1) bits &= cross_one[a][b];
                if (level == 2) bits &= ~(cross_zero[a][b] | cross_one[a][b]);
                return bits;
            };
            for (u64 windows = hm; windows; windows &= windows - 1) {
                const int b = __builtin_ctzll(windows);
                for (int level = 0; level < 3; ++level) totals[level] += __builtin_popcount(options_at(b, level));
            }
            if (!(totals[0] + totals[1] + totals[2])) return false;
            // Loss classes 0/1/2 receive 4/2/1 tickets per eligible direction.
            int level = 0, skip = rng.below(4 * totals[0] + 2 * totals[1] + totals[2]);
            while (skip >= (totals[level] << (2 - level))) {
                skip -= totals[level] << (2 - level);
                ++level;
            }
            skip >>= 2 - level;
            int code = 0;
            for (u64 windows = hm; windows; windows &= windows - 1) {
                b = __builtin_ctzll(windows);
                uint32_t options = options_at(b, level);
                const int count = __builtin_popcount(options);
                if (skip >= count) {
                    skip -= count;
                    continue;
                }
                code = select_bit(options, skip);
                break;
            }
            cross_options[a][b] &= ~(1U << code);
            eb = code % 15;
            oldb = mask[eb];
            ib = position[b];
            mask[ea] &= ~(1ULL << a);
            mask[eb] |= 1ULL << b;
            pol = (pol & ~(1ULL << b)) | (u64(code / 15) << b);
            ++cross_samples;
        } else if (swindow) {  // generic window a <-> handle window b
            int color = ((oldpol >> a) ^ rng.next()) & 1;
            if (selected.size() == unsigned(need)) {
                if (window_epoch[a] != epoch) {
                    DP_SCOPE(aw_windows);
                    window_options[a] = prepare_windows(a, ea);
                    window_epoch[a] = epoch;
                }
                Bits options = window_options[a];
                if (!(options[0] | options[1])) return false;
                int skip = rng.below(__builtin_popcountll(options[0]) + __builtin_popcountll(options[1]));
                const int first = __builtin_popcountll(options[0]);
                color = skip >= first;
                if (color) skip -= first;
                b = select_bit(options[color], skip);
                ib = position[b];
                window_options[a][color] &= ~(1ULL << b);
                ++window_samples;
            }
            mask[ea] ^= (1ULL << a) | (1ULL << b);
            pol = (pol & ~(1ULL << b)) | (u64(color) << b);
        } else {  // window a to another pair
            if (counts[ea] < 2) return false;
            int new_color = -1;
            if (selected.size() == unsigned(need)) {
                if (transfer_epoch[a] != epoch) {
                    DP_SCOPE(aw_transfer);
                    transfer_options[a] = make_transfer_options(a, ea);
                    transfer_epoch[a] = epoch;
                    ++transfer_rows;
                }
                uint32_t available = transfer_options[a];
                if (!available) return false;
                int best_priority = 1 << 30;
                uint32_t shortlist = 0;
                for (uint32_t q = available; q; q &= q - 1) {
                    const int code = __builtin_ctz(q), priority = transfer_priority[a][code];
                    if (priority < best_priority) {
                        best_priority = priority;
                        shortlist = 0;
                    }
                    if (priority == best_priority) shortlist |= 1U << code;
                }
                available = shortlist;
                const int code = select_bit(available, rng.below(__builtin_popcount(available)));
                transfer_options[a] &= ~(1U << code);
                eb = code % 15;
                new_color = code / 15;
                ++transfer_samples;
            } else
                eb = rng.mod(ne);
            if (ea == eb) return false;
            oldb = mask[eb];
            mask[ea] ^= 1ULL << a;
            mask[eb] |= 1ULL << a;
            transfer = eb;
            if (new_color >= 0)
                pol = (pol & ~(1ULL << a)) | (u64(new_color) << a);
            else if (rng.next() & 1)
                pol ^= 1ULL << a;
        }
        mv = {ia, ib, a, b, kind, ea, eb, transfer, swindow, olda, oldb, oldpol};
        // Keys distinguish the destination sheet pair and polarity.
        if (cross_move)
            move_key = 16384 + 2 * (ne * (64 * a + b) + eb) + int(pol >> b & 1);
        else if (swindow)
            move_key = 2 * (64 * a + b) + ((pol >> b) & 1);
        else
            move_key = 12352 + 2 * (ne * a + eb) + ((pol >> a) & 1);
        memo_hit = memo_epoch[move_key] == 2 * epoch + 1;
        if (memo_hit) {
            memo_hits++;
            return true;
        }
        exact_evals++;
        {
            DP_SCOPE(aw_evaluate);
            evaluate_pairs(ea, eb);
        }
        return true;
    };
    auto handles_after = [&](const Move& mv) { return hm ^ (mv.swindow ? (1ULL << mv.a) | (1ULL << mv.b) : 0); };
    // ==== Window assignment: elite paths ====

    struct Elite {
        bool ready = false;
        double cost = 1e30;
        u64 generic = 0, pol = 0;
        std::array<int, 64> which{};
    };
    std::array<Elite, 8> elites{};
    auto elite_differs = [&](const Elite& saved) {
        if (saved.generic != (kActiveWindows & ~hm) || ((saved.pol ^ pol) & saved.generic)) return true;
        for (u64 windows = saved.generic; windows; windows &= windows - 1) {
            const int a = __builtin_ctzll(windows);
            if (which[a] != saved.which[a]) return true;
        }
        return false;
    };
    long long path_internal = 0;
    Elite path_target;
    bool path_active = false;
    long long path_starts = 0, path_complete = 0, path_blocked = 0;
    long long elite_updates = 0, elite_attempts = 0, elite_candidates = 0, elite_accepts = 0;
    unsigned elite_epoch = 0;
    auto record_elite = [&](double cost) {
        if (!as_elite) return;
        u64 h = 1469598103934665603ULL;
        for (int e = 0; e < ne; ++e) h = (h ^ (mask[e] + e)) * 1099511628211ULL;
        h = (h ^ (pol & ~hm)) * 1099511628211ULL;
        auto& saved = elites[(h ^ (h >> 32)) & 7];
        if (saved.ready && saved.cost <= cost) return;
        saved.ready = true; saved.cost = cost; saved.generic = kActiveWindows & ~hm; saved.pol = pol;
        std::copy(which.begin(), which.end(), saved.which.begin());
        ++elite_updates;
    };
    // A path-relinking step changes roles toward a stored good assignment. Only unseen
    // moves passing the unchanged selected-pair screen reach the full objective.
    auto propose_elite = [&](Move& mv) {
        if (!as_elite || selected.size() != unsigned(need)) return false;
        if (elite_epoch == epoch) { path_active = false; return false; }
        elite_epoch = epoch;
        ++elite_attempts;
#if AS_PROFILE
        auto& ap = as_profile[as_phase][5];
        ++ap.proposed;
        AssignScope as_time(ap.propose_cycles);
#endif
        if (path_active && !elite_differs(path_target)) {
            path_active = false; ++path_complete;
        }
        if (!path_active) {
            unsigned available = 0;
            for (int i = 0; i < 8; ++i)
                if (elites[i].ready && elite_differs(elites[i])) available |= 1U << i;
            if (!available) return false;
            path_target = elites[select_bit(available, rng.below(__builtin_popcount(available)))];
            path_active = true; ++path_starts;
        }
        const auto& target = path_target;
        const u64 sources = kActiveWindows & ~hm & ~target.generic;
        std::array<std::array<int, 3>, 64 * 64> choices;
        int count = 0;
        for (u64 from = sources; from; from &= from - 1) {
            const int a = __builtin_ctzll(from), ea = which[a];
            for (u64 windows = hm & target.generic; windows; windows &= windows - 1) {
                const int b = __builtin_ctzll(windows), eb = target.which[b], color = target.pol >> b & 1;
                int key;
                if (ea == eb) {
                    if (window_epoch[a] != epoch) {
                        DP_SCOPE(aw_windows);
                        window_options[a] = prepare_windows(a, ea); window_epoch[a] = epoch;
                    }
                    if (!(window_options[a][color] >> b & 1)) continue;
                    key = 2 * (64 * a + b) + color;
                } else {
                    if (counts[ea] < 2) continue;
                    if (cross_epoch[a] != epoch) {
                        DP_SCOPE(aw_cross);
                        cross_options[a] = prepare_cross(a, ea); cross_epoch[a] = epoch;
                    }
                    if (!(cross_options[a][b] >> (eb + 15 * color) & 1)) continue;
                    key = 16384 + 2 * (ne * (64 * a + b) + eb) + color;
                }
                if (memo_epoch[key] == 2 * epoch + 1) continue;
                choices[count++] = {a, b, 0};
            }
        }
        // Align the sheet pair and polarity of windows already generic in both states.
        for (u64 windows = (kActiveWindows & ~hm) & target.generic; windows; windows &= windows - 1) {
            const int a = __builtin_ctzll(windows), ea = which[a], eb = target.which[a];
            const int color = target.pol >> a & 1;
            int key, type;
            if (ea == eb) {
                if (int(pol >> a & 1) == color) continue;
                key = 8192 + a; type = 1;
                if (memo_epoch[key] == 2 * epoch + 1) continue;
                Move probe{position[a], position[a], a, a, 0, ea, ea, -1, false, mask[ea], mask[ea], pol};
                pol ^= 1ULL << a;
                const int loss = swap_losses(probe);
                pol ^= 1ULL << a;
                if (loss >= kRejectLoss) continue;
            } else {
                if (counts[ea] < 2) continue;
                key = 12352 + 2 * (ne * a + eb) + color; type = 2;
                if (memo_epoch[key] == 2 * epoch + 1) continue;
                if (transfer_epoch[a] != epoch) {
                    DP_SCOPE(aw_transfer);
                    transfer_options[a] = make_transfer_options(a, ea);
                    transfer_epoch[a] = epoch; ++transfer_rows;
                }
                if (!(transfer_options[a] >> (eb + 15 * color) & 1)) continue;
            }
            choices[count++] = {a, a, type};
        }
        if (!count) { path_active = false; ++path_blocked; return false; }
        const auto [a, b, type] = choices[rng.below(count)];
        const int ea = which[a], eb = target.which[b], color = target.pol >> b & 1;
        mv = {position[a], position[b], a, b, type == 2 ? 8 : 0, ea, eb,
              type == 2 ? eb : -1, type == 0, mask[ea], mask[eb], pol, true};
        if (type == 1) {
            pol ^= 1ULL << a;
            move_key = 8192 + a;
        } else if (type == 2) {
            mask[ea] &= ~(1ULL << a); mask[eb] |= 1ULL << a;
            pol = (pol & ~(1ULL << a)) | (u64(color) << a);
            transfer_options[a] &= ~(1U << (eb + 15 * color));
            move_key = 12352 + 2 * (ne * a + eb) + color;
        } else {
            if (ea == eb) {
                mask[ea] ^= (1ULL << a) | (1ULL << b);
                window_options[a][color] &= ~(1ULL << b);
                move_key = 2 * (64 * a + b) + color;
            } else {
                mask[ea] &= ~(1ULL << a); mask[eb] |= 1ULL << b;
                cross_options[a][b] &= ~(1U << (eb + 15 * color));
                move_key = 16384 + 2 * (ne * (64 * a + b) + eb) + color;
            }
            pol = (pol & ~(1ULL << b)) | (u64(color) << b);
        }
        path_internal += type != 0;
        memo_hit = false;
        ++elite_candidates;
        ++exact_evals;
        { DP_SCOPE(aw_evaluate); evaluate_pairs(ea, eb); }
        return true;
    };
    // ==== Window assignment: acceptance and search loops ====

    auto apply_move = [&](const Move& mv) {
        elite_accepts += mv.elite;
        DP_SCOPE(aw_apply);
        if (memo_hit) {  // the cached objective: rebuild the relations and the matching of the move
            evaluate_pairs(mv.ea, mv.eb);
            matching_cost(nrel.data(), handles_after(mv));
        }
        ++epoch;
        selected = candidate_selected;
        screen_dirty = true;
        accepted++;
        pairs.dir.swap(ndir);
        pairs.rel.swap(nrel);
        if (mv.swindow) {
            which[mv.a] = -1;
            which[mv.b] = mv.eb;
            if (mv.ea != mv.eb) {
                --counts[mv.ea];
                ++counts[mv.eb];
                ++cross_accepts;
            }
            std::swap(order[mv.ia], order[mv.ib]);
            position[order[mv.ia]] = mv.ia;
            position[order[mv.ib]] = mv.ib;
            hm = handles_after(mv);
        } else {
            if (mv.transfer >= 0) {
                counts[mv.ea]--;
                counts[mv.eb]++;
                which[mv.a] = mv.eb;
            }
        }
    };
    for (int p = 0; p < np; ++p)
        if (pairs.rel[p]) valid[nvalid++] = p;
    double cur = matching_cost(pairs.rel.data(), hm), best = cur;
    record_elite(cur);
    selected = candidate_selected;
    auto best_mask = mask;
    auto best_order = order;
    u64 best_pol = pol;
    double elapsed = 0;
    Move mv;
    // The loss screen makes the neighborhood small. Near a local minimum, millions of
    // random draws can revisit cached rejections. Remember the least-cost eligible neighbor
    // actually evaluated in this state and install it once the state has stalled. Its exact
    // objective is already cached; apply_move rebuilds its relations and matching on acceptance.
    std::vector<unsigned> tabu_epoch(kMemoSize, 0);
    int last_accept_it = 0;
    double escape_floor = 1e30;
    Move escape_move{};
    u64 escape_ma = 0, escape_mb = 0, escape_pol = 0;
    int escape_key = 0;
    bool escape_valid = false;
    long long direct_steps = 0;
    auto remember_escape = [&](double candidate) {
        if (candidate < escape_floor) {
            escape_floor = candidate;
            escape_move = mv;
            escape_key = move_key;
            escape_ma = mask[mv.ea];
            escape_mb = mask[mv.eb];
            escape_pol = pol;
            escape_valid = true;
        }
    };
    // Saved move indices, masks, and cache entries stay valid only within the current epoch.
    // Every acceptance and the phase transition below invalidate the saved neighbor.
    auto install_escape = [&] {
        mv = escape_move;
        move_key = escape_key;
        mask[mv.ea] = escape_ma;
        mask[mv.eb] = escape_mb;
        pol = escape_pol;
        memo_hit = true;
        ++memo_hits;
        ++direct_steps;
    };
    long long forced_steps = 0, tabu_skips = 0;
#if DESIGN_PROFILE
    dp_cycles[dp_aw_setup] += __builtin_ia32_rdtsc() - dp_setup_start;
    dp_calls[dp_aw_setup]++;
#endif
    // The exact objective of the proposed (or installed) move, cached under its key.
    auto candidate_cost = [&] {
#if AS_PROFILE
        auto& ap = as_profile[as_phase][as_kind(mv)];
        ++ap.candidates;
        ap.memo += memo_hit;
        AssignScope as_time(ap.matching_cycles);
#endif
        DP_SCOPE(aw_matching);
        const double candidate = memo_hit ? memo_value[move_key] : matching_cost(nrel.data(), handles_after(mv));
        memo_epoch[move_key] = 2 * epoch + 1;
        memo_value[move_key] = candidate;
        return candidate;
    };
    // Accepts the move at iteration it: its reverse becomes taboo for kTabuAccepted accepted states
    // (the taboo key includes the old color when reversing a transfer), and the best state is kept.
    auto take_move = [&](int it, double candidate) {
#if AS_PROFILE
        auto& ap = as_profile[as_phase][as_kind(mv)];
        ++ap.accepted;
        ap.descending += candidate < cur - 1e-9;
        ap.descent += std::max(0.0, cur - candidate);
        ap.improved += candidate < best - 1e-9;
        ap.best_gain += std::max(0.0, best - candidate);
        if (!memo_hit) {
            std::array<unsigned char, 32640> chosen{};
            for (int p : selected) chosen[p] = 1;
            for (int p : candidate_selected) {
                ap.entering += !chosen[p];
                ap.new_valid += !pairs.rel[p];
            }
        }
#endif
        int reverse_key = move_key;
        if (mv.swindow && mv.ea != mv.eb)
            reverse_key = 16384 + 2 * (ne * (64 * mv.b + mv.a) + mv.ea) + int(mv.oldpol >> mv.a & 1);
        else if (mv.swindow)
            reverse_key = 2 * (64 * mv.b + mv.a) + ((mv.oldpol >> mv.a) & 1);
        else if (mv.transfer >= 0)
            reverse_key = 12352 + 2 * (ne * mv.a + mv.ea) + ((mv.oldpol >> mv.a) & 1);
        tabu_epoch[reverse_key] = epoch + kTabuAccepted + 1;
        last_accept_it = it;
        escape_floor = 1e30;
        escape_valid = false;
        apply_move(mv);
        cur = candidate;
        record_elite(cur);
        if (cur < best - 1e-9) {
            best = cur;
            best_mask = mask;
            best_pol = pol;
            best_order = order;
        }
    };
    // Both phases share proposal, cache lookup and tabu filtering. A new best
    // overrides tabu; otherwise rejected proposals leave mask/pol unchanged.
    auto propose_candidate = [&](int it, int stall, double& candidate) {
        const bool path_move = path_active && propose_elite(mv);
        if (!path_move && it - last_accept_it >= stall && escape_valid) {
            if (!propose_elite(mv)) install_escape();
        } else if (!path_move) {
            DP_SCOPE(aw_propose);
            if (!propose(mv)) return false;
        }
        candidate = candidate_cost();
        if (tabu_epoch[move_key] > epoch && candidate >= best - 1e-9) {
            ++tabu_skips;
            undo_move(mv);
            return false;
        }
        remember_escape(candidate);
        return true;
    };
#if DESIGN_PROFILE
    unsigned long long dp_loop_start = __builtin_ia32_rdtsc();
#endif
    for (int it = 0;; it++) {
        if ((it & 15) == 0) {
            elapsed = scaled_since(start);
            if (elapsed >= seconds || (fixed_iters > 0 && it >= fixed_iters)) break;
        }
        stats.iterations++;
#if AS_PROFILE
        as_phase = fixed_iters ? std::min(3, 4 * it / fixed_iters) : 0;
#endif
        double progress = fixed_iters ? double(it) / fixed_iters : elapsed / seconds;
        double candidate;
        if (!propose_candidate(it, kMapStall, candidate)) continue;
        auto temp = [&] { return 0.05 * std::pow(0.00125 / 0.05, progress); };
        const bool force = it - last_accept_it >= kMapStall && candidate <= escape_floor + 1e-9;
        if (candidate <= cur || force || rng.real() < std::exp((cur - candidate) / temp())) {
            forced_steps += force && candidate > cur;
            take_move(it, candidate);
        } else {
            undo_move(mv);
        }
    }
    // Search from the annealing best for the original final time interval. Normally descend;
    // at stagnation take the least-cost observed neighbor, and retain the best visited state.
#if DESIGN_PROFILE
    unsigned long long dp_final_start = __builtin_ia32_rdtsc();
    dp_cycles[dp_aw_loop] += dp_final_start - dp_loop_start;
#endif
    ++epoch;
    mask = best_mask, pol = best_pol, order = best_order;
    for (int j = 0; j < 64; j++) position[order[j]] = j;
    std::fill(which.begin(), which.end(), -1);
    hm = kActiveWindows;
    for (int e = 0; e < ne; e++) {
        counts[e] = __builtin_popcountll(mask[e]);
        hm &= ~mask[e];
        for (u64 x = mask[e]; x; x &= x - 1) which[__builtin_ctzll(x)] = e;
    }
    for (int p = 0; p < np; p++) pair_state(pairs.au[p], pairs.diff[p], pairs.dir[p], pairs.rel[p]);
    for (int p = 0; p < np8; p++) pairs.wit[p] = relations.witness(pairs.dir[p], pairs.rel[p]);
    nvalid = 0;
    for (int p = 0; p < np; ++p)
        if (pairs.rel[p]) valid[nvalid++] = p;
    cur = matching_cost(pairs.rel.data(), hm);
    selected = candidate_selected;
    screen_dirty = true;
    stats.gobj_before = cur;
    best = cur;
    best_mask = mask;
    best_pol = pol;
    best_order = order;
    std::fill(tabu_epoch.begin(), tabu_epoch.end(), 0);
    escape_floor = 1e30;
    escape_valid = false;
    last_accept_it = 0;
    long long climb_forced_steps = 0;
#if DESIGN_PROFILE
    dp_cycles[dp_aw_final] += __builtin_ia32_rdtsc() - dp_final_start;
    dp_calls[dp_aw_final]++;
#endif
#if AS_PROFILE
    as_phase = 4;
#endif
    if (climb_steps > 0 || climb_seconds > 0) {
        const auto climb_start = Clock::now();
        for (int it = 0;; it++) {
            if (climb_steps > 0 ? it >= climb_steps : (it & 15) == 0 && scaled_since(climb_start) >= climb_seconds)
                break;
            stats.climb_steps = it + 1;
            double candidate;
            if (!propose_candidate(it, kClimbStall, candidate)) continue;
            const bool force = it - last_accept_it >= kClimbStall && candidate <= escape_floor + 1e-9;
            if (candidate <= cur || force) {
                climb_forced_steps += force && candidate > cur;
                take_move(it, candidate);
            } else {
                undo_move(mv);
            }
        }
    }
    // The returned assignment is the best visited state, not the last uphill escape. Pair
    // caches need not be rebuilt here: the remaining code only uses mask, pol, and order.
    mask = best_mask;
    pol = best_pol;
    order = best_order;
    cur = best;
    std::cerr << "climb_forced_steps = " << climb_forced_steps << '\n';
    std::cerr << "search_accept = " << accepted << "\nsearch_rejected = " << screen_rejected
              << "\nsearch_screen_checks = " << screen_checks << '\n';
    std::cerr << "search_memo_hits = " << memo_hits << "\nsearch_exact_evals = " << exact_evals << '\n';
    std::cerr << "search_screen_hits = " << screen_hits << '\n';
    std::cerr << "forced_steps = " << forced_steps << "\ntabu_skips = " << tabu_skips << '\n';
    std::cerr << "direct_steps = " << direct_steps << '\n';
    std::cerr << "transfer_rows = " << transfer_rows << "\ntransfer_samples = " << transfer_samples << '\n';
    std::cerr << "screen_color_pairs = " << screen_color_pairs << "\nscreen_refreshes = " << screen_refreshes << '\n';
    std::cerr << "transfer_empty = " << transfer_empty << "\ntransfer_single = " << transfer_single
              << "\ntransfer_many = " << transfer_many << '\n';
    std::cerr << "window_rows = " << window_rows << "\nwindow_samples = " << window_samples << '\n';
    std::cerr << "cross_rows = " << cross_rows << "\ncross_samples = " << cross_samples
              << "\ncross_accepts = " << cross_accepts << '\n';
#if AS_PROFILE
    constexpr const char* as_names[] = {"window", "flip", "exchange", "transfer", "cross", "elite"};
    for (int phase = 0; phase < 5; ++phase)
        for (int op = 0; op < 6; ++op) {
            const auto& ap = as_profile[phase][op];
            std::cerr << "#assign " << phase << ' ' << as_names[op] << ' ' << ap.proposed << ' ' << ap.candidates
                      << ' ' << ap.memo << ' ' << ap.accepted << ' ' << ap.descending << ' ' << ap.improved
                      << ' ' << ap.descent << ' ' << ap.best_gain << ' ' << ap.entering << ' ' << ap.new_valid
                      << ' ' << ap.propose_cycles * 1e-6 << ' ' << ap.matching_cycles * 1e-6 << '\n';
        }
#endif
    std::cerr << "as_elite = " << as_elite << "\nas_work = " << as_work << "\nelite_updates = " << elite_updates
              << "\nelite_attempts = " << elite_attempts << "\nelite_candidates = " << elite_candidates
              << "\nelite_accepts = " << elite_accepts << '\n';
    std::cerr << "path_starts = " << path_starts << "\npath_complete = " << path_complete
              << "\npath_blocked = " << path_blocked << '\n';
    std::cerr << "as_screen = " << as_screen << "\nas_work = " << as_work << "\ndirect_checks = " << direct_checks
              << "\ndirect_rejects = " << direct_rejects << '\n';
    std::cerr << "path_internal = " << path_internal << '\n';
    stats.gobj_after = cur;
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
#if DESIGN_PROFILE
    dp_cycles[dp_aw_total] += __builtin_ia32_rdtsc() - dp_setup_start;
    dp_calls[dp_aw_total]++;
    dp_report();
#endif
    return stats;
}

// ==== Design: units, columns and the cost model ====

// Optional sampling only; no search RNG or design state is touched.
#ifndef AF_PROFILE
#define AF_PROFILE 0
#endif
#if AF_PROFILE
struct AFProfile {
    enum Id { column_move, target_move, handle_swap, column_swap, multi_move, eval_holes, unit_rows,
              anneal, climb, head_rebuild, head_gradient, head_donor, head_target, hungarian,
              rematch, interleave, adaptive, lookahead, comparator_tables, perforation, perforation_cache, Count };
    struct Entry { long long calls, samples; double seconds; };
    inline static std::array<Entry, Count> entry{};
    struct Scope {
        Id id; bool sampled; Clock::time_point start;
        Scope(Id i, unsigned stride) : id(i), sampled((++entry[i].calls & (stride - 1)) == 0) {
            if (sampled) start = Clock::now();
        }
        ~Scope() { if (sampled) { entry[id].seconds += scaled_since(start); ++entry[id].samples; } }
    };
    static void report() {
        const char* names[] = {"column_move", "target_move", "handle_swap", "column_swap", "multi_move", "eval_holes", "unit_rows",
            "anneal", "climb", "head_rebuild", "head_gradient", "head_donor", "head_target", "hungarian",
            "rematch", "interleave", "adaptive", "lookahead", "comparator_tables", "perforation", "perforation_cache"};
        for (int i = 0; i < Count; ++i) {
            auto e = entry[i];
            std::cerr << "af_" << names[i] << "_calls = " << e.calls << '\n'
                      << "af_" << names[i] << "_samples = " << e.samples << '\n'
                      << "af_" << names[i] << "_sec = " << (e.samples ? e.seconds * e.calls / e.samples : 0) << '\n';
        }
    }
};
#define AF_SCOPE(name, stride) AFProfile::Scope af_scope_##name(AFProfile::name, stride)
#else
#define AF_SCOPE(name, stride) ((void)0)
#endif

// kBitLanes[v][i]: bit i of v as 0.0f / 1.0f (8 float lanes of a byte of a bit mask; Design::Annealer)
alignas(32) const std::array<std::array<float, 8>, 256> kBitLanes = [] {
    std::array<std::array<float, 8>, 256> a{};
    for (int v = 0; v < 256; v++)
        for (int i = 0; i < 8; i++) a[v][i] = float(v >> i & 1);
    return a;
}();

// A unit is one target or a compatible pair in column c. handle[j] selects its physical window;
// hb[t] packs target t at these handles. The design objective sums weighted column depths,
// expected handle-hole repairs with reset demand, and the exact mean generic-layer cost.
struct Design {
    struct Unit {
        int a = -1, b = -1, c = -1;
    };
    static constexpr double kHoleWeight = 0.38;
    inline static double kClimbProxyWeight = 0.5;
    XorShift rng{0x6176abcd1349ULL ^ deval_seed_salt()};
    int G, H, U, need;  // generic windows, handles, units, pairs
    std::vector<u64> A, hb;
    std::vector<int> handle, owner;  // owner[t]: unit of target t
    std::vector<Unit> unit;
    std::vector<std::vector<int>> partners;  // compatible targets
    std::array<std::array<uint8_t, 256>, 256> ok{};
    std::array<std::array<float, 256>, 256> gcost{};
    std::vector<int> nc, nt, n1, pairOne;  // per column: units, targets, units / pairs of color 1
    std::vector<std::array<int, 2>> hn;    // per handle: holes of color 0 and 1
    static constexpr double reset_strength = 2.0;
    std::vector<float> reset_targets;
    std::vector<double> cval;  // colcost of the current counts
    double cur = 0;
    double anneal_reheat=1.,reheat_start=.5;
    int anneal_iters = 0, climb_iters = 0, climb_accepted = 0;
    int climb_evaluated = 0, climb_cached = 0;
    int colswap_tried = 0, colswap_accepted = 0, replace_tried = 0, replace_accepted = 0;  // (anneal)
    double proxy_before = 0, proxy_after = 0;

    static int pc(u64 x) { return __builtin_popcountll(x); }
    Design(const std::vector<u64>& a, int m, int g) : G(g), H(63 - g), U(191 - m), need(256 - U), A(a) {
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
        reset_targets.assign(H, 0);
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
    // Twice the least weighted depth W of a column with nc units and nt targets (np = nt - nc pairs),
    // p1 of its pairs of color 1 at its handle: the least sum of the depths weighted by the targets (a
    // pair counts twice) with the pairs on top, nc (nc - 1) / 2 + np (np - 1) / 2, plus np - 1 when
    // the pairs all have one handle color (a single of the other color must then be second, below the
    // first pair).
    __attribute__((always_inline)) static int least_depths2(int nc, int nt, int p1) {
        const int np = nt - nc, p0 = np - p1;
        const int correction = std::max(0, np - 1) * int((p0 == 0) | (p1 == 0));
        return nc * (nc - 1) + np * (np - 1) + 2 * correction;
    }
    // colcost of a column with nc units, nt targets, n1 units and p1 pairs of color 1 at its handle:
    // W, plus 1e5 if either handle color is absent.
    __attribute__((always_inline)) static double colcost_of(int nc, int nt, int n1, int p1) {
        return least_depths2(nc, nt, p1) * 0.5 + 100000.0 * int((n1 == 0) | (n1 == nc));
    }
    double colcost(int c) const { return colcost_of(nc[c], nt[c], n1[c], pairOne[c]); }
    // Forty times colcost_of, exactly in integers (Annealer).
    __attribute__((always_inline)) static int colcost40(int nc, int nt, int n1, int p1) {
        return 20 * least_depths2(nc, nt, p1) + 4000000 * int((n1 == 0) | (n1 == nc));
    }
    static double hole_cost_of(double x, double y, double reset) {
        return 4 * kHoleWeight * (x * y + .5 * reset * std::min(x, y)) / std::max(1., x + y + reset);
    }
    static std::array<double, 2> head_probability(double x, double y, double reset) {
        const double n = x + y + reset, p = n ? (y + reset * (y > x)) / n : .5;
        return {1 - p, p};
    }
    double hcost(int j) const { return hole_cost_of(hn[j][0], hn[j][1], reset_targets[j]); }
    // The reset demand of every handle from the current column sizes (hcost), and the model rebuilt.
    void refresh_reset() {
        for (int c = 0; c < H; c++) reset_targets[c] = float(reset_strength * nt[c]);
        rebuild();
    }
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
    // ==== Design annealing ====

    // Anneal product pairing, column membership, and handle order. Each of kAnnealSegments
    // schedule segments starts from the previous best and refreshes the column reset demand.
    // Use fixedIterations when positive, otherwise the time budget; retain the 256-step checkpoints.
    static constexpr int kAnnealSegments = 4;
    void anneal(double seconds, int fixedIterations = 0, int firstSegment = 0, int endSegment = 4) {
        const auto t0 = Clock::now();
        int total = 0;
        for (int s = firstSegment; s < endSegment; s++) {
            refresh_reset();
            const double used = scaled_since(t0);
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
    // NR AVX2 registers cover H <= 8*NR handles. Evaluate without mutation;
    // commit the hole counts and qf values only after acceptance.
    // rows[c].t1/u1/p1/pd count targets/units/pairs of color 1 and differing pairs
    // at every handle. Handle exchanges use these column aggregates.
    // key[x] = 2*column + handle color identifies partners for two-unit moves.
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
        alignas(32) float n0[L] = {}, n1[L] = {}, hq[L] = {}, reset[L] = {};
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
            const __m128i np = _mm_sub_epi32(nt, nc), p0 = _mm_sub_epi32(np, p1);
            const __m128i same = _mm_or_si128(_mm_cmpeq_epi32(p0, z), _mm_cmpeq_epi32(p1, z));
            const __m128i correction = _mm_and_si128(_mm_max_epi32(z, _mm_sub_epi32(np, one)), same);
            const __m128i nm = _mm_sub_epi32(nc, one);
            const __m128i minimum2 =
                _mm_add_epi32(_mm_add_epi32(_mm_mullo_epi32(nc, nm), _mm_mullo_epi32(np, _mm_sub_epi32(np, one))),
                              _mm_slli_epi32(correction, 1));
            const __m128i retrieval = _mm_mullo_epi32(minimum2, _mm_set1_epi32(20));
            const __m128i penalty =
                _mm_and_si128(_mm_set1_epi32(4000000), _mm_or_si128(_mm_cmpeq_epi32(n1, z), _mm_cmpeq_epi32(n1, nc)));
            return _mm_add_epi32(retrieval, penalty);
        }
        static const float* bit_lanes(unsigned v) { return kBitLanes[v].data(); }
        // q of hcost (without the factor 4 kHoleWeight) for a / b holes of color 0 / 1 and the reset
        // demand `reset`: the same operations as eval_holes per lane
        ANNEAL_TARGET static float qf(float a, float b, float reset) {
            const float s = a + b + reset;
            return (a * b + .5f * reset * std::min(a, b)) / (s > 1.f ? s : 1.f);
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
            _Pragma("GCC unroll 5") for (int r = 0; r < NR; r++) acc[r] =
                _mm256_fmadd_ps(_mm256_load_ps(bit_lanes((m >> (8 * r)) & 255)), kv, acc[r]);
        }
        ANNEAL_TARGET static void add_bits(float* row, u64 m, float k) {
            const __m256 kv = _mm256_set1_ps(k);
            _Pragma("GCC unroll 5") for (int r = 0; r < NR; r++) _mm256_store_ps(
                row + 8 * r, _mm256_add_ps(_mm256_load_ps(row + 8 * r),
                                           _mm256_mul_ps(_mm256_load_ps(bit_lanes((m >> (8 * r)) & 255)), kv)));
        }
        // New counts N0 = n0 + d0, N1 = n1 + d1 and their q; returns the sum of the changes of q.
        // Keep the temporary SIMD arrays in the caller. Without forced inlining GCC -O2
        // emits a separate function and passes all five arrays through the stack.
        ANNEAL_TARGET __attribute__((always_inline)) float eval_holes(const __m256* d0, const __m256* d1, __m256* N0, __m256* N1, __m256* Q,
                                       u64 dirty = ~u64(0)) const {
            AF_SCOPE(eval_holes, 4096);
            const __m256 one = _mm256_set1_ps(1.0f);
            __m256 dif[NR];
            _Pragma("GCC unroll 5") for (int r = 0; r < NR; r++) {
                // The final SIMD group is usually outside these column moves. Skipping
                // only this group keeps the frequent central groups branch-free. All counts
                // are small integers, so qf and SIMD evaluation have the same exact numerator
                // and rounded division; an unchanged lane has exactly +0 change.
                if (r == NR - 1 && !((dirty >> (8 * r)) & 255)) {
                    N0[r] = _mm256_load_ps(n0 + 8 * r);
                    N1[r] = _mm256_load_ps(n1 + 8 * r);
                    Q[r] = _mm256_load_ps(hq + 8 * r);
                    dif[r] = _mm256_setzero_ps();
                    continue;
                }
                N0[r] = _mm256_add_ps(_mm256_load_ps(n0 + 8 * r), d0[r]);
                N1[r] = _mm256_add_ps(_mm256_load_ps(n1 + 8 * r), d1[r]);
                const __m256 reset_count = _mm256_load_ps(reset + 8 * r);
                const __m256 s = _mm256_max_ps(_mm256_add_ps(_mm256_add_ps(N0[r], N1[r]), reset_count), one);
                const __m256 numerator = _mm256_fmadd_ps(_mm256_mul_ps(_mm256_set1_ps(.5f), reset_count),
                                                         _mm256_min_ps(N0[r], N1[r]), _mm256_mul_ps(N0[r], N1[r]));
                Q[r] = _mm256_div_ps(numerator, s);
                dif[r] = _mm256_sub_ps(Q[r], _mm256_load_ps(hq + 8 * r));
            }
            __m256 acc = _mm256_add_ps(_mm256_add_ps(dif[0], dif[1]), _mm256_add_ps(dif[2], dif[3]));
            if constexpr (NR == 5) acc = _mm256_add_ps(acc, dif[4]);
            static_assert(NR == 4 || NR == 5);
            return hsum(acc);
        }
        ANNEAL_TARGET void commit_holes(const __m256* N0, const __m256* N1, const __m256* Q) {
            _Pragma("GCC unroll 5") for (int r = 0; r < NR; r++) {
                _mm256_store_ps(n0 + 8 * r, N0[r]);
                _mm256_store_ps(n1 + 8 * r, N1[r]);
                _mm256_store_ps(hq + 8 * r, Q[r]);
            }
        }
        // The rows of column u.c: the unit u added (sgn 1) or removed (-1).
        ANNEAL_TARGET void unit_rows(const Unit& u, float sgn) {
            AF_SCOPE(unit_rows, 4096);
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
        // All row entries are integer counts at most 256. Combine the two opposite column
        // updates before storing them: integer additions/subtractions are exact in float,
        // including intermediate values, so this has the same rows as four unit_rows calls.
        ANNEAL_TARGET void column_rows(const Unit& x, const Unit& y, int P, int Q, int sy) {
            auto& a = rows[P];
            auto& b = rows[Q];
            const u64 xa = D.hb[x.a], xb = x.b >= 0 ? D.hb[x.b] : 0;
            const u64 xp = x.b >= 0 ? xa : 0, xd = x.b >= 0 ? xa ^ xb : 0;
            const u64 ya = sy ? D.hb[y.a] : 0, yb = sy && y.b >= 0 ? D.hb[y.b] : 0;
            const u64 yp = sy && y.b >= 0 ? ya : 0, yd = sy && y.b >= 0 ? ya ^ yb : 0;
            const __m256 sign = _mm256_set1_ps(float(sy));
            _Pragma("GCC unroll 5") for (int r = 0; r < NR; ++r) {
                const int shift = 8 * r;
                const __m256 ax = _mm256_load_ps(bit_lanes((xa >> shift) & 255));
                const __m256 ay = _mm256_load_ps(bit_lanes((ya >> shift) & 255));
                const __m256 dxu = _mm256_fnmadd_ps(sign, ay, ax);
                const __m256 dxt = _mm256_fnmadd_ps(sign,
                    _mm256_add_ps(ay, _mm256_load_ps(bit_lanes((yb >> shift) & 255))),
                    _mm256_add_ps(ax, _mm256_load_ps(bit_lanes((xb >> shift) & 255))));
                const __m256 dxp = _mm256_fnmadd_ps(sign, _mm256_load_ps(bit_lanes((yp >> shift) & 255)),
                    _mm256_load_ps(bit_lanes((xp >> shift) & 255)));
                const __m256 dxd = _mm256_fnmadd_ps(sign, _mm256_load_ps(bit_lanes((yd >> shift) & 255)),
                    _mm256_load_ps(bit_lanes((xd >> shift) & 255)));
                _mm256_store_ps(a.t1 + shift, _mm256_sub_ps(_mm256_load_ps(a.t1 + shift), dxt));
                _mm256_store_ps(b.t1 + shift, _mm256_add_ps(_mm256_load_ps(b.t1 + shift), dxt));
                _mm256_store_ps(a.u1 + shift, _mm256_sub_ps(_mm256_load_ps(a.u1 + shift), dxu));
                _mm256_store_ps(b.u1 + shift, _mm256_add_ps(_mm256_load_ps(b.u1 + shift), dxu));
                _mm256_store_ps(a.p1 + shift, _mm256_sub_ps(_mm256_load_ps(a.p1 + shift), dxp));
                _mm256_store_ps(b.p1 + shift, _mm256_add_ps(_mm256_load_ps(b.p1 + shift), dxp));
                _mm256_store_ps(a.pd + shift, _mm256_sub_ps(_mm256_load_ps(a.pd + shift), dxd));
                _mm256_store_ps(b.pd + shift, _mm256_add_ps(_mm256_load_ps(b.pd + shift), dxd));
            }
        }
        int unit_key(const Unit& u) const { return u.c * 2 + D.color(u, u.c); }
        bool accept(double d) { return d <= 0 || d < temp * logs[D.rng.next() & 16383]; }

        explicit Annealer(Design& d) : D(d), H(d.H), U(d.U), rows(d.H), key(d.U) {
            std::memset(static_cast<void*>(rows.data()), 0, rows.size() * sizeof(ColRow));
            for (int j = 0; j < H; j++) {
                reset[j] = D.reset_targets[j];
                n0[j] = float(D.hn[j][0]);
                n1[j] = float(D.hn[j][1]);
                hq[j] = qf(n0[j], n1[j], reset[j]);
            }
            for (int c = 0; c < H; c++) cnc[c] = D.nc[c], cnt[c] = D.nt[c], cn1[c] = D.n1[c], cp1[c] = D.pairOne[c];
            for (int c = 0; c < H; c++) cv[c] = colcost40(cnc[c], cnt[c], cn1[c], cp1[c]);
            for (const auto& u : D.unit) unit_rows(u, 1.0f);
            for (int x = 0; x < U; x++) key[x] = unit_key(D.unit[x]);
            cur = D.cur;
        }

        // Units x, y moved between the columns P = ox.c and Q = nx.c (!= P): x to Q, y to the other
        // column (ny.c != oy.c) or not (ny.c == oy.c; its terms then cancel). Applied if accepted.
        ANNEAL_TARGET void column_move(int x, int y, const Unit& ox, const Unit& oy, const Unit& nx, const Unit& ny) {
            AF_SCOPE(column_move, 1024);
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
            const __m128i costs = colcost_pair(_mm_setr_epi32(cnc[P] + dnc[0], cnc[Q] + dnc[1], 0, 0),
                                               _mm_setr_epi32(cnt[P] + dnt[0], cnt[Q] + dnt[1], 0, 0),
                                               _mm_setr_epi32(cn1[P] + dn1[0], cn1[Q] + dn1[1], 0, 0),
                                               _mm_setr_epi32(cp1[P] + dp1[0], cp1[Q] + dp1[1], 0, 0));
            const int cvP = _mm_cvtsi128_si32(costs), cvQ = _mm_extract_epi32(costs, 1);
            const int delta_col40 = (cvP - cv[P]) + (cvQ - cv[Q]);
            // Each handle has at most 256 target holes: 0 <= q <= 64. Even over
            // all 64 handles, the hole-cost change is below 8192 (4*kHoleWeight < 2).
            // A column-cost increase >10000 is therefore positive and exceeds the
            // largest anneal threshold (temp <=2, log <=log(32768)<11). It must
            // reject. Preserve exactly the one random draw of accept(positive).
            if (delta_col40 > 400000) {
                D.rng.next();
                return;
            }
            // The handles between the two columns stop (moving deeper) or start being holes of the
            // unit, except its pair differences (always holes); a pair's targets agree there.
            __m256 d0[NR], d1[NR];
            _Pragma("GCC unroll 5") for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
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
            const float dq = eval_holes(d0, d1, N0, N1, Qv, interval);
            const double delta = delta_col40 * (1.0 / 40) + kHoleScale * dq;
            if (!accept(delta)) return;
            cur += delta;
            commit_holes(N0, N1, Qv);
            cnc[P] += dnc[0], cnt[P] += dnt[0], cn1[P] += dn1[0], cp1[P] += dp1[0], cv[P] = cvP;
            cnc[Q] += dnc[1], cnt[Q] += dnt[1], cn1[Q] += dn1[1], cp1[Q] += dp1[1], cv[Q] = cvQ;
            column_rows(ox, oy, P, Q, sy);
            D.unit[x] = nx;
            key[x] = unit_key(nx);
            if (ny.c != oy.c) {
                D.unit[y] = ny;
                key[y] = unit_key(ny);
            }
        }
        // An exchange of targets between units x and y (both keep their columns). Applied if accepted.
        ANNEAL_TARGET void target_move(int x, int y, const Unit& ox, const Unit& oy, const Unit& nx, const Unit& ny) {
            AF_SCOPE(target_move, 1024);
            const int cx = ox.c, cy = oy.c, iy = cx == cy ? 0 : 1;
            int dnt[2] = {0, 0}, dn1[2] = {0, 0}, dp1[2] = {0, 0};  // [0]: column of x, [1]: of y (if other)
            __m256 d0[NR], d1[NR];
            _Pragma("GCC unroll 5") for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            _Pragma("GCC unroll 4") for (const auto& [u, i, sgn] : {std::tuple<const Unit&, int, int>{ox, 0, -1},
                                                                    std::tuple<const Unit&, int, int>{nx, 0, 1},
                                                                    std::tuple<const Unit&, int, int>{oy, iy, -1},
                                                                    std::tuple<const Unit&, int, int>{ny, iy, 1}}) {
                const int cl = D.color(u, u.c);
                dnt[i] += sgn * D.weight(u), dn1[i] += sgn * cl, dp1[i] += sgn * (u.b >= 0) * cl;
                const u64 hs = D.holes(u);
                _Pragma("GCC unroll 2") for (int t : {u.a, u.b}) {
                    if (t < 0) continue;
                    add_bits(d1, hs & D.hb[t], float(sgn));
                    add_bits(d0, hs & ~D.hb[t], float(sgn));
                }
            }
            const __m128i costs = colcost_pair(_mm_setr_epi32(cnc[cx], cnc[cy], 0, 0),
                                               _mm_setr_epi32(cnt[cx] + dnt[0], cnt[cy] + dnt[1], 0, 0),
                                               _mm_setr_epi32(cn1[cx] + dn1[0], cn1[cy] + dn1[1], 0, 0),
                                               _mm_setr_epi32(cp1[cx] + dp1[0], cp1[cy] + dp1[1], 0, 0));
            const int cvx = _mm_cvtsi128_si32(costs), cvy = iy ? _mm_extract_epi32(costs, 1) : 0;
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
                column_move(x, y, ox, oy, nx, ny);                               // (the pairs are compatible)
            } else {
                if ((nx.b >= 0 && !D.ok[nx.a][nx.b]) || (ny.b >= 0 && !D.ok[ny.a][ny.b])) return;
                target_move(x, y, ox, oy, nx, ny);
            }
        }
        // Rename two handle coordinates in every target and aggregate row.
        // Column membership and cached costs are updated by the caller.
        void swap_handle_windows(int a, int b) {
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
        }
        // Exchange the handles at positions a < b. The units of the columns < a and >= b see h_a and
        // h_b exchanged, so the new hole counts are the old ones of the other handle, corrected for
        // the targets of the columns a..b-1 (b deeper, a only a pair difference: one hole of each
        // color); the colors at the handles of the columns a and b change. Applied if accepted.
        ANNEAL_TARGET void handle_swap(int a, int b) {
            AF_SCOPE(handle_swap, 1024);
            if (rows[a].pd[b] != 0 || rows[b].pd[a] != 0) return;  // a pair must agree at the new handle of its column
            const int n1a = int(rows[a].u1[b]), n1b = int(rows[b].u1[a]), pa = int(rows[a].p1[b]),
                      pb = int(rows[b].p1[a]);
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
            const float qa = qf(na0, na1, reset[a]), qb = qf(nb0, nb1, reset[b]);
            const __m128i costs =
                colcost_pair(_mm_setr_epi32(cnc[a], cnc[b], 0, 0), _mm_setr_epi32(cnt[a], cnt[b], 0, 0),
                             _mm_setr_epi32(n1a, n1b, 0, 0), _mm_setr_epi32(pa, pb, 0, 0));
            const int cva = _mm_cvtsi128_si32(costs), cvb = _mm_extract_epi32(costs, 1);
            const double delta =
                kHoleScale * ((qa - hq[a]) + (qb - hq[b])) + ((cva + cvb) - (cv[a] + cv[b])) * (1.0 / 40);
            if (!accept(delta)) return;
            cur += delta;
            swap_handle_windows(a, b);
            n0[a] = na0, n1[a] = na1, hq[a] = qa, n0[b] = nb0, n1[b] = nb1, hq[b] = qb;
            cn1[a] = n1a, cn1[b] = n1b, cp1[a] = pa, cp1[b] = pb, cv[a] = cva, cv[b] = cvb;
            for (int x = 0; x < U; x++) key[x] = unit_key(D.unit[x]);
        }
        // Exchange the columns at positions a < b together with their handle windows. Every unit keeps its
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
            AF_SCOPE(column_swap, 1024);
            ++D.colswap_tried;
            float T = 0, X1 = 0, Xd = 0;  // columns a..b-1 at h_b (small integers: exact)
            for (int c = a; c < b; c++) T += float(cnt[c]), X1 += rows[c].t1[b], Xd += rows[c].pd[b];
            float T2 = 0, Y1 = 0, Yd = 0;  // columns a+1..b at h_a
            for (int c = a + 1; c <= b; c++) T2 += float(cnt[c]), Y1 += rows[c].t1[a], Yd += rows[c].pd[a];
            __m256 d0[NR], d1[NR];
            if (b - a > 1) {
                const u64 mid = low_bits(b) & ~low_bits(a + 1);
                const __m256 ta = _mm256_set1_ps(float(cnt[a])), tb = _mm256_set1_ps(float(cnt[b]));
                _Pragma("GCC unroll 5") for (int r = 0; r < NR; r++) {
                    const __m256 m = _mm256_load_ps(bit_lanes((mid >> (8 * r)) & 255));
                    const __m256 a1 =
                        _mm256_sub_ps(_mm256_load_ps(rows[a].t1 + 8 * r), _mm256_load_ps(rows[a].pd + 8 * r));
                    const __m256 b1 =
                        _mm256_sub_ps(_mm256_load_ps(rows[b].t1 + 8 * r), _mm256_load_ps(rows[b].pd + 8 * r));
                    const __m256 a0 = _mm256_sub_ps(_mm256_sub_ps(ta, _mm256_load_ps(rows[a].t1 + 8 * r)),
                                                    _mm256_load_ps(rows[a].pd + 8 * r));
                    const __m256 b0 = _mm256_sub_ps(_mm256_sub_ps(tb, _mm256_load_ps(rows[b].t1 + 8 * r)),
                                                    _mm256_load_ps(rows[b].pd + 8 * r));
                    d1[r] = _mm256_mul_ps(m, _mm256_sub_ps(b1, a1));
                    d0[r] = _mm256_mul_ps(m, _mm256_sub_ps(b0, a0));
                }
            } else {
                _Pragma("GCC unroll 5") for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            }
            const u64 ba = u64(1) << a, bb = u64(1) << b;
            add_bits(d0, ba, (n0[b] - n0[a]) - (T - X1 - Xd));
            add_bits(d1, ba, (n1[b] - n1[a]) - (X1 - Xd));
            add_bits(d0, bb, (n0[a] - n0[b]) + (T2 - Y1 - Yd));
            add_bits(d1, bb, (n1[a] - n1[b]) + (Y1 - Yd));
            __m256 N0[NR], N1[NR], Qv[NR];
            const float dq = eval_holes(d0, d1, N0, N1, Qv, low_bits(b + 1) & ~low_bits(a));
            const double delta = kHoleScale * dq;
            if (!accept(delta)) return;
            ++D.colswap_accepted;
            cur += delta;
            commit_holes(N0, N1, Qv);
            std::swap(cnc[a], cnc[b]), std::swap(cnt[a], cnt[b]), std::swap(cn1[a], cn1[b]);
            std::swap(cp1[a], cp1[b]), std::swap(cv[a], cv[b]);
            swap_handle_windows(a, b);
            std::swap(rows[a], rows[b]);
            for (int x = 0; x < U; x++) {
                auto& u = D.unit[x];
                if (u.c == a || u.c == b) {
                    u.c ^= a ^ b;
                    key[x] = unit_key(u);
                }
            }
        }
        // Replace units xs[0..k) by nu[0..k), summing column and hole deltas before acceptance.
        ANNEAL_TARGET void multi_move(int k, const int* xs, const Unit* nu) {
            AF_SCOPE(multi_move, 1024);
            int cols[6], dnc[6], dnt[6], dn1[6], dp1[6], ncols = 0;
            __m256 d0[NR], d1[NR];
            _Pragma("GCC unroll 5") for (int r = 0; r < NR; r++) d0[r] = d1[r] = _mm256_setzero_ps();
            _Pragma("GCC unroll 3") for (int i = 0; i < k; i++)
                _Pragma("GCC unroll 2") for (int sgn = -1; sgn <= 1; sgn += 2) {
                const Unit& u = sgn < 0 ? D.unit[xs[i]] : nu[i];
                int ci = 0;
                while (ci < ncols && cols[ci] != u.c) ci++;
                if (ci == ncols) cols[ncols] = u.c, dnc[ncols] = dnt[ncols] = dn1[ncols] = dp1[ncols] = 0, ncols++;
                const int cl = D.color(u, u.c);
                dnc[ci] += sgn, dnt[ci] += sgn * D.weight(u), dn1[ci] += sgn * cl, dp1[ci] += sgn * (u.b >= 0) * cl;
                const u64 hs = D.holes(u);
                _Pragma("GCC unroll 2") for (int t : {u.a, u.b}) {
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

        // ==== Design annealing: move proposals ====

        // p0, p1: the slice of the whole schedule (progress) that this run covers
        ANNEAL_TARGET void run(double seconds, int fixedIterations, double p0 = 0, double p1 = 1) {
            AF_SCOPE(anneal, 1);
            const auto start = Clock::now();
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
                    const double elapsed = scaled_since(start);
                    progress = fixedIterations > 0 ? double(it) / fixedIterations : elapsed / seconds;
                    if (progress >= 1 || elapsed >= seconds) break;
                    temp = 2.0 * std::pow(0.015 / 2.0, p0 + (p1 - p0) * progress);
                    temp*=std::pow(D.anneal_reheat,(1-p0-(p1-p0)*progress)/(1-D.reheat_start));

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

    // ==== Filler climb: columns of the units for the filler value ====

    // Expected fixes saved minus placement/return cost; probability(j) gives
    // the chance that covered handle j is wrong. Keep increasing-bit order.
    template<class Probability>
    static double covered_gain(u64 covered, Probability probability) {
        if (!covered) return 0;
        if(!covered)return 0;
        // The first Bernoulli step starts at (p0,p1,mean)=(1,0,0).
        // Multiplication by 0/1 and addition to +0 are exact for these
        // finite nonnegative probabilities. Seed it directly, retaining every
        // later multiply/add and the final subtraction order.
        const double first=probability(__builtin_ctzll(covered));
        double p0=1-first,p1=first,expected=first;
        for (u64 z = covered & (covered-1); z; z &= z - 1) {
            const double p = probability(__builtin_ctzll(z));
            expected += p;
            p1 = p1 * (1 - p) + p0 * p;
            p0 *= 1 - p;
        }
        return std::max(0.0, expected - (1 - p0) - 0.6 * (1 - p0 - p1));
    }
    // The expected saving of the paper of a unit (colors yb at the handles, pair differences dy) of
    // column c as a filler for a target (colors tb, its paper in column l with pair differences
    // targetdiff): the filler covers the handle holes of the target's paper (handles deeper than l and
    // the pair differences) from just past its deepest mismatch with the target to h_{c-1} (h_c
    // excluded). A covered hole h_j saves a fix when the head of column j shows the other color, with
    // probability p_j = (q[j + 1] - q[j]) / 2 (independent; q: prefix sums of twice the wrong-color
    // probabilities of the heads for the target, resolved once before calls). The saving is the expected number of fixes, less 1
    // move if there is at least one (the placement) and 0.6 more if there are two (the later return),
    // at least 0.
    static double filler_gain(u64 tb, int l, u64 targetdiff, u64 yb, u64 dy, int c, const double* q) {
        if (c == l) return 0;
        u64 holes = ~low_bits(l + 1);
        holes |= targetdiff;
        u64 range = low_bits(c + 1) & ~dy & holes;
        u64 mis = (yb ^ tb) & range;
        int level = mis ? 64 - __builtin_clzll(mis) : 0;
        if (level >= c) return 0;
        u64 covered = range & low_bits(c) & ~low_bits(level);
        return covered_gain(covered, [&](int j) { return q[j]; });
    }
    // A climb on the columns of the units: exchange the columns of two pairs (or two singles) whose
    // papers keep their colors at both handles. A move is kept when it lowers cur minus the filler
    // value of the heads: utility[y] is the filler_gain of the paper of unit y summed over all the
    // targets, and a column head of color b is modeled as the strongest eligible paper of that color
    // (eligible: the largest weight there, pairs ahead of singles), weighted by the probability that
    // the head shows b. Until `seconds` (or fixedIterations).
    void filler_climb(double seconds, int fixedIterations = 0) {
        AF_SCOPE(climb, 1);
        refresh_reset();
        const auto start = Clock::now();
        std::vector<u64> diffb(U);  // pair differences of each unit at the handles
        for (int x = 0; x < U; x++)
            if (unit[x].b >= 0) diffb[x] = hb[unit[x].a] ^ hb[unit[x].b];
        // color_probability[c][b]: the head of column c shows b (the hole counts plus the reset demand
        // 2 nt[c] for the majority color); q[t][j]: twice the expected wrong heads at h_0..h_{j-1} for t.
        std::vector<std::vector<double>> q(256, std::vector<double>(H + 1));
        std::vector<std::array<double, 2>> color_probability(H);
        std::vector<std::array<int, 2>> max_weight(H);
        std::vector<std::vector<int>> members(H);
        for (int c = 0; c < H; c++)
            color_probability[c] = head_probability(hn[c][0], hn[c][1], 2.0 * nt[c]);
        for (int t = 0; t < 256; t++)
            for (int c = 0; c < H; c++) q[t][c + 1] = q[t][c] + 2 * color_probability[c][(hb[t] >> c & 1) ^ 1];
        // Resolve the original rounded prefix differences once. Ascending
        // writes do not touch either input needed by any following difference.
        for(int t=0;t<256;++t)for(int c=0;c<H;++c)q[t][c]=0.5*(q[t][c+1]-q[t][c]);
        for (int x = 0; x < U; x++) {
            auto u = unit[x];
            members[u.c].push_back(x);
            max_weight[u.c][color(u, u.c)] = std::max(max_weight[u.c][color(u, u.c)], weight(u));
        }
        std::array<u64,P> target_holes{},donor_cover{},donor_bits{};
        std::array<int,P> target_column{};
        std::array<bool,P> head_eligible{};
        auto cache_unit=[&](int x) {
            const auto& u=unit[x];
            donor_cover[x]=low_bits(u.c+1)&~diffb[x];donor_bits[x]=hb[u.a];
            head_eligible[x]=weight(u)==max_weight[u.c][color(u,u.c)];
            for(int t:{u.a,u.b})if(t>=0) {
                target_column[t]=u.c;target_holes[t]=~low_bits(u.c+1)|diffb[x];
            }
        };
        for(int x=0;x<U;++x)cache_unit(x);
        auto gain=[&](int t,int y,int c) {
            if(target_column[t]==c)return 0.0;
            const u64 range=donor_cover[y]&target_holes[t],mis=(donor_bits[y]^hb[t])&range;
            const int level=mis?64-__builtin_clzll(mis):0;
            if(level>=c)return 0.0;
            return covered_gain(range&low_bits(c)&~low_bits(level),[&](int j){return q[t][j];});
        };
        // Only the two exchanged units change geometry or head eligibility;
        // rollback restores the same cache before the next random proposal.
        auto eligible=[&](int x){return head_eligible[x];};
        std::vector<double> utility(U);
        for (int y = 0; y < U; y++)
            if (eligible(y))
                for (int t = 0; t < 256; t++) utility[y] += gain(t, y, unit[y].c);
        // A rejected exchange can be skipped until the next acceptance. Draw the same random pairs
        // regardless, so the cache does not change the search sequence.
        std::vector<int> rejected_epoch(U * U, -1);
        auto column_value = [&](int c) {
            std::array<double, 2> best{};
            std::array<int, 2> count{};
            for (int y : members[c]) {
                int b = color(unit[y], c);
                count[b]++;
                if (weight(unit[y]) == max_weight[c][b]) best[b] = std::max(best[b], utility[y]);
            }
            double value = 0;
            for (int b = 0; b < 2; b++)
                if (count[b]) value += color_probability[c][b] * best[b];
            return value;
        };
        double proxy = 0;
        for (int c = 0; c < H; c++) proxy += column_value(c);
        proxy_before = proxy;
        std::vector<double> old_utility(U);
        for (int it = 0;; it++) {
            if (fixedIterations > 0 ? it >= fixedIterations : ((it & 63) == 0 && scaled_since(start) >= seconds)) break;
            climb_iters = it + 1;
            int x = rng.below(U), y = rng.below(U), a = unit[x].c, b = unit[y].c;
            if (a == b || (unit[x].b >= 0) != (unit[y].b >= 0)) continue;
            Unit ox = unit[x], oy = unit[y], nx = ox, ny = oy;
            nx.c = b;
            ny.c = a;
            if (!valid(nx, b) || !valid(ny, a) || color(nx, b) != color(oy, b) || color(ny, a) != color(ox, a))
                continue;
            {
                int& epoch = rejected_epoch[std::min(x, y) * U + std::max(x, y)];
                if (epoch == climb_accepted) {
                    ++climb_cached;
                    continue;
                }
                epoch = climb_accepted;
            }
            ++climb_evaluated;
            std::array<int,4> moved{ox.a,ox.b,oy.a,oy.b};
            old_utility = utility;
            // Moving a target changes the contribution to every donor; moving
            // the two donors also changes their opacity and allowed placement.
            for (int z = 0; z < U; z++)
                if (z != x && z != y && eligible(z))
                    for (int t : moved) if(t>=0) utility[z] -= gain(t, z, unit[z].c);
            unit[x] = nx;
            unit[y] = ny;
            cache_unit(x);cache_unit(y);
            utility[x] = utility[y] = 0;
            if (eligible(x))
                for (int t = 0; t < 256; t++) utility[x] += gain(t, x, b);
            if (eligible(y))
                for (int t = 0; t < 256; t++) utility[y] += gain(t, y, a);
            for (int z = 0; z < U; z++)
                if (z != x && z != y && eligible(z))
                    for (int t : moved) if(t>=0) utility[z] += gain(t, z, unit[z].c);
            auto ix = std::find(members[a].begin(), members[a].end(), x);
            auto iy = std::find(members[b].begin(), members[b].end(), y);
            *ix = y;
            *iy = x;
            double next = 0;
            for (int c = 0; c < H; c++) next += column_value(c);
            double old = cur;
            update(ox, -1);
            update(oy, -1);
            update(nx, 1);
            update(ny, 1);
            // The filler proxy contributes half its predicted saving to the climb objective.
            if (cur - old - kClimbProxyWeight * (next - proxy) < -1e-9) {
                proxy = next;
                climb_accepted++;
            } else {
                update(nx, -1);
                update(ny, -1);
                update(ox, 1);
                update(oy, 1);
                cur = old;
                unit[x] = ox;
                unit[y] = oy;
                cache_unit(x);cache_unit(y);
                *ix = x;
                *iy = y;
                utility = old_utility;
            }
        }
        proxy_after = proxy;
        rebuild();
    }
};

// ==== Head-aware reassignment of the targets (Hungarian matching) ====

// Empty for ordinary finishing. The final design-only search can accept a
// complete Hungarian cycle using V instead of its linear proposal model.
struct MatchStats {
    int iterations = 0, accepted_cycles = 0, changed = 0;
    double decrease = 0, seconds = 0;
    double initial_model = 0, final_model = 0, initial_filler = 0, final_filler = 0;
};
// The assignment of least total cost of a square cost matrix (the Hungarian algorithm with
// potentials, O(n^3)): answer[i] is the column of row i.
__attribute__((target("avx2"))) std::vector<int> hungarian(const std::vector<std::vector<double>>& cost) {
    AF_SCOPE(hungarian, 1);
    int n = cost.size();
    std::vector<double> u(n + 1), v(n + 1);
    std::vector<int> p(n + 1), way(n + 1);
    std::vector<double> minv(n + 1);
    std::vector<uint8_t> used(n + 1);
    std::vector<int> visited(n + 1);
    for (int i = 1; i <= n; i++) {
        p[0] = i;
        int j0 = 0, visited_count = 0;
        std::fill(minv.begin(), minv.end(), 1e100);
        std::fill(used.begin(), used.end(), 0);
        do {
            used[j0] = true;
            visited[visited_count++]=j0;
            int i0 = p[j0], j1 = 0;
            double delta = 1e100;
            // Four independent columns; reduction ties use the lower column
            // index, exactly as the original increasing-j scalar scan.
            __m256d minima=_mm256_set1_pd(1e100);
            __m256i indices=_mm256_set1_epi64x(n+1);
            const __m256d potential=_mm256_set1_pd(u[i0]);
            int j=1;
            for(;j+3<=n;j+=4) {
                uint32_t packed;
                std::memcpy(&packed,used.data()+j,4);
                const __m256i flags=_mm256_cvtepu8_epi64(_mm_cvtsi32_si128(int(packed)));
                const __m256d live=_mm256_castsi256_pd(_mm256_cmpeq_epi64(flags,_mm256_setzero_si256()));
                const __m256d old=_mm256_loadu_pd(minv.data()+j);
                const __m256d cur=_mm256_sub_pd(_mm256_sub_pd(_mm256_loadu_pd(cost[i0-1].data()+j-1),potential),_mm256_loadu_pd(v.data()+j));
                const __m256d improve=_mm256_and_pd(live,_mm256_cmp_pd(cur,old,_CMP_LT_OQ));
                const __m256d next=_mm256_blendv_pd(old,cur,improve);
                _mm256_storeu_pd(minv.data()+j,next);
                const int mask=_mm256_movemask_pd(improve);
                if(mask&1)way[j]=j0;
                if(mask&2)way[j+1]=j0;
                if(mask&4)way[j+2]=j0;
                if(mask&8)way[j+3]=j0;
                const __m256d better=_mm256_and_pd(live,_mm256_cmp_pd(next,minima,_CMP_LT_OQ));
                minima=_mm256_blendv_pd(minima,next,better);
                indices=_mm256_blendv_epi8(indices,_mm256_setr_epi64x(j,j+1,j+2,j+3),_mm256_castpd_si256(better));
            }
            alignas(32) double values[4];alignas(32) long long at[4];
            _mm256_store_pd(values,minima);_mm256_store_si256(reinterpret_cast<__m256i*>(at),indices);
            for(int lane=0;lane<4;++lane)
                if(values[lane]<delta || (values[lane]==delta && at[lane]<j1))delta=values[lane],j1=at[lane];
            for(;j<=n;++j)if(!used[j]) {
                const double cur=cost[i0-1][j-1]-u[i0]-v[j];
                if(cur<minv[j])minv[j]=cur,way[j]=j0;
                if(minv[j]<delta)delta=minv[j],j1=j;
            }
            for(int q=0;q<visited_count;++q) {
                const int j=visited[q];
                u[p[j]]+=delta;v[j]-=delta;
            }
            // A visited column is never read from minv again in this search.
            // Updating its dead slack too permits a branch-free vector loop;
            // every live slack has exactly the original subtraction sequence.
            for(int j=1;j<=n;++j)minv[j]-=delta;
            j0 = j1;
        } while (p[j0]);
        do {
            int j1 = way[j0];
            p[j0] = p[j1];
            j0 = j1;
        } while (j0);
    }
    std::vector<int> answer(n);
    for (int j = 1; j <= n; j++) answer[p[j] - 1] = j - 1;
    return answer;
}

// The filler value of the column heads for rematch_probability (as in Design::filler_climb, with the
// head color probabilities from the reset demand `strength` nt[c], recomputed on every rebuild):
// utility[x] is the filler_gain of the paper of unit x summed over the targets, and beta[x] the
// probability that unit x is the head of its column (nonzero only for the strongest eligible unit of
// each column and color).
struct ProbabilityHead {
    Design& d;
    std::vector<std::vector<double>> q;  // q[t][j]: as in filler_climb
    std::vector<std::array<double, 2>> prob;
    std::vector<u64> diff;  // pair differences of each unit at the handles
    std::vector<double> utility, beta;
    std::vector<int> active_heads;  // beta != 0, in the original unit-index order
    std::array<u64,P> target_holes{},unit_cover{},unit_bits{};
    std::array<int,P> target_column{},unit_column{};
    // All masks are rebuilt together with the probabilities after a proposed cycle.
    // The floating-point polynomial and its enumeration order stay unchanged.
    static double range_gain(u64 target,u64 donor,u64 range,int c,const double* p) {
        const u64 mismatch=(target^donor)&range;
        const int level=mismatch?64-__builtin_clzll(mismatch):0;
        if(level>=c)return 0;
        const u64 covered=range&low_bits(c)&~low_bits(level);
        return Design::covered_gain(covered,[&](int j){return p[j];});
    }
    double strength;
    double last_value = 0;
    const std::vector<u64>* extra;
    std::vector<std::array<int, 2>> extended_counts;
    ProbabilityHead(Design& design, double strength_, const std::vector<u64>* extra_ = nullptr)
        : d(design),
          q(P, std::vector<double>(d.H + 1)),
          prob(d.H),
          diff(d.U),
          utility(d.U),
          beta(d.U),
          strength(strength_),
          extra(extra_) {
        rebuild();  // Includes update_probability().
    }
    u64 extra_holes(int slot) const { return extra && slot >= 0 ? (*extra)[slot] : 0; }
    const std::vector<std::array<int, 2>>& hole_counts() const { return extra ? extended_counts : d.hn; }
    double model_cost() const {
        double value = d.cur;
        if (extra) for (int c = 0; c < d.H; ++c)
            value += Design::hole_cost_of(extended_counts[c][0], extended_counts[c][1], d.reset_targets[c]) - d.hcost(c);
        return value;
    }
    void update_probability() {
        if (extra) {
            extended_counts = d.hn;
            for (int x = 0; x < d.U; ++x) {
                const auto& u = d.unit[x];
                const u64 added = (*extra)[x] & ~d.holes(u);
                for (u64 z = added; z; z &= z - 1) {
                    const int h = __builtin_ctzll(z);
                    ++extended_counts[h][d.hb[u.a] >> h & 1];
                    if (u.b >= 0) ++extended_counts[h][d.hb[u.b] >> h & 1];
                }
            }
        }
        const auto& counts = hole_counts();
        for (int c = 0; c < d.H; c++)
            prob[c] = Design::head_probability(counts[c][0], counts[c][1], strength * d.nt[c]);
        for (int t = 0; t < P; t++) {
            q[t][0] = 0;
            for (int c = 0; c < d.H; c++) q[t][c + 1] = q[t][c] + 2 * prob[c][(d.hb[t] >> c & 1) ^ 1];
            for(int c=0;c<d.H;++c)q[t][c]=0.5*(q[t][c+1]-q[t][c]);
        }
    }
    // The strongest eligible unit of each column and color: the largest weight, then the largest
    // utility (the first on ties).
    std::vector<std::array<int, 2>> heads() const {
        std::vector<std::array<int, 2>> best(d.H, {-1, -1});
        for (int x = 0; x < d.U; x++) {
            auto u = d.unit[x];
            int b = d.color(u, u.c), &y = best[u.c][b];
            if (y < 0 || d.weight(u) > d.weight(d.unit[y]) ||
                (d.weight(u) == d.weight(d.unit[y]) && utility[x] > utility[y]))
                y = x;
        }
        return best;
    }
    // The derivative of the filler value with respect to the probability that each head shows color
    // 1. For a covered hole, the derivative of the expected positive gain is 1 - P(other errors = 0)
    // - 0.6 P(other errors = 1); prefix / suffix polynomials avoid dividing by probabilities near zero
    // or one.
    std::vector<double> probability_gradient() const {
        AF_SCOPE(head_gradient, 1);
        std::vector<double> gradient(d.H);
        const auto selected = heads();
        for (int c = 0; c < d.H; c++) gradient[c] = utility[selected[c][1]] - utility[selected[c][0]];
        for (int y = 0; y < d.U; y++)
            if (beta[y]) {
                auto u = d.unit[y];
                int c = u.c;
                for (int t = 0; t < P; t++) {
                    auto target = d.unit[d.owner[t]];
                    if (c == target.c) continue;
                    u64 range = low_bits(c + 1) & ~diff[y] & (d.holes(target) | extra_holes(d.owner[t])), wrong = (d.hb[t] ^ d.hb[u.a]) & range;
                    int lo = wrong ? 64 - __builtin_clzll(wrong) : 0;
                    if (lo >= c) continue;
                    u64 covered = range & low_bits(c) & ~low_bits(lo);
                    std::array<int, 64> indices;
                    std::array<double, 64> chance;
                    int n = 0;
                    for (u64 z = covered; z; z &= z - 1) {
                        int j = __builtin_ctzll(z);
                        indices[n] = j;
                        chance[n] = prob[j][(d.hb[t] >> j & 1) ^ 1];
                        n++;
                    }
                    if (n < 2) continue;
                    // left[i] / right[i]: the probabilities of 0 and 1 errors among the first i /
                    // the last n - i covered holes
                    std::array<std::array<double, 2>, 65> left, right;
                    left[0] = {1, 0};
                    right[n] = {1, 0};
                    for (int i = 0; i < n; i++) {
                        double p = chance[i];
                        left[i + 1] = {left[i][0] * (1 - p), left[i][1] * (1 - p) + left[i][0] * p};
                    }
                    for (int i = n - 1; i >= 0; i--) {
                        double p = chance[i];
                        right[i] = {right[i + 1][0] * (1 - p), right[i + 1][1] * (1 - p) + right[i + 1][0] * p};
                    }
                    for (int i = 0; i < n; i++) {
                        int j = indices[i];
                        double p0 = left[i][0] * right[i + 1][0],
                               p1 = left[i][1] * right[i + 1][0] + left[i][0] * right[i + 1][1];
                        gradient[j] += beta[y] * (1 - p0 - .6 * p1) * ((d.hb[t] >> j & 1) ? -1 : 1);
                    }
                }
            }
        return gradient;
    }
    // The filler value of the paper of unit u over all the targets.
    double donor(const Design::Unit& u,int slot=-1) const {
        AF_SCOPE(head_donor,64);
        double sum=0;
        const u64 dy=(u.b>=0?d.hb[u.a]^d.hb[u.b]:0)|extra_holes(slot);
        const u64 cover=low_bits(u.c+1)&~dy,bits=d.hb[u.a];
        for(int t=0;t<P;++t)if(target_column[t]!=u.c)
            sum+=range_gain(d.hb[t],bits,cover&target_holes[t],u.c,q[t].data());
        return sum;
    }
    // The filler value that the heads give target t when its paper is that of unit u.
    double target(int t,const Design::Unit& u,int slot=-1) const {
        AF_SCOPE(head_target,256);
        double sum=0;
        const u64 dx=(u.b>=0?d.hb[u.a]^d.hb[u.b]:0)|extra_holes(slot);
        const u64 holes=~low_bits(u.c+1)|dx;
        for(int y:active_heads)if(unit_column[y]!=u.c)
            sum+=beta[y]*range_gain(d.hb[t],unit_bits[y],unit_cover[y]&holes,unit_column[y],q[t].data());
        return sum;
    }
    // Recomputes everything from the design; returns the filler value of the heads.
    double rebuild() {
        AF_SCOPE(head_rebuild, 1);
        update_probability();
        for (int x = 0; x < d.U; x++) {
            auto u = d.unit[x];
            diff[x] = (u.b >= 0 ? d.hb[u.a] ^ d.hb[u.b] : 0) | extra_holes(x);
            unit_cover[x]=low_bits(u.c+1)&~diff[x];unit_bits[x]=d.hb[u.a];unit_column[x]=u.c;
        }
        for(int t=0;t<P;++t) {
            const int x=d.owner[t];target_column[t]=d.unit[x].c;
            target_holes[t]=~low_bits(target_column[t]+1)|diff[x];
        }
        // Only maximum-weight units of a column/color can be its head. Lower-weight
        // utility is never observed by the selected heads or their gradient; a higher
        // weight wins independently of utility (including exact ties).
        std::array<std::array<int, 2>, 64> max_weight{};
        for (const auto& u : d.unit)
            max_weight[u.c][d.color(u, u.c)] = std::max(max_weight[u.c][d.color(u, u.c)], d.weight(u));
        for (int x = 0; x < d.U; x++) {
            const auto& u = d.unit[x];
            utility[x] = d.weight(u) == max_weight[u.c][d.color(u, u.c)] ? donor(u, x) : 0;
        }
        const auto best = heads();
        std::fill(beta.begin(), beta.end(), 0);
        double sum = 0;
        for (int c = 0; c < d.H; c++)
            for (int b = 0; b < 2; b++) {
                int y = best[c][b];
                assert(y >= 0);
                beta[y] = prob[c][b];
                sum += prob[c][b] * utility[y];
            }
        active_heads.clear();
        for (int y = 0; y < d.U; ++y) if (beta[y]) active_heads.push_back(y);
        return last_value = sum;
    }
};
// Reassign mobile targets with a Hungarian matching; each pair keeps a random anchor.
// The linearized cost combines handle-hole gradients and head filler value. Try cycles in
// predicted-gain order, accepting only an exact decrease of cur - weight * filler value.
MatchStats rematch_probability(Design& d, int iterations, double weight, double strength,
                               const std::vector<u64>* extra = nullptr) {
    AF_SCOPE(rematch, 1);
    const auto start = Clock::now();
    MatchStats stats;
    d.refresh_reset();
    ProbabilityHead head(d, strength, extra);
    double initial = head.model_cost() - weight * head.last_value, merit = initial;
    stats.initial_model = stats.final_model = head.model_cost() / P;
    stats.initial_filler = stats.final_filler = head.last_value / P;
    std::mt19937_64 rng(0x181ba71c83ULL ^ deval_seed_salt());
    for (int it = 0; it < iterations; it++) {
        std::vector<int> anchor(d.U, -1), mobile(d.U), color(d.U);
        for (int x = 0; x < d.U; x++) {
            auto u = d.unit[x];
            color[x] = d.color(u, u.c);
            mobile[x] = u.a;
            if (u.b >= 0) {
                anchor[x] = u.b;
                if (rng() & 1) std::swap(anchor[x], mobile[x]);
            }
        }
        // gradient[j][b]: the change of hcost at h_j for one more hole of color b, plus the change of
        // the filler value through the head color probability
        std::vector<std::array<double, 2>> gradient(d.H);
        const auto& counts = head.hole_counts();
        for (int j = 0; j < d.H; j++) {
            double x = counts[j][0], y = counts[j][1], t = d.reset_targets[j], den = std::max(1., x + y + t),
                   k = 4 * Design::kHoleWeight, n = x * y + .5 * t * std::min(x, y);
            gradient[j] = {k * ((y + .5 * t * (x <= y)) * den - n) / (den * den),
                           k * ((x + .5 * t * (y < x)) * den - n) / (den * den)};
        }
        {
            auto g = head.probability_gradient();
            for (int j = 0; j < d.H; j++) {
                double den = std::max(1., counts[j][0] + counts[j][1] + strength * d.nt[j]), p = head.prob[j][1];
                gradient[j][0] += weight * g[j] * p / den;
                gradient[j][1] -= weight * g[j] * (1 - p) / den;
            }
        }
        // tail[a][j]: the hole cost of target a on the handles h_j.. (deeper than a column j - 1)
        std::vector<std::vector<double>> tail(P, std::vector<double>(d.H + 1)),
            single_target(P, std::vector<double>(d.H, -1)), single_donor(P, std::vector<double>(d.H, -1));
        for (int a = 0; a < P; a++) {
            for (int j = d.H - 1; j >= 0; j--) tail[a][j] = tail[a][j + 1] + gradient[j][d.hb[a] >> j & 1];
        }
        // cost[i][j]: the mobile target of unit j in unit i (with i's anchor, column and color)
        std::vector<std::vector<double>> cost(d.U, std::vector<double>(d.U, 1e9));
        for (int i = 0; i < d.U; i++) {
            int c = d.unit[i].c, a = anchor[i];
            for (int j = 0; j < d.U; j++) {
                int b = mobile[j];
                if (int(d.hb[b] >> c & 1) != color[i] || (a >= 0 && !d.ok[a][b])) continue;
                double v = tail[b][c + 1], profit = 0;
                Design::Unit u{b, a, c};
                if (a >= 0) {
                    v += tail[a][c + 1] + 2 * d.gcost[a][b];
                    for (u64 z = (d.hb[a] ^ d.hb[b]) & low_bits(c + 1); z; z &= z - 1) {
                        int k = __builtin_ctzll(z);
                        v += gradient[k][0] + gradient[k][1];
                    }
                    for (u64 z = head.extra_holes(i) & ~(d.hb[a] ^ d.hb[b]); z; z &= z - 1) {
                        const int h = __builtin_ctzll(z);
                        v += 2 * gradient[h][d.hb[b] >> h & 1];
                    }
                    profit = head.target(a, u, i) + head.target(b, u, i);
                    if (head.beta[i]) profit += head.beta[i] * head.donor(u, i);
                } else {
                    // Only mobile targets and allowed singleton colors enter the matrix.
                    // The state is fixed while building it, so deferred evaluation is exact.
                    if (head.extra_holes(i)) {
                        for (u64 z = head.extra_holes(i); z; z &= z - 1) {
                            const int h = __builtin_ctzll(z);
                            v += gradient[h][d.hb[b] >> h & 1];
                        }
                        profit = head.target(b, u, i);
                        if (head.beta[i]) profit += head.beta[i] * head.donor(u, i);
                    } else {
                        auto& target_profit = single_target[b][c];
                        if (target_profit < 0) target_profit = head.target(b, {b, -1, c});
                        profit = target_profit;
                        if (head.beta[i]) {
                            auto& value = single_donor[b][c];
                            if (value < 0) value = head.donor(u);
                            profit += head.beta[i] * value;
                        }
                    }
                }
                cost[i][j] = v - weight * profit;
            }
            assert(cost[i][i] < 1e8);
        }
        auto assigned = hungarian(cost);
        std::vector<bool> seen(d.U);
        std::vector<std::pair<double, std::vector<int>>> cycles;  // (predicted change, units)
        for (int i = 0; i < d.U; i++)
            if (!seen[i]) {
                std::vector<int> cycle;
                double gain = 0;
                int x = i;
                do {
                    assert(!seen[x]);
                    seen[x] = true;
                    cycle.push_back(x);
                    gain += cost[x][assigned[x]] - cost[x][x];
                    x = assigned[x];
                } while (x != i);
                if (cycle.size() > 1) cycles.push_back({gain, cycle});
            }
        std::sort(cycles.begin(), cycles.end(), [](auto& a, auto& b) { return a.first < b.first; });
        bool head_dirty = false;
        for (auto& [predicted, cycle] : cycles) {
            std::vector<Design::Unit> old;
            for (int x : cycle) {
                old.push_back(d.unit[x]);
                d.unit[x].a = mobile[assigned[x]];
                d.unit[x].b = anchor[x];
                assert(d.valid(d.unit[x], d.unit[x].c));
            }
            d.rebuild();
            const double head_value = head.rebuild();
            double next = head.model_cost() - weight * head_value;
            head_dirty = false;
            if (next < merit - 1e-7) {
                merit = next;
                stats.final_model = head.model_cost() / P;
                stats.final_filler = head.last_value / P;
                stats.accepted_cycles++;
                stats.changed += cycle.size();
            } else {
                for (int z = 0; z < int(cycle.size()); z++) d.unit[cycle[z]] = old[z];
                d.rebuild();
                // The matching and cycle order are already fixed. A rejected state's head
                // tables are not read by the next trial: rebuild overwrites every field from
                // d. Defer restoring these tables until they are needed for the next matching.
                head_dirty = true;
            }
        }
        if (head_dirty && it + 1 < iterations) head.rebuild();
        stats.iterations++;
    }
    stats.decrease = (merit - initial) / P;
    stats.seconds = scaled_since(start);
    return stats;
}

// ==== Helper tables: dedicated papers inside the generic layer (Interleave) ====

struct Paper {
    u64 opaque = 0, black = 0;
};

// Helpers inside the generic layer: a dedicated paper x of
// another column placed between the generic sheets shows its colors on the generic windows that the
// sheets above it leave as holes, hides the sheets below it there, and also shows on the handle holes
// of the requested paper D. The 720 orders s of the 6 generic sheets (states) and their distances are
// those of the Comparator (the bottom sheet of the layer never moves). For a target u, helpers[u]
// lists the papers x (not of D's column, the same colors as A_u on their opaque handle holes of D,
// opaque on some generic hole of D) with the goals (s, t) such that order s with x inserted under the
// t upper sheets shows A_u on D's generic holes (the deepest t per s).
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
        AF_SCOPE(interleave, 1);
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
            std::vector<u64> wrong(NS);
            for (int state = 0; state < NS; ++state) wrong[state] = (display[state] ^ A[u]) & gh;
            for (int x = GM; x < (int)paper.size(); x++) {
                if ((x & 15) == 0 && elapsed_sec() > limit) return;
                if (x == ded[u] || col_of[x] == col_of[ded[u]]) continue;
                const auto& pp = paper[x];
                if ((pp.black ^ A[u]) & pp.opaque & hh) continue;
                if (!(pp.opaque & gh)) continue;
                Helper h{x, {}};
                const u64 helper_wrong = (pp.black ^ A[u]) & pp.opaque & gh;
                for (int s = 0; s < NS; s++) {
                    const u64 bad = wrong[s];
                    if (!bad) { h.goals.push_back({(uint16_t)s, GM}); continue; }
                    if (bad & ~pp.opaque) continue;  // helper cannot cover these generic errors
                    // Generic errors must stay below the helper. Prefix masks only grow,
                    // so find the largest t with no such error above it, then check that
                    // the generic sheets cover all wrong colors of the helper itself.
                    int lo = 0, hi = GM;  // prefix[0] is empty; prefix[GM] contains bad
                    while (lo + 1 < hi) {
                        const int mid = (lo + hi) / 2;
                        if (prefix[s][mid] & bad) hi = mid; else lo = mid;
                    }
                    if (!(helper_wrong & ~prefix[s][lo]))
                        h.goals.push_back({(uint16_t)s, (uint8_t)lo});
                }
                if (!h.goals.empty()) helper_papers++, helpers[u].push_back(std::move(h));
            }
        }
        ready = true;
    }
    int state(const std::array<uint8_t, K>& order) const {  // the order of the generic sheets in the stack
        std::vector<int> p;
        for (int k : order)
            if (k < GM) p.push_back(k);
        return comp->order_index(p);
    }
    Pick best(int s, const Helper& h) const {
        CF_SCOPE(single_helper);  // the nearest goal (deeper on ties)
        Pick b{h.paper, -1, 0, 255};
        for (auto g : h.goals) {
            const int d = comp->distance(s, g.state);
            if (d < b.distance || (d == b.distance && g.depth > b.depth)) b = {h.paper, g.state, g.depth, d};
        }
        return b;
    }
};

// ==== Column MDP: long-run values of the order of a column ====

// A column paper has type 2 * (paired target) + handle color. States are type sequences.
// Requesting paper i costs i digs, leaving its suffix in order; moved papers may be reinserted
// anywhere. Requiring handle color b costs d_b digs and preserves that first matching head.
// F(s) is the minimum value of full orders containing s as a subsequence; H(s) also fixes its head.
// Relative value iteration uses g + V(pi) = (sum_i p_i [i + F(suffix_i)]
// + sum_b lambda_b [d_b + H(pi[d_b..])]) / W, where W is the event rate.
// Propagate minima down the sequence-deletion DAG. fix[b](s) values the column after digging b.
// Index each sequence by its mixed-radix type counts and lexicographic rank. Suffix counts
// also yield the indices of every insertion gap in one pass.
struct ColumnMdp {
    static constexpr int kMaxLength = 15;  // (array capacity; COLMDP_MAXLEN defaults to 14)
    bool ok = false;
    int top = 0;  // count vector of the whole column
    long long full = 0, sequences = 0;
    std::array<int, 4> radix{};
    std::vector<int> offset;                 // per count vector: the index of its first sequence
    std::vector<std::array<int, 4>> before;  // per count vector and type (see above)
    std::vector<float> F, H;                 // per sequence
    std::array<std::vector<float>, 2> fix;   // per color and sequence
    double rate = 0;                         // W: the events per request

    // out[g] = the index of q[0..L) with a paper of type tau inserted at gap g, for g = 0..L.
    void insertion_indices(const int* q, int L, int tau, int* out) const {
        std::array<int, kMaxLength + 1> r, suffix;  // count vectors of q[j..L), rank contributions of q[j..L)
        r[L] = 0;
        suffix[L] = 0;
        for (int j = L - 1; j >= 0; j--) {
            r[j] = r[j + 1] + radix[q[j]];
            suffix[j] = suffix[j + 1] + before[r[j]][q[j]];
        }
        const int added = radix[tau];
        const int base = offset[r[0] + added];
        int prefix = 0;  // the contributions of q[0..g), with tau among the papers below them
        for (int g = 0; g <= L; g++) {
            out[g] = base + prefix + before[r[g] + added][tau] + suffix[g];
            if (g < L) prefix += before[r[g] + added][q[g]];
        }
    }
    // Builds the tables of a column with cnt[t] papers of type t, each of type t requested at rate
    // p[t] per request, and the handle colors needed at rates lambda[b]. False (ok false) if the
    // column exceeds the limits (length, full states, all sequences) or has no events.
    bool build(const std::array<int, 4>& cnt, const std::array<double, 4>& p, const std::array<double, 2>& lambda,
               int iters, int max_length, long long max_full, long long max_sequences) {
        ok = false;
        const auto& count = cnt;
        const int n = cnt[0] + cnt[1] + cnt[2] + cnt[3];
        if (n == 0 || n > std::min(max_length, kMaxLength)) return false;
        radix[0] = 1;
        for (int t = 1; t < 4; t++) radix[t] = radix[t - 1] * (count[t - 1] + 1);
        const int vectors = radix[3] * (count[3] + 1);
        top = vectors - 1;
        std::vector<std::array<int, 4>> digits(vectors);
        std::vector<int> length(vectors);
        std::vector<long long> mult(vectors);  // the sequences of each count vector (multinomial)
        long long total = 0;
        for (int m = 0; m < vectors; m++) {
            int rest = m, len = 0;
            long long value = 1;
            for (int t = 0; t < 4; t++) {
                digits[m][t] = rest % (count[t] + 1);
                rest /= count[t] + 1;
                for (int i = 1; i <= digits[m][t]; i++) value = value * (++len) / i;  // exact at every step
            }
            length[m] = len;
            mult[m] = value;
            total += value;
        }
        full = mult[top];
        sequences = total;
        if (full > max_full || total > max_sequences) return false;
        bool present[2] = {count[0] + count[2] > 0, count[1] + count[3] > 0};
        rate = 0;
        for (int t = 0; t < 4; t++) rate += count[t] * p[t];
        for (int b = 0; b < 2; b++)
            if (present[b]) rate += lambda[b];
        if (rate <= 0) return false;
        offset.assign(vectors, 0);
        for (long long m = 0, at = 0; m < vectors; m++) offset[m] = int(at), at += mult[m];
        before.assign(vectors, {0, 0, 0, 0});
        for (int m = 0; m < vectors; m++)
            for (int t = 0, at = 0; t < 4; t++) {
                before[m][t] = at;
                if (digits[m][t]) at += int(mult[m - radix[t]]);
            }
        // Every sequence, numbered in the lexicographic order of each count vector (next_permutation
        // from the sorted sequence), 2 bits per paper, top first.
        std::vector<uint32_t> code(total);
        std::vector<uint8_t> code_length(total);
        auto decode = [&](int g, std::array<int, kMaxLength>& s) {
            for (int j = 0; j < code_length[g]; j++) s[j] = code[g] >> (2 * j) & 3;
            return int(code_length[g]);
        };
        for (int m = 0; m < vectors; m++) {
            std::array<int, kMaxLength> s;
            int L = 0;
            for (int t = 0; t < 4; t++)
                for (int i = 0; i < digits[m][t]; i++) s[L++] = t;
            int g = offset[m];
            do {
                uint32_t c = 0;
                for (int j = 0; j < L; j++) c |= uint32_t(s[j]) << (2 * j);
                code[g] = c;
                code_length[g] = uint8_t(L);
                g++;
            } while (std::next_permutation(s.begin(), s.begin() + L));
        }
        // The deletions of every sequence (one per run of equal types), as index << 1 | (1 if only F
        // may use it: the first paper deleted and the second one of another type).
        std::vector<int> edge_start(total + 1, 0), edge;
        edge.reserve(total * 4);
        for (int g = 0; g < total; g++) {
            edge_start[g] = int(edge.size());
            std::array<int, kMaxLength> s;
            const int L = decode(g, s);
            std::array<int, kMaxLength + 1> r, suffix;
            r[L] = 0;
            suffix[L] = 0;
            for (int j = L - 1; j >= 0; j--) {
                r[j] = r[j + 1] + radix[s[j]];
                suffix[j] = suffix[j + 1] + before[r[j]][s[j]];
            }
            for (int j = 0; j < L; j++) {
                if (j > 0 && s[j] == s[j - 1]) continue;  // the same sequence as deleting j - 1
                const int t = s[j];
                int rank = suffix[j + 1];
                for (int i = 0; i < j; i++) rank += before[r[i] - radix[t]][s[i]];
                const int target = offset[r[0] - radix[t]] + rank;
                const bool f_only = j == 0 && !(L > 1 && s[1] == s[0]);
                edge.push_back(target << 1 | int(f_only));
            }
        }
        edge_start[total] = int(edge.size());
        // The full states: types, the index of every suffix s[i..] (i = 0..n), first paper of each color.
        const int first_full = offset[top];
        std::vector<int> full_type(full * n), full_suffix(full * (n + 1)), full_first(full * 2);
        for (int f = 0; f < full; f++) {
            std::array<int, kMaxLength> s;
            decode(first_full + f, s);
            std::array<int, kMaxLength + 1> r, suffix;
            r[n] = 0;
            suffix[n] = 0;
            for (int j = n - 1; j >= 0; j--) {
                r[j] = r[j + 1] + radix[s[j]];
                suffix[j] = suffix[j + 1] + before[r[j]][s[j]];
            }
            full_first[2 * f] = full_first[2 * f + 1] = -1;
            for (int j = 0; j < n; j++) {
                full_type[f * n + j] = s[j];
                if (full_first[2 * f + (s[j] & 1)] < 0) full_first[2 * f + (s[j] & 1)] = j;
            }
            for (int j = 0; j <= n; j++) full_suffix[f * (n + 1) + j] = offset[r[j]] + suffix[j];
        }
        // the count vectors, longest first (the propagation runs from longer to shorter sequences)
        std::vector<int> by_length(vectors);
        std::iota(by_length.begin(), by_length.end(), 0);
        std::stable_sort(by_length.begin(), by_length.end(), [&](int a, int b) { return length[a] > length[b]; });
        constexpr double kInf = 1e300;
        std::vector<double> Fv(total, 0.0), Hv(total, 0.0), V(full);
        for (int it = 0; it < iters; it++) {
            double lowest = kInf;
            for (int f = 0; f < full; f++) {
                const int* type = &full_type[f * n];
                const int* suffix = &full_suffix[f * (n + 1)];
                double value = 0;
                for (int i = 0; i < n; i++) value += p[type[i]] * (i + Fv[suffix[i + 1]]);
                for (int b = 0; b < 2; b++) {
                    const int d = full_first[2 * f + b];
                    if (d >= 0) value += lambda[b] * (d + Hv[suffix[d]]);
                }
                V[f] = value / rate;
                lowest = std::min(lowest, V[f]);
            }
            std::fill(Fv.begin(), Fv.end(), kInf);
            std::fill(Hv.begin(), Hv.end(), kInf);
            for (int f = 0; f < full; f++) Fv[first_full + f] = Hv[first_full + f] = V[f] - lowest;
            for (int m : by_length) {
                if (!length[m]) continue;
                for (int g = offset[m], e = offset[m] + int(mult[m]); g < e; g++)
                    for (int x = edge_start[g]; x < edge_start[g + 1]; x++) {
                        const int target = edge[x] >> 1;
                        Fv[target] = std::min(Fv[target], Fv[g]);
                        if (!(edge[x] & 1)) Hv[target] = std::min(Hv[target], Hv[g]);
                    }
            }
        }
        F.assign(Fv.begin(), Fv.end());
        H.resize(total);
        for (int g = 0; g < total; g++) H[g] = float(Hv[g] < kInf ? Hv[g] : 0.0);  // (the empty sequence)
        for (int b = 0; b < 2; b++) fix[b].resize(total);
        for (int g = 0; g < total; g++) {
            std::array<int, kMaxLength> s;
            const int L = decode(g, s);
            std::array<int, kMaxLength + 1> r, suffix;
            r[L] = 0;
            suffix[L] = 0;
            for (int j = L - 1; j >= 0; j--) {
                r[j] = r[j + 1] + radix[s[j]];
                suffix[j] = suffix[j + 1] + before[r[j]][s[j]];
            }
            for (int b = 0; b < 2; b++) {
                int d = 0;
                while (d < L && (s[d] & 1) != b) d++;
                fix[b][g] = d < L ? H[offset[r[d]] + suffix[d]] : F[g];
            }
        }
        ok = true;
        return true;
    }
};

// The use of the column MDP (environment variables, read once; the defaults are the submitted
// configuration, used by the normal run):
//   COLMDP          0: disable the column MDP
//   COLMDP_UNIT     1: the MDP values per event as they are (moves over the long run; default);
//                   0: times the column's events per request W (the units of the one-step model)
//   COLMDP_MIX      adaptive_insert: the weight of the MDP value (default 0.5)
//   COLMDP_KEEP     adaptive_insert: the factor of the one-step cost kept (default 1 - COLMDP_MIX)
//   COLMDP_NEXTMIX  adaptive_next_cost: the weight of the MDP value of every column (default 0.5)
//   COLMDP_NEXTKEEP adaptive_next_cost: the factor of its cost kept (default 1: the MDP value is added)
//   COLMDP_INSERT / COLMDP_NEXT  0: adaptive_insert / adaptive_next_cost without the MDP (default 1)
//   COLMDP_ITERS    steps of value iteration (default 8)
//   COLMDP_MAXLEN / COLMDP_MAXFULL / COLMDP_MAXSUB  the limits of a covered column: papers, full
//                   states, all sequences (14, 40000, 250000)
//   COLMDP_CASES    the insertions of adaptive_insert that use the values, a sum of: 1 a return
//                   without a barrier, 2 a dig for a paper that leaves the column, 4 a dig of a handle
//                   fix, 8 a return below the requested paper of the same column (default 15)
//   COLMDP_NEEDFIX  0: a return before a dig of its column for the request's color is valued by F, not
//                   by fix (default 1)
//   COLMDP_CTRL     a control for experiments: > 0 multiplies the one-step cost of those insertions by
//                   it instead of mixing in the MDP values (the scale alone, without the MDP's shape)
struct ColMdpConfig {
    bool on = true, insert = true, next = true, need_fix = true;
    double mix = 0.5, ctrl = 0, keep = 0.5, next_mix = 0.5, next_keep = 1.0;
    int unit = 1, iters = 8, max_length = 14, cases = 15;
    long long max_full = 40000, max_sequences = 250000;
};
double env_real(const char* name, double fallback) {
    const char* s = std::getenv(name);
    return s && *s ? std::atof(s) : fallback;
}
const ColMdpConfig& colmdp_config() {
    static const ColMdpConfig config = [] {
        ColMdpConfig c;
        c.on = env_real("COLMDP", c.on) != 0;
        c.insert = env_real("COLMDP_INSERT", c.insert) != 0;
        c.next = env_real("COLMDP_NEXT", c.next) != 0;
        c.mix = env_real("COLMDP_MIX", c.mix);
        c.unit = int(env_real("COLMDP_UNIT", c.unit));
        c.iters = int(env_real("COLMDP_ITERS", c.iters));
        c.max_length = int(env_real("COLMDP_MAXLEN", c.max_length));
        c.max_full = (long long)env_real("COLMDP_MAXFULL", double(c.max_full));
        c.max_sequences = (long long)env_real("COLMDP_MAXSUB", double(c.max_sequences));
        c.cases = int(env_real("COLMDP_CASES", c.cases));
        c.need_fix = env_real("COLMDP_NEEDFIX", c.need_fix) != 0;
        c.ctrl = env_real("COLMDP_CTRL", c.ctrl);
        c.keep = env_real("COLMDP_KEEP", 1 - c.mix);
        c.next_mix = env_real("COLMDP_NEXTMIX", c.next_mix);
        c.next_keep = env_real("COLMDP_NEXTKEEP", c.next_keep);
        return c;
    }();
    return config;
}

#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC pop_options
#endif
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC push_options
#pragma GCC optimize("O3")
#endif
// ==== Solver: papers, handles and the generic look-ahead ====

// Papers, stack state, and request planning with the comparator and adaptive column insertions.
// Generic sheets are papers 0..M-1.
struct Solver {
    using Moves = std::vector<std::pair<int, int>>;
    int M = 6, H = 25;
    Comparator comparator;
    std::vector<u64> A;
    std::vector<int> handle;   // window of h_j (set_handles)
    u64 gmask = 0, hmask = 0;  // generic windows, handle windows
    std::vector<Paper> paper;
    std::vector<u64> h_opq, h_blk;  // per paper: opaque / black handles, by handle index
    std::vector<int> col_of, ded;   // column of each dedicated paper (-1: generic); paper of each target
    // the index of the deepest generic sheet. Papers above it are in or above the generic
    // layer (gen_harm, move_to_level). Generic sheets may be in any order, but set_generic
    // needs them contiguous: a column paper between them would invalidate the plan.
    int generic_bottom() const {
        int b = -1;
        for (int i = 0; i < int(order.size()); i++)
            if (order[i] < M) b = i;
        return b;
    }

    // State of the stack.
    std::array<uint8_t, K> order{};  // top first
    int top_d = -1;          // dedicated paper lifted to the top, -1 if none
    // Fillers: column papers out of their column, showing on the handles h_lvl..h_hi (hi = their
    // column).
    struct Filler {
        int paper;
        int lvl = 0, hi = 0;
    };
    // State snapshots normally have at most four fillers. Copy those records
    // inline; the overflow path retains the vector's unbounded semantics.
    class FillerList {
        static constexpr size_t Inline=4;
        std::array<Filler,Inline> local_;
        std::vector<Filler> large_;
        size_t count_=0;
    public:
        FillerList()=default;
        FillerList(std::initializer_list<Filler> init){assign(init.begin(),init.end());}
        FillerList(const FillerList& other){assign(other.begin(),other.end());}
        FillerList(FillerList&& other) noexcept { *this=std::move(other); }
        FillerList& operator=(const FillerList& other) {
            if(this!=&other)assign(other.begin(),other.end());return *this;
        }
        FillerList& operator=(FillerList&& other) noexcept {
            if(this==&other)return *this;
            count_=other.count_;
            if(count_<=Inline)std::copy_n(other.local_.data(),count_,local_.data());
            else large_=std::move(other.large_);
            other.count_=0;return *this;
        }
        size_t size()const{return count_;}
        bool empty()const{return count_==0;}
        Filler* begin(){return count_<=Inline?local_.data():large_.data();}
        const Filler* begin()const{return count_<=Inline?local_.data():large_.data();}
        Filler* end(){return begin()+count_;}
        const Filler* end()const{return begin()+count_;}
        Filler& operator[](size_t i){return begin()[i];}
        const Filler& operator[](size_t i)const{return begin()[i];}
        Filler& back(){return begin()[count_-1];}
        const Filler& back()const{return begin()[count_-1];}
        template<class It> void assign(It first,It last) {
            const size_t size=last-first;
            if(size<=Inline)std::copy(first,last,local_.begin());
            else large_.assign(first,last);
            count_=size;
        }
        void push_back(Filler value) {
            if(count_<Inline)local_[count_]=value;
            else {
                if(count_==Inline)large_.assign(local_.begin(),local_.end());
                large_.push_back(value);
            }
            ++count_;
        }
        template<class Pred> void erase_if(Pred pred) {
            Filler* start=begin();const auto last=std::remove_if(start,start+count_,pred);
            const size_t size=last-start;
            if(count_>Inline) {
                if(size<=Inline)std::copy_n(start,size,local_.data());
                else large_.resize(size);
            }
            count_=size;
        }
    };
    FillerList fillers;
    Moves ops;  // moves (paper, depth) of the plan being simulated
#ifdef LOCAL_BENCH
    std::vector<uint8_t> op_tags;  // the label of each move of ops (OpLabel)
    uint8_t op_tag = kOpOther;     // the label of the moves made now (OP_LABEL)
#endif
    explicit Solver(std::vector<u64> a) : A(std::move(a)) {}

    // The handle windows (h_j = window handle[j]; H set already) and the table of handle_bits:
    // handle_lookup[i][v] is the handle set of the windows v in byte i of a window set.
    int handle_first_byte = 0, handle_last_byte = 7;
    std::array<std::array<u64, 256>, 8> handle_lookup{};
    void set_handles(const std::vector<int>& h) {
        handle = h;
        handle_lookup = {};
        handle_first_byte = 7;
        handle_last_byte = 0;
        for (int c = 0; c < H; c++) {
            int j = handle[c];
            handle_first_byte = std::min(handle_first_byte, j / 8);
            handle_last_byte = std::max(handle_last_byte, j / 8);
            for (int v = 0; v < 256; v++)
                if (v >> (j % 8) & 1) handle_lookup[j / 8][v] |= 1ULL << c;
        }
    }
    // The window set by handle index (bit j = window h_j).
    u64 handle_bits(u64 windows) const {
        u64 r = 0;
        for (int j = handle_first_byte; j <= handle_last_byte; j++) r |= handle_lookup[j][(windows >> (8 * j)) & 255];
        return r;
    }

    // Orders the generic sheets (contiguous in the stack) so that the generic holes `holes` of the
    // paper of u show A_u (Comparator::plan).
    void set_generic(int u, u64 holes) {
        OP_LABEL(kOpGen);
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
        Moves path;
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

    // sat[u] lists generic-sheet orders satisfying the holes of target u. future[s] is the mean
    // minimum distance from s to those orders; it breaks ties in the current request's generic plan.
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

    // ==== Solver: future-cost model of the stack ====

    // Adaptive columns: a paper moved out of the way (dig) or back into its column (return_paper)
    // goes to the depth of least expected future cost: weighted depths (a pair's paper is asked twice
    // as often, plus its demand as a filler: add_filler_demand) / P + for each handle color the depth
    // of the first paper of that color times the share of the requests with a hole of that color at
    // the handle (adaptive_holes); a dig never inserts above its barrier (the paper being dug for), so
    // the current dig is not lengthened.
    int adaptive_request = -1;
    bool adaptive_initialized = false;
    std::vector<double> adaptive_weights;
    std::vector<std::array<double, 2>> adaptive_holes;
    // Returns may use the column top without a penalty; modes 1 and 2 then simulate the same plan.
    static constexpr double kTopPenalty = 0.00, kEndWeight = 1.0;
    long long plan_failures = 0;
    // Estimate each paper's filler savings over all targets. Shift its adaptive weight by
    // kFillerDemandWeight times the deviation from its column mean, with a minimum weight of 0.25.
    static constexpr double kFillerDemandWeight = 0.25;
    double filler_demand_spread = 0;  // the root mean square of the changes
    void add_filler_demand() {
        std::vector<double> utility(K), sum(H);
        std::vector<int> count(H);
        for (int k = M + 1; k < K; k++) {
            int c = col_of[k];
            if (c < 0) continue;
            for (int u = 0; u < P; u++) {
                int d = ded[u];
                if (d < 0 || d == k) continue;
                u64 shown = h_opq[k] & ~h_opq[d], wrong = shown & (h_blk[k] ^ handle_bits(A[u]));
                int level = wrong ? 64 - __builtin_clzll(wrong) : 0;
                if (level >= c) continue;
                u64 cover = shown & low_bits(c) & ~low_bits(level);
                double p0 = 1, p1 = 0, expected = 0;
                for (u64 bits = cover; bits; bits &= bits - 1) {
                    int j = __builtin_ctzll(bits), color = A[u] >> handle[j] & 1;
                    double total = adaptive_holes[j][0] + adaptive_holes[j][1];
                    double bad = total ? adaptive_holes[j][color ^ 1] / total : .5;
                    p1 = p1 * (1 - bad) + p0 * bad;
                    p0 *= 1 - bad;
                    expected += bad;
                }

                const double value = expected - (1 - p0) - .8 * (1 - p0 - p1);
                utility[k] += std::max(0.0, value) / P;
            }
            sum[c] += utility[k];
            count[c]++;
        }
        double square = 0;
        int n = 0;
        for (int k = M + 1; k < K; k++) {
            int c = col_of[k];
            if (c < 0 || sum[c] <= 1e-12) continue;
            double mean = sum[c] / count[c], change = kFillerDemandWeight * (utility[k] / mean - 1);
            change = std::max(change, .25 - adaptive_weights[k]);
            adaptive_weights[k] += change;
            square += change * change;
            n++;
        }
        filler_demand_spread = std::sqrt(square / std::max(1, n));
    }
    void init_adaptive() {  // (once)
        if (adaptive_initialized) return;
        adaptive_initialized = true;
        adaptive_weights.assign(K, 0.0);
        adaptive_holes.assign(H, {0.0, 0.0});
        column_color.assign(K, -1);
        for (int k = 0; k < K; k++)
            if (col_of[k] >= 0) column_color[k] = 2 * col_of[k] + int(paper[k].black >> handle[col_of[k]] & 1);
        for (int u = 0; u < P; u++) {
            int d = ded[u];
            if (d < 0) continue;
            adaptive_weights[d] += 1.0;
            for (int c = 0; c < H; c++)
                if (!(paper[d].opaque >> handle[c] & 1)) adaptive_holes[c][A[u] >> handle[c] & 1] += 1.0 / P;
        }
        add_filler_demand();
        init_stay_value();
        init_colmdp();
        std::array<int, 64> sizes{};
        for (int k = 0; k < K; k++) if (col_of[k] >= 0) sizes[col_of[k]]++;
        const int stride = *std::max_element(sizes.begin(), sizes.begin() + H) + 1;
        depth_terms.resize(K * stride);
        for (int k = 0; k < K; k++) {
            for (int depth = 0; depth < stride; depth++)
                depth_terms[k * stride + depth] = adaptive_weights[k] * depth / P;
            next_paper[k] = {uint16_t(k * stride), uint8_t(column_color[k]), uint8_t(colmdp_type[k])};
        }
    }
    // A filler left below the generic layer may serve the next request as it is. stay_table[k][level]:
    // for paper k left as a filler of that level (showing on its opaque handles from h_level on), the
    // share of the targets (not of paper k, and whose column handle k does not cover) whose handle
    // holes k shows right wherever it covers them (probability), and per other handle the share of
    // those targets with a hole there that k covers (cover). filler_charge and adaptive_next_cost
    // credit such fillers with kStayStrength / kCoverStrength.
    static constexpr double kStayStrength = .25, kCoverStrength = .25;
    struct StayValue {
        double probability = 0;
        std::array<double, 64> cover{};
    };
    std::vector<std::vector<StayValue>> stay_table;
    void init_stay_value() {
        std::array<u64, P> target_bits;
        for (int u = 0; u < P; ++u) target_bits[u] = handle_bits(A[u]);
        stay_table.assign(K, std::vector<StayValue>(H + 1));
        for (int k = M + 1; k < K; k++)
            for (int level = 0; level <= col_of[k]; level++) {
                auto& value = stay_table[k][level];
                value = {};
                u64 shown = h_opq[k] & ~low_bits(level);
                for (int u = 0; u < P; u++) {
                    int d = ded[u];
                    if (d == k || (shown >> col_of[d] & 1)) continue;
                    u64 holes = shown & ~h_opq[d], target = target_bits[u];
                    if ((h_blk[k] ^ target) & holes) continue;
                    value.probability += 1. / P;
                    for (u64 z = holes; z; z &= z - 1) {
                        int c = __builtin_ctzll(z);
                        if (c != col_of[k]) value.cover[c] += 1. / P;
                    }
                }
            }
    }
    // above[k] marks papers through the M-th generic sheet in one scan. A column paper is below
    // the generic layer exactly when all M sheets are found and !above[k].
    struct GenericSplit {
        std::array<bool, K> above{};
        bool complete = false;
        bool below(int k) const { return complete && !above[k]; }
    };
    void split_generic(GenericSplit& split) const {
        int count = 0;
        for (int i = 0; i < K && count < M; i++) {
            split.above[order[i]] = true;
            if (order[i] < M) count++;
        }
        split.complete = count == M;
    }
    // A paper left out costs its return later but is often re-used instead (kFillerCharge each); a
    // filler below the generic layer that would often stay right is charged less (stay_table).
    // Charge fillers by their estimated probability of needing a later return.
    static constexpr double kFillerCharge = 0.7;
    double filler_charge(const GenericSplit& split) const {
        CF_SCOPE(filler_charge);
        double charge = kFillerCharge * fillers.size();
        for (auto f : fillers)
            if (split.below(f.paper)) charge += kStayStrength * (.3 - stay_table[f.paper][f.lvl].probability);
        return charge;
    }
    // Expected cost of the next request from the stack left (weighted depths and handle colors).
    // column_color[k] = 2 * column + the color of paper k at its column's handle (-1: not a
    // column paper), set by init_adaptive; the sums are taken in the same order as before.
    std::vector<int> column_color;
    struct NextPaper { uint16_t offset; uint8_t color, type; };
    std::array<NextPaper, K> next_paper;
    std::vector<double> depth_terms;
    // A value depends on the ordered in-column subsequence and the below-generic
    // fillers (paper, level), not on the positions/order of generic sheets. The
    // excluded column papers also determine available colors. Compare the complete
    // key, and retain the exact double computed with the original summation order.
    struct NextValueEntry {
        std::array<uint8_t, 3 * K + 8> key;
        int size = 0;
        double value = 0;
    };
    mutable std::array<NextValueEntry, 256> next_value_cache;
    mutable long long cf_value_hits = 0, cf_value_misses = 0;
    double adaptive_next_cost(const GenericSplit& split) const {
        CF_SCOPE(next_cost);
        std::array<bool, K> extra{};  // the lifted paper and the fillers (out of their columns)
        if (top_d >= 0) extra[top_d] = true;
        for (auto f : fillers) extra[f.paper] = true;
        std::array<uint8_t, 3 * K + 8> key;
        int key_size = 0;
        for (int k : order) if (col_of[k] >= 0 && !extra[k]) key[key_size++] = k;
        const int in_place = key_size;
        key[key_size++] = 255;
        for (const auto& f : fillers) if (split.below(f.paper)) {
            key[key_size++] = f.paper;
            key[key_size++] = f.lvl;
        }
        const int padded = (key_size + 7) & ~7;
        std::fill(key.begin() + key_size, key.begin() + padded, 0);
        u64 hash = 0xcbf29ce484222325ULL ^ key_size;
        for (int i = 0; i < padded; i += 8) {
            u64 word;
            std::memcpy(&word, key.data() + i, 8);
            hash = (hash ^ word) * 0x100000001b3ULL;
        }
        NextValueEntry& cached = next_value_cache[(hash ^ (hash >> 32)) & (next_value_cache.size() - 1)];
        if (cached.size == key_size && std::memcmp(cached.key.data(), key.data(), key_size) == 0) {
            cf_value_hits++;
            return cached.value;
        }
        cf_value_misses++;
        std::array<int, 64> rank{};
        std::array<int, 128> first;
        std::array<bool, 128> available{};
        if (top_d >= 0 && column_color[top_d] >= 0) available[column_color[top_d]] = true;
        for (const auto& f : fillers) if (column_color[f.paper] >= 0) available[column_color[f.paper]] = true;
        std::fill(first.begin(), first.begin() + 2 * H, -1);
        // With every column covered, encode its in-place type sequence during the
        // same scan. A leading 1 distinguishes lengths; each type uses exactly two bits.
        const bool mdp_scan = colmdp_next && colmdp_columns == H;
        std::array<uint32_t, 64> mdp_code;
        if (mdp_scan) std::fill(mdp_code.begin(), mdp_code.begin() + H, 1);
        double cost = 0;
        // The key already contains this exact subsequence, in stack order.
        // Iterate it without testing every paper's role again. Terms were computed
        // with the original multiplication/division; only the same ordered additions remain.
        for(int i=0;i<in_place;) {
            const int c=next_paper[key[i]].color>>1;
            int depth=rank[c];
            uint32_t code=mdp_scan?mdp_code[c]:0;
            // Runs use register-local rank/code, but retain the exact global
            // left-to-right addition order. Disjoint runs of one column also work.
            do {
                const auto& np=next_paper[key[i]];
                if(first[np.color]<0)first[np.color]=depth;
                cost+=depth_terms[np.offset+depth];
                ++depth;
                if(mdp_scan)code=(code<<2)|np.type;
                ++i;
            } while(i<in_place && (next_paper[key[i]].color>>1)==c);
            rank[c]=depth;
            if(mdp_scan)mdp_code[c]=code;
        }
        // covered[c][color]: the largest share of the requests whose hole at h_c a filler below the
        // generic layer shows in that color (stay_table)
        std::array<std::array<double, 2>, 64> covered{};
        for (auto f : fillers)
            if (split.below(f.paper)) {
                const auto& value = stay_table[f.paper][f.lvl];
                for (int c = 0; c < H; c++) {
                    int color = h_blk[f.paper] >> c & 1;
                    covered[c][color] = std::max(covered[c][color], value.cover[c]);
                }
            }
        for (int c = 0; c < H; c++)
            for (int color = 0; color < 2; color++) {
                int fixes = available[2 * c + color] ? 0 : first[2 * c + color];
                if (fixes < 0) fixes = rank[c];
                cost += (adaptive_holes[c][color] - kCoverStrength * covered[c][color]) * fixes;
            }
        if (mdp_scan)
            cost += colmdp_next_scanned(mdp_code, cost);
        else if (colmdp_next)
            cost += colmdp_next_term(extra, available, first, rank, covered);
        cached.size = key_size;
        std::memcpy(cached.key.data(), key.data(), key_size);
        cached.value = cost;
        return cost;
    }
    // The cost of a plan of `moves` moves that leaves the current state (process).
    double plan_cost(size_t moves) const {
        CF_SCOPE(plan_cost);
        GenericSplit split;
        split_generic(split);
        return moves + filler_charge(split) + kEndWeight * adaptive_next_cost(split);
    }

    // Puts paper x into its column at the best depth below `barrier`; mode 1 adds kTopPenalty for the
    // very top. With u, a handle of x's column that the paper of u leaves as a hole adds the digs to
    // set it for u (when not digging). barrier_stays: the barrier stays on top of the column (a dig of
    // a handle fix), else it leaves (it is lifted or placed as a filler); only the column MDP uses it.
    void adaptive_insert(int x, int u, int barrier = -1, int mode = 2, bool barrier_stays = false) {
        CF_SCOPE(insert);
        const int c = col_of[x], cx = paper[x].black >> handle[c] & 1;
        std::array<int, K> v, vpos;  // the other papers in place in the column, top first, and their positions
        int n = 0, xpos = -1;        // (the positions kept for the move below)
        for (int i = 0; i < K; i++) {
            const int k = order[i];
            if (k == x)
                xpos = i;
            else if (in_column(k, c))
                vpos[n] = i, v[n++] = k;
        }
        int lo = 0;
        if (barrier >= 0) {
            auto it = std::find(v.begin(), v.begin() + n, barrier);
            if (it == v.begin() + n) {
                invalid = true;
                return;
            }
            lo = int(it - v.begin()) + 1;
        }
        std::array<double, K + 1> suffix;  // suffix[i]: the weights of v[i..n)
        suffix[n] = 0;
        std::array<int, 2> first = {n, n};
        for (int i = n - 1; i >= 0; i--) {
            suffix[i] = suffix[i + 1] + adaptive_weights[v[i]];
            first[paper[v[i]].black >> handle[c] & 1] = i;
        }
        int requested = u >= 0 ? ded[u] : -1;
        bool need = requested >= 0 && c != col_of[requested] && !(paper[requested].opaque >> handle[c] & 1);
        int desired = u >= 0 ? (A[u] >> handle[c] & 1) : 0;
        // the column MDP: colmdp_drop of the one-step cost replaced by colmdp_weight times the long-run
        // value of the column after the insertion at each gap (colmdp_gap_values), for the kinds of
        // insertion in colmdp_cases (x out of its column: a return; else a dig)
        const bool mdp = colmdp_insert && colmdp[c].ok &&
                         (colmdp_cases & (x == top_d || is_filler(x) ? (barrier < 0 ? 1 : 8) : (barrier_stays ? 4 : 2)));
        std::array<float, K + 1> mdp_value;
        if (mdp && colmdp_ctrl <= 0)
            colmdp_gap_values(x, v.data(), n, lo, barrier_stays, need && barrier < 0 && colmdp_need_fix ? desired : -1,
                              mdp_value);
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
            if (mdp) value = colmdp_ctrl > 0 ? colmdp_ctrl * value : value + colmdp_weight[c] * mdp_value[i] - colmdp_drop * value;
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
            const int from = xpos, to = vpos[gap];
            move_from(x, from, from < to ? to - 1 : to);
        } else if (vpos[n - 1] + 1 != xpos)  // as move_after(x, v[n - 1])
            move_from(x, xpos, vpos[n - 1] - int(vpos[n - 1] > xpos) + 1);
    }

    // ==== Solver: column MDP values in the future-cost model ====

    // A ColumnMdp per column (init_colmdp, after the adaptive weights; ColMdpConfig). The type of a
    // paper: 2 * (it serves two targets) + its color at its column's handle; the rate of a type: the
    // mean adaptive weight of its papers in the column / P; the rate of a handle color: adaptive_holes
    // (the units of the one-step model, per request). In a covered column (ok):
    //   - adaptive_insert: the value of a gap is (1 - colmdp_drop) times the one-step cost plus
    //     colmdp_weight[c] times the MDP value of the column after the insertion (colmdp_gap_values),
    //     plus the digs of this request as before;
    //   - adaptive_next_cost: (1 - colmdp_next_drop) times its cost plus colmdp_next_weight[c] times F
    //     of the papers in place of every column.
    // The weights are COLMDP_MIX / COLMDP_NEXTMIX, times the column's events per request W with
    // COLMDP_UNIT=0 (the values per request, as the one-step model), times 1 with COLMDP_UNIT=1 (the
    // values per event: moves over the long run).
    std::vector<ColumnMdp> colmdp;
    std::vector<int> colmdp_type;       // per paper: its type in its column (-1: not a column paper)
    std::vector<double> colmdp_weight;  // per column (0: not covered)
    double colmdp_ctrl = 0;
    double colmdp_drop = 0, colmdp_next_drop = 0;  // the shares of the one-step cost removed (1 - keep)
    std::vector<double> colmdp_next_weight;       // per column: as colmdp_weight, for adaptive_next_cost
    bool colmdp_insert = false, colmdp_next = false, colmdp_need_fix = true;
    int colmdp_cases = 0;  // (ColMdpConfig::cases)
    int colmdp_columns = 0;  // covered columns
    long long colmdp_full_states = 0, colmdp_sequences = 0;
    double colmdp_sec = 0;
    void init_colmdp() {
        const ColMdpConfig& config = colmdp_config();
        colmdp.assign(H, ColumnMdp{});
        colmdp_type.assign(K, -1);
        colmdp_weight.assign(H, 0.0);
        colmdp_next_weight.assign(H, 0.0);
        if (!config.on) return;
        const auto start = Clock::now();
        std::vector<int> targets(K, 0);
        for (int u = 0; u < P; u++)
            if (ded[u] >= 0) targets[ded[u]]++;
        for (int c = 0; c < H; c++) {
            std::array<int, 4> count{};
            std::array<double, 4> weight{}, rate{};
            for (int k = 0; k < K; k++) {
                if (col_of[k] != c) continue;
                const int t = 2 * int(targets[k] >= 2) + int(paper[k].black >> handle[c] & 1);
                colmdp_type[k] = t;
                count[t]++;
                weight[t] += adaptive_weights[k];
            }
            for (int t = 0; t < 4; t++) rate[t] = count[t] ? weight[t] / count[t] / P : 0.0;
            if (!colmdp[c].build(count, rate, adaptive_holes[c], config.iters, config.max_length, config.max_full,
                                 config.max_sequences))
                continue;
            colmdp_columns++;
            colmdp_full_states += colmdp[c].full;
            colmdp_sequences += colmdp[c].sequences;
            colmdp_weight[c] = config.mix * (config.unit == 0 ? colmdp[c].rate : 1.0);
            colmdp_next_weight[c] = config.next_mix * (config.unit == 0 ? colmdp[c].rate : 1.0);
        }
        colmdp_drop = 1 - config.keep;
        colmdp_next_drop = 1 - config.next_keep;
        colmdp_cases = config.cases;
        colmdp_ctrl = config.ctrl;
        colmdp_need_fix = config.need_fix;
        colmdp_insert = config.insert && colmdp_columns > 0;
        colmdp_next = config.next && colmdp_columns > 0;
        colmdp_sec = scaled_since(start);
    }
    // The MDP values of x's column after x is inserted at each gap i in [lo, n] of v[0..n) (the other
    // papers in place, top first) into out[i]: without a barrier (a return; lo = 0), F of the column,
    // or with fix_color >= 0 (the column is dug for that color later in this request) fix[fix_color];
    // with a barrier that leaves (a dig for a paper lifted or placed as a filler: the papers above it
    // are dug as well), F of the papers below the barrier; with a barrier that stays (a dig of a handle
    // fix), H of the barrier and the papers below it.
    void colmdp_gap_values(int x, const int* v, int n, int lo, bool stays, int fix_color,
                           std::array<float, K + 1>& out) const {
        CF_SCOPE(mdp_gaps);
        const ColumnMdp& mdp = colmdp[col_of[x]];
        const int from = lo == 0 ? 0 : stays ? lo - 1 : lo;  // q = v[from..n); gap i of v is gap i - from of q
        const int L = n - from;
        std::array<int, ColumnMdp::kMaxLength> q;
        std::array<int, ColumnMdp::kMaxLength + 1> index;
        for (int j = 0; j < L; j++) q[j] = colmdp_type[v[from + j]];
        mdp.insertion_indices(q.data(), L, colmdp_type[x], index.data());
        const std::vector<float>& table = lo == 0 ? (fix_color >= 0 ? mdp.fix[fix_color] : mdp.F) : stays ? mdp.H : mdp.F;
        for (int i = lo; i <= n; i++) out[i] = table[index[i - from]];
    }
    // The packed type sequence completely determines a column's F. Each column
    // retains 16 exact keys/values across requests; all model parameters are immutable.
    mutable std::array<std::array<uint32_t, 16>, 64> colmdp_code_cache{};
    mutable std::array<std::array<float, 16>, 64> colmdp_value_cache{};
    // With every column covered, remove colmdp_next_drop of the one-step cost and
    // add the same weighted F values in column order. Cache misses use the original
    // integer suffix-count/lexicographic index; floating-point additions are unchanged.
    double colmdp_next_scanned(const std::array<uint32_t, 64>& codes, double cost) const {
        double term = -colmdp_next_drop * cost;
        for (int c = 0; c < H; c++) {
            // The leading 1 records the length, followed by two exact bits per type.
            // At most 15 papers fit a covered column, so this is a collision-free
            // sequence identifier. Hash collisions only replace an entry, never a value.
            const uint32_t key = codes[c];
            const int slot = (key ^ (key >> 9) ^ (key >> 17)) & 15;
            if (colmdp_code_cache[c][slot] != key) {
                const ColumnMdp& mdp = colmdp[c];
                int r = 0, rank = 0;
                for (uint32_t rest = key; rest > 1; rest >>= 2) {
                    const int t = rest & 3;
                    r += mdp.radix[t];
                    rank += mdp.before[r][t];
                }
                colmdp_code_cache[c][slot] = key;
                colmdp_value_cache[c][slot] = mdp.F[mdp.offset[r] + rank];
            }
            term += colmdp_next_weight[c] * colmdp_value_cache[c][slot];
        }
        return term;
    }
    // The same when some column is not covered (its arrays passed): in every covered column,
    // colmdp_next_drop of the column's terms of adaptive_next_cost (the weighted depths and the handle
    // colors) removed and colmdp_next_weight times F of its papers in place added.
    double colmdp_next_term(const std::array<bool, K>& extra, const std::array<bool, 128>& available,
                            const std::array<int, 128>& first, const std::array<int, 64>& rank,
                            const std::array<std::array<double, 2>, 64>& covered) const {
        std::array<int, 64> left, start, sequence_rank{}, depth{};  // count vector of the papers in place not yet seen
        std::array<double, 64> one_step{};
        for (int c = 0; c < H; c++) left[c] = colmdp[c].ok ? colmdp[c].top : -1;
        auto take_out = [&](int k) {
            const int c = col_of[k];
            if (c >= 0 && colmdp[c].ok) left[c] -= colmdp[c].radix[colmdp_type[k]];
        };
        if (top_d >= 0) take_out(top_d);
        for (const auto& f : fillers) take_out(f.paper);
        start = left;
        for (int k : order) {
            const int c = col_of[k];
            if (c < 0 || extra[k] || !colmdp[c].ok) continue;
            const ColumnMdp& mdp = colmdp[c];
            const int t = colmdp_type[k];
            one_step[c] += adaptive_weights[k] * depth[c] / P;
            depth[c]++;
            sequence_rank[c] += mdp.before[left[c]][t];
            left[c] -= mdp.radix[t];
        }
        double term = 0;
        for (int c = 0; c < H; c++) {
            if (!colmdp[c].ok) continue;
            for (int color = 0; color < 2; color++) {
                int fixes = available[2 * c + color] ? 0 : first[2 * c + color];
                if (fixes < 0) fixes = rank[c];
                one_step[c] += (adaptive_holes[c][color] - kCoverStrength * covered[c][color]) * fixes;
            }
            const ColumnMdp& mdp = colmdp[c];
            term += colmdp_next_weight[c] * mdp.F[mdp.offset[start[c]] + sequence_rank[c]] - colmdp_next_drop * one_step[c];
        }
        return term;
    }

    // ==== Solver: stack operations (moves, digs, lifts, handle fixes) ====

    int index_of(int k) const {
        const auto* found = static_cast<const uint8_t*>(std::memchr(order.data(), k, K));
        return found ? int(found - order.data()) : -1;
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
    void move(int k, int d) { move_from(k, index_of(k), d); }
    // move with the position i of k known
    void move_from(int k, int i, int d) {
        if (i == d) return;
        if (check_vis && !visible_at(k, i)) invalid = true;
        shift_paper(i, d);
        ops.push_back({k, d});
        OP_TAG(op_tags.push_back(op_tag);)
    }
    // Moves paper k just below paper x.
    void move_after(int k, int x) {
        const int i = index_of(k), ix = index_of(x);
        move_from(k, i, ix - int(ix > i) + 1);
    }
    // Is paper k, at position i, visible?
    bool visible_at(int k, int i) const {
        u64 e = paper[k].opaque;
        for (int j = 0; j < i && e; j++) e &= ~paper[order[j]].opaque;
        return e != 0;
    }
    // The paper at position i goes to position d (the papers between shift by one).
    void shift_paper(int i, int d) {
        assert(0 <= i && i < K && 0 <= d && d < K);
        shift_byte(order, i, d);
    }
    bool is_filler(int k) const {
        for (auto& f : fillers)
            if (f.paper == k) return true;
        return false;
    }
    void drop_filler(int k) {
        fillers.erase_if([&](const Filler& f) { return f.paper == k; });
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
    // for; -1: below the column bottom), at the best depth (adaptive_insert; stays: the barrier stays
    // on top, a handle fix).
    void dig(int l, int barrier = -1, bool stays = false) {
        int t = column_top(l);
        if (t < 0) {
            invalid = true;
            return;
        }
        if (barrier < 0) {
            for (int k : order)
                if (in_column(k, l)) barrier = k;
        }
        if (t != barrier) adaptive_insert(t, adaptive_request, barrier, 2, stays);
    }
    // The cap stays above the generic layer. A dedicated sheet printed white
    // at the cap window requests black by stopping immediately below the cap;
    // otherwise the usual top insertion shows its own (correct) printed color.
    void move_to_target_top(int d) {
        OP_LABEL(kOpLift);
        const bool needs_cap = (A[adaptive_request] & kCapBit) && !(paper[d].black & kCapBit);
        if (!needs_cap)
            move(d, 0);
        else {
            const int cp = index_of(kCapPaper), dp = index_of(d);
            move(d, cp + int(dp > cp));
        }
    }
    // Digs the column of d until d is its top, and performs its cap-aware lift.
    void lift(int d) {
        int c = col_of[d];
        for (int it = 0; column_top(c) != d; it++) {
            if (it >= K || invalid) {
                invalid = true;
                return;
            }
            OP_LABEL(kOpDig);
            dig(c, d);
        }
        move_to_target_top(d);
        top_d = d;
    }
    // Digs column l until its handle shows `color` (until the first paper of that color is on top).
    void set_handle(int l, int color) {
        OP_LABEL(kOpFix);
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
            dig(l, barrier, true);
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
    // handle_fix_cost of A_u's color for every handle of the windows hh (0 for the others), in one
    // scan of the stack: the papers in place of a column above its first paper of the right color.
    std::vector<int> fix_costs(int u, u64 hh) const {
        std::vector<int> fix(H, 0);
        u64 pending = hh;
        for (int k : order) {
            int c = col_of[k];
            if (c < 0 || !(pending >> handle[c] & 1) || k == top_d || is_filler(k)) continue;
            if (!((paper[k].black ^ A[u]) >> handle[c] & 1))
                pending &= ~(1ULL << handle[c]);
            else
                fix[c]++;
        }
        for (int c = 0; c < H; c++)
            if (pending >> handle[c] & 1) fix[c] = 0;  // no paper of the right color: as handle_fix_cost
        return fix;
    }
    // The level just past the deepest handle of the windows `wrong`.
    int level_past(u64 wrong) const {
        u64 mask = handle_bits(wrong);
        return mask ? 64 - __builtin_clzll(mask) : 0;
    }
    // The handle windows a filler shows on.
    u64 shown_by(const Filler& f) const {
        u64 m = 0;
        for (int j = f.lvl; j <= f.hi; j++)
            if (paper[f.paper].opaque >> handle[j] & 1) m |= 1ULL << handle[j];
        return m;
    }
    // A filler [lvl, c] placed now would sit above a filler of a deeper level that it reaches.
    static bool reaches_deeper(int lvl, int c, const FillerList& placed) {
        for (auto& f : placed)
            if (f.lvl > lvl && c >= f.lvl) return true;
        return false;
    }
    // Paper x to level lvl: just above the first paper in place of a column >= lvl, i.e. below the
    // generic layer, the columns 0..lvl-1 and the fillers of lower levels. lazy: no move if x is
    // already between the last paper in place of a column < lvl (or the generic layer, below_generic) and
    // that position.
    void move_to_level(int x, int lvl, bool lazy = false, bool below_generic = false) {
        int q = K, last_above = -1;
        for (int i = 0; i < K; i++) {
            int k = order[i];
            if (below_generic && k < M) last_above = i;  // the deepest sheet
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
            OP_LABEL(kOpFdig);
            dig(c, x);
        }
        {
            OP_LABEL(kOpFill);
            move_to_level(x, lvl);
        }
        fillers.push_back({x, lvl, c});
        hh &= ~shown_by(fillers.back());
    }
    // An out-of-place paper x (the lifted paper or a filler) goes back to its column at the best
    // depth (adaptive_insert; mode 1 adds the top penalty); below u's paper if that paper is still in
    // place in the same column (the column is dug for it in this request).
    void return_paper(int x, int u, int mode) {
        OP_LABEL(x == top_d ? kOpRet : kOpFret);
        const int d = u >= 0 ? ded[u] : -1;
        adaptive_insert(x, u, d >= 0 && d != x && col_of[d] == col_of[x] && in_column(d, col_of[x]) ? d : -1, mode);
    }
    // Returns the fillers olds to their columns (return_paper), each time the last one in the list
    // that is visible: fillers may hide each other
    // (fillers_reachable), and an invisible paper cannot move. The order is the reverse list order
    // when nothing is hidden. Invalid if at some point none of the fillers left is visible.
    void return_visible_fillers(const FillerList& olds, int u, int mode) {
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

    // ==== Request plans: options, fillers and the joint interval DP ====

    // Plan options: return the previous product (1/2), or reuse it as a filler (3);
    // return old fillers (0/1), reposition them (4), or jointly choose them with new fillers (5).
    struct PlanOpt {
        int ret_mode = 0;
        int fret_mode = 0;
        bool use_filler = false;
        bool value_fillers = false;  // joint DP also tries the marginal stack value
        bool complete_value = false;
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
    // the candidate lists of the interval DPs reuse their storage (cleared for each use; the
    // DPs never overlap).
    mutable std::vector<std::vector<Cand>> cand_scratch;
    std::vector<std::vector<Cand>>& fresh_candidates() const {
        cand_scratch.resize(H);
        for (auto& v : cand_scratch) v.clear();
        return cand_scratch;
    }
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
    // taking (up to kFillerDepth).
    static constexpr int kFillerDepth = 4, kFillerCost = 1, kMaxFillers = 8;
    // The papers in place at depth <= kFillerDepth of every column (top first), in one scan of the
    // stack: tops[c][0..counts[c]).
    using ColumnTops = std::array<std::array<int, kFillerDepth + 1>, 64>;
    void all_column_tops(ColumnTops& tops, std::array<int, 64>& counts) const {
        counts = {};
        std::array<bool, K> out{};  // the papers out of their columns (in_column in one pass)
        if (top_d >= 0) out[top_d] = true;
        for (const auto& f : fillers) out[f.paper] = true;
        for (int k : order) {
            int c = col_of[k];
            if (c < 0 || counts[c] > kFillerDepth || out[k]) continue;
            tops[c][counts[c]++] = k;
        }
    }
    // Fillers when D (column l) is already on top (kept plans): the papers at depth <= kFillerDepth of
    // the columns whose handle is a hole of D, at the level just past their deepest wrong handle.
    std::vector<FillerPick> choose_fillers_dp(int u, int d, u64 hh) const {
        auto fix = fix_costs(u, hh);
        auto& cand = fresh_candidates();
        ColumnTops tops;
        std::array<int, 64> ntop;
        all_column_tops(tops, ntop);
        for (int c = 0; c < H; c++) {
            if (!(hh >> handle[c] & 1)) continue;
            const auto& top = tops[c];
            if (ntop[c] == 0 || top[0] == d) continue;
            for (int depth = 0; depth < ntop[c]; depth++) {
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
    // A filler above the bottom of the generic layer may show on the generic holes of D;
    // where its colors differ from A_u
    // it cannot stay there: re-leveling moves it below the generic layer, and it is not harmless in
    // place.
    bool gen_harm(int x, int d, int u) const {
        if (d < 0 || index_of(x) > generic_bottom()) return false;
        return (paper[x].opaque & gmask & ~paper[d].opaque & (paper[x].black ^ A[u])) != 0;
    }
    // Reposition old fillers that cover remaining holes of D. Keep harmless others in place;
    // return the rest. Process them top-down because fillers may hide one another.
    // fillers_reachable later checks that every retained filler can be removed.
    void refill_or_return(int u, FillerList olds, u64& pre_cov, FillerList& placed) {
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
                    use = save >= 0;
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
            {
                OP_LABEL(kOpRelevel);
                move_to_level(x, lvl, true, gen_harm(x, d, u));
            }
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
    long long value_filler_trials = 0;
    long long value_filler_plans = 0, value_filler_better = 0;
    double value_filler_gain = 0;
    // Marginal future cost of taking one paper out: its return charge, the column
    // left after digging, and the coverage credit at this level. Keep the immediate
    // extraction moves separate. The interval DP adds these local estimates; the
    // completed plan is still checked and scored by the unchanged plan_cost.
    long long complete_value_calls = 0, complete_value_invalid = 0, complete_value_plans = 0;
    // With request >= 0, compare complete local plans: include the extraction
    // moves and fix the holes left uncovered. c == -1 gives the no-filler reference.
    double filler_value_increment(int c, int depth, int level, double before,
                                  int request = -1, u64 holes = 0) {
        const auto state = save();
        const size_t nops = ops.size();
        const bool was_invalid = invalid, was_checking = check_vis;
        OP_TAG(const size_t ntags = op_tags.size(); const auto last_tag = op_tag;)
        check_vis = false;  // a post-lift placement is evaluated before D is lifted
        invalid = false;
        u64 hh = holes;
        if (c >= 0) place_filler(c, depth, level, hh);
        if (request >= 0) {
            if (!invalid) fix_handles(request, hh);
            ++complete_value_calls;
            complete_value_invalid += invalid;
        }
        const double delta = invalid ? 1e30 : plan_cost(request < 0 ? 0 : ops.size() - nops) - before;
        restore(state);
        ops.resize(nops);
        invalid = was_invalid;
        check_vis = was_checking;
        OP_TAG(op_tags.resize(ntags); op_tag = last_tag;)
        return delta;
    }
    std::vector<Cand> joint_value_picks;
    long long complete_value_duplicates = 0;
    void run_joint(int u, const PlanOpt& opt) {
        CF_SCOPE(run_joint);
        int d = ded[u];
        if (d < 0 || d == top_d) {
            invalid = true;
            return;
        }
        const int l = col_of[d];
        const double before_value = opt.value_fillers ? plan_cost(0) : 0;
        const u64 hole_all = (gmask | hmask) & ~paper[d].opaque;
        u64 hh = hole_all & ~gmask;
        auto fix = fix_costs(u, hh);
        const double completed_reference = opt.complete_value ? filler_value_increment(-1, 0, 0, 0, u, hh) : 1e30;
        // With no feasible completed reference, every weight would be the
        // original weighted plan's weight. That plan was already tried.
        if (opt.complete_value && completed_reference >= 1e29) {
            ++complete_value_duplicates;
            invalid = true;
            return;
        }
        const bool d_out = is_filler(d);
        FillerList olds;
        for (auto& f : fillers)
            if (f.paper != d) olds.push_back(f);
        const int x0 = top_d;
        auto& cand = fresh_candidates();
        auto mism_level = [&](int x) { return level_past((paper[x].black ^ A[u]) & paper[x].opaque & hh); };
        // (the handles j in [lvl, c] that are holes and that x covers, as a mask of handle indices)
        const u64 hh_index = handle_bits(hh);
        auto saved = [&](int x, int lvl, int c, bool skip_c) {
            u64 m = h_opq[x] & hh_index & low_bits(c + 1) & ~low_bits(lvl);
            if (skip_c) m &= ~(1ULL << c);
            int sv = 0;
            for (; m; m &= m - 1) sv += fix[__builtin_ctzll(m)];
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
        ColumnTops tops;
        std::array<int, 64> ntop;
        all_column_tops(tops, ntop);
        for (int c = 0; c < H; c++) {
            bool hole_c = hh >> handle[c] & 1;
            if (c == l || (d_out && !hole_c)) continue;
            const auto& top = tops[c];
            for (int depth = 0; depth < ntop[c]; depth++) {
                int f = top[depth];
                int lvl = mism_level(f);
                for (int lv = lvl; lv <= c; lv++) {
                    if (lv > lvl && !covers(f, lv)) continue;
                    bool post = d_out || (c > l && lv <= l && (paper[f].opaque >> handle[l] & 1));
                    const int raw_gain = saved(f, lv, c, depth == 0 && hole_c) - 1 - depth;
                    double gain = raw_gain;
                    if (opt.value_fillers) {
                        if (raw_gain < 1) continue;
                        ++value_filler_trials;
                        if (opt.complete_value && completed_reference < 1e29)
                            gain = -filler_value_increment(c, depth, lv, completed_reference, u, hh);
                        else gain -= filler_value_increment(c, depth, lv, before_value);
                    }
                    if (opt.value_fillers ? gain > 0 : raw_gain >= kFillerCost)
                        cand[c].push_back({lv, gain, c, 0, 0, f, post});
                }
            }
        }
        const auto picks = best_intervals(cand);
        if (opt.value_fillers && !opt.complete_value) joint_value_picks = picks;
        if (opt.complete_value && picks.size() == joint_value_picks.size() &&
            std::equal(picks.begin(), picks.end(), joint_value_picks.begin(), [](const Cand& a, const Cand& b) {
                return a.lvl == b.lvl && a.c == b.c && a.depth == b.depth &&
                       a.kind == b.kind && a.idx == b.idx && a.post == b.post;
            })) {
            ++complete_value_duplicates;
            invalid = true;
            return;
        }
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
                OP_LABEL(kOpReuse);
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
            OP_LABEL(kOpRelevel);
            if (old_dec[i] == 1) move_to_level(x, old_lvl[i], true, gen_harm(x, d, u));
        }
        for (auto& f : fillers)
            if (f.paper != d) hh &= ~shown_by(f);
        set_generic(u, hole_all);
        for (auto& cd : picks)
            if (cd.kind == 0 && !cd.post) place_filler(cd.c, depth_in_column(cd.idx), cd.lvl, hh);
        if (d_out) {
            drop_filler(d);
            move_to_target_top(d);
            top_d = d;
        } else {
            lift(d);
        }
        for (auto& cd : picks)
            if (cd.kind == 0 && cd.post) place_filler(cd.c, depth_in_column(cd.idx), cd.lvl, hh);
        fix_handles(u, hh);
    }
    // ==== Request plans: one plan (run_plan) and its shared tail ====

    // One plan: the previous lifted paper and the old fillers (PlanOpt), the generic layer, new
    // fillers (chosen with every column top visible: those that do not reach D's handle go in before
    // the dig and the lift, the others after), the lift of D and the digs of the remaining handle
    // holes.
    void run_plan(int u, const PlanOpt& opt) {
        CF_SCOPE(run_plan);
        if (opt.fret_mode == 5) {
            run_joint(u, opt);
            return;
        }
        u64 pre_cov = 0;
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
            FillerList vis_old, def_old;
            for (auto& f : fillers) (visible(f.paper) ? vis_old : def_old).push_back(f);
            FillerList placed = {{x, lvl, lp}};
            pre_cov |= cov0;
            auto put_back = [&](const FillerList& olds) {
                if (opt.fret_mode == 4)
                    refill_or_return(u, olds, pre_cov, placed);
                else
                    return_visible_fillers(olds, u, opt.fret_mode);
            };
            put_back(vis_old);
            {
                OP_LABEL(kOpReuse);
                move_to_level(x, lvl);
            }
            top_d = -1;
            put_back(def_old);
            for (auto& f : placed) fillers.push_back(f);
        } else {
            if (top_d >= 0) return_paper(top_d, u, opt.ret_mode);
            if (opt.fret_mode == 4) {
                FillerList olds = fillers, placed;
                refill_or_return(u, olds, pre_cov, placed);
                for (auto& f : placed) fillers.push_back(f);
            } else {
                const auto olds = fillers;
                return_visible_fillers(olds, u, opt.fret_mode);
            }
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
            if (e.hash == h && e.pre_cov == pre_cov && e.use_filler == opt.use_filler && e.top_d == top_d &&
                e.order == order && same_fillers(e.fillers, fillers)) {
                tail_hits++;
                order = e.out_order;
                top_d = e.out_top;
                fillers = e.out_fillers;
                ops.insert(ops.end(), e.out_ops.begin(), e.out_ops.end());
                OP_TAG(op_tags.insert(op_tags.end(), e.out_tags.begin(), e.out_tags.end());)
                invalid = e.out_invalid;
                return;
            }
        TailEntry e{h, order, top_d, fillers, pre_cov, opt.use_filler, {}, -1, {}, {}, false OP_TAG(, {})};
        const size_t prefix = ops.size();
        run_plan_tail(u, opt, pre_cov);
        e.out_order = order;
        e.out_top = top_d;
        e.out_fillers = fillers;
        e.out_ops.assign(ops.begin() + prefix, ops.end());
        OP_TAG(e.out_tags.assign(op_tags.begin() + prefix, op_tags.end());)
        e.out_invalid = invalid;
        tail_cache.push_back(std::move(e));
    }
    // Plans that reach the same state after their first part (the previous lifted paper and the old
    // fillers handled) share the rest: while process tries
    // the plan options (tail_cache_on), the result of run_plan_tail is kept per request and re-used
    // (the same moves appended, the same state). The output is unchanged.
    struct TailEntry {
        u64 hash;
        std::array<uint8_t, K> order{};
        int top_d;
        FillerList fillers;
        u64 pre_cov;
        bool use_filler;
        std::array<uint8_t, K> out_order{};
        int out_top;
        FillerList out_fillers;
        Moves out_ops;
        bool out_invalid;
        OP_TAG(std::vector<uint8_t> out_tags;)  // the labels of out_ops
    };
    std::vector<TailEntry> tail_cache;
    bool tail_cache_on = false;
    long long tail_hits = 0;
    static bool same_fillers(const FillerList& a, const FillerList& b) {
        if (a.size() != b.size()) return false;
        for (size_t i = 0; i < a.size(); i++)
            if (a[i].paper != b[i].paper || a[i].lvl != b[i].lvl || a[i].hi != b[i].hi) return false;
        return true;
    }
    // The second part of run_plan: the generic layer, the new fillers, the lift of D and the digs of
    // the handle holes left.
    void run_plan_tail(int u, const PlanOpt& opt, u64 pre_cov) {
        CF_SCOPE(plan_tail);
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
    // there and on (cU, cL]; L may be wrong where U masks it. A stack is a candidate when it saves at
    // least 1 dig more than its 2 + depths moves.
    // With beam_enabled, chains of up to kChainLength papers (append_wide_chains) are candidates too.
    std::vector<FillerPick> choose_fillers_prelift(int u, int d, u64 hh) {
        CF_SCOPE(choose_fillers);
        placement_chains.clear();
        const int l = col_of[d];
        const u64 hole_all = hmask & ~paper[d].opaque;
        u64 covered = 0;
        for (auto& f : fillers) covered |= shown_by(f);
        auto fix = fix_costs(u, hh);
        auto& cand = fresh_candidates();
        ColumnTops tops;
        std::array<int, 64> ntop;
        all_column_tops(tops, ntop);
        const u64 hh_i = handle_bits(hh), au_i = handle_bits(A[u]);
        for (int c = 0; c < H; c++) {
            if (c == l || (covered >> handle[c] & 1)) continue;
            bool hole_c = hole_all >> handle[c] & 1;
            const auto& top = tops[c];
            for (int depth = 0; depth < ntop[c]; depth++) {
                int f = top[depth];
                u64 shown = paper[f].opaque & hh;
                int lvl = level_past((paper[f].black ^ A[u]) & shown);
                if (lvl > c || reaches_deeper(lvl, c, fillers)) continue;
                // (the covered holes in [lv, c] as a mask of handle indices)
                u64 shown_c = h_opq[f] & hh_i & low_bits(c + 1);
                if (!depth && hole_c) shown_c &= ~(1ULL << c);
                int save = 0;
                for (u64 m = shown_c & ~low_bits(lvl); m; m &= m - 1) save += fix[__builtin_ctzll(m)];
                for (int lv = lvl; lv <= c; save -= ((shown_c >> lv) & 1) ? fix[lv] : 0, lv++) {
                    if (lv > lvl && (!(shown >> handle[lv] & 1) || reaches_deeper(lv, c, fillers))) continue;
                    bool post = c > l && lv <= l && (paper[f].opaque >> handle[l] & 1);
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
                if (U.fsum + L.fsum < 2 * kFillerCost + U.depth + L.depth + 1) continue;
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
                if (gain < 1) continue;
                stacks.push_back({U.c, U.depth, L.c, L.depth, postU, postL});
                cand[L.c].push_back({a, (double)gain, L.c, -(int)stacks.size()});
            }
        }
        std::vector<ChainRecord> wide_chains;
        if (beam_enabled) append_wide_chains(u, d, hh, fix, tops, ntop, cand, wide_chains);
        std::vector<FillerPick> res;
        for (auto& cd : best_intervals(cand)) {
            if (cd.kind == 7) {
                // a chain: its papers taken in increasing column order (res is reversed below), each
                // placed at its rank among those of the chain already placed (place_picked_filler)
                auto chain = wide_chains[cd.idx];
                const int chain_id = placement_chains.size();
                placement_chains.emplace_back(chain.length, -1);
                for (int i = 0; i < chain.length; i++) chain.pick[i].chain_id = chain_id, chain.pick[i].chain_rank = i;
                // (the papers of a chain are of distinct columns)
                std::sort(chain.pick.begin(), chain.pick.begin() + chain.length,
                          [](const FillerPick& a, const FillerPick& b) { return a.c > b.c; });
                for (int i = 0; i < chain.length; i++) res.push_back(chain.pick[i]);
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

    // ==== Request plans: filler chains ====

    // Chains of fillers: up to kChainLength papers of
    // distinct columns (at most kChainDepth deep in their column) stacked at one level, the first of
    // the path on top. Walking down the path, the opaque handles O of the papers so far and the
    // wrong ones B (shown with a color other than A_u on a hole of D, not masked by a paper above)
    // are updated; the level is just past the deepest wrong handle and must not exceed the least
    // column. The gain is the digs (fix) of the holes of D covered from the level on, less 1 + depth
    // per paper; a beam of kBeamWidth paths per length, pruned when the cost reaches the digs left
    // from the level on (suffixFix: an upper bound of the saving). A chain is an interval candidate
    // [level, deepest column] (kind 7, idx: its index in chains). Papers of columns deeper than D's
    // are placed after the lift (D must not cover their handle, or their column top is hidden).
    static constexpr int kChainDepth = 2, kChainLength = 3, kBeamWidth = 16;
    long long chain_trials = 0, chain_selected = 0, chain_papers = 0;
    bool beam_enabled = false;                       // choose_fillers_prelift searches chains
    std::vector<std::vector<int>> placement_chains;  // per chain of the plan: the paper placed at each rank
    // A chain found by append_wide_chains: its papers top first.
    struct ChainRecord {
        std::array<FillerPick, kChainLength> pick;
        int length = 0;
    };
    // Fixed-size chain records; sort (gain, index) proxies to preserve the order of equal gains.
    struct BeamState {
        std::array<int, kChainLength> path{};
        int length = 0, minc = 0, maxc = 0, cost = 0, level = 0, gain = 0;
        u64 opaque = 0, bad = 0;
    };
    struct BeamKey {
        int gain, index;
    };
    std::vector<BeamState> beam_current, beam_next;
    std::vector<BeamKey> beam_keys;
    void append_wide_chains(int u, int d, u64 hh, const std::vector<int>& fix, const ColumnTops& tops,
                            const std::array<int, 64>& ntop, std::vector<std::vector<Cand>>& cand,
                            std::vector<ChainRecord>& chains) {
        CF_SCOPE(chains);
        const int totalFix = std::accumulate(fix.begin(), fix.end(), 0);
        if (totalFix < 3) return;
        std::array<int, 65> suffixFix{};
        for (int j = H - 1; j >= 0; j--) suffixFix[j] = suffixFix[j + 1] + fix[j];
        struct PC {
            int c, depth;
            u64 opaque, bad;  // by handle index
        };
        const int l = col_of[d];
        const u64 hh_i = handle_bits(hh), au_i = handle_bits(A[u]);
        u64 covered = 0;
        for (const auto& f : fillers) covered |= shown_by(f);
        std::array<PC, 64 * (kChainDepth + 1)> pool;
        int pool_size = 0;
        for (int c = 0; c < H; c++) {
            if (c == l || (covered >> handle[c] & 1)) continue;
            const int n = std::min(ntop[c], std::min(kFillerDepth, kChainDepth) + 1);
            for (int depth = 0; depth < n; depth++) {
                const int k = tops[c][depth];
                pool[pool_size++] = {c, depth, h_opq[k], h_opq[k] & hh_i & (h_blk[k] ^ au_i)};
            }
        }
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
            ChainRecord chain;
            for (int j = 0; j < b.length; j++) {
                const auto& p = pool[b.path[j]];
                const bool post = p.c > l;
                if (post && (paper[d].opaque >> handle[p.c] & 1)) return;
                chain.pick[chain.length++] = {p.c, p.depth, b.level, post};
            }
            const int index = chains.size();
            chains.push_back(chain);
            cand[b.maxc].push_back({b.level, double(b.gain), b.maxc, 0, 7, index});
        };
        auto& current = beam_current;
        auto& next = beam_next;
        current.clear();
        for (int i = 0; i < pool_size; i++) {
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
            next.clear();
            for (const auto& b : current) {
                for (int i = 0; i < pool_size; i++) {
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
            // the kBeamWidth states of largest gain, as std::sort of the states by gain would leave them
            beam_keys.resize(next.size());
            for (int i = 0; i < (int)next.size(); i++) beam_keys[i] = {next[i].gain, i};
            std::sort(beam_keys.begin(), beam_keys.end(),
                      [](const BeamKey& a, const BeamKey& b) { return a.gain > b.gain; });
            const int width = std::min<int>(kBeamWidth, next.size());
            current.resize(width);
            for (int i = 0; i < width; i++) current[i] = next[beam_keys[i].index];
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
            OP_LABEL(kOpFdig);
            dig(pick.c, x);
        }
        OP_LABEL(kOpFill);
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
    // (fillers may hide each other). Removing a paper
    // never hides another, so taking any visible one (here the topmost) decides it.
    bool fillers_reachable() const {
        CF_SCOPE(reachable);
        if (fillers.empty()) return true;
        std::array<bool, K> pending{};
        for (const auto& f : fillers) {
            if (pending[f.paper] || f.paper == top_d) return false;
            pending[f.paper] = true;
        }
        // A lower removal cannot expose a paper above it. In this top-down pass,
        // a pending paper still hidden when reached can never be removed.
        int left = fillers.size();
        u64 covered = 0;
        for (int k : order) {
            if (k == top_d) continue;
            if (pending[k]) {
                if (!(paper[k].opaque & ~covered)) return false;
                if (--left == 0) return true;
            } else covered |= paper[k].opaque;
        }
        return false;
    }

    // ==== Solver: canonical records of the stack ====

    // The records of the papers out of their columns rebuilt from the order after every request.
    // Walking up from the bottom, a paper of column c <= cur (cur = column of the nearest paper in
    // place below) is in place, one of a column > cur is out (a filler of level cur), and a column
    // paper above a generic sheet is out (level 0); the paper on the very top is the lifted one.
    // (fixed-size arrays instead of vectors; the same records.)
    void canonicalize() {
        CF_SCOPE(canonicalize);
        std::array<char, 64> nonempty{};
        std::array<Filler, K> nf;
        int cur = H, ntop = -1, nf_count = 0;
        bool gen_seen = false;
        // Collect only the out-of-column papers during the original bottom-up scan.
        // Reversing this small list gives the same top-down order as the old second K scan.
        for (int i = K - 1; i >= 0; i--) {
            const int k = order[i], c = col_of[k];
            if (c < 0) {
                if (k < M) gen_seen = true;
            } else if (!gen_seen && c <= cur) {
                cur = c;
                nonempty[c] = 1;
            } else if (i == 0 || (i == 1 && order[0] == kCapPaper)) ntop = k;
            else nf[nf_count++] = {k, gen_seen ? 0 : std::min(cur, c), c};
        }
        std::reverse(nf.begin(), nf.begin() + nf_count);
        std::array<int, K> nf_index;
        nf_index.fill(-1);
        for (int i = 0; i < nf_count; i++) {
            while (nf[i].lvl > 0 && !nonempty[nf[i].lvl - 1]) nf[i].lvl--;
            nf_index[nf[i].paper] = i;
        }
        // the old fillers first, in their order, then the others in the order of the stack
        std::array<Filler, 2 * K> res;
        std::array<bool, K> old_filler{};
        int res_count = 0;
        for (auto& f : fillers) {
            old_filler[f.paper] = true;
            if (nf_index[f.paper] >= 0) res[res_count++] = nf[nf_index[f.paper]];
        }
        for (int i = 0; i < nf_count; i++)
            if (!old_filler[nf[i].paper]) res[res_count++] = nf[i];
        top_d = ntop;
        fillers.assign(res.begin(), res.begin() + res_count);
    }
    struct State {
        std::array<uint8_t, K> order{};
        int top_d;
        FillerList fillers;
    };
    State save() const { return {order, top_d, fillers}; }
    void restore(const State& st) {
        order = st.order;
        top_d = st.top_d;
        fillers = st.fillers;
    }

    void start_plan(const State& initial) {
        restore(initial);
        ops.clear();
        OP_TAG(op_tags.clear();)
        invalid = false;
    }

    // ==== Request plans: helpers inside the generic layer ====

    // Return the previous product and fillers, order the generic layer, and insert one or two
    // helpers at its gaps. Dig shallower columns before lifting D, deeper columns afterwards;
    // cover remaining handle holes with the usual interval-DP fillers and digs.
    std::shared_ptr<Interleave> interleave;
    long long interleave_trials = 0, interleave_selected = 0;
    struct PairHelperPick {
        int upper, lower, goal, tu, tl, distance;
    };
    // the states in the order visited (by distance from the source, then by index) come
    // from by_distance (sort_by_distance), and a state whose display is wrong on a hole of D that
    // neither x nor y covers (no insertion depth can change it) is skipped.
    struct StatesByDistance {
        std::vector<uint16_t> state;
        std::vector<uint8_t> distance;
    };
    StatesByDistance states_by_distance;  // (scratch of try_helpers)
    void sort_by_distance(int source, StatesByDistance& out) const {
        const int n = comparator.perms.size();
        std::array<int, 257> start{};
        for (int s = 0; s < n; s++) start[comparator.distance(source, s) + 1]++;
        for (int d = 0; d < 256; d++) start[d + 1] += start[d];
        out.state.resize(n);
        out.distance.resize(n);
        for (int s = 0; s < n; s++) {
            const int d = comparator.distance(source, s), at = start[d]++;
            out.state[at] = s;
            out.distance[at] = d;
        }
    }
    PairHelperPick best_interleave_pair(const StatesByDistance& by_distance, int u, int x, int y, int limit) const {
        CF_SCOPE(pair_helper);
        const u64 gh = gmask & ~paper[ded[u]].opaque;
        // the holes where z below is the display of the state whatever tl and tu
        const u64 free = gh & ~(paper[x].opaque | paper[x].black | paper[y].opaque | paper[y].black);
        for (int i = 0; i < int(by_distance.state.size()); i++) {
            const int distance = by_distance.distance[i], state = by_distance.state[i];
            if (distance >= limit) break;
            if ((interleave->display[state] ^ A[u]) & free) continue;
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
    void set_helper_goal(int goal) {
        OP_LABEL(kOpGen);
        for (auto [k, depth] : comparator.path(interleave->state(order), goal)) move(k, depth + 1);
    }
    bool insert_helper(int k, int depth) {
        const int c = col_of[k];
        for (int it = 0; column_top(c) != k; ++it) {
            if (it >= K || invalid) { invalid = true; return false; }
            OP_LABEL(kOpHdig);
            dig(c, k);
        }
        OP_LABEL(kOpHelp);
        move(k, depth);
        fillers.push_back({k, 0, c});
        return true;
    }
    void run_interleave(int u, const Interleave::Pick& pk) {
        const int d = ded[u], c = col_of[pk.paper], l = col_of[d];
        set_helper_goal(pk.goal);
        if (c < l) insert_helper(pk.paper, 1 + pk.depth);  // shallower columns must be dug before D
        lift(d);
        if (c > l) insert_helper(pk.paper, 2 + pk.depth);
        if (invalid) return;
        finish_handles(u, d, hmask & ~paper[d].opaque & ~paper[pk.paper].opaque);
    }
    void run_interleave_pair(int u, const PairHelperPick& pk) {
        const int d = ded[u], l = col_of[d];
        set_helper_goal(pk.goal);
        int placed = 0;
        bool lifted = false;
        auto get = [&](int x, int depth) {
            const int c = col_of[x];
            if (c > l && !lifted) lift(d), lifted = true;
            if (!insert_helper(x, 1 + depth + placed + (lifted ? 1 : 0))) return;
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
        CF_SCOPE(helpers);
        const int d = ded[u];
        start_plan(st0);
        if (top_d >= 0) return_paper(top_d, u, 1);
        const auto olds = fillers;
        return_visible_fillers(olds, u, 1);
        if (invalid) return;
        if (order[0] != kCapPaper) return;
        for (int i = 0; i < M; i++)
            if (order[i + 1] >= M) return;
        const State clean = save();
        const auto clean_ops = ops;
        OP_TAG(const auto clean_tags = op_tags;)
        const int s = interleave->state(order);
        std::vector<int> current(order.begin() + 1, order.begin() + 1 + M);
        const int base_generic = comparator.plan(current, A[u], ~paper[d].opaque & gmask).size();
        const auto fixes = fix_costs(u, ~paper[d].opaque & hmask);
        std::array<int, K> helper_depth{};
        std::array<int, 64> helper_rank{};
        for (int k : order) {
            const int c = col_of[k];
            if (c < 0) continue;
            helper_depth[k] = helper_rank[c];
            if (in_column(k, c)) helper_rank[c]++;
        }
        // single helpers: at most 5 deep in their column, fewer generic moves than without; the 6 of
        // least distance + depth + 1.8 + digs of the handle holes they do not cover
        std::vector<std::pair<double, Interleave::Pick>> picks;
        for (const auto& h : interleave->helpers[u]) {
            const int dep = helper_depth[h.paper];
            if (dep < 0 || dep > 5) continue;
            auto pk = interleave->best(s, h);
            if (pk.distance >= base_generic) continue;
            double score = pk.distance + dep + 1.8;
            for (u64 z = ~h_opq[h.paper] & low_bits(H); z; z &= z - 1) score += fixes[__builtin_ctzll(z)];
            picks.push_back({score, pk});
        }
        std::sort(picks.begin(), picks.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
        if (picks.size() > 6) picks.resize(6);
        // pairs: a helper x at most 3 deep and a paper y of a deeper column (not D's) at most 3 deep
        // that is right on the handle holes of D that x leaves; the 12 of least estimate, then the 6
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
                for (u64 z = ~(h_opq[x] | h_opq[y]) & low_bits(H); z; z &= z - 1) estimate += fixes[__builtin_ctzll(z)];
                pairs.push_back({estimate, x, y});
            }
        }
        std::sort(pairs.begin(), pairs.end(), [](const PP& a, const PP& b) { return a.estimate < b.estimate; });
        if (pairs.size() > 12) pairs.resize(12);
        std::vector<std::pair<double, PairHelperPick>> pair_picks;
        if (!pairs.empty()) sort_by_distance(s, states_by_distance);
        for (auto pp : pairs) {
            auto pk = best_interleave_pair(states_by_distance, u, pp.x, pp.y, base_generic);
            if (pk.goal >= 0) pair_picks.push_back({pp.estimate + pk.distance, pk});
        }
        std::sort(pair_picks.begin(), pair_picks.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
        if (pair_picks.size() > 6) pair_picks.resize(6);
        auto finish = [&]() {
            if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) return;
            keep(plan_cost(ops.size()));
        };
        for (const auto& item : pair_picks) {
            restore(clean);
            ops = clean_ops;
            OP_TAG(op_tags = clean_tags;)
            invalid = false;
            interleave_trials++;
            run_interleave_pair(u, item.second);
            finish();
        }
        for (const auto& item : picks) {
            restore(clean);
            ops = clean_ops;
            OP_TAG(op_tags = clean_tags;)
            invalid = false;
            interleave_trials++;
            run_interleave(u, item.second);
            finish();
        }
    }

    // ==== Post-processing: deletions and new anchors of the edits ====

    // Edits are "paper goes below anchor" (anchor -1: top), replayed with recomputed depths.
    // Accept only legal moves, display A_u, reachable fillers, and a lower plan_cost.
    // Edit passes try deletions, new anchors for old extras/repeated papers, and both together.
    // Eject passes replace two edits by one repair; neutral collection also tries two repairs.
    long long eject_pairs = 0, eject_trials = 0, eject_accepts = 0, eject_inside = 0;
    long long triple_trials = 0, triple_repairs = 0, triple_accepts = 0;
    // Settings are read once. The fast defaults favor one-to-one repairs and new-paper candidates.
    static const char* search_env(const char* name) {
        // F3_* is private to this solver; no fallback to shared environment names.
        const std::string local = std::string("F3_") + name;
        if(const char* value=std::getenv(local.c_str()))return value;
        if(std::strcmp(name,"REPEAT_MIN")==0)return ".05";
        if(std::strcmp(name,"POST_CANDIDATES")==0)return "5";
        if(std::strcmp(name,"NEUTRAL_WIDTH")==0)return "3";
        return nullptr;
    }
    struct SearchConfig {
        static int get(const char* name, int fallback) {
            const char* value = search_env(name);
            return value ? std::atoi(value) : fallback;
        }
        static double number(const char* name, double fallback) {
            const char* value = search_env(name);
            return value ? std::atof(value) : fallback;
        }
        // MODE=0 is the replay-comparison preset; explicit F3_* settings override presets.
        const int mode = std::clamp(get("MODE", 1), 0, 2);
        int rounds = std::max(0, get("NS_ROUNDS", 2));
        int short_rounds = std::max(0, get("NS_SHORT_ROUNDS", 0));
        int post_candidates = std::max(2, get("POST_CANDIDATES", mode == 2 ? 8 : mode == 1 ? 3 : 2));
        int interior = std::clamp(get("NS_INTERIOR", 0), 0, 128);
        int pair_filter = std::clamp(get("NS_PAIR_FILTER", 1), 0, 3);
        bool one = get("NS_ONE", 1);
        bool two = get("NS_TWO", mode != 0);
        bool triples = get("NS_TRIPLES", 0);
        bool recheck = get("NS_RECHECK", 0);
        bool trace = get("HEAVY_TRACE", 0);
        bool predict = get("HEAVY_PREDICT", 0);
        bool new_only = get("NS_NEW_ONLY", 1);
        bool alternate = get("NS_ALTERNATE", 0);
        bool delete_only = get("NS_DELETE_ONLY", 0);
        double alternate_gap = number("NS_ALTERNATE_GAP", .75);
        int plan_limit = std::max(0, get("PLAN_LIMIT", mode ? 1 : 99));
        int plan_ejects = std::max(0, get("PLAN_EJECTS", mode ? 2 : 4));
        int plan_priority = get("PLAN_PRIORITY", 0);
        double plan_gap = number("PLAN_GAP", 1e9);
        bool plan_reuse = get("PLAN_REUSE", 1);
        bool plan_stop = get("PLAN_STOP", 0);
        bool plan_trace = get("PLAN_TRACE", 0);
        bool memo = get("MEMO", 1);
        bool prefix = get("PREFIX", 1);
        int joint_limit = std::max(0, get("JOINT_LIMIT", 0));
        bool joint_stop = get("JOINT_STOP", 0);
        bool three_hidden = get("THREE_HIDDEN", 0);
        bool plan_skip_edited = get("PLAN_SKIP_EDITED", mode != 0);
        bool plan_screen = get("PLAN_SCREEN", mode != 0);
        int refine_best = std::max(0, get("REFINE_BEST", 0));
        bool collect = get("COLLECT", 1);
        bool plan_distinct = get("PLAN_DISTINCT", mode != 0);
        int candidate_mode = get("CANDIDATE_MODE", mode ? 2 : 1);
        int candidate_priority = get("CANDIDATE_PRIORITY", mode != 0);
        int one_limit = std::max(0, get("ONE_LIMIT", 0));
        int plan_shortlist = get("PLAN_SHORTLIST", mode == 1 ? 2 : 0);
        double repeat_min = number("REPEAT_MIN", mode == 2 ? .05 : 0);
        bool lazy_tail = get("LAZY_TAIL", 1);
        int one_anchors = std::max(0, get("ONE_ANCHORS", mode ? 2 : 0));
        bool three_extra = get("THREE_EXTRA", 0);
        bool pair_owners = get("PAIR_OWNERS", 1);
        bool hidden_rank = get("HIDDEN_RANK", 1);
        double promising_slack = number("PROMISING_SLACK", mode ? .75 : 0);
    };
    static const SearchConfig& search_config() {
        static const SearchConfig config;
        return config;
    }
    F3_DIAG(int f3_stage = 0, f3_round = 0;)
    long long ns_rounds = 0, ns_plan_calls = 0, ns_one_trials = 0, ns_one_accepts = 0;
    long long ns_three_trials = 0, ns_three_accepts = 0, ns_changed = 0, ns_saved = 0;
    long long f2_plan_reused = 0, f2_plan_skipped = 0, f2_plan_wins = 0;
    long long f2_memo_hits = 0, f2_memo_misses = 0;
    long long f2_prefix_steps = 0, f2_replay_steps = 0;
    long long f2_plan_screens = 0;
    long long f2_refine_calls = 0, f2_refine_saved = 0;
    int last_post_operator = 0;  // 0 eject/edit, 1 two-to-two, 2 one-to-one, 3 three-to-two, 4 plans
    static const char* operator_name(int op) {
        static constexpr const char* names[] = {"eject", "22", "11", "32", "plans"};
        return names[op];
    }
#ifdef LOCAL_BENCH
    std::string heavy_log;  // buffered until main's statistics, keeping stderr I/O outside req_sec
    static std::string trace_path(const Moves& path, const std::vector<uint8_t>& tags) {
        if (path.empty()) return "-";
        std::string text;
        for (int i = 0; i < int(path.size()); i++) {
            auto [k, d] = path[i];
            const int out = k == kCapPaper ? 0 : k < kCapPaper ? k + 1 : k;
            if (i) text += ',';
            text += std::to_string(out) + ':' + std::to_string(d) + ':' + kOpLabelName[tags[i]];
        }
        return text;
    }
    static std::string trace_value(double v) {
        char buffer[64];
        std::snprintf(buffer, sizeof(buffer), "%.12g", v);
        return buffer;
    }
#endif
    struct NeutralCandidate {
        State state;
        Moves path;
        OP_TAG(std::vector<uint8_t> tags;)  // labels belong to this path, not to the current best path
        double value;
        u64 signature;
        int origin = 0;
        int repeats = 0;
        int hides = 0;  // moved parent display owners that this candidate leaves hidden
    };
    bool neutral_collect = false;
    std::vector<NeutralCandidate> neutral_candidates;
    long long neutral_total = 0, neutral_accepted = 0, neutral_direct_saved = 0, neutral_escape_saved = 0;
    OP_TAG(long long request_counter = 0;)
    long long rewrite_trials = 0, rewrite_accepts = 0, rewrite_same_column = 0;
    long long post_saved = 0;
    struct Edit {
        int paper, anchor;
        OP_TAG(uint8_t tag = kOpRepair;)  // the label of its move (anchorize sets it; a new edit is a repair)
    };
    // Scratch buffers of post_optimize and eject_repairs (kept to avoid allocations).
    std::vector<Edit> trial_buffer, eject_trial, eject_next;
    Moves path_buffer;
    OP_TAG(std::vector<uint8_t> path_tag_buffer;)  // the labels of path_buffer
    std::vector<int> eject_anchors;
    // an order of the K papers as bytes, for the replays of the post-processing (memchr finds
    // a paper, memmove shifts the papers between two positions).
    using ByteOrder = std::array<uint8_t, K>;
    static int find_paper(const ByteOrder& o, int k) {
        return int(static_cast<const uint8_t*>(std::memchr(o.data(), k, K)) - o.data());
    }
    // The paper at position p goes to position dest (the papers between shift by one).
    static void shift_byte(ByteOrder& o, int p, int dest) {
        const uint8_t k = o[p];
        if (p < dest)
            std::memmove(&o[p], &o[p + 1], dest - p);
        else
            std::memmove(&o[dest + 1], &o[dest], p - dest);
        o[dest] = k;
    }
    // Convert depths to predecessor IDs; later replay may start from a different stack.
    static std::vector<Edit> anchorize(const ByteOrder& initial,
                                      const Moves& path
                                      OP_TAG(, const std::vector<uint8_t>& labels)) {
        ByteOrder ord = initial;
        std::vector<Edit> edits;
        edits.reserve(path.size());
        for (auto [k, d] : path) {
            const int p = find_paper(ord, k);
            // The predecessor at gap d after removing k is shifted by one if k was above it.
            edits.push_back({k, d ? int(ord[d - 1 + int(p < d)]) : -1});
            OP_TAG(edits.back().tag = labels[edits.size() - 1];)
            shift_byte(ord, p, d);
        }
        return edits;
    }
    // An order of the papers as a doubly linked list: the sentinel kRoot before the top and after the
    // bottom, byte links.
    using Links = std::array<uint8_t, K + 1>;
    static constexpr int kRoot = K;
    // Move k immediately after a; kRoot is the sentinel for the top and bottom.
    static void splice_after(Links& next, Links& prev, int k, int a) {
        if (prev[k] == a) return;
        next[prev[k]] = next[k];
        prev[next[k]] = prev[k];
        const int b = next[a];
        next[a] = k;
        prev[k] = a;
        next[k] = b;
        prev[b] = k;
    }
    struct PostContext {
        bool ready = false;
        Links next, prev;
        ByteOrder bytes;
        std::array<int, K> position;
        // A block maps incoming coverage to the first color on its opaque windows. Combining
        // overlapping sparse-table blocks is exact: the repeated overlap is already covered.
        struct Block { u64 cov, disp; };
        std::array<std::array<Block, K>, 8> blocks;
    } post_context;
    struct EndMemo {
        u64 generation = 0;
        Links next;
        int top_d;
        bool reachable;
        double charge, next_cost;
        FillerList fillers;
    };
    std::array<EndMemo, 128> end_memo;
    u64 memo_generation = 0;
    struct ReplayPrefix {
        std::vector<Edit> edits;
        std::vector<ByteOrder> orders;
        std::vector<int> lengths;
        Moves path;
        OP_TAG(std::vector<uint8_t> tags;)
    } replay_prefix;
    void prepare_post_context(const State& initial) {
        CF_SCOPE(post_setup);
        if (post_context.ready) return;
        auto& c = post_context;
        c.ready = true;
        c.next[kRoot] = initial.order.front();
        c.prev[kRoot] = initial.order.back();
        for (int j = 0; j < K; j++) {
            const int k = initial.order[j];
            c.position[k] = j;
            c.bytes[j] = k;
            c.prev[k] = j ? initial.order[j - 1] : kRoot;
            c.next[k] = j + 1 < K ? initial.order[j + 1] : kRoot;
            c.blocks[0][j] = {paper[k].opaque, paper[k].black};

        }
        for (int level = 1; (1 << level) <= K; level++) {
            const int half = 1 << (level - 1);
            for (int j = 0; j + 2 * half <= K; j++) {
                const auto a = c.blocks[level - 1][j], b = c.blocks[level - 1][j + half];
                c.blocks[level][j] = {a.cov | b.cov, a.disp | (b.disp & ~a.cov)};
            }
        }
    }
    // Under LOCAL_BENCH, tags holds the labels of input_ops and receives those of the result.
    Moves post_optimize(const State& initial, Moves input_ops,
                                                   int u OP_TAG(, std::vector<uint8_t>& tags), bool eject = false,
                                                   bool delete_only = false) {
        CF_SCOPE(post);
        if (input_ops.empty()) return input_ops;
        const auto& cfg = search_config();
        const u64 generation = ++memo_generation;
        prepare_post_context(initial);
        const auto& initial_bytes = post_context.bytes;
        const auto& initial_order = post_context.bytes;
        const auto& initial_position = post_context.position;
        const auto& initial_next = post_context.next;
        const auto& initial_prev = post_context.prev;
        constexpr int root = kRoot;
        auto& prefix = replay_prefix;
        if (cfg.prefix) {
            prefix.edits.clear();
            prefix.path.clear();
            OP_TAG(prefix.tags.clear();)
            if (prefix.orders.size() < input_ops.size() + 3) {
                prefix.orders.resize(input_ops.size() + 3);
                prefix.lengths.resize(input_ops.size() + 3);
            }
            prefix.orders[0] = initial_bytes;
            prefix.lengths[0] = 0;
        }
        auto edits = anchorize(initial_bytes, input_ops OP_TAG(, tags));
        std::array<bool, K> initial_extra{};  // the old lifted paper and old fillers
        if (initial.top_d >= 0) initial_extra[initial.top_d] = true;
        for (const auto& f : initial.fillers) initial_extra[f.paper] = true;
        // Every candidate rebuilds its records from the same saved state (canonicalize keeps the
        // priority of the fillers listed there).
        const State seed = save();
        State best_state = seed;
        auto best_ops = input_ops;
        OP_TAG(auto best_tags = std::move(tags);)  // the labels of best_ops (tags gets them back at the end)
        double best_score = plan_cost(best_ops.size());
        int trial_operator = 0, best_operator = 0;
        F3_DIAG(
            std::array<long long, 7> fp_trials{}, fp_legal{}, fp_accepts{}, fp_saved{};
            std::array<double, 7> fp_gain{}, fp_sec{};
            int fp_op = 0, fp_repeats = 0;
            std::array<bool, K> fp_seen{};
            for (auto [k, d] : input_ops) { fp_repeats += fp_seen[k]; fp_seen[k] = true; }
            const double fp_start_score = best_score;
            const double fp_start = elapsed_sec();
            double fp_tick = fp_start;
            auto fp_switch = [&](int op) {
                double now = elapsed_sec();
                fp_sec[fp_op] += now - fp_tick;
                fp_tick = now;
                fp_op = op;
            };
        )
        std::array<bool, K> input_moved{};
        std::array<uint16_t, K> input_counts{};
        if (neutral_collect && cfg.new_only)
            for (auto [k, d] : input_ops) { input_moved[k] = true; input_counts[k]++; }
        std::array<u64, 3> parent_owner_moves{};
        if (neutral_collect && (cfg.hidden_rank || cfg.predict)) {
            u64 covered = 0;
            for (int k : seed.order) {
                if (input_moved[k] && (paper[k].opaque & ~covered))
                    parent_owner_moves[k >> 6] |= 1ULL << (k & 63);
                covered |= paper[k].opaque;
                if (covered == ~u64(0)) break;
            }
        }
        // The replay of evaluate (a byte array instead of vectors): the order and the prefix
        // covers cover[j] (the windows of the papers ord[0..j)), valid for j <= cover_valid.
        ByteOrder ord;
        std::array<u64, K + 1> cover;
        // Keeps the trial if valid and better (best_ops / best_state / best_score). No-op edits are
        // dropped. The final order is first determined without checking intermediate visibility: the
        // linked list makes this necessary-condition filter on the display cheap. Surviving
        // candidates are then replayed with positions, checking every move.
        // The initial stack is shared by every pass of this request. A range's first opaque
        // colors come from two overlapping power-of-two blocks, in O(1) with no changed arithmetic.
        auto run_of = [&](int i, int e, u64& cov, u64& disp) {
            const int level = 31 - __builtin_clz(unsigned(e - i + 1));
            const int j = e + 1 - (1 << level);
            const auto a = post_context.blocks[level][i], b = post_context.blocks[level][j];
            cov = a.cov | b.cov;
            disp = a.disp | (b.disp & ~a.cov);
        };
        auto evaluate = [&](const std::vector<Edit>& trial) {
            CF_SCOPE(evaluate);
            F3_DIAG(fp_trials[fp_op]++;)
            EndMemo* memo = nullptr;
            bool memo_hit = false;
            std::array<u64, 3> moved{}, breaks{};
            auto next = initial_next, prev = initial_prev;
            {
                CF_SCOPE(eval_filter);
                // Bit positions refer to the initial order. A run ends at a moved paper,
                // immediately above one, or at an anchor. Build all predecessors in three shifts.
                for (const Edit& e : trial) {
                    const int k = e.paper, a = e.anchor < 0 ? root : e.anchor;
                    if (a == k) return false;
                    const int p = initial_position[k];
                    moved[p >> 6] |= 1ULL << (p & 63);
                    if (e.anchor >= 0) {
                        const int q = initial_position[e.anchor];
                        breaks[q >> 6] |= 1ULL << (q & 63);
                    }
                    splice_after(next, prev, k, a);
                }
                for (int w = 0; w < 3; ++w) {
                    breaks[w] |= moved[w] | (moved[w] >> 1);
                    if (w < 2) breaks[w] |= moved[w + 1] << 63;
                }
                auto next_break = [&](int i) {  // the first break at or after position i (K - 1: none)
                    int w = i >> 6;
                    u64 m = breaks[w] & (~0ULL << (i & 63));
                    while (!m) {
                        if (++w == 3) return K - 1;
                        m = breaks[w];
                    }
                    return w * 64 + __builtin_ctzll(m);
                };
                // The same final cap invariant as below, checked before the more costly legality
                // replay. The cap is never moved, and its predecessor chain is already available.
                for (int k = next[root]; k != root && k != kCapPaper; k = next[k])
                    if (k < M) return false;
                u64 seen = 0, view = 0;
                for (int k = next[root]; k != root;) {
                    u64 cov, disp;
                    const int i = initial_position[k];
                    if (breaks[i >> 6] >> (i & 63) & 1) {  // the range is the single paper k
                        const auto b = post_context.blocks[0][i];
                        cov = b.cov, disp = b.disp;
                        k = next[k];
                    } else {
                        const int e = next_break(i);
                        run_of(i, e, cov, disp);
                        k = next[initial_order[e]];
                    }
                    // Newly exposed colors are final: lower sheets cannot repair them.
                    if ((disp ^ A[u]) & cov & ~seen) return false;
                    view |= disp & ~seen;
                    seen |= cov;
                    if (seen == ~u64(0)) break;
                }
                if (view != A[u]) return false;
                if (cfg.memo) {
                    // Only final-order properties are cached. The full successor array is the
                    // collision check; every usable path still passes its own visibility replay.
                    u64 hash = 0xcbf29ce484222325ULL;
                    for (int j = 0; j + 8 <= K; j += 8) {
                        u64 word;
                        std::memcpy(&word, next.data() + j, 8);
                        hash = (hash ^ word) * 0x100000001b3ULL;
                    }
                    hash = (hash ^ next[root]) * 0x100000001b3ULL;
                    memo = &end_memo[(hash ^ (hash >> 32)) & (end_memo.size() - 1)];
                    memo_hit = memo->generation == generation && memo->next == next;
                    if (memo_hit) {
                        f2_memo_hits++;
                        if (!memo->reachable) return false;
                    } else {
                        f2_memo_misses++;
                        memo->generation = 0;  // an illegal path may return before filling this slot
                        memo->next = next;
                    }
                }
            }
            auto& path = path_buffer;
            path.clear();
            OP_TAG(auto& path_tags = path_tag_buffer;)
            OP_TAG(path_tags.clear();)
            {
                CF_SCOPE(eval_replay);
                int cover_valid = 0;
                cover[0] = 0;

                int common = 0;
                if (cfg.prefix) {
                    while (common < int(trial.size()) && common < int(prefix.edits.size())) {
                        const Edit& a = trial[common];
                        const Edit& b = prefix.edits[common];
                        if (a.paper != b.paper || a.anchor != b.anchor OP_TAG(|| a.tag != b.tag)) break;
                        common++;
                    }
                    ord = prefix.orders[common];
                    path.assign(prefix.path.begin(), prefix.path.begin() + prefix.lengths[common]);
                    OP_TAG(path_tags.assign(prefix.tags.begin(), prefix.tags.begin() + prefix.lengths[common]);)
                    f2_prefix_steps += common;
                    if (prefix.orders.size() < trial.size() + 1) {
                        prefix.orders.resize(trial.size() + 1);
                        prefix.lengths.resize(trial.size() + 1);
                    }
                } else ord = initial_bytes;
                auto remember = [&](int count) {
                    if (!cfg.prefix) return;
                    prefix.edits.assign(trial.begin(), trial.begin() + count);
                    prefix.path = path;
                    OP_TAG(prefix.tags = path_tags;)
                };
                for (int index = common; index < int(trial.size()); index++) {
                    const Edit& e = trial[index];
                    f2_replay_steps++;
                    const int k = e.paper, a = e.anchor;
                    const int p = find_paper(ord, k);
                    int dest = a < 0 ? 0 : find_paper(ord, a) + 1;
                    if (p < dest) dest--;
                    if (p != dest) {
                        // Only the changed suffix is replayed. Coverage is rebuilt lazily from the
                        // cached prefix's stack; no cover array is copied at every checkpoint.
                        for (; cover_valid < p; cover_valid++)
                            cover[cover_valid + 1] = cover[cover_valid] | paper[ord[cover_valid]].opaque;
                        if (!(paper[k].opaque & ~cover[p])) { remember(index); return false; }
                        shift_byte(ord, p, dest);
                        cover_valid = std::min(cover_valid, std::min(p, dest));
                        path.push_back({k, dest});
                        OP_TAG(path_tags.push_back(e.tag);)
                    }
                    if (cfg.prefix) {
                        prefix.orders[index + 1] = ord;
                        prefix.lengths[index + 1] = path.size();
                    }
                }
                remember(trial.size());
                // Preserve the invariant needed by contiguous generic planning
                // and the +1 offset of helper insertion. The cap itself is never
                // an edit, so this also prevents a generic edit crossing the cap.
                for (int j = 0, cap = find_paper(ord, kCapPaper); j < cap; j++)
                    if (ord[j] < M) return false;
            }
            CF_SCOPE(eval_value);
            // as restore(seed) with the order replaced
            order = ord;
            double value;
            if (memo_hit) {
                top_d = memo->top_d;
                fillers = memo->fillers;
                // Keep the original left-to-right floating-point sum (moves + charge + next).
                value = path.size() + memo->charge + memo->next_cost;
            } else {
                top_d = seed.top_d;
                fillers = seed.fillers;
                canonicalize();
                const bool reachable = fillers_reachable();
                if (memo) {
                    memo->generation = generation;
                    memo->reachable = reachable;
                    if (reachable) {
                        memo->top_d = top_d;
                        memo->fillers = fillers;
                        GenericSplit split;
                        split_generic(split);
                        memo->charge = filler_charge(split);
                        memo->next_cost = kEndWeight * adaptive_next_cost(split);
                    }
                }
                if (!reachable) return false;
                value = memo ? path.size() + memo->charge + memo->next_cost : plan_cost(path.size());
            }
            F3_DIAG(fp_legal[fp_op]++;)
            if (neutral_collect && cfg.collect) {
                static const int neutral_width = [] {
                    const char* s = search_env("NEUTRAL_WIDTH");
                    return s ? std::max(1, std::atoi(s)) : 2;
                }();
                static const double kNeutralSlack = [] {
                    const char* s = search_env("NEUTRAL_SLACK");
                    return s ? std::atof(s) : 0.25;
                }();
                bool has_new_paper = !cfg.new_only;
                int repeats = 0;
                std::array<u64, 3> retained_moves{};
                if (cfg.candidate_mode == 2 || cfg.candidate_priority || cfg.promising_slack > 0) {
                    std::array<uint16_t, K> count{};
                    for (auto [k, d] : path) {
                        repeats += count[k]++ > 0;
                        if (cfg.hidden_rank || cfg.predict) retained_moves[k >> 6] |= 1ULL << (k & 63);
                        if (cfg.candidate_mode == 2 && count[k] > input_counts[k]) has_new_paper = true;
                        if (!input_moved[k]) has_new_paper = true;
                    }
                } else if (!has_new_paper)
                    for (auto [k, d] : path) if (!input_moved[k]) { has_new_paper = true; break; }
                // A short candidate or a repeated paper has a concrete deletion opportunity.
                // Only those signals may use the optional wider temporary value allowance.
                const double slack = (repeats || path.size() < input_ops.size())
                    ? std::max(kNeutralSlack, cfg.promising_slack) : kNeutralSlack;
                if (has_new_paper && path.size() <= input_ops.size() && value <= best_score + slack && order != seed.order) {
                    // Hash the top-down paper sequence that owns at least one of the first two
                    // opaque layers. This is approximate diversity filtering, not a validity test.
                    u64 seen = 0, twice = 0, signature = 7819213141ULL;
                    std::array<u64, 3> still_visible{};
                    for (int k : order) {
                        const u64 op = paper[k].opaque;
                        if ((cfg.hidden_rank || cfg.predict) && (op & ~seen))
                            still_visible[k >> 6] |= 1ULL << (k & 63);
                        if (op & ~twice) signature = (signature ^ u64(k + 1)) * 0x100000001b3ULL;
                        twice |= seen & op;
                        seen |= op;
                        if (twice == ~u64(0)) break;
                    }
                    int hides = 0;
                    for (int w = 0; w < 3; w++)
                        hides += __builtin_popcountll(parent_owner_moves[w] & retained_moves[w] & ~still_visible[w]);
                    bool found = false;
                    for (auto& c : neutral_candidates)
                        if (c.signature == signature) {
                            if (value < c.value) c = {save(), path OP_TAG(, path_tags), value, signature, trial_operator, repeats, hides};
                            found = true;
                            break;
                        }
                    if (!found)
                        neutral_candidates.push_back({save(), path OP_TAG(, path_tags), value, signature, trial_operator, repeats, hides});
                    std::sort(neutral_candidates.begin(), neutral_candidates.end(),
                              [&](const auto& a, const auto& b) {
                                  if (cfg.candidate_priority) {
                                      if (a.path.size() != b.path.size()) return a.path.size() < b.path.size();
                                      // Covering an old display owner can make its retained move redundant.
                                      // Spend the same two re-edit slots on concrete deletion opportunities.
                                      if (cfg.hidden_rank && a.hides != b.hides) return a.hides > b.hides;
                                      if (a.repeats != b.repeats) return a.repeats > b.repeats;
                                  }
                                  return a.value < b.value;
                              });
                    if (neutral_candidates.size() > size_t(neutral_width)) neutral_candidates.pop_back();
                }
            }
            if (value + 1e-8 >= best_score) return false;
            F3_DIAG(
                fp_accepts[fp_op]++;
                fp_gain[fp_op] += best_score - value;
                fp_saved[fp_op] += int(best_ops.size()) - int(path.size());
            )
            best_score = value;
            best_operator = trial_operator;
            best_ops = path;
            OP_TAG(best_tags = path_tags;)
            best_state = save();
            return true;
        };
        auto& trial = trial_buffer;  // the trials of the edit pass (evaluate does not keep it)
        auto delete_singles = [&]() {
            F3_DIAG(const int previous_op = fp_op; fp_switch(0);)
            bool any = false;
            for (int i = int(edits.size()) - 1; i >= 0; i--) {
                trial.assign(edits.begin(), edits.end());
                trial.erase(trial.begin() + i);
                if (evaluate(trial)) {
                    edits = anchorize(initial_bytes, best_ops OP_TAG(, best_tags));
                    any = true;
                    i = std::min(i, int(edits.size()));  // other edits may have become no-ops
                }
            }
            F3_DIAG(fp_switch(previous_op);)
            return any;
        };
        // Other anchors for the paper k of edit i: the top, around the papers of its column and the
        // column boundaries (a column paper), or around the other papers out of the columns (a generic
        // sheet), in the order before edit i; and the anchors of its later edits.
        // (the replay on a byte order, and the duplicates found with a table)
        auto anchor_candidates = [&](int i) {
            const int k = edits[i].paper;
            ByteOrder ord = initial_bytes;
            for (int t = 0; t < i; t++) {
                const int x = edits[t].paper, a = edits[t].anchor;
                const int p = find_paper(ord, x);
                int dest = a < 0 ? 0 : find_paper(ord, a) + 1;
                if (p < dest) dest--;  // x goes just below a once taken out
                shift_byte(ord, p, dest);
            }
            std::vector<int> anchors{-1};
            std::array<bool, K + 1> listed{};  // listed[a + 1]: a is in anchors
            listed[0] = true;
            auto add = [&](int a) {
                if (a != k && !listed[a + 1]) listed[a + 1] = true, anchors.push_back(a);
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
            return anchors;
        };
        if (eject) {
            F3_DIAG(fp_switch(3);)
            const auto accepted_before = eject_accepts;
            if (edits.size() >= 2 && (!neutral_collect || cfg.recheck))
                eject_repairs(initial, edits, u, initial_next, initial_prev, initial_bytes, evaluate);
            if (neutral_collect) {
                // Start the 2-to-2 enumeration from the best result of the 2-to-1 pass.
                // Freeze that edit list during enumeration, even when evaluate finds improvements.
                edits = anchorize(initial_bytes, best_ops OP_TAG(, best_tags));
                if (edits.size() >= 2 && cfg.two) {
                    F3_DIAG(fp_switch(4);)
                    trial_operator = 1;
                    neutral_repairs(edits, u, initial_bytes, evaluate, 2, &best_state);
                    edits = anchorize(initial_bytes, best_ops OP_TAG(, best_tags));
                }
                if (edits.size() >= 1 && cfg.one) {
                    F3_DIAG(fp_switch(5);)
                    trial_operator = 2;
                    const auto before_trials = eject_trials, before_accepts = eject_accepts;
                    // One edit is exchanged for a repair at the earliest/latest visible time.
                    // This can change a filler or comparator move excluded by the usual anchor pass.
                    eject_repairs(initial, edits, u, initial_next, initial_prev, initial_bytes, evaluate, 1);
                    ns_one_trials += eject_trials - before_trials;
                    ns_one_accepts += eject_accepts - before_accepts;
                    edits = anchorize(initial_bytes, best_ops OP_TAG(, best_tags));
                }
                if (edits.size() >= 3 && cfg.triples) {
                    F3_DIAG(fp_switch(6);)
                    trial_operator = 3;
                    const auto before_trials = triple_trials, before_accepts = triple_accepts;
                    // Remove a dependent dig/return/repair group together, then jointly repair it.
                    neutral_repairs(edits, u, initial_bytes, evaluate, 3, &best_state, &initial_extra);
                    ns_three_trials += triple_trials - before_trials;
                    ns_three_accepts += triple_accepts - before_accepts;
                    edits = anchorize(initial_bytes, best_ops OP_TAG(, best_tags));
                }
            }
            if (eject_accepts > accepted_before) {
                edits = anchorize(initial_bytes, best_ops OP_TAG(, best_tags));
                for (int pass = 0; pass < 3; pass++)
                    if (!delete_singles()) break;
            }
        } else {
            for (int pass = 0; pass < 3; pass++)
                if (!delete_singles()) break;
            // The cheap candidate pass stops at deletions: a new repair often makes an old return
            // or dig redundant. The ordinary pass still explores all its original anchor changes.
            F3_DIAG(fp_switch(1);)
            // Other anchors for an old extra / a paper moved twice.
            for (int i = int(edits.size()) - 1; !delete_only && i >= 0; i--) {
                const int k = edits[i].paper;
                if (!initial_extra[k]) {
                    int repeats = 0;
                    for (const auto& e : edits) repeats += e.paper == k;
                    if (repeats < 2) continue;
                }
                const auto anchors = anchor_candidates(i);
                auto chosen = edits;
                for (int a : anchors) {
                    if (a == edits[i].anchor) continue;
                    trial.assign(edits.begin(), edits.end());
                    trial[i].anchor = a;
                    if (evaluate(trial)) chosen = anchorize(initial_bytes, best_ops OP_TAG(, best_tags));
                }
                edits = std::move(chosen);
                i = std::min(i, int(edits.size()));
            }
            F3_DIAG(fp_switch(2);)
            // Delete an edit jointly with changing the insertion of an old extra k: the deleted edit
            // j moves a paper of a column rc other than D's whose handle k covers in A_u's color, and
            // k's new anchor is not in a column deeper than rc.
            for (int i = int(edits.size()) - 1; !delete_only && i >= 0; i--) {
                const int k = edits[i].paper;
                if (!initial_extra[k]) continue;
                const auto anchors = anchor_candidates(i);
                auto chosen = edits;
                for (int j = 0; j < int(edits.size()); j++)
                    if (j != i) {
                        int removed = edits[j].paper;
                        int rc = col_of[removed];
                        bool repair = rc >= 0 && rc != col_of[ded[u]] && (paper[k].opaque >> handle[rc] & 1) &&
                                      !((paper[k].black ^ A[u]) >> handle[rc] & 1);
                        if (!repair) continue;
                        for (int a : anchors) {
                            if (a == edits[i].anchor) continue;
                            if (a >= 0 && col_of[a] > rc) continue;
                            trial.assign(edits.begin(), edits.end());
                            trial[i].anchor = a;
                            trial.erase(trial.begin() + j);
                            rewrite_trials++;
                            if (evaluate(trial)) {
                                chosen = anchorize(initial_bytes, best_ops OP_TAG(, best_tags));
                                rewrite_accepts++;
                                rewrite_same_column += col_of[k] == col_of[removed];
                            }
                        }
                    }
                edits = std::move(chosen);
                i = std::min(i, int(edits.size()));
            }
            delete_singles();
        }
        F3_DIAG(
            fp_switch(fp_op);
            const std::string header = std::to_string(request_counter - 1) + ' ' + std::to_string(f3_stage)
                + ' ' + std::to_string(f3_round) + ' ' + std::to_string(input_ops.size())
                + ' ' + std::to_string(fp_repeats) + ' ' + std::to_string(initial.fillers.size());
            heavy_log += "#f3post " + header + ' ' + trace_value(fp_start_score - best_score)
                + ' ' + std::to_string(best_ops.size()) + ' ' + trace_value(elapsed_sec() - fp_start) + '\n';
            for (int o = 0; o < 7; o++) if (fp_trials[o] || fp_sec[o] > 0)
                heavy_log += "#f3op " + header + ' ' + std::to_string(o) + ' ' + std::to_string(fp_trials[o])
                    + ' ' + std::to_string(fp_legal[o]) + ' ' + std::to_string(fp_accepts[o])
                    + ' ' + trace_value(fp_gain[o]) + ' ' + std::to_string(fp_saved[o])
                    + ' ' + trace_value(fp_sec[o]) + '\n';
        )
        post_saved += int(input_ops.size()) - int(best_ops.size());
        restore(best_state);
        last_post_operator = best_operator;
        OP_TAG(tags = std::move(best_tags);)
        return best_ops;
    }

    // ==== Post-processing: two deletions and one repair (eject) ====

    // The eject pass of post_optimize (from base_edits, the edits of the plan). For every two edits
    // i < j (the latest pairs first), the trial without them leaves some windows wrong; a paper k that
    // would leave exactly a set `bad` of windows wrong once lifted out of the trial's final order, and
    // that is opaque and right on all of them, repairs the display if it is inserted above the first
    // other paper on every bad window and below the first other paper on every window where it is
    // wrong (an interval of gaps [lo, hi]). The anchors tried are the ends of the interval and the
    // column boundaries in it; the repair edit is inserted at the earliest and at the latest time
    // when k is visible (not after the first illegal edit of the trial). evaluate keeps the better
    // results.
    template <class Evaluate>
    void eject_repairs(const State& initial, const std::vector<Edit>& base_edits, int u, const Links& initial_next,
                       const Links& initial_prev, const ByteOrder& initial_bytes, Evaluate& evaluate, int removed = 2) {
        CF_SCOPE(eject);
        const auto& cfg = search_config();
        constexpr int root = kRoot;
        const auto accepts_at_start = eject_accepts;
        // The papers that can move at some time: those of the edits, and the unmoved papers visible
        // in the initial order (the relative order of the unmoved papers never changes, so one covered
        // by the unmoved papers above it stays covered).
        std::array<bool, K> possible{};
        for (auto e : base_edits) possible[e.paper] = true;
        u64 blocked = 0;
        for (int k : initial.order)
            if (!possible[k]) {
                if (paper[k].opaque & ~blocked) possible[k] = true;
                blocked |= paper[k].opaque;
            }
        std::array<int, K> candidates;
        int candidate_count = 0;
        for (int k = 0; k < K; k++)
            if (k != kCapPaper && possible[k]) candidates[candidate_count++] = k;
        auto& trial = eject_trial;
        auto& next = eject_next;
        auto& anchors = eject_anchors;
        // ord / ord_position: the final order of the trial and the position of every paper in it.
        std::array<int, K> ord, ord_position;
        std::array<int, K> owner_stamp{};
        int trial_stamp = 0;
        std::array<u64, K> owned;
        std::array<int, 64> first, second, column_first, column_second;
        // The replay of the trial for the visibility of a candidate (as evaluate: order, prefix covers).
        ByteOrder replay_order;
        std::array<u64, K + 1> replay_cover;
        const int n = base_edits.size();
        for (int j = n - 1; j >= (removed == 1 ? 0 : 1); j--)
            for (int i = removed == 1 ? -1 : j - 1; i >= (removed == 1 ? -1 : 0); i--) {
                trial.clear();
                for (int e = 0; e < n; e++)
                    if (e != i && e != j) trial.push_back(base_edits[e]);
                const int length = trial.size();
                // The final order of the trial (linked-list replay, visibility not checked), and on the
                // way down the display of the final order (shown), the windows where each paper is the
                // top opaque one (owned; papers from position `processed` on own nothing) and the
                // colors of the second opaque paper there (second_black).
                u64 covered = 0, twice = 0, shown = 0, second_black = 0;
                int processed = K, tail = root;
                trial_stamp++;
                auto nx = initial_next;
                {
                    auto pv = initial_prev;
                    for (const Edit& e : trial) {
                        const int k = e.paper, a = e.anchor < 0 ? root : e.anchor;
                        splice_after(nx, pv, k, a);
                    }
                    int t = 0, k = nx[root];
                    for (; k != root; k = nx[k]) {
                        ord[t] = k;
                        ord_position[k] = t++;
                        const u64 two = paper[k].opaque & covered & ~twice, one = paper[k].opaque & ~covered;
                        second_black |= paper[k].black & two;
                        owned[k] = one;
                        if (one) owner_stamp[k] = trial_stamp;
                        shown |= paper[k].black & one;
                        covered |= paper[k].opaque;
                        twice |= two;
                        if (twice == ~u64(0)) {
                            processed = t;
                            k = nx[k];
                            break;
                        }
                    }
                    tail = k;
                }
                bool order_ready = false;
                auto prepare_order = [&] {
                    if (order_ready) return;
                    order_ready = true;
                    int t = processed;
                    for (int k = tail; k != root; k = nx[k]) {
                        ord[t] = k;
                        ord_position[k] = t++;
                    }
                };
                // Most deletions have no single-paper repair. Their top two opaque layers
                // suffice to reject every paper, so only materialize the untouched tail when a
                // surviving repair needs its positions/anchors. Stamps distinguish real owners
                // without clearing all K ownership masks for each deletion pair.
                if (!cfg.lazy_tail) prepare_order();
                eject_pairs++;
                // first / second: the positions of the top two opaque papers of every window (K if
                // none; computed when needed).
                bool positions_ready = false;
                auto prepare_positions = [&] {
                    if (positions_ready) return;
                    positions_ready = true;
                    first.fill(K);
                    second.fill(K);
                    u64 once_seen = 0, twice_seen = 0;
                    for (int t = 0; t < K; t++) {
                        int k = ord[t];
                        u64 two = paper[k].opaque & once_seen & ~twice_seen, one = paper[k].opaque & ~once_seen;
                        for (u64 z = two; z; z &= z - 1) second[__builtin_ctzll(z)] = t;
                        for (u64 z = one; z; z &= z - 1) first[__builtin_ctzll(z)] = t;
                        once_seen |= paper[k].opaque;
                        twice_seen |= two;
                        if (twice_seen == ~u64(0)) break;
                    }
                };
                // column_first / column_second: the positions of the top two papers of every column
                // (-1 if none; computed when needed).
                bool columns_ready = false;
                auto prepare_columns = [&] {
                    if (columns_ready) return;
                    columns_ready = true;
                    std::fill(column_first.begin(), column_first.begin() + H, -1);
                    std::fill(column_second.begin(), column_second.begin() + H, -1);
                    for (int t = 0; t < K; t++) {
                        const int c = col_of[ord[t]];
                        if (c < 0) continue;
                        if (column_first[c] < 0)
                            column_first[c] = t;
                        else if (column_second[c] < 0)
                            column_second[c] = t;
                    }
                };
                if (shown == A[u]) continue;  // nothing to repair (a single wrong window is enough)
                for (int ci = 0; ci < candidate_count; ci++) {
                    const int k = candidates[ci];
                    // The display with k lifted out (its own windows show the paper below) and the
                    // windows then wrong; k must cover them all with the right colors.
                    const u64 own = owner_stamp[k] == trial_stamp ? owned[k] : 0;
                    u64 after = shown ^ ((shown ^ second_black) & own), bad = after ^ A[u];
                    u64 wrong = paper[k].opaque & (paper[k].black ^ A[u]);
                    if (!bad || (bad & ~paper[k].opaque) || (bad & wrong)) continue;
                    prepare_order();
                    prepare_positions();
                    // without_pos(w): the position, in the order without k, of the top opaque paper
                    // other than k at window w
                    const int pos = ord_position[k];
                    int lo = 0, hi = K - 1;
                    auto without_pos = [&](int w) {
                        int p = first[w] == pos ? second[w] : first[w];
                        return p - int(p > pos);
                    };
                    for (u64 z = bad; z; z &= z - 1) hi = std::min(hi, without_pos(__builtin_ctzll(z)));
                    for (u64 z = wrong; z && lo <= hi; z &= z - 1)
                        lo = std::max(lo, without_pos(__builtin_ctzll(z)) + 1);
                    if (lo > hi) continue;
                    // the order without k: without(t) is its paper at position t
                    auto without = [&](int t) { return ord[t < pos ? t : t + 1]; };
                    anchors.clear();
                    auto add = [&](int gap) {
                        if (gap < lo || gap > hi || gap == pos) return;
                        int a = gap ? without(gap - 1) : -1;
                        if (std::find(anchors.begin(), anchors.end(), a) == anchors.end()) anchors.push_back(a);
                    };
                    add(lo);
                    add(hi);
                    // The gaps at the column boundaries of the order without k (around the papers out
                    // of the columns, above the first paper of every column <= k's, around the papers
                    // of k's column), in the order of the gaps: only the positions t whose add calls
                    // can fall in [lo, hi] are visited.
                    // Only the first one_anchors entries are used by 1->1. Interior
                    // anchors are appended, so they cannot change an already full prefix.
                    if (!(removed == 1 && cfg.one_anchors && int(anchors.size()) >= cfg.one_anchors)) {
                        prepare_columns();
                        const int ck = col_of[k];
                        auto first_in_without = [&](int c) {
                            int p = column_first[c] == pos ? column_second[c] : column_first[c];
                            return p - int(p > pos);
                        };
                        for (int t = std::max(0, lo - 1), t_end = std::min(K - 2, hi); t <= t_end; t++) {
                            const int c = col_of[without(t)];
                            if (c < 0)
                                add(t), add(t + 1);
                            else if (first_in_without(c) == t) {
                                if (c <= ck) add(t);
                            }
                            if (c == ck) add(t), add(t + 1);
                        }
                    }
                    if (anchors.empty()) continue;
                    // Replays the trial: k visible before edit t (earliest / latest such t), up to the
                    // first edit that moves an invisible paper (included: the state before it).
                    int earliest = length + 1, latest = -1;
                    replay_order = initial_bytes;
                    int cover_valid = 0;
                    replay_cover[0] = 0;
                    auto visible_at = [&](int x, int p) {  // paper x at position p
                        for (; cover_valid < p; cover_valid++)
                            replay_cover[cover_valid + 1] =
                                replay_cover[cover_valid] | paper[replay_order[cover_valid]].opaque;
                        return (paper[x].opaque & ~replay_cover[p]) != 0;
                    };
                    for (int t = 0;; t++) {
                        if (visible_at(k, find_paper(replay_order, k))) {
                            earliest = std::min(earliest, t);
                            latest = t;
                        }
                        if (t == length) break;
                        const int x = trial[t].paper, a = trial[t].anchor;
                        const int p = find_paper(replay_order, x);
                        int dest = a < 0 ? 0 : find_paper(replay_order, a) + 1;
                        if (p < dest) dest--;
                        if (dest == p) continue;
                        if (!visible_at(x, p)) break;  // the first illegal edit
                        shift_byte(replay_order, p, dest);
                        cover_valid = std::min(cover_valid, std::min(p, dest));
                    }
                    if (latest < 0) continue;
                    for (int pass = 0; pass < (earliest == latest ? 1 : 2); pass++) {
                        const int t = pass ? latest : earliest;
                        // The interval endpoints precede column-interior anchors. A small research
                        // budget may inspect only those endpoints for 1->1; ordinary 2->1 is intact.
                        const int count = removed == 1 && cfg.one_anchors
                            ? std::min(int(anchors.size()), cfg.one_anchors) : int(anchors.size());
                        for (int ai = 0; ai < count; ai++) {
                            next.assign(trial.begin(), trial.end());
                            next.insert(next.begin() + t, {k, anchors[ai]});
                            eject_trials++;
                            if (evaluate(next)) {
                                eject_accepts++;
                                eject_inside += t < length;
                                if (removed == 1 && cfg.one_limit &&
                                    eject_accepts - accepts_at_start >= cfg.one_limit) return;
                            }
                        }
                    }
                }
            }
    }

    // ==== Post-processing: two deletions and two repairs (neutral rewrite) ====

    // Remove two edits, replay the remaining prefix legally, then repair its display with
    // two tail moves. f is above g in the final order (not necessarily the first paper moved).
    // By default the shallowest and deepest feasible gap pairs are sampled; NS_INTERIOR adds structural gaps. Equal pairs
    // are intentionally not deduplicated, preserving the original enumeration and counters.
    template <class Evaluate>
    void neutral_repairs(const std::vector<Edit>& base, int u, const ByteOrder& initial_bytes, Evaluate& evaluate,
                         int removed = 2, const State* reference = nullptr, const std::array<bool, K>* initial_extra = nullptr) {
        CF_SCOPE(neutral);
        const auto& cfg = search_config();
        std::array<u64, K> wrong_color;
        for (int k = 0; k < K; k++) wrong_color[k] = (paper[k].black ^ A[u]) & paper[k].opaque;
        std::array<bool, K> edited{}, end_visible{};
        for (const auto& e : base) edited[e.paper] = true;
        if (reference) {
            u64 covered = 0;
            for (int k : reference->order) {
                end_visible[k] = bool(paper[k].opaque & ~covered);
                covered |= paper[k].opaque;
            }
        }
        // These buffers are no longer in use by eject_repairs; evaluate has separate buffers.
        auto& trial = eject_trial;
        auto& next = eject_next;
        int legal_trials = 0;
        for (int y = int(base.size()) - 1; y >= 1; y--)
            for (int x = y - 1; x >= (removed == 3 ? 1 : 0); x--)
              for (int z = removed == 3 ? x - 1 : -1; z >= (removed == 3 ? 0 : -1); z--) {
                // State-only rewrites mostly replace papers responsible for the final display.
                // Restrict the expensive two-paper search to such pairs (mode 2 allows one owner).
                const int owners = int(end_visible[base[x].paper]) + int(end_visible[base[y].paper]);
                if (reference && cfg.pair_filter && owners < (cfg.pair_filter == 1 ? 2 : 1)) continue;
                if (reference && cfg.pair_filter == 3 && owners != 1) continue;
                // A hidden return/dig plus two final display owners is a common dependent triple.
                if (removed == 3 && cfg.three_hidden && end_visible[base[z].paper]) continue;
                // An old lifted/filler paper may need a return only to make the two later display
                // owners movable. Removing that return and both owners is a targeted 3->2 escape.
                if (removed == 3 && cfg.three_extra && !(*initial_extra)[base[z].paper]) continue;
                trial = base;
                trial.erase(trial.begin() + y);
                trial.erase(trial.begin() + x);
                if (z >= 0) trial.erase(trial.begin() + z);
                ByteOrder ord = initial_bytes;
                std::array<u64, K + 1> cover;
                cover[0] = 0;
                int cover_valid = 0;
                bool legal = true;
                for (const Edit& e : trial) {
                    const int k = e.paper, a = e.anchor;
                    const int p = find_paper(ord, k);
                    int d = a < 0 ? 0 : find_paper(ord, a) + 1;
                    if (p < d) d--;
                    if (p == d) continue;  // evaluate also drops no-op edits before visibility checks
                    for (; cover_valid < p; cover_valid++)
                        cover[cover_valid + 1] = cover[cover_valid] | paper[ord[cover_valid]].opaque;
                    if (!(paper[k].opaque & ~cover[p])) {
                        legal = false;
                        break;
                    }
                    shift_byte(ord, p, d);
                    cover_valid = std::min(cover_valid, std::min(p, d));
                }
                if (!legal) continue;
                if (cfg.joint_limit && legal_trials == cfg.joint_limit) return;
                legal_trials++;
                triple_trials++;
                std::array<int, N> first, second, third;
                first.fill(K);
                second.fill(K);
                third.fill(K);
                std::array<u64, K> owned{}, owned2{};
                std::array<int, K> position, pool, pool_index;
                pool_index.fill(-1);
                int pool_count = 0;
                u64 seen = 0, twice = 0, thrice = 0, view = 0, black2 = 0, black3 = 0;
                for (int t = 0; t < K; t++) {
                    const int k = ord[t];
                    position[k] = t;
                    const u64 one = paper[k].opaque & ~seen;
                    const u64 two = paper[k].opaque & seen & ~twice;
                    const u64 three = paper[k].opaque & twice & ~thrice;
                    owned[k] = one;
                    owned2[k] = two;
                    // A first move must be visible; it can expose only a former second owner.
                    if ((one || two) && k != kCapPaper) { pool_index[k] = pool_count; pool[pool_count++] = k; }
                    view |= paper[k].black & one;
                    black2 |= paper[k].black & two;
                    black3 |= paper[k].black & three;
                    for (u64 b = one; b; b &= b - 1) first[__builtin_ctzll(b)] = t;
                    for (u64 b = two; b; b &= b - 1) second[__builtin_ctzll(b)] = t;
                    for (u64 b = three; b; b &= b - 1) third[__builtin_ctzll(b)] = t;
                    seen |= paper[k].opaque;
                    twice |= two;
                    thrice |= three;
                    // Once all third owners are known, the tail owns no first/second window.
                    // Only inverse positions (including possible tail anchors) remain needed.
                    if (thrice == ~u64(0)) {
                        for (++t; t < K; t++) position[ord[t]] = t;
                        break;
                    }
                }
                if (view == A[u]) {
                    if (evaluate(trial)) {
                        triple_accepts++;
                        if (cfg.joint_stop) return;
                    }
                    continue;
                }
                const u64 oldbad = view ^ A[u];
                for (int fi = 0; fi < pool_count; fi++) {
                    const int f = pool[fi];
                    // If f has the wrong color on an old wrong window it does not own, the
                    // original pair filter requires g to own that window. Ownership is disjoint,
                    // so a nonempty mask forces at most one g. Keep the old order of viable pairs.
                    const u64 must_own = cfg.pair_owners ? oldbad & wrong_color[f] & ~owned[f] : 0;
                    int first_g = 0, end_g = pool_count;
                    if (must_own) {
                        const int g = ord[first[__builtin_ctzll(must_own)]];
                        if (pool_index[g] < 0 || (must_own & ~owned[g])) continue;
                        first_g = pool_index[g];
                        end_g = first_g + 1;
                    }
                    for (int gi = first_g; gi < end_g; gi++) {
                        const int f = pool[fi], g = pool[gi];
                        if (f == g || !(owned[f] | owned[g])) continue;
                        const u64 opf = paper[f].opaque, opg = paper[g].opaque;
                        if (oldbad & ~(opf | opg)) continue;
                        if (oldbad & wrong_color[f] & ~(owned[f] | owned[g])) continue;
                        const u64 own = owned[f] | owned[g];
                        const u64 both = (owned[f] & owned2[g]) | (owned[g] & owned2[f]);
                        // Remove f and g: expose the second color on own, or the third on both.
                        const u64 after = view ^ ((view ^ black2) & own) ^ ((black2 ^ black3) & both);
                        const u64 bad = after ^ A[u];
                        if (!bad || (bad & wrong_color[f])) continue;
                        const u64 lowerbad = bad & ~opf;
                        if ((lowerbad & ~opg) || (lowerbad & wrong_color[g])) continue;
                        const int pf = position[f], pg = position[g];
                        // Position of the first remaining opaque owner (K-2 is the white background).
                        auto without_pos = [&](int w) {
                            int p = first[w];
                            if (p == pf || p == pg) p = second[w];
                            if (p == pf || p == pg) p = third[w];
                            return p - int(p > pf) - int(p > pg);
                        };
                        int la = 0, ha = K - 2, lb = 0, hb = K - 2;
                        for (u64 b = bad & opf; b; b &= b - 1)
                            ha = std::min(ha, without_pos(__builtin_ctzll(b)));
                        for (u64 b = lowerbad; b; b &= b - 1)
                            hb = std::min(hb, without_pos(__builtin_ctzll(b)));
                        // f must be no deeper than g. A wrong color must stay below its owner;
                        // g's wrong colors hidden by f impose no independent lower bound.
                        ha = std::min(ha, hb);
                        for (u64 b = wrong_color[f]; b && la <= ha; b &= b - 1)
                            la = std::max(la, without_pos(__builtin_ctzll(b)) + 1);
                        if (la > ha) continue;
                        lb = la;
                        for (u64 b = wrong_color[g] & ~opf; b && lb <= hb; b &= b - 1)
                            lb = std::max(lb, without_pos(__builtin_ctzll(b)) + 1);
                        if (lb > hb) continue;
                        // Index the order with both papers removed without copying or erasing it.
                        auto without = [&](int t) {
                            if (t >= std::min(pf, pg)) t++;
                            if (t >= std::max(pf, pg)) t++;
                            return int(ord[t]);
                        };
                        std::array<std::pair<int, int>, 130> gap_pairs;
                        int gap_count = 2;
                        gap_pairs[0] = {la, lb};
                        gap_pairs[1] = {ha, hb};
                        if (cfg.interior) {
                            // Interior placements at column boundaries and around edited/generic
                            // papers can keep a useful filler near its home without returning it
                            // all the way to either endpoint. Enumerate structural gaps, not all K^2.
                            std::vector<int> slots;
                            for (int t = 0; t <= K - 2; t++) {
                                if (t == 0 || t == K - 2) { slots.push_back(t); continue; }
                                const int left = without(t - 1), right = without(t);
                                if (col_of[left] != col_of[right] || col_of[left] < 0 ||
                                    edited[left] || edited[right]) slots.push_back(t);
                            }
                            auto add = [&](int a, int b) {
                                if (gap_count == 2 + cfg.interior || a < la || a > ha ||
                                    b < lb || b > hb || a > b) return;
                                const std::pair<int, int> pair{a, b};
                                for (int i = 0; i < gap_count; i++) if (gap_pairs[i] == pair) return;
                                gap_pairs[gap_count++] = pair;
                            };
                            for (int t : slots) add(t, t);
                            for (int t : slots) { add(t, hb); add(la, t); }
                            for (int a : slots) {
                                if (gap_count == 2 + cfg.interior) break;
                                for (int b : slots) {
                                    add(a, b);
                                    if (gap_count == 2 + cfg.interior) break;
                                }
                            }
                        }
                        for (int gap = 0; gap < gap_count; gap++) {
                            const auto [a, b] = gap_pairs[gap];
                            const int aa = a ? without(a - 1) : -1;
                            const int ab = b ? without(b - 1) : -1;
                            struct Tail {
                                int x = -1, a = -1, y = -1, b = -1, moves = 3;
                            };
                            Tail best_tail;
                            // Try g then f before f then g; ties keep the former.
                            for (int rev = 0; rev < 2; rev++) {
                                const int k1 = rev ? f : g, k2 = rev ? g : f;
                                const int anc1 = rev ? aa : ab;
                                const int anc2 = rev ? (a == b ? f : ab) : aa;
                                const int p1 = position[k1], p2 = position[k2];
                                int d1 = anc1 < 0 ? 0 : position[anc1] + 1;
                                d1 -= int(p1 < d1);
                                if (d1 != p1 && !owned[k1]) continue;
                                auto after_position = [&](int k) {
                                    if (k == k1) return d1;
                                    const int q = position[k] - int(position[k] > p1);
                                    return q + int(q >= d1);
                                };
                                const int p2new = after_position(k2);
                                int d2 = anc2 < 0 ? 0 : after_position(anc2) + 1;
                                d2 -= int(p2new < d2);
                                if (d2 != p2new) {
                                    // Removing k1 exposes its former second owner k2. Reinserting
                                    // k1 above k2 can cover some or all of those windows again.
                                    u64 exposed = owned[k2] | (owned[k1] & owned2[k2]);
                                    if (d1 <= p2 - int(p2 > p1)) exposed &= ~paper[k1].opaque;
                                    if (!exposed) continue;
                                }
                                const int moves = int(d1 != p1) + int(d2 != p2new);
                                if (moves < best_tail.moves) best_tail = {k1, anc1, k2, anc2, moves};
                            }
                            if (best_tail.moves <= 2) {
                                next = trial;
                                // New edits use Edit's default kOpRepair label; surviving edits keep theirs.
                                next.push_back({best_tail.x, best_tail.a});
                                next.push_back({best_tail.y, best_tail.b});
                                triple_repairs++;
                                if (evaluate(next)) {
                                    triple_accepts++;
                                    if (cfg.joint_stop) return;
                                }
                            }
                        }
                    }
                }
            }
    }

    // Re-edit only after an accepted ejection. Keep ordinary stage/round profiler labels.
    Moves polish_ejects(const State& initial,
            Moves path, int u OP_TAG(, std::vector<uint8_t>& tags),
            int rounds, [[maybe_unused]] bool ordinary = false) {
        for (int round = 0; round < rounds; ++round) {
            F3_DIAG(if (ordinary) { f3_stage = 2; f3_round = round; })
            const auto before = eject_accepts;
            if (round) path = post_optimize(initial, std::move(path), u OP_TAG(, tags), false);
            path = post_optimize(initial, std::move(path), u OP_TAG(, tags), true);
            if (eject_accepts == before) break;
        }
        return path;
    }

    // ==== Request processing (process) ====

    // Simulate plan options, a filler-chain plan and helper plans from the same starting stack.
    // Keep valid candidates (correct display, <=2K moves, reachable fillers), edit the best
    // kPostCandidates, then polish by ejection and neutral rewrites (F3_NEUTRAL=0 disables neutral).
    // If none is valid, try the plain plan; return no moves if even that plan is illegal.
    long long unsafe_plans = 0;
    static constexpr int kPostCandidates = 3;
    long long post_alternate = 0, post_candidate_calls = 0, post_secondary_saved = 0;
    // Process-wide diagnostics keep Solver's hot-state layout unchanged.
    inline static long long value_seed_trials = 0, value_seed_valid = 0, value_seed_accepts = 0, value_seed_saved = 0;
    inline static double value_seed_gain = 0;
    // Keep the uncommon extra plan's snapshots and editing work out of process's
    // main frame; its eligibility was checked using the existing edited cache.
    template<class Candidate>
    [[gnu::noinline]] bool finish_weighted_plan(const State& initial, const Candidate& c,
                                               int u, double value, Moves& chosen
                                               OP_TAG(, std::vector<uint8_t>& chosen_tags)) {
        const auto incumbent = save();
        restore(c.state);
        canonicalize();
        OP_TAG(auto tags = c.tags;)
        F3_DIAG(f3_stage = 3; f3_round = 0;)
        ++value_seed_trials;
        auto path = polish_ejects(initial, c.path, u OP_TAG(, tags), 4, true);
        const double next = plan_cost(path.size());
        const bool valid = display() == A[u] && fillers_reachable();
        value_seed_valid += valid;
        if (valid && next < value - 1e-9) {
            ++value_seed_accepts;
            value_seed_gain += value - next;
            value_seed_saved += int(chosen.size()) - int(path.size());
            chosen = std::move(path);
            OP_TAG(chosen_tags = std::move(tags);)
            return true;
        }
        restore(incumbent);
        return false;
    }
    Moves process(int u) {
        CF_SCOPE(process);
        post_context.ready = false;  // all post-processing in this call replays the same st0
        static const bool neutral_config = [] {
            const char* s = search_env("NEUTRAL");
            return s ? std::atoi(s) != 0 : true;
        }();
        const bool neutral_enabled=neutral_config;
        OP_TAG(if (neutral_enabled) ++request_counter;)
        init_adaptive();
        adaptive_request = u;
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
        if (d != top0) opts.push_back({1, 5, true, true});
        if (d != top0) opts.push_back({1, 5, true, true, true});
        double best = 1e18, best_normal = 1e18;
        Moves best_ops;
        OP_TAG(std::vector<uint8_t> best_tags;)  // the labels of best_ops, then of chosen_path
        State best_state;
        // The candidates for the post-processing, cheapest first, of distinct final orders and
        // moved-paper sequences: different insertion depths of the same moved-paper sequence often
        // collapse to one result during post-processing, so the second slot goes to a different
        // sequence while the cheaper family member is kept.
        struct FutureCandidate {
            double cost;
            State state;
            Moves path;
            OP_TAG(std::vector<uint8_t> tags;)  // the labels of path
        };
        FutureCandidate weighted_raw{};
        bool weighted_ready = false;
        std::vector<FutureCandidate> future_candidates, expanded_candidates, edited_candidates;
        struct CachedPlan { FutureCandidate raw, edited; bool complete = false; };
        std::vector<CachedPlan> plan_cache;
        const bool cache_plans = neutral_enabled && search_config().post_candidates > 2 && search_config().plan_reuse;
        int chosen_cache = -1;
        auto same_family = [](const auto& a, const auto& b) {
            if (a.size() != b.size()) return false;
            for (int i = 0; i < int(a.size()); i++)
                if (a[i].first != b[i].first) return false;
            return true;
        };
        auto by_cost = [](auto& a, auto& b) { return a.cost < b.cost; };
        auto collect_future = [&](std::vector<FutureCandidate>& candidates, size_t width, double cost) {
            if (candidates.size() == width && cost >= candidates.back().cost) return;
            for (auto& candidate : candidates)
                if (candidate.state.order == order || same_family(candidate.path, ops)) {
                    if (cost < candidate.cost) {
                        candidate = {cost, save(), ops OP_TAG(, op_tags)};
                        std::sort(candidates.begin(), candidates.end(), by_cost);
                    }
                    return;
                }
            candidates.push_back({cost, save(), ops OP_TAG(, op_tags)});
            std::sort(candidates.begin(), candidates.end(), by_cost);
            if (candidates.size() > width) candidates.pop_back();
        };
        auto record_future = [&](double cost) {
            // Keep separate ordinary and expanded collectors, in the same insertion order.
            if (neutral_enabled && search_config().post_candidates > 2)
                collect_future(expanded_candidates, search_config().post_candidates, cost);
            collect_future(future_candidates, kPostCandidates, cost);
        };
        auto find_cached_plan = [&](const FutureCandidate& c) -> const CachedPlan* {
            for (const auto& old : plan_cache)
                if (old.raw.path == c.path && old.raw.state.order == c.state.order &&
                    old.raw.state.top_d == c.state.top_d && same_fillers(old.raw.state.fillers, c.state.fillers)
                    OP_TAG(&& old.raw.tags == c.tags)) return &old;
            return nullptr;
        };
        PlanOpt best_normal_opt;
        check_vis = true;
        tail_cache.clear();
        tail_cache_on = true;
        struct RepeatedPlan {
            PlanOpt opt;
            State state;
            Moves path;
            OP_TAG(std::vector<uint8_t> tags; uint8_t last_tag;)
            bool invalid;
            std::vector<std::vector<int>> chains;
        };
        std::vector<RepeatedPlan> repeated_plans;
        repeated_plans.reserve(3);
        for (const PlanOpt& o : opts) {
            start_plan(st0);
            // These modes differ only by adding kTopPenalty to a top insertion.
            // With the fixed zero penalty their complete candidate simulations agree.
            // Still visit and score every option in the original order.
            const RepeatedPlan* repeated = nullptr;
            if (kTopPenalty == 0 && o.ret_mode == 2)
                for (const auto& q : repeated_plans)
                    if (q.opt.fret_mode == o.fret_mode && q.opt.use_filler == o.use_filler &&
                        q.opt.value_fillers == o.value_fillers && q.opt.complete_value == o.complete_value) { repeated = &q; break; }
            if (repeated) {
                restore(repeated->state);
                ops = repeated->path;
                OP_TAG(op_tags = repeated->tags; op_tag = repeated->last_tag;)
                invalid = repeated->invalid;
                placement_chains = repeated->chains;
            } else {
                run_plan(u, o);
                if (kTopPenalty == 0 && o.ret_mode == 1)
                    repeated_plans.push_back({o, save(), ops OP_TAG(, op_tags, op_tag), invalid, placement_chains});
            }
            if (invalid || ops.size() > 2 * K || display() != A[u] || !fillers_reachable()) continue;
            double cost = plan_cost(ops.size());
            if (o.value_fillers) {
                if (cache_plans && !o.complete_value) {
                    weighted_raw = {cost, save(), ops OP_TAG(, op_tags)};
                    weighted_ready = true;
                }
                ++value_filler_plans;
                if (cost < best) ++value_filler_better, value_filler_gain += best - cost;
            }
            complete_value_plans += o.complete_value;
            record_future(cost);
            if (cost < best) best = cost, best_ops = ops OP_TAG(, best_tags = op_tags), best_state = save();
            if (o.fret_mode != 5 && cost < best_normal) best_normal = cost, best_normal_opt = o;
        }
        tail_cache_on = false;
        int source = 0, chain_count = 0;  // the plan kept: 0 the options, 1 the chain search, 2 helpers
        if (best_normal < 1e17) {
            start_plan(st0);
            beam_enabled = true;
            run_plan(u, best_normal_opt);
            beam_enabled = false;
            if (!placement_chains.empty()) chain_trials++;
            for (const auto& ch : placement_chains) chain_count += ch.size();
            placement_chains.clear();
            if (!invalid && ops.size() <= 2 * K && display() == A[u] && fillers_reachable()) {
                double cost = plan_cost(ops.size());
                record_future(cost);
                if (cost < best) best = cost, best_ops = ops OP_TAG(, best_tags = op_tags), best_state = save(), source = 1;
            }
        }
        if (interleave && interleave->ready && d >= 0 && d != top0 && !interleave->helpers[u].empty()) {
            bool used = false;
            try_helpers(u, st0, [&](double cost) {
                record_future(cost);
                if (cost < best) best = cost, best_ops = ops OP_TAG(, best_tags = op_tags), best_state = save(), used = true;
            });
            interleave_selected += used;
            if (used) source = 2;
        }
        if (source == 1) chain_selected++, chain_papers += chain_count;
        if (best > 1e17) {
            plan_failures++;
            start_plan(st0);
            run_plan(u, PlanOpt{});
            check_vis = false;
            if (invalid || ops.size() > 2 * K) {
                unsafe_plans++;
                restore(st0);
                ops.clear();
                OP_TAG(op_tags.clear();)
            }
            return ops;
        }
        check_vis = false;
        restore(best_state);
        canonicalize();
        if (cache_plans) {
            plan_cache.push_back({{best, best_state, best_ops OP_TAG(, best_tags)}, {}});
            chosen_cache = 0;
        }
        F3_DIAG(f3_stage = 0; f3_round = 0;)
        auto chosen_path = post_optimize(st0, std::move(best_ops), u OP_TAG(, best_tags));
        if (cache_plans) plan_cache.back().edited = {plan_cost(chosen_path.size()), save(), chosen_path OP_TAG(, best_tags)};
        if (neutral_enabled && search_config().alternate)
            edited_candidates.push_back({plan_cost(chosen_path.size()), save(), chosen_path OP_TAG(, best_tags)});
        post_candidate_calls++;
        const int original_length = chosen_path.size();
        if (future_candidates.size() > 1) {
            auto chosen = save();
            const auto original_order = best_state.order;
            double value = plan_cost(chosen_path.size());
            bool changed = false;
            for (auto& candidate : future_candidates) {
                if (candidate.state.order == original_order) continue;
                restore(candidate.state);
                canonicalize();
                if (cache_plans) plan_cache.push_back({candidate, {}});
                OP_TAG(auto tags = std::move(candidate.tags);)  // (the candidates are not used afterwards)
                F3_DIAG(f3_stage = 1;)
                auto path = post_optimize(st0, candidate.path, u OP_TAG(, tags));
                if (cache_plans) plan_cache.back().edited = {plan_cost(path.size()), save(), path OP_TAG(, tags)};
                if (neutral_enabled && search_config().alternate)
                    edited_candidates.push_back({plan_cost(path.size()), save(), path OP_TAG(, tags)});
                post_candidate_calls++;
                double next = plan_cost(path.size());
                if (next < value - 1e-9) {
                    value = next;
                    chosen = save();
                    chosen_path = std::move(path);
                    OP_TAG(best_tags = std::move(tags);)
                    if (cache_plans) chosen_cache = int(plan_cache.size()) - 1;
                    changed = true;
                }
            }
            restore(chosen);
            post_alternate += changed;
        }
        const auto ordinary_eject_start = neutral_enabled && search_config().alternate ? order : std::array<uint8_t, K>{};
        chosen_path = polish_ejects(st0, std::move(chosen_path), u OP_TAG(, best_tags), 4, true);
        if (cache_plans && chosen_cache >= 0) {
            plan_cache[chosen_cache].edited = {plan_cost(chosen_path.size()), save(), chosen_path OP_TAG(, best_tags)};
            plan_cache[chosen_cache].complete = true;
        }
        if (neutral_enabled) {
            const auto& cfg = search_config();
            static const int neutral_depth = [] {
                const char* s = search_env("NEUTRAL_DEPTH");
                return s ? std::atoi(s) : 2;
            }();
            // Baseline for the heavy traces: before extra operators or plans.
            const auto baseline_path = chosen_path;
            const double baseline_value = plan_cost(chosen_path.size());
            OP_TAG(const auto baseline_tags = best_tags;)
            OP_TAG(double baseline_filler = 0, baseline_next = 0;)
            // The research trace needs the cost terms separately; the normal fast run does not.
            OP_TAG(if (cfg.trace) {
                GenericSplit baseline_split;
                split_generic(baseline_split);
                baseline_filler = filler_charge(baseline_split);
                baseline_next = kEndWeight * adaptive_next_cost(baseline_split);
            })
            [[maybe_unused]] int winning_operator = 0, winning_round = 0;
            [[maybe_unused]] bool winning_escape = false;
            if (cfg.alternate) {
                // The ordinary edit pass already paid for this alternative. It can lose before
                // ejection yet win afterwards; reuse its edited state rather than planning again.
                auto incumbent = save();
                double incumbent_value = baseline_value;
                for (auto& c : edited_candidates) {
                    if (c.state.order == ordinary_eject_start || c.cost > baseline_value + cfg.alternate_gap) continue;
                    restore(c.state);
                    auto path = c.path;
                    OP_TAG(auto tags = c.tags;)
                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), 4);
                    ns_plan_calls++;
                    const double value = plan_cost(path.size());
                    if (value < incumbent_value - 1e-9) {
                        incumbent_value = value;
                        incumbent = save();
                        chosen_path = std::move(path);
                        OP_TAG(best_tags = std::move(tags);)
                        winning_operator = 4;
                    }
                }
                restore(incumbent);
            }
            F3_DIAG(f3_stage = 3; f3_round = 0;)
            if (!expanded_candidates.empty()) {
                auto incumbent = save();
                double incumbent_value = plan_cost(chosen_path.size());
                if (cfg.plan_screen) {
                    // Obvious deletions are cheaper than anchor rewrites and ejection. Rank the
                    // remaining plans by their value after this small pass, then fully search only
                    // PLAN_LIMIT of them. This changes the neighborhood; it is not an exact cache.
                    std::vector<FutureCandidate> screened;
                    for (const auto& c : expanded_candidates) {
                        const CachedPlan* cached = find_cached_plan(c);
                        if ((cached && (cached->complete || cfg.plan_skip_edited)) ||
                            c.cost > baseline_value + cfg.plan_gap) { f2_plan_skipped++; continue; }
                        if (cached) { screened.push_back(c); continue; }
                        restore(c.state);
                        canonicalize();
                        auto path = c.path;
                        OP_TAG(auto tags = c.tags;)
                        path = post_optimize(st0, std::move(path), u OP_TAG(, tags), false, true);
                        screened.push_back({plan_cost(path.size()), save(), std::move(path) OP_TAG(, std::move(tags))});
                        f2_plan_screens++;
                    }
                    expanded_candidates = std::move(screened);
                    std::stable_sort(expanded_candidates.begin(), expanded_candidates.end(), by_cost);
                    restore(incumbent);
                }
                if (cfg.plan_priority) {
                    // A repeated paper can lose both its dig and its return after changing plans.
                    auto priority = [&](const FutureCandidate& c) {
                        std::array<bool, K> moved{};
                        int repeated = 0;
                        for (auto [k, d] : c.path) { repeated += moved[k]; moved[k] = true; }
                        return c.cost - .75 * repeated;
                    };
                    std::stable_sort(expanded_candidates.begin(), expanded_candidates.end(),
                                     [&](const auto& a, const auto& b) {
                                         if (cfg.plan_priority == 2 && a.path.size() != b.path.size())
                                             return a.path.size() < b.path.size();
                                         return priority(a) < priority(b);
                                     });
                }
                [[maybe_unused]] int attempted = 0, plan_rank = 0;
                for (auto& c : expanded_candidates) {
                    plan_rank++;
                    [[maybe_unused]] int repeated = 0, added = 0;
                    if (cfg.plan_shortlist || cfg.plan_trace) {
                        std::array<uint16_t, K> count{}, old{};
                        for (auto [k, d] : baseline_path) old[k]++;
                        for (auto [k, d] : c.path) {
                            repeated += count[k]++ > 0;
                            added += count[k] > old[k];
                        }
                    }
                    if (cfg.plan_shortlist && !(c.path.size() < chosen_path.size() ||
                        (cfg.plan_shortlist == 1 && repeated) ||
                        (cfg.plan_shortlist == 3 && c.path.size() == chosen_path.size()))) {
                        f2_plan_skipped++;
                        continue;
                    }
                    // Cheap deletion may collapse a nominally distinct family to the incumbent's
                    // exact path. Give the full-search slot to a different path in this mode.
                    if (cfg.plan_distinct && c.path == chosen_path && c.state.order == incumbent.order &&
                        c.state.top_d == incumbent.top_d && same_fillers(c.state.fillers, incumbent.fillers)) {
                        f2_plan_skipped++;
                        continue;
                    }
                    // Cache identity includes the raw path and filler priority, not just final order.
                    const CachedPlan* cached = find_cached_plan(c);
                    if ((cached && (cached->complete || cfg.plan_skip_edited)) || c.cost > baseline_value + cfg.plan_gap) {
                        f2_plan_skipped++;
                        continue;
                    }
                    if (attempted == cfg.plan_limit) break;
                    attempted++;
                    auto path = cached ? cached->edited.path : c.path;
                    OP_TAG(auto tags = cached ? cached->edited.tags : c.tags;)
                    if (cached) {
                        restore(cached->edited.state);
                        f2_plan_reused++;
                    } else {
                        restore(c.state);
                        canonicalize();
                        path = post_optimize(st0, std::move(path), u OP_TAG(, tags), false);
                    }
                    [[maybe_unused]] const double edited_value = plan_cost(path.size());
                    path = polish_ejects(st0, std::move(path), u OP_TAG(, tags), cfg.plan_ejects);
                    ns_plan_calls++;
                    const double value = plan_cost(path.size());
                    const bool won = value < incumbent_value - 1e-9;
#ifdef LOCAL_BENCH
                    if (cfg.plan_trace) {
                        heavy_log += "#f2plan " + std::to_string(request_counter - 1) + ' ' + std::to_string(plan_rank)
                            + ' ' + std::to_string(bool(cached)) + ' ' + std::to_string(c.path.size())
                            + ' ' + std::to_string(path.size()) + ' ' + trace_value(c.cost - baseline_value)
                            + ' ' + trace_value(edited_value - baseline_value) + ' ' + trace_value(baseline_value - value)
                            + ' ' + std::to_string(won) + ' ' + std::to_string(baseline_path.size())
                            + ' ' + std::to_string(repeated) + ' ' + std::to_string(added) + '\n';
                    }
#endif
                    if (won) {
                        f2_plan_wins++;
                        incumbent_value = value;
                        incumbent = save();
                        chosen_path = std::move(path);
                        OP_TAG(best_tags = std::move(tags);)
                        winning_operator = 4;
                    }
                    if (won && cfg.plan_stop) break;
                }
                restore(incumbent);
            }
            for (int round = 1; round <= cfg.rounds; round++) {
                F3_DIAG(f3_stage = 4; f3_round = round;)
                ns_rounds++;
                const auto parent_path = chosen_path;
                const double parent_value = plan_cost(chosen_path.size());
                const int neutral_before = chosen_path.size();
                neutral_candidates.clear();
                neutral_collect = true;
                chosen_path = post_optimize(st0, std::move(chosen_path), u OP_TAG(, best_tags), true);
                neutral_collect = false;
                neutral_direct_saved += neutral_before - int(chosen_path.size());
                const int escape_before = chosen_path.size();
                auto incumbent = save();
                double incumbent_value = plan_cost(chosen_path.size());
                if (incumbent_value < parent_value - 1e-9) {
                    winning_operator = last_post_operator;
                    winning_round = round;
                    winning_escape = false;
                }
                auto proposals = std::move(neutral_candidates);
                neutral_candidates.clear();
                neutral_total += proposals.size();
                bool neutral_better = false;
                [[maybe_unused]] int rank = 0;
                if (neutral_depth)
                    for (auto& c : proposals) {
                        CF_SCOPE(neutral_edits);
                        rank++;
                        F3_DIAG(f3_stage = 4 + rank;)
#ifdef LOCAL_BENCH
                        int repeats = 0, dead = 0, removed = 0, added = 0;
                        if (cfg.predict) {
                            std::array<int, K> count{}, old_count{};
                            std::array<bool, K> visible{};
                            u64 covered = 0;
                            for (int k : c.state.order) {
                                visible[k] = bool(paper[k].opaque & ~covered);
                                covered |= paper[k].opaque;
                            }
                            for (auto [k, d] : parent_path) old_count[k]++;
                            for (auto [k, d] : c.path) {
                                repeats += count[k]++ > 0;
                                dead += !visible[k];
                            }
                            for (int k = 0; k < K; k++) {
                                removed += std::max(0, old_count[k] - count[k]);
                                added += std::max(0, count[k] - old_count[k]);
                            }
                        }
#endif
                        restore(c.state);
                        auto path = c.path;
                        OP_TAG(auto tags = c.tags;)
                        if (neutral_depth >= 2)
                            path = post_optimize(st0, std::move(path), u OP_TAG(, tags), false, cfg.delete_only);
                        for (int it = 0; it < cfg.short_rounds; it++) {
                            const auto before = eject_accepts;
                            path = post_optimize(st0, std::move(path), u OP_TAG(, tags), true);
                            if (eject_accepts == before) break;
                            path = post_optimize(st0, std::move(path), u OP_TAG(, tags), false);
                        }
                        const double value = plan_cost(path.size());
                        const bool better = value < incumbent_value - 1e-9;
#ifdef LOCAL_BENCH
                        if (cfg.predict) {
                            heavy_log += "#heavycand " + std::to_string(request_counter - 1) + ' ' + std::to_string(round)
                                + ' ' + operator_name(c.origin) + ' ' + std::to_string(rank)
                                + ' ' + std::to_string(parent_path.size()) + ' ' + std::to_string(c.path.size())
                                + ' ' + trace_value(c.value - parent_value) + ' ' + std::to_string(repeats)
                                + ' ' + std::to_string(dead) + ' ' + std::to_string(removed) + ' ' + std::to_string(added)
                                + ' ' + std::to_string(path.size()) + ' ' + trace_value(c.value - value)
                                + ' ' + trace_value(parent_value - value) + ' ' + std::to_string(better) + ' ' + std::to_string(c.hides) + '\n';
                        }
#endif
                        if (better) {
                            incumbent_value = value;
                            incumbent = save();
                            chosen_path = std::move(path);
                            OP_TAG(best_tags = std::move(tags);)
                            neutral_better = true;
                            winning_operator = c.origin;
                            winning_round = round;
                            winning_escape = true;
                        }
                    }
                restore(incumbent);
                neutral_accepted += neutral_better;
                neutral_escape_saved += escape_before - int(chosen_path.size());
                if (cfg.refine_best && incumbent_value < parent_value - 1e-9) {
                    // Spend a full shortening pass on the incumbent that actually changed, rather
                    // than on several near-best states. A one-to-one rewrite can unlock an eject.
                    const int old_length = chosen_path.size();
                    const double old_value = incumbent_value;
                    for (int it = 0; it < cfg.refine_best; it++) {
                        f2_refine_calls++;
                        const auto before = eject_accepts;
                        chosen_path = post_optimize(st0, std::move(chosen_path), u OP_TAG(, best_tags), false);
                        chosen_path = post_optimize(st0, std::move(chosen_path), u OP_TAG(, best_tags), true);
                        if (eject_accepts == before) break;
                    }
                    incumbent_value = plan_cost(chosen_path.size());
                    f2_refine_saved += old_length - int(chosen_path.size());
                    if (incumbent_value < old_value - 1e-9) winning_escape = true;
                }
                if (incumbent_value >= parent_value - 1e-9 || parent_value - incumbent_value < cfg.repeat_min) break;
            }
            // The value-weighted joint plan can lose before ejection. Reuse its paid
            // edit pass, but do not repeat a plan already ejected as the main winner.
            // A whole neutral search here costs more than the extra improvements buy.
            if (weighted_ready) if (const auto* cached = find_cached_plan(weighted_raw);
                cached && !cached->complete && cached->edited.state.order != order) {
                const auto& c = cached->edited;
                const double value = plan_cost(chosen_path.size());
                if (c.cost <= value + .5) {
                    if (finish_weighted_plan(st0, c, u, value, chosen_path OP_TAG(, best_tags))) {
                        winning_operator = 4; winning_round = 0; winning_escape = false;
                    }
                }
            }
            if (chosen_path != baseline_path) {
                ns_changed++;
                ns_saved += int(baseline_path.size()) - int(chosen_path.size());
#ifdef LOCAL_BENCH
                if (cfg.trace) {
                    GenericSplit final_split;
                    split_generic(final_split);
                    heavy_log += "#heavy " + std::to_string(request_counter - 1) + ' ' + std::to_string(u)
                        + ' ' + operator_name(winning_operator) + (winning_escape ? ".escape" : ".direct")
                        + ' ' + std::to_string(winning_round) + ' ' + trace_value(baseline_value)
                        + ' ' + trace_value(plan_cost(chosen_path.size())) + ' ' + trace_value(baseline_filler)
                        + ' ' + trace_value(baseline_next) + ' ' + trace_value(filler_charge(final_split))
                        + ' ' + trace_value(kEndWeight * adaptive_next_cost(final_split))
                        + ' ' + trace_path(baseline_path, baseline_tags) + ' ' + trace_path(chosen_path, best_tags) + '\n';
                }
#endif
            }
        }
        post_secondary_saved += original_length - int(chosen_path.size());
        OP_TAG(op_tags = std::move(best_tags);)  // the labels of the moves returned
        return chosen_path;
    }
};

#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC pop_options
#endif
// ==== Emergency design ====

// Emergency design (no feasible design found): one white and one black sheet per window; moving the
// visible sheet of a window to the bottom flips it, so any request takes at most 64 moves.
int emergency_design(const std::vector<u64>& A, int R) {
    std::string output;
    for (int k = 0; k < K; k++) {
        std::string row(N, '.');
        if (k < 128) row[k % 64] = k < 64 ? '0' : '1';
        output += row + '\n';
    }
    std::cout << output << std::flush;
#ifdef LOCAL_BENCH
    // the analysis output (AGENTS.md): paper k < 64 is white on window k, 64 <= k < 128 black on
    // window k - 64, the rest blank; every move flips one window
    std::string labels = "@paper role =", windows = "@paper window =";
    for (int k = 0; k < K; k++) {
        labels += k < 64 ? " white" : k < 128 ? " black" : " blank";
        windows += k < 128 ? ' ' + std::to_string(k % 64) : std::string(" -");
    }
    std::cerr << labels << '\n' << windows << '\n';
    labels.clear();
#endif
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
#ifdef LOCAL_BENCH
        const int flips = __builtin_popcountll(different);
        labels += "@ops " + std::to_string(r) + " =" +
                  (flips == 0 ? "" : flips == 1 ? " flip" : " flip*" + std::to_string(flips)) + '\n';
#endif
        current = A[u];
        std::cout << output << std::flush;
    }
#ifdef LOCAL_BENCH
    std::cerr << labels;
#endif
    std::cerr << "total_moves = " << total << "\nemergency_design = 1\n";
    return 0;
}

#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC push_options
#pragma GCC optimize("O3")
#endif
// ==== Handle perforation ====

// Perforation of the column heads (after the papers are printed, before the requests). A column head
// (per column and color: the most frequent paper there, the largest filler utility on ties; chosen
// once) may get a hole on a printed handle h_c of a shallower column c (its own handle stays). Its
// targets then have a hole there too (more hole cost: hole_cost, the hcost of the handles with the
// reset demand 2 demands[c]), but as a filler the head no longer shows a wrong color there, so it can
// cover the holes of other targets from a lower level. profit: the expected saving of the heads as
// fillers, an interval DP per target over kSamples samples of the head colors (from their
// probabilities). A change is kept when hole_cost - weight * profit decreases; a cheap screen
// (separate_profit: the heads' utilities weighted by the probabilities of their colors) rejects most
// changes before the DP. All the handle sets here are by handle index.
template<int Capacity>
struct Perforation {
    // All interval gains are multiples of 1/5: repaired handles cost 5,
    // placement/return 8, and a donor dig 5. Store DP values in these units.
    static constexpr int kSamples = 8;
    static constexpr int kFirst = kCapPaper + 1;  // the first column paper
    // The DP of one target and one sample of the head colors: forward[c] / backward[c] are the best
    // gains of intervals within h_0..h_{c-1} / h_c..h_{H-1}, avoid[c] the best gain without an
    // interval ending at c (the head of column c not used), value the best gain.
    struct QueryCache {
        std::array<int16_t, Capacity + 1> forward{}, backward{};
        std::array<int16_t, Capacity> avoid{};
        int16_t value = 0;
    };
    struct Edges {
        std::array<std::array<int16_t, Capacity + 1>, Capacity> value;
        std::array<u64, Capacity> starts{}, ends{};
        auto& operator[](int c) { return value[c]; }
        const auto& operator[](int c) const { return value[c]; }
    };  // Only starts[c] entries are initialized; ends[lo] is the transpose.
    Solver& s;
    int H;
    std::vector<u64> opacity, allowed, colors, target;      // per paper (opaque, printed, black); per target
    std::vector<int> frequency, columns;                    // per paper: its targets, its column
    std::vector<std::vector<int>> owners;                   // per paper: its targets
    std::vector<std::array<int, 2>> counts, max_frequency;  // per handle: holes of each color; per column
    std::vector<int> demands;                               // per column: its targets
    std::vector<std::array<double, 2>> probability;         // per handle: the head shows each color
    std::vector<std::vector<double>> gains, bad;            // gains[k][u]: gain(u, k); bad[u][j]: h_j wrong for u
    std::vector<double> utility;                            // per paper: its gains summed over the targets
    std::vector<std::array<int, 2>> heads;                  // per column and color (best_heads, chosen once)
    std::vector<int> donors;  // fixed heads, in the original paper-index order
    std::vector<u64> samples, cache_opacity;                // head colors per target and sample; opacity of cache
    std::array<bool, P> cache_dirty{};
    std::array<uint32_t,P> dirty_samples{};
    int cache_sum=0;
    long long cache_rows = 0, cache_skips = 0;
    std::vector<QueryCache> cache;                          // per target and sample
    int trials = 0, accepted = 0;
    double last_owner_raw = 0, last_owner_corrected = 0;
    bool last_profit_possible = true;
    int owner_bound_checks = 0, owner_bound_skips = 0;
    double accepted_owner_raw = 0, accepted_owner_corrected = 0, accepted_donor = 0;

    double hole_cost = 0, profit = 0;

    explicit Perforation(Solver& solver)
        : s(solver),
          H(s.H),
          opacity(s.h_opq),
          allowed(s.h_opq),
          colors(s.h_blk),
          target(P),
          frequency(K),
          columns(s.col_of),
          owners(K),
          counts(H),
          max_frequency(H),
          demands(H),
          probability(H),
          gains(K, std::vector<double>(P)),
          bad(P, std::vector<double>(H)),
          utility(K) {
        assert(H <= Capacity);
        for (int u = 0; u < P; u++) {
            int k = s.ded[u];
            owners[k].push_back(u);
            frequency[k]++;
            demands[columns[k]]++;
            target[u] = s.handle_bits(s.A[u]);
            for (int c = 0; c < H; c++)
                if (!(opacity[k] >> c & 1)) counts[c][target[u] >> c & 1]++;
        }
        for (int k = kFirst; k < K; k++) {
            int& m = max_frequency[columns[k]][colors[k] >> columns[k] & 1];
            m = std::max(m, frequency[k]);
        }
        rebuild();
    }
    // hcost of handle c (as Design::hcost, the reset demand 2 demands[c])
    double cost(int c) const {
        return Design::hole_cost_of(counts[c][0], counts[c][1], 2 * demands[c]);
    }
    // The filler gain of paper k for target u (as Design::filler_gain, the wrong-color probabilities
    // of the heads bad[u]).
    double gain(int u, int k) const {
        int c = columns[k];
        u64 mask = opacity[k] & ~opacity[s.ded[u]];
        u64 wrong = mask & (colors[k] ^ target[u]);
        int level = wrong ? 64 - __builtin_clzll(wrong) : 0;
        if (level >= c) return 0;
        u64 cover = mask & low_bits(c) & ~low_bits(level);
        return Design::covered_gain(cover, [&](int j) { return bad[u][j]; });
    }
    double separate_profit() const {
        double sum = 0;
        for (int c = 0; c < H; c++)
            for (int b = 0; b < 2; b++) sum += probability[c][b] * utility[heads[c][b]];
        return sum;
    }
    std::vector<std::array<int, 2>> best_heads() const {
        std::vector<std::array<int, 2>> best(H, std::array<int, 2>{-1, -1});
        for (int k = kFirst; k < K; k++) {
            int c = columns[k], b = colors[k] >> c & 1;
            if (frequency[k] == max_frequency[c][b] && (best[c][b] < 0 || utility[k] > utility[best[c][b]]))
                best[c][b] = k;
        }
        return best;
    }
    // edge[lo]: the best gain of a head of column c as a filler for target u on the handles [lo, c],
    // with the head colors `color` (bit j: the color shown at h_j): the wrong holes of u it covers less
    // 1.6 moves, plus one dig when its color is not the one shown at h_c. Returns the mask
    // of feasible starts; the other entries are not read.
    struct Geometry {
        std::array<u64, 2> cover{};
        std::array<int, 2> lo{};
    };
    Geometry geometry_for(int u,int c) const {
        Geometry g;
        const int own=s.ded[u];
        if(c==columns[own]) { g.lo.fill(H+1); return g; }
        const u64 holes=low_bits(H)&~opacity[own];
        for(int b=0;b<2;++b) {
            const int k=heads[c][b];
            const u64 mask=opacity[k]&holes;
            const u64 wrong=mask&(colors[k]^target[u]);
            g.lo[b]=wrong?64-__builtin_clzll(wrong):0;
            g.cover[b]=mask&~low_bits(g.lo[b]);
        }
        return g;
    }
    std::array<Geometry,Capacity> all_geometry(int u) const {
        std::array<Geometry,Capacity> out;
        for(int c=0;c<H;++c)out[c]=geometry_for(u,c);
        return out;
    }
    // Integer geometry is constant across samples. The two donors, feasible
    // starts, and double operations below keep their original order.
    __attribute__((target("popcnt"))) u64 edge_column(int u, u64 color, int c,
            std::array<int16_t, Capacity + 1>& edge,const Geometry& geometry) const {
        u64 valid=0;
        const u64 bad_mask=color^target[u];
        for(int b=0;b<2;++b) {
            const int lo=geometry.lo[b];
            if(lo>c)continue;
            const u64 covered=bad_mask&geometry.cover[b];
            int number=5*__builtin_popcountll(covered);
            const int price=8+5*(b!=int(color>>c&1));
            for(int start=lo;start<=c && number>price;++start) {
                const u64 bit=u64(1)<<start;
                const int v=number-price;
                edge[start]=valid&bit?std::max<int>(edge[start],v):v;
                valid|=bit;
                number-=5*int(covered>>start&1);
            }
        }
        return valid;
    }
    Edges make_edges(int u,u64 color,const std::array<Geometry,Capacity>& geometry) const {
        Edges edges;
        for(int c=0;c<H;++c) {
            edges.starts[c]=edge_column(u,color,c,edges[c],geometry[c]);
            for(u64 z=edges.starts[c];z;z&=z-1)edges.ends[__builtin_ctzll(z)]|=u64(1)<<c;
        }
        return edges;
    }
    // The best set of disjoint intervals (weighted interval scheduling over the handles).
    std::array<int16_t, Capacity + 1> forward_values(const Edges& edges) const {
        std::array<int16_t, Capacity + 1> dp{};
        for (int c = 0; c < H; c++) {
            dp[c + 1] = dp[c];
            for (u64 z = edges.starts[c]; z; z &= z - 1) {
                const int lo = __builtin_ctzll(z);
                dp[c + 1] = std::max<int>(dp[c + 1], dp[lo] + edges[c][lo]);
            }
        }
        return dp;
    }
    int solve_edges(const Edges& edges) const { return forward_values(edges)[H]; }
    QueryCache make_cache(const Edges& edges) const {
        QueryCache q;
        q.forward = forward_values(edges);
        q.value = q.forward[H];
        for (int lo = H - 1; lo >= 0; lo--) {
            q.backward[lo] = q.backward[lo + 1];
            for (u64 z = edges.ends[lo]; z; z &= z - 1) {
                const int c = __builtin_ctzll(z);
                q.backward[lo] = std::max<int>(q.backward[lo], edges[c][lo] + q.backward[c + 1]);
            }
        }
        // A path which does not use a donor ending at c either takes the
        // zero-cost c -> c+1 step, or crosses it with an interval ending later.
        for (int c = 0; c < H; c++) q.avoid[c] = q.forward[c] + q.backward[c + 1];
        // Missing edges had value -1e9 and can never beat a nonnegative DP value.
        // Keep the same order of all contributing additions/maxima. Between two
        // present endpoints, best is constant, so the identical sum is reused.
        for (int lo = 0; lo < H; lo++) {
            int best = -10000;
            u64 z = edges.ends[lo] & ~low_bits(lo + 1);
            while (z) {
                const int end = 63 - __builtin_clzll(z);
                z ^= u64(1) << end;
                best = std::max(best, edges[end][lo] + q.backward[end + 1]);
                const int next = z ? 63 - __builtin_clzll(z) : lo;
                const int v = q.forward[lo] + best;
                for (int c = end - 1; c >= next; --c) q.avoid[c] = std::max<int>(q.avoid[c], v);
            }
        }
        return q;
    }
    void refresh_cache(bool all = true) {
        AF_SCOPE(perforation_cache, 1);
        cache_opacity = opacity;
        cache.resize(P * kSamples);
        for (int u = 0; u < P; u++) {
            // total_profit proved that unchanged signatures produce identical edges
            // for every sample. Head identities, colors and sample probabilities stay fixed.
            if (!all && !cache_dirty[u]) {
                cache_skips += kSamples;
                continue;
            }
            const auto geometry=all_geometry(u);
            for (int sample = 0; sample < kSamples; sample++) {
                int i = u * kSamples + sample;
                if(!all && !(dirty_samples[u]>>sample&1U)) { ++cache_skips;continue; }
                cache_sum-=cache[i].value;
                cache[i] = make_cache(make_edges(u, samples[i],geometry));
                cache_sum+=cache[i].value;
                ++cache_rows;
            }
        }
    }
    double cached_profit() const {
        return double(cache_sum) / (5 * kSamples);
    }
    // For an owner, changing one hole (or that head's color) changes only intervals
    // crossing that window. A disjoint solution has at most one such interval;
    // its prefix and suffix are unchanged and already cached.
    int changed_window_value(int u, u64 color, int h, const QueryCache& q, const std::array<Geometry,Capacity>& geometry) const {
        int value = q.forward[h] + q.backward[h + 1];
        for (int c = h; c < H; ++c) {
            std::array<int16_t, Capacity + 1> edge;
            const u64 valid = edge_column(u, color, c, edge,geometry[c]) & low_bits(h + 1);
            for (u64 z = valid; z; z &= z - 1) {
                const int lo = __builtin_ctzll(z);
                value = std::max(value, q.forward[lo] + edge[lo] + q.backward[c + 1]);
            }
        }
        return value;
    }
    // profit with the opacity of the head k (of column c) changed since the cache: the targets of k
    // are solved again; for the others only column c changes (nothing if what k covers for them, its
    // level and covered handles, is the same as in the cache).
    double total_profit(int k, double required_gain) {
        const int c = columns[k];
        const u64 changed = opacity[k] ^ cache_opacity[k];
        assert(__builtin_popcountll(changed) == 1);
        const int changed_handle = __builtin_ctzll(changed);
        last_owner_raw = last_owner_corrected = 0;
        last_profit_possible = true;
        std::vector<bool> same(P);
        cache_dirty.fill(true);  // the changed paper's own targets always need rebuilding
        dirty_samples.fill(~0U>>(32-kSamples));
        for (int u = 0; u < P; u++) {
            if (s.ded[u] == k) continue;
            u64 holes = low_bits(H) & ~opacity[s.ded[u]];
            auto signature = [&](int x, const std::vector<u64>& opq) {
                u64 mask = opq[x] & holes, wrong = mask & (colors[x] ^ target[u]);
                int lo = wrong ? 64 - __builtin_clzll(wrong) : 0;
                u64 cover = mask & ~low_bits(lo) & low_bits(c + 1);
                if (__builtin_popcountll(cover) < 2) return std::pair<u64, int>{0, 0};
                return std::pair<u64, int>{cover, lo};
            };
            same[u] = true;
            bool fixed_starts=true;
            for (int b = 0; b < 2; b++) {
                const auto before=signature(heads[c][b],cache_opacity);
                const auto after=signature(heads[c][b],opacity);
                same[u]=same[u]&&(before==after);
                fixed_starts=fixed_starts&&(before.second==after.second)&&!((before.first^after.first)&~changed);
            }
            cache_dirty[u] = !same[u];
            if(same[u])dirty_samples[u]=0;
            else if(fixed_starts) {
                // Only the changed handle's reward differs. Samples in which
                // that handle is already correct have exactly the same edges.
                uint32_t dirty=0;
                for(int sample=0;sample<kSamples;++sample)
                    if((samples[u*kSamples+sample]^target[u])&changed)dirty|=uint32_t(1)<<sample;
                dirty_samples[u]=dirty;
            }
        }
        int sum=cache_sum;
        for (int u = 0; u < P; ++u) {
          const auto geometry=geometry_for(u,c);
          for (int sample = 0; sample < kSamples; ++sample) {
            const int i = u * kSamples + sample;
            const auto& q = cache[i];
            if(s.ded[u]==k || !(dirty_samples[u]>>sample&1U))continue;
            {
                std::array<int16_t, Capacity + 1> edge;
                const u64 valid = edge_column(u, samples[i], c, edge,geometry);
                int value = q.avoid[c];
                for (u64 z = valid; z; z &= z - 1) {
                    const int lo = __builtin_ctzll(z);
                    value = std::max(value, q.forward[lo] + edge[lo] + q.backward[c + 1]);
                }
                sum+=value-q.value;
            }
          }
        }
        if (cache_opacity[k] & changed) {
            // Adding this hole can only restrict the old donor intervals. Its extra
            // reward is at most one repaired error, and disjoint intervals count it
            // at most once. Conditioning the color bounds the owner gain by P(error).
            double upper = double(sum) / (5 * kSamples) - profit;
            for (int u : owners[k]) upper += probability[changed_handle][(target[u] >> changed_handle & 1) ^ 1];
            ++owner_bound_checks;
            if (upper < required_gain - 1e-8) {
                ++owner_bound_skips;
                last_profit_possible = false;
                return profit;
            }
        }
        for (int u : owners[k]) {
          const auto new_geometry=all_geometry(u);
          const u64 saved_opacity=opacity[k];
          opacity[k]=cache_opacity[k];
          const auto old_geometry=all_geometry(u);
          opacity[k]=saved_opacity;
          for (int sample = 0; sample < kSamples; ++sample) {
            const int i = u * kSamples + sample;
            const auto& q = cache[i];
            const int value = changed_window_value(u, samples[i], changed_handle, q,new_geometry);
            const int direct = value - q.value;
            const int flip_new = changed_window_value(u, samples[i] ^ changed, changed_handle, q,new_geometry);
            int flip_old;
            if (cache_opacity[k] & changed) {
                // Before a hole is added, its window is covered by the target paper.
                // Changing the head color changes only this column's donor price.
                std::array<int16_t, Capacity + 1> old_edge;
                const u64 old_starts = edge_column(u, samples[i] ^ changed, changed_handle, old_edge,old_geometry[changed_handle]);
                flip_old = q.avoid[changed_handle];
                for (u64 bits = old_starts; bits; bits &= bits - 1) {
                    const int lo = __builtin_ctzll(bits);
                    flip_old = std::max(flip_old, q.forward[lo] + old_edge[lo] + q.backward[changed_handle+1]);
                }
            } else {
                // A restored hole can affect all donor intervals in the old state.
                flip_old = changed_window_value(u, samples[i] ^ changed, changed_handle, q,old_geometry);
            }
            const int b = int(samples[i] >> changed_handle & 1);
            last_owner_raw += direct;
            last_owner_corrected += probability[changed_handle][b] * direct +
                probability[changed_handle][b ^ 1] * (flip_new - flip_old);
            sum+=value-q.value;
          }
        }
        // Every DP value is an exact small integer, so only changed rows need
        // to contribute a difference to the cached total.
        last_owner_raw /= (5 * kSamples);
        last_owner_corrected /= (5 * kSamples);
        return double(sum) / (5 * kSamples);
    }
    // Everything from the current opacity (the heads chosen on the first call).
    void rebuild() {
        hole_cost = 0;
        for (int c = 0; c < H; c++) {
            hole_cost += cost(c);
            probability[c] = Design::head_probability(counts[c][0], counts[c][1], 2 * demands[c]);
            for (int u = 0; u < P; u++) bad[u][c] = probability[c][(target[u] >> c & 1) ^ 1];
        }
        std::fill(utility.begin(), utility.end(), 0);
        // A lower-frequency paper cannot be selected initially; afterwards the heads
        // are fixed, and only their utilities/gains are ever read by the search.
        for (int k = kFirst; k < K; k++) {
            const int c = columns[k], b = int(colors[k] >> c & 1);
            if (heads.empty() ? frequency[k] != max_frequency[c][b] : k != heads[c][b]) continue;
            for (int u = 0; u < P; u++) utility[k] += gains[k][u] = gain(u, k);
        }
        if (heads.empty()) heads = best_heads();
        donors.clear();
        for (int k = kFirst; k < K; k++)
            if (k == heads[columns[k]][colors[k] >> columns[k] & 1]) donors.push_back(k);
        std::mt19937_64 random(731000003 ^ deval_seed_salt());
        samples.assign(P * kSamples, 0);
        // A uniform draw in each stratum, independently shuffled for each target/column.
        for (int u = 0; u < P; ++u) for (int c = 0; c < H; ++c) {
            std::array<int, kSamples> strata;
            std::iota(strata.begin(), strata.end(), 0);
            std::shuffle(strata.begin(), strata.end(), random);
            for (int sample = 0; sample < kSamples; ++sample) {
                const double draw = (strata[sample] + (random() >> 11) * 0x1.0p-53) / kSamples;
                if (draw < probability[c][1]) samples[u * kSamples + sample] |= 1ULL << c;
            }
        }
        refresh_cache();
        profit = cached_profit();
    }
    // One pass over the printed handles h_c (c shallower than the column) of the heads in random
    // order: perforate (or restore) the handle when
    // that lowers hole_cost - weight * profit.
    void run(double weight) {
        AF_SCOPE(perforation, 1);
        std::mt19937_64 rng(0xc9a513a1ULL ^ deval_seed_salt());
        // The constructor already rebuilt this unchanged design, including the DP cache.
        std::vector<std::pair<int, int>> candidates;  // (head, handle)
        for (int k = kFirst; k < K; k++) {
            int c = columns[k], b = colors[k] >> c & 1;
            if (k != heads[c][b]) continue;
            for (u64 bits = allowed[k] & low_bits(c); bits; bits &= bits - 1)
                candidates.push_back({k, __builtin_ctzll(bits)});
        }
        std::shuffle(candidates.begin(), candidates.end(), rng);
        for (auto [k, c] : candidates) {
            trials++;
            const u64 bit = 1ULL << c;
            bool remove = opacity[k] & bit;
            auto old_utility = utility, old_row = gains[k];
            std::array<std::array<double, 2>, K> old_columns;  // gains of the other papers for k's targets
            for (int y : donors)
                if (y != k)
                    for (int q = 0; q < int(owners[k].size()); q++) {
                        int u = owners[k][q];
                        old_columns[y][q] = gains[y][u];
                        utility[y] -= gains[y][u];
                    }
            double old_cost = cost(c), old_separate = separate_profit();
            opacity[k] ^= bit;
            for (int u : owners[k]) counts[c][target[u] >> c & 1] += remove ? 1 : -1;
            const double delta = cost(c) - old_cost;
            utility[k] = 0;
            for (int u = 0; u < P; u++) utility[k] += gains[k][u] = gain(u, k);
            for (int y : donors)
                if (y != k)
                    for (int u : owners[k]) utility[y] += gains[y][u] = gain(u, y);
            const bool viable = delta - (separate_profit() - old_separate) < -1e-9;
            const double next = viable ? total_profit(k, weight > 0 ? delta / weight : 1e100) : profit;
            const double correction = last_owner_corrected - last_owner_raw;
            if (viable && last_profit_possible && delta - weight * (next - profit + correction) < -1e-9) {
                accepted_owner_raw += last_owner_raw;
                accepted_owner_corrected += last_owner_corrected;
                accepted_donor += next - profit - last_owner_raw;
                hole_cost += delta;
                profit = next;
                accepted++;
                refresh_cache(false);
                assert(std::abs(profit - cached_profit()) < 1e-7);
            } else {
                opacity[k] ^= bit;
                for (int u : owners[k]) counts[c][target[u] >> c & 1] += remove ? -1 : 1;
                utility = std::move(old_utility);
                gains[k] = std::move(old_row);
                for (int y : donors)
                    if (y != k)
                        for (int q = 0; q < int(owners[k].size()); q++) gains[y][owners[k][q]] = old_columns[y][q];
            }
        }
    }
    // The number of perforated handles.
    int holes() const {
        int answer = 0;
        for (int k = kFirst; k < K; k++) answer += __builtin_popcountll(allowed[k] & ~opacity[k]);
        return answer;
    }
    // Writes the perforated handles into the solver's papers.
    void install() {
        for (int k = kFirst; k < K; k++) {
            for (int c = 0; c < H; c++)
                if (!(opacity[k] >> c & 1)) s.paper[k].opaque &= ~(1ULL << s.handle[c]);
            s.paper[k].black &= s.paper[k].opaque;
            s.h_opq[k] = s.handle_bits(s.paper[k].opaque);
            s.h_blk[k] = s.handle_bits(s.paper[k].black);
        }
    }
};

// ==== Design state: what the requests need from the design (DesignState, make_solver) ====

// The result of the design. design_papers computes it and make_solver builds the solver of the
// requests from it; under LOCAL_BENCH, DesignStore can save it to a file and load it instead of
// designing (AGENTS.md, scripts/pahcer_run.py --save-design / --design-from). A change of the design
// whose result does not fit in these fields has to add them here, in make_solver and in DesignStore.
struct DesignState {
    bool emergency = false;                 // no design: emergency_design serves the requests
    int M = 0, G = 0, H = 0;                // generic sheets, generic windows, handles
    std::vector<int> permutation;           // original window of each internal window
    std::vector<u64> A;                     // the targets on the internal windows (with the cap)
    std::vector<std::pair<int, int>> edge;  // the comparator's pairs and colors (Comparator::rebuild)
    std::vector<int> polarity;
    std::vector<Paper> papers;  // the K papers (internal numbers; after the perforation in the result)
    std::vector<int> columns;   // column of each paper (-1: a generic sheet or the cap)
    std::vector<int> ded;       // paper of each target
    std::vector<int> handle;    // window of each handle h_c
};

// The solver of a design state (before the helper tables and the look-ahead, which main adds).
Solver make_solver(const DesignState& state) {
    Solver solver(state.A);
    solver.M = state.M;
    solver.H = state.H;
    solver.comparator.M = state.M;
    solver.comparator.G = state.G;
    solver.comparator.edge = state.edge;
    solver.comparator.polarity = state.polarity;
    solver.comparator.rebuild();
    solver.paper = state.papers;
    solver.col_of = state.columns;
    solver.ded = state.ded;
    solver.set_handles(state.handle);
    solver.gmask = low_bits(state.G);
    solver.hmask = kActiveWindows & ~solver.gmask;
    solver.h_opq.resize(K);
    solver.h_blk.resize(K);
    for (int x = 0; x < K; x++) {
        solver.h_opq[x] = solver.handle_bits(state.papers[x].opaque);
        solver.h_blk[x] = solver.handle_bits(state.papers[x].black);
    }
    std::iota(solver.order.begin(), solver.order.end(), 0);
    // Model the one initial legal cap move now; emit it before the first plan.
    std::rotate(solver.order.begin(), solver.order.begin() + kCapPaper, solver.order.begin() + kCapPaper + 1);
    return solver;
}

// ==== Initial column order ====

// Start each column in a low-cost state before any orders are observed.
// This changes only the order/numbering of papers within the same column.
void improve_initial_columns(DesignState& state) {
    const double begin=elapsed_sec();
    Solver probe=make_solver(state);
    probe.adaptive_weights.assign(K,0.);probe.adaptive_holes.assign(probe.H,{0.,0.});
    std::array<int,K> frequency{};
    for(int u=0;u<P;++u) {
        const int k=probe.ded[u];++frequency[k];probe.adaptive_weights[k]+=1.;
        for(int c=0;c<probe.H;++c)if(!(probe.h_opq[k]>>c&1))probe.adaptive_holes[c][probe.A[u]>>probe.handle[c]&1]+=1./P;
    }
    probe.add_filler_demand();
    
    std::array<int,K> destination;std::iota(destination.begin(),destination.end(),0);
    const auto original=state.papers;
    double gain=0;int changed=0;
    for(int c=0;c<probe.H;++c) {
        std::vector<int> slots;
        for(int k=0;k<K;++k)if(state.columns[k]==c)slots.push_back(k);
        std::vector<int> sequence;
                std::array<std::vector<int>,2> groups;
        for(int k:slots)groups[(probe.paper[k].black>>probe.handle[c])&1].push_back(k);
        for(auto& group:groups)std::stable_sort(group.begin(),group.end(),[&](int a,int b){return probe.adaptive_weights[a]>probe.adaptive_weights[b];});
        const int n0=groups[0].size(),n1=groups[1].size(),stride=n1+1;
        std::vector<double> dp((n0+1)*stride,1e100);std::vector<int> prev(dp.size());dp[0]=0;
        for(int i=0;i<=n0;++i)for(int j=0;j<=n1;++j)for(int color=0;color<2;++color) {
            int used=color?j:i;if(used>=int(groups[color].size()))continue;
            const int k=groups[color][used],to=(i+(color==0))*stride+j+(color==1);
            const double value=dp[i*stride+j]+probe.adaptive_weights[k]*(i+j)/P+(used==0?probe.adaptive_holes[c][color]*(i+j):0.);
            if(value<dp[to])dp[to]=value,prev[to]=color;
        }
        int i=n0,j=n1;
        while(i+j){int color=prev[i*stride+j];sequence.push_back(groups[color][color?--j:--i]);}
        std::reverse(sequence.begin(),sequence.end());
        std::array<bool,2> seen{};double old=0;
        for(int j=0;j<int(slots.size());++j){int k=slots[j],color=(probe.paper[k].black>>probe.handle[c])&1;old+=probe.adaptive_weights[k]*j/P;if(!seen[color])old+=probe.adaptive_holes[c][color]*j;seen[color]=true;}
        gain+=old-dp.back();

        for(int j=0;j<int(slots.size());++j) {
            const int old=sequence[j],to=slots[j];
            state.papers[to]=original[old];destination[old]=to;changed+=old!=to;
        }
    }
    for(int u=0;u<P;++u)state.ded[u]=destination[state.ded[u]];
    std::cerr<<"initial_order_changed = "<<changed<<"\ninitial_order_model_gain = "<<gain
             <<"\ninitial_order_sec = "<<elapsed_sec()-begin<<'\n';
}

// ==== V: design-only expected moves ====
// Design-only handle surrogate. Contents: State; Donors; Cover expectation.
// There is deliberately no Solver, stack, request sequence or operation emitter.

namespace deval {
using U64 = std::uint64_t;
constexpr int P=256,K=192,MaxH=63;
inline U64 low(int n) { return n==64 ? ~U64(0) : (U64(1)<<n)-1; }
inline int high(U64 x) { return int(std::bit_width(x)); }

// ==== State ====
struct State {
    int M=6,G=38,H=25;
    std::array<U64,P> target{};
    std::array<U64,K> opaque{},black{};
    std::array<int,K> col{};
    std::array<int,P> ded{};
    std::array<int,MaxH> handle{};
    std::array<std::array<int,2>,64> edge{};
    std::array<int,64> polarity{};
    std::array<U64,P> hb{};
    std::array<U64,K> op{},bl{};
    std::array<double,K> freq{};
    std::array<double,MaxH> nc{},nt{},n1{},p1{};
    std::array<std::array<double,2>,MaxH> xy{};

    U64 handles(U64 b) const {
        U64 z=0;
        for(int c=0;c<H;++c) z|=((b>>handle[c])&1)<<c;
        return z;
    }
    // Called after copying the public fields from the solver's DesignState.
    void prepare() {
        freq={};nc={};nt={};n1={};p1={};xy={};
        for(int k=0;k<K;++k) op[k]=handles(opaque[k]),bl[k]=handles(black[k]);
        for(int t=0;t<P;++t) {
            hb[t]=handles(target[t]);
            const int k=ded[t];
            ++freq[k];++nt[col[k]];
            for(int c=0;c<H;++c) if(!(op[k]>>c&1)) ++xy[c][hb[t]>>c&1];
        }
        for(int k=0;k<K;++k) if(col[k]>=0) {
            const int c=col[k],b=bl[k]>>c&1;
            ++nc[c];n1[c]+=b;p1[c]+=(freq[k]==2)*b;
        }
    }
    std::array<double,MaxH> probabilities(double strength) const {
        std::array<double,MaxH> p{};
        for(int c=0;c<H;++c) {
            const auto [x,y]=xy[c];const double r=strength*nt[c];
            p[c]=(y+r*(y>x))/std::max(1.,x+y+r);
        }
        return p;
    }
};

// ==== Donors ====
struct Donors {
    std::array<std::array<U64,K>,P> cover{};
    std::array<std::array<std::uint8_t,K>,P> start{};
    std::array<double,K> utility{};
    std::array<std::array<int,2>,MaxH> head{};
    explicit Donors(const State& s,const std::array<double,MaxH>& prob) {
        for(auto& a:head)a={-1,-1};
        for(int t=0;t<P;++t) {
            const int own=s.ded[t];
            for(int k=0;k<K;++k) {
                const int c=s.col[k];
                if(c<0||c==s.col[own])continue;
                const U64 shown=s.op[k]&~s.op[own];
                const int lo=high(shown&(s.bl[k]^s.hb[t]));
                if(lo>c)continue;
                const U64 cv=shown&~low(lo);
                cover[t][k]=cv;start[t][k]=std::uint8_t(lo);
                double p0=1,p1=0,e=0;
                for(U64 z=cv&low(c);z;z&=z-1) {
                    const int j=std::countr_zero(z);
                    const double p=(s.hb[t]>>j&1) ? 1-prob[j] : prob[j];
                    p1=p1*(1-p)+p0*p;p0*=1-p;e+=p;
                }
                utility[k]+=std::max(0.,e-(1-p0)-.6*(1-p0-p1));
            }
        }
        for(int k=0;k<K;++k) {
            const int c=s.col[k];if(c<0)continue;
            int& old=head[c][s.bl[k]>>c&1];
            if(old<0||s.freq[k]>s.freq[old]||(s.freq[k]==s.freq[old]&&utility[k]>utility[old]))old=k;
        }
    }
    double head_utility(const State& s,const std::array<double,MaxH>& p) const {
        double v=0;
        for(int c=0;c<s.H;++c)v+=(1-p[c])*utility[head[c][0]]+p[c]*utility[head[c][1]];
        return v/P;
    }
};

// ==== Cover expectation ====
struct CoverResult {
    // raw, total cost, residual fix, filler count, donor digs, covered handles,
    // interval length, squared residual fix. Rows are equally likely targets.
    std::array<std::array<double,8>,P> target{};
    std::array<std::array<double,2>,MaxH> flips{};
    std::array<double,8> mean() const {
        std::array<double,8> a{};
        for(const auto& row:target)for(int j=0;j<8;++j)a[j]+=row[j]/P;
        return a;
    }
};
// Samples are row-major Sobol uniforms, [nSample,H]. They are fixed design-independent
// quadrature points shipped with the evaluator; no random request stream is sampled.
__attribute__((target("popcnt"))) inline CoverResult expectation(const State& s,const Donors& d,
                              const std::array<double,MaxH>& prob,
                              const double* samples,int nSample,double price) {
    CoverResult ans;
    const U64 all=low(s.H);
    std::array<std::uint32_t,MaxH> threshold{};
    for(int c=0;c<s.H;++c)threshold[c]=std::uint32_t(std::clamp(prob[c],0.,1.)*1073741824.);
    static const auto shifts=[] {
        std::array<std::array<std::uint32_t,MaxH>,P> shifts{};
        for(int t=0;t<P;++t)for(int c=0;c<MaxH;++c) {
            std::uint32_t h=0x9e3779b9U*(1+t*MaxH+c);
            h^=h>>16;h*=0x7feb352dU;h^=h>>15;h*=0x846ca68bU;h^=h>>16;
            shifts[t][c]=h&0x3fffffffU;
        }
        return shifts;
    }();
    std::vector<std::array<std::uint32_t,MaxH>> draws(nSample);
    for(int i=0;i<nSample;++i)for(int c=0;c<s.H;++c)
        draws[i][c]=std::uint32_t(samples[i*s.H+c]*1073741824.);
    // A target's donor intervals are reused for every quadrature point; this
    // order keeps them in L1 while preserving each target's summation order.
    for(int t=0;t<P;++t) {
        const int own=s.ded[t];
        const U64 holes=all&~s.op[own];
        double exact_raw=0;
        for(U64 z=holes;z;z&=z-1) {
            const int c=std::countr_zero(z),b=s.hb[t]>>c&1;
            const double mismatch=b?1-prob[c]:prob[c];
            exact_raw+=mismatch;ans.flips[c][b]+=mismatch;
        }
        for(int sample=0;sample<nSample;++sample) {
            U64 colors=0;
            for(int c=0;c<s.H;++c)
                colors|=U64((draws[sample][c]^shifts[t][c])<threshold[c])<<c;
            const U64 wrong=(colors^s.hb[t])&holes;
            const int raw=std::popcount(wrong);
            std::array<double,MaxH+1> dp{};
            std::array<int,MaxH+1> prev{},picked{};
            std::array<int,MaxH+1> pickdepth{};
            picked.fill(-1);
            for(int c=0;c<s.H;++c) {
                dp[c+1]=dp[c];
                if(c==s.col[own])continue;
                for(int b=0;b<2;++b) {
                    const int k=d.head[c][b];if(k<0)continue;
                    const U64 cov=d.cover[t][k];if(!cov)continue;
                    const int depth=(b!=int(colors>>c&1));
                    int saving=std::popcount(cov&wrong);
                    for(int lo=d.start[t][k];lo<=c;++lo) {
                        const double gain=saving-price-depth;
                        if(gain>0&&dp[lo]+gain>dp[c+1]+1.e-12) {
                            dp[c+1]=dp[lo]+gain;prev[c+1]=lo;picked[c+1]=k;pickdepth[c+1]=depth;
                        }
                        saving-=int(((cov&wrong)>>lo)&1);
                        if(saving<=price+depth)break;
                    }
                }
            }
            U64 covered=0;int nf=0,digs=0,length=0;
            for(int j=s.H;j>0;) {
                const int k=picked[j];
                if(k<0){--j;continue;}
                const int lo=prev[j];
                covered|=d.cover[t][k]&~low(lo);
                ++nf;digs+=pickdepth[j];length+=j-lo;j=lo;
            }
            const U64 left=wrong&~covered;
            const int fixes=std::popcount(left);
            const std::array<double,8> row{exact_raw,exact_raw-dp[s.H],exact_raw-(raw-fixes),double(nf),double(digs),
                double(std::popcount(covered)),double(length),double(fixes*fixes)};
            for(int j=0;j<8;++j)ans.target[t][j]+=row[j]/nSample;
            for(U64 z=wrong&covered;z;z&=z-1) {
                const int c=std::countr_zero(z);
                ans.flips[c][s.hb[t]>>c&1]-=1./nSample;
            }
        }
    }
    for(auto& f:ans.flips)for(double& x:f)x=std::max(0.,x);
    return ans;
}
} // namespace deval
namespace deval {
// ==== V: compact fixed quadrature ====
inline constexpr std::uint32_t kBasis25[6][25]={
    {1054442932,931871753,610629168,17084755,782689727,264802305,1068414870,299387375,640330417,430326169,805249303,353388788,291402371,660991922,260525808,510646295,682520416,792658013,460740408,850305590,251880979,398885384,226919837,568152832,1026181147},
    {725082623,612647233,994863144,610413970,1003611358,910265516,718079099,794596137,893315293,950565919,706560329,629542173,1062370503,823787191,964348517,738763022,971050276,748107452,894550042,799559366,552416432,588491447,831666450,668734108,675718922},
    {945544255,520005792,426979871,439370228,703897733,719771331,472598575,999708199,642567607,639410624,918824418,923601343,393946688,476847545,613475796,482441712,787634531,447409807,580066816,381556646,475032227,862056646,394539813,278669526,503394851},
    {420102838,370400537,837010087,904859124,465573963,268225990,340014719,805872934,725809513,937235558,1007784132,488852103,484662033,942551295,304910681,945081300,512378686,941362498,718534826,237149672,148143361,240003615,472777208,1049119070,979457865},
    {228837614,423373976,767971080,343193864,1034348865,448959133,308008040,901875076,793726652,426224529,644638220,72676896,619886596,603863886,595900982,1043900753,675211281,810957828,744500293,305439193,243376919,714778121,218582831,976131312,355582080},
    {81983120,305154027,355766481,749223052,283766814,555536421,701478734,1033689851,426182845,234202112,79151713,512507126,935211813,1002812231,417491667,33829508,745658536,700794023,569359590,53502706,754463706,1050133623,880280738,550113010,710043642},
};
inline constexpr std::uint32_t kBasis31[6][31]={
    {1054442932,931871753,610629168,17084755,782689727,264802305,1068414870,299387375,640330417,430326169,805249303,353388788,291402371,660991922,260525808,510646295,682520416,792658013,460740408,850305590,251880979,398885384,226919837,568152832,1026181147,592531127,430433738,663316317,210257080,330458719,113307707},
    {771260356,554717307,857344516,948659387,880359318,811805482,859905743,925158005,800733016,706676714,659575397,562251615,882848209,645901785,1051892076,573064089,943933740,634236725,879756943,705933728,994913315,619359729,613303463,923051816,833209023,740070940,948176126,1001477401,540695571,539920158,578417395},
    {922161146,531245065,483166154,470842626,757604698,699773142,449973236,630557142,859008454,925396998,822704311,859992008,516526092,453471869,607745280,274627607,748050678,448504807,617054265,528869820,337291472,947663286,286050656,386545054,273451251,837823302,415408320,720228013,361796847,868722330,409007372},
    {311471526,351749739,955296223,734231824,268833483,255029656,286105551,707348907,951999065,658839976,1013199104,416457180,282510421,730611654,321148484,1026749703,445763460,922964154,754854551,145193488,220151926,193628099,461405753,705845170,676713047,1039743824,269590624,922681486,262303944,142392339,300587812},
    {217201583,453715456,563331612,355353125,834293824,480552826,385161766,744579371,1070837562,434824318,790201122,87918631,548274443,932107192,556699034,975852645,733611124,965673240,671813995,422082138,141084129,715752028,231984085,799357989,477110300,101244176,1054914817,149362306,715468135,1006764646,336380418},
    {113091640,303168203,287585361,873407282,444336058,557058375,837669814,557235907,331493244,258539530,133208175,453983625,965527935,694997482,479900894,51159326,779495959,558967292,669989296,35175574,806155953,837885418,536946868,813939847,848952989,237936930,200519868,770594161,141564182,396941078,330970794},
};
inline constexpr std::uint32_t kBasis35[6][35]={
    {1054442932,931871753,610629168,17084755,782689727,264802305,1068414870,299387375,640330417,430326169,805249303,353388788,291402371,660991922,260525808,510646295,682520416,792658013,460740408,850305590,251880979,398885384,226919837,568152832,1026181147,592531127,430433738,663316317,210257080,330458719,113307707,442573128,716678798,854010711,298297473},
    {1065876552,822413236,832610374,683035581,663976292,640856748,873590005,843884371,1000568202,569409185,889529944,942962165,703798545,670752151,724145856,579090846,607425225,1020982101,654338298,557521422,886227505,782950169,686049917,810185348,983313403,566845894,675303406,991252880,598065464,585658848,664743735,668809203,760641868,917324051,676894741},
    {795934631,446857367,482901155,285724706,847386030,995822958,488685388,693673316,590797921,847708268,546802544,606534786,479789254,276228062,865554444,367509873,962957155,465190524,1014498193,408853445,296389895,935533409,281843209,279140832,348688187,1057141864,472517640,786229977,420040444,1014655406,370102478,269552892,340206488,792499822,882434392},
    {420141665,393504445,1057660413,876073217,409021621,188160390,282721525,580164276,736470422,743545484,776146954,355081678,359417173,683932779,306537541,992956534,287111240,674565037,937601395,175612173,166987620,145259578,403170197,690322214,626861431,932427022,286918157,938477805,170331270,265011510,514437697,242653006,829401690,588643871,550825438},
    {253999858,481452034,624697793,451158619,598017026,441087907,391225961,638980788,758838187,380520423,1033384487,131629684,987762879,1022180228,921229738,1051018842,1067468613,552604034,816912059,512189856,244080152,580396489,222084438,777241175,453116352,76402945,772509718,175204390,777180785,874522209,416030762,805681392,117971420,667160559,738564261},
    {98190210,320842931,373507344,653407023,398490540,893424761,920468329,795601973,337835977,244318380,84510463,385079449,583833596,718085802,531320298,46797288,996319600,957521865,1056152322,59492713,953117458,1024581295,772967244,876333172,966781404,183112236,255527875,719673108,251761005,445477222,497248940,365759130,80529435,540198318,303801158},
};
inline const double* samples_for(int H) {
    static std::array<double,32*35> samples{};
    static int cachedH=0;
    if(cachedH!=H) {
        assert(H==25||H==31||H==35);
        const std::uint32_t* basis=H==25?&kBasis25[0][0]:H==31?&kBasis31[0][0]:&kBasis35[0][0];
        for(int i=0;i<32;++i) for(int j=0;j<H;++j) {
            auto v=basis[j];
            for(int b=0;b<5;++b)if(i>>b&1)v^=basis[(b+1)*H+j];
            samples[i*H+j]=double(v)/1073741824.;
        }
        cachedH=H;
    }
    return samples.data();
}
} // namespace deval
// Contents: Exact generic costs; Static design features; Filler features.

namespace deval {
using FeatureMap=std::map<std::string,double>;

// ==== Exact generic costs ====
// A design-independent initialization shared by every candidate. In an integrated
// solver this table can share the existing exact generic-layer cost infrastructure.
struct GenericTable {
    GenericTable() { (void)PosetSums::get(); }
    __attribute__((target("popcnt"))) std::pair<double,int> cost(const State& s,int t) const {
        if(s.M!=6)throw std::runtime_error("expected six generic papers");
        std::array<unsigned,6> reach{};
        U64 holes=(~s.opaque[s.ded[t]])&low(s.G);
        for(U64 z=holes;z;z&=z-1) {
            const int j=std::countr_zero(z);
            auto [a,b]=s.edge[j];
            if(int(s.target[t]>>j&1)!=s.polarity[j])std::swap(a,b);
            reach[a]|=1U<<b;
        }
        for(int k=0;k<6;++k)for(int a=0;a<6;++a)if(reach[a]>>k&1)reach[a]|=reach[k];
        U64 relation=0;int nr=0;
        for(int a=0;a<6;++a){relation|=U64(reach[a])<<(8*a);nr+=std::popcount(reach[a]);}
        return {PosetSums::get().one_of(relation)/720.,nr};
    }
};

// ==== Static design features ====
__attribute__((target("popcnt"))) inline FeatureMap static_features(const State& s,const GenericTable& gt) {
    FeatureMap out;
    std::array<double,MaxH> colcost{},dem{},minor{},balance{},unitminor{},pairminor{},np{},depth{};
    for(int c=0;c<s.H;++c) {
        np[c]=s.nt[c]-s.nc[c];
        colcost[c]=(s.nc[c]*(s.nc[c]-1)+np[c]*(np[c]-1))/2
            +std::max(0.,np[c]-1)*(s.p1[c]==0||s.p1[c]==np[c]);
        dem[c]=s.xy[c][0]+s.xy[c][1];minor[c]=std::min(s.xy[c][0],s.xy[c][1]);
        balance[c]=dem[c]>0?minor[c]/dem[c]:0.;
        unitminor[c]=std::min(s.n1[c],s.nc[c]-s.n1[c]);
        pairminor[c]=std::min(s.p1[c],np[c]-s.p1[c]);
        depth[c]=double(c)/std::max(1,s.H-1);
        out["col"]+=colcost[c]/P;
    }
    out["G"]=s.G;out["H"]=s.H;out["holes"]=0;out["extra_holes"]=0;out["gc"]=0;
    const std::array<std::string,8> tn{"generic","gen_holes","gen_relations","holes","early_holes","minor_requests","hole_bal","hole_bal2"};
    std::array<std::array<double,3>,8> moments{};
    for(int t=0;t<P;++t) {
        const auto [gc,nrel]=gt.cost(s,t);
        const int k=s.ded[t],cown=s.col[k];
        const U64 holes=low(s.H)&~s.op[k];
        std::array<double,8> a{gc,double(std::popcount(~s.opaque[k]&low(s.G))),double(nrel),
            double(std::popcount(holes)),double(std::popcount(holes&low(cown))),0,0,0};
        for(U64 z=holes;z;z&=z-1) {
            const int c=std::countr_zero(z);
            a[5]+=(int(s.hb[t]>>c&1)!=int(s.xy[c][1]>s.xy[c][0]));
            a[6]+=balance[c];a[7]+=balance[c]*balance[c];
        }
        out["gc"]+=gc/P;out["holes"]+=a[3]/P;out["extra_holes"]+=a[4]/P;
        for(int j=0;j<8;++j) {
            double v=a[j];
            for(int power=1;power<=3;++power){moments[j][power-1]+=v/P;v*=a[j];}
        }
    }
    for(int j=0;j<8;++j)for(int power=1;power<=3;++power)
        out["t_"+tn[j]+"_p"+std::to_string(power)]=moments[j][power-1];
    const std::array<double,6> strengths{0,.5,1,2,4,8};
    const std::array<std::string,6> sn{"0","0.5","1","2","4","8"};
    for(int si=0;si<6;++si) {
        const auto p=s.probabilities(strengths[si]);
        const std::string key="h"+sn[si];
        for(int power=0;power<4;++power)out[key+"_d"+std::to_string(power)]=0;
        for(int band:{1,2,3,5})out[key+"_last"+std::to_string(band)]=0;
        out[key+"_balance"]=0;out[key+"_balance2"]=0;
        for(int c=0;c<s.H;++c) {
            const double h=(s.xy[c][0]*p[c]+s.xy[c][1]*(1-p[c]))/P;
            double v=h;
            for(int power=0;power<4;++power){out[key+"_d"+std::to_string(power)]+=v;v*=depth[c];}
            for(int band:{1,2,3,5})if(c>=s.H-band)out[key+"_last"+std::to_string(band)]+=h;
            out[key+"_balance"]+=h*balance[c];out[key+"_balance2"]+=h*balance[c]*balance[c];
        }
    }
    const std::array<std::string,7> cn{"dem","minor","balance","unit_minor","pair_minor","nc","np"};
    const std::array<const std::array<double,MaxH>*,7> ca{&dem,&minor,&balance,&unitminor,&pairminor,&s.nc,&np};
    for(int j=0;j<7;++j)for(int power=1;power<=3;++power) {
        double sum=0;
        for(int c=0;c<s.H;++c) {
            double x=(*ca[j])[c];if(j<2)x/=P;
            double v=1;for(int k=0;k<power;++k)v*=x;
            sum+=v;
        }
        out[cn[j]+"_p"+std::to_string(power)]=sum;
    }
    return out;
}

// ==== Filler features ====
inline void add_cover_summary(FeatureMap& out,const std::string& key,
                              const CoverResult& r,bool moments) {
    const std::array<std::string,8> names{"raw","cost","fix","fill","fdig","covered","length","fix2"};
    const auto mean=r.mean();
    for(int j=0;j<8;++j)out[key+"_"+names[j]]=mean[j];
    if(moments)for(int power:{2,3}) {
        double v=0;
        for(const auto& t:r.target)v+=std::pow(t[1],power)/P;
        out[key+"_moment"+std::to_string(power)]=v;
    }
}
inline void add_filler_features(FeatureMap& out,const State& s,double strength,
                                const std::vector<double>& prices,int nSamples) {
    const auto p=s.probabilities(strength);
    const Donors donors(s,p);
    const std::string skey="f_s"+std::to_string(int(strength));
    out[skey+"_headutility"]=donors.head_utility(s,p);
    for(double price:prices) {
        std::ostringstream name;name<<price;
        const std::string key=skey+"_p"+name.str();
        const auto r=expectation(s,donors,p,samples_for(s.H),nSamples,price);
        add_cover_summary(out,key,r,true);
    }
}

// Two-state mean-field update. Conditional rates, rather than surviving demand
// counts, account for the fact that a filler is selected depending on current
// head colours. Representatives remain fixed during this cheap approximation.
inline void add_stationary_features(FeatureMap& out,const State& s,int nSamples,int steps) {
    auto p=s.probabilities(2.);
    const Donors donors(s,p);
    out["f_s2_headutility"]=donors.head_utility(s,p);
    auto r=expectation(s,donors,p,samples_for(s.H),nSamples,1.6);
    add_cover_summary(out,"f_s2_p1.6",r,true);
    for(int step=1;step<=steps;++step) {
        for(int c=0;c<s.H;++c) {
            const double a=r.flips[c][1]/std::max(1.e-4,1-p[c]);
            const double b=r.flips[c][0]/std::max(1.e-4,p[c]);
            const double reset=2*s.nt[c];
            const double next=(a+reset*(s.xy[c][1]>s.xy[c][0]))/std::max(1.,a+b+reset);
            p[c]=.5*p[c]+.5*next;
        }
        r=expectation(s,donors,p,samples_for(s.H),nSamples,1.6);
        const std::string key="m_s2_it"+std::to_string(step);
        add_cover_summary(out,key,r,false);
        out[key+"_lastfix"]=(r.flips[s.H-1][0]+r.flips[s.H-1][1])/P;
        double tail=0;
        for(int c=std::max(0,s.H-5);c<s.H;++c)tail+=r.flips[c][0]+r.flips[c][1];
        out[key+"_tailfix"]=tail/P;
    }
}
} // namespace deval
// Frozen fitted V; generated by emit_cpp.py. Lower means fewer expected moves.
// Contents: Coefficients; Prediction; Adapter from the solver's DesignState.
namespace deval {
// ==== Coefficients ====
struct ModelTerm { const char* name; double coefficient; };
inline constexpr double kIntercept=2.6592913045031414;
inline constexpr std::array<ModelTerm,142> kTerms{{
    {"col",0.51911298817896012},
    {"gc",0.26629169530626212},
    {"G",0},
    {"H",0},
    {"holes",0.0022908973381129674},
    {"extra_holes",0.0098543628202360546},
    {"h0_d0",-0.070615864666553105},
    {"h0_d1",0.049300488541686047},
    {"h0_d2",-0.0086021693408773955},
    {"h0_d3",0.19909868661921512},
    {"h0_last1",0.11246688276510788},
    {"h0_last2",0.16368762183185814},
    {"h0_last3",-0.27691168740665095},
    {"h0_last5",0.055955765905122273},
    {"h0_balance",0.11681589592319511},
    {"h0_balance2",0.083908746266352557},
    {"h0.5_d0",-0.060309852862733167},
    {"h0.5_d1",0.044361656915058938},
    {"h0.5_d2",-0.034657674810439791},
    {"h0.5_d3",0.14373632413036685},
    {"h0.5_last1",0.0097438403233363006},
    {"h0.5_last2",0.11581397371460421},
    {"h0.5_last3",-0.16694114808529015},
    {"h0.5_last5",0.029436836413913679},
    {"h0.5_balance",0.11428500833131629},
    {"h0.5_balance2",0.074435950671184484},
    {"h1_d0",-0.052166455397066575},
    {"h1_d1",0.039199627531708442},
    {"h1_d2",-0.056557742727951096},
    {"h1_d3",0.098385807688413165},
    {"h1_last1",-0.060848683161509771},
    {"h1_last2",0.077921074875098043},
    {"h1_last3",-0.080656881803724212},
    {"h1_last5",0.0091209844488996071},
    {"h1_balance",0.11144719344264976},
    {"h1_balance2",0.065411622031337935},
    {"h2_d0",-0.040685043907293522},
    {"h2_d1",0.029052459312867818},
    {"h2_d2",-0.090574401555212833},
    {"h2_d3",0.030023958669050124},
    {"h2_last1",-0.1479124780869257},
    {"h2_last2",0.02228071621206458},
    {"h2_last3",0.043474119777755428},
    {"h2_last5",-0.01860071076801437},
    {"h2_balance",0.10520219389189109},
    {"h2_balance2",0.04857161952504787},
    {"h4_d0",-0.0292120736879731},
    {"h4_d1",0.011789148191226693},
    {"h4_d2",-0.13250570099692899},
    {"h4_d3",-0.051117041039591714},
    {"h4_last1",-0.22629849742049568},
    {"h4_last2",-0.044144157153740982},
    {"h4_last3",0.1834255463257583},
    {"h4_last5",-0.045035607306516935},
    {"h4_balance",0.092186440555845198},
    {"h4_balance2",0.019312163509391463},
    {"h8_d0",-0.023982872907833668},
    {"h8_d1",-0.0097270354201893436},
    {"h8_d2",-0.16636607673438189},
    {"h8_d3",-0.11602387130581465},
    {"h8_last1",-0.27309788775047622},
    {"h8_last2",-0.10565819826947878},
    {"h8_last3",0.2956272312933671},
    {"h8_last5",-0.055265435915099227},
    {"h8_balance",0.06959149529425733},
    {"h8_balance2",-0.024665098377644631},
    {"dem_p1",0.0022908973381225136},
    {"dem_p2",0.063843663166879311},
    {"dem_p3",-0.026407092510486157},
    {"minor_p1",-0.033033226702483709},
    {"minor_p2",0.00093434389718316394},
    {"minor_p3",-0.15809310563056883},
    {"balance_p1",0.00097946400136795543},
    {"balance_p2",0.014770106988164727},
    {"balance_p3",-0.063895499928807706},
    {"unit_minor_p1",0.0017315242588189365},
    {"unit_minor_p2",-0.00021796561869747805},
    {"unit_minor_p3",2.2125213994186997e-05},
    {"pair_minor_p1",-0.0041385326851156269},
    {"pair_minor_p2",0.00041525788820505528},
    {"pair_minor_p3",0.00047997760337295411},
    {"nc_p1",0},
    {"nc_p2",0.00092024589876214065},
    {"nc_p3",-1.2746962026717906e-05},
    {"np_p1",0},
    {"np_p2",0.00091408709666423213},
    {"np_p3",-5.3432997965032504e-05},
    {"t_generic_p1",0.26629169530621299},
    {"t_generic_p2",0.062537381309616516},
    {"t_generic_p3",0.015767541973285715},
    {"t_gen_holes_p1",0.05036719289217826},
    {"t_gen_holes_p2",-0.00056227161584972824},
    {"t_gen_holes_p3",-3.6290407734441208e-05},
    {"t_gen_relations_p1",0.0169685593533636},
    {"t_gen_relations_p2",-0.00041078091193232097},
    {"t_gen_relations_p3",-0.00010449382776667072},
    {"t_holes_p1",0.0022908973381324501},
    {"t_holes_p2",-0.0016454270066399975},
    {"t_holes_p3",9.6255676569607338e-05},
    {"t_early_holes_p1",0.0098543628202323891},
    {"t_early_holes_p2",0.0013378535265670473},
    {"t_early_holes_p3",-0.00014719579751983392},
    {"t_minor_requests_p1",-0.033033226702470442},
    {"t_minor_requests_p2",-0.0077914122922586081},
    {"t_minor_requests_p3",6.2433828852649265e-05},
    {"t_hole_bal_p1",-0.033033226702557698},
    {"t_hole_bal_p2",-0.0063739511492997688},
    {"t_hole_bal_p3",8.8047090829033916e-05},
    {"t_hole_bal2_p1",-0.025725727795410911},
    {"t_hole_bal2_p2",-0.017932615974768574},
    {"t_hole_bal2_p3",-0.0032131413073254165},
    {"f_s2_headutility",-0.070119687270759942},
    {"f_s2_p1.6_raw",-0.040685043907355029},
    {"f_s2_p1.6_cost",-0.10350357444858947},
    {"f_s2_p1.6_fix",-0.12312953755170605},
    {"f_s2_p1.6_fill",0.40354568264743668},
    {"f_s2_p1.6_fdig",0.035605199865600894},
    {"f_s2_p1.6_covered",-0.016887730215888463},
    {"f_s2_p1.6_length",-0.025320700491777419},
    {"f_s2_p1.6_fix2",-0.00080179645237437257},
    {"f_s2_p1.6_moment2",-0.0035111430036715049},
    {"f_s2_p1.6_moment3",0.0011811965550397718},
    {"m_s2_it1_raw",0.035067666850584205},
    {"m_s2_it1_cost",0.12250377820992842},
    {"m_s2_it1_fix",0.089053543522435968},
    {"m_s2_it1_fill",-0.11961324769102072},
    {"m_s2_it1_fdig",-0.06012527079579686},
    {"m_s2_it1_covered",-0.018724521338072692},
    {"m_s2_it1_length",-0.01178430223168531},
    {"m_s2_it1_fix2",0.0020852051646461944},
    {"m_s2_it1_lastfix",-0.18265101969386224},
    {"m_s2_it1_tailfix",-0.15700191801822924},
    {"m_s2_it2_raw",0.22317415232272048},
    {"m_s2_it2_cost",0.38418924167764812},
    {"m_s2_it2_fix",0.18158441352689741},
    {"m_s2_it2_fill",0.1098536039479996},
    {"m_s2_it2_fdig",0.39640938444602875},
    {"m_s2_it2_covered",0.062141751174649866},
    {"m_s2_it2_length",0.01444291387885824},
    {"m_s2_it2_fix2",0.0064075429863520821},
    {"m_s2_it2_lastfix",0.59346117133390486},
    {"m_s2_it2_tailfix",0.20261508375187909},
}};
// ==== Prediction ====
// Construct once and share its design-independent table across candidates.
class DesignValue {
    GenericTable generic_;
public:
    double operator()(State state,int nSamples=16) const {
        state.prepare();
        auto features=static_features(state,generic_);
        add_stationary_features(features,state,nSamples,2);
        double value=kIntercept;
        for(const auto& term:kTerms)value+=term.coefficient*features.at(term.name);
        return value;
    }
    // ==== Adapter from the solver's DesignState ====
    template<class DesignState> double from_design(const DesignState& d,int nSamples=16) const {
        State s;s.M=d.M;s.G=d.G;s.H=d.H;
        for(int t=0;t<P;++t)s.target[t]=d.A[t],s.ded[t]=d.ded[t];
        for(int k=0;k<K;++k) {
            s.opaque[k]=d.papers[k].opaque;s.black[k]=d.papers[k].black;s.col[k]=d.columns[k];
        }
        for(int c=0;c<s.H;++c)s.handle[c]=d.handle[c];
        for(int j=0;j<s.G;++j) {
            s.edge[j]={d.edge[j].first,d.edge[j].second};s.polarity[j]=d.polarity[j];
        }
        return (*this)(s,nSamples);
    }
    template<class DesignState> FeatureMap features_from_design(const DesignState& d,int nSamples=16) const {
        State s;s.M=d.M;s.G=d.G;s.H=d.H;
        for(int t=0;t<P;++t)s.target[t]=d.A[t],s.ded[t]=d.ded[t];
        for(int k=0;k<K;++k) {
            s.opaque[k]=d.papers[k].opaque;s.black[k]=d.papers[k].black;s.col[k]=d.columns[k];
        }
        for(int c=0;c<s.H;++c)s.handle[c]=d.handle[c];
        for(int j=0;j<s.G;++j) {
            s.edge[j]={d.edge[j].first,d.edge[j].second};s.polarity[j]=d.polarity[j];
        }
        s.prepare(); auto features=static_features(s,generic_); add_stationary_features(features,s,nSamples,2); return features;
    }
    template<class DesignState> FeatureMap head_features_from_design(const DesignState& d,int nSamples=16) const {
        State s;s.M=d.M;s.G=d.G;s.H=d.H;
        for(int t=0;t<P;++t)s.target[t]=d.A[t],s.ded[t]=d.ded[t];
        for(int k=0;k<K;++k) {
            s.opaque[k]=d.papers[k].opaque;s.black[k]=d.papers[k].black;s.col[k]=d.columns[k];
        }
        for(int c=0;c<s.H;++c)s.handle[c]=d.handle[c];
        for(int j=0;j<s.G;++j) {
            s.edge[j]={d.edge[j].first,d.edge[j].second};s.polarity[j]=d.polarity[j];
        }
        s.prepare(); auto features=static_features(s,generic_); const auto p=s.probabilities(2.); const Donors donors(s,p); features["f_s2_headutility"]=donors.head_utility(s,p); return features;
    }
};
} // namespace deval

// A proposal exchanges complete single/pair target units between physical slots.


// ==== Design iteration counts ====

// Design budgets: window annealing, its matching climb, product/column annealing, filler climb,
// and head-aware reassignments. Perforation makes one pass; helper tables are completed.
// ITER_SCALE scales the four iteration budgets below; stage environment overrides take precedence.
#ifndef ITER_SCALE
#define ITER_SCALE 1.0
#endif
constexpr int kMapIters = int(450000 * ITER_SCALE), kMapRetryIters = int(160000 * ITER_SCALE);
constexpr int kGoptSteps = int(133000 * ITER_SCALE), kAnnealIters = int(11175000 * ITER_SCALE);
constexpr int kClimbIters = int(50000 * ITER_SCALE), kMatchIterations = 2;

// The design from the targets as read (window assignment, design annealing, printing of the papers
// and their perforation; its statistics go to stderr). `emergency` if no feasible design was found.
DesignState design_papers(const std::vector<u64>& originalA) {
    // ==== design_papers: window assignment and the initial design ====

    deval_salt=std::max(0,env_int("DEVAL_SALT"));
    const u64 first_salt=deval_salt;
    const int candidates=4;
    const int shared=2;
    const double branch_scale=0.25;
    DesignState state;
    std::vector<u64> A;
    const int map_env = env_int("MAP_ITERS"), anneal_env = env_int("ANNEAL_ITERS");
    const int climb_env = 50000, gopt_env = env_int("GOPT_STEPS");
    const int anneal_iters = anneal_env ? anneal_env : kAnnealIters;
    const int climb_iters = climb_env ? climb_env : kClimbIters;
    std::vector<int> permutation(64);  // original window of each internal window
    int M = 6, G = 38;
    Comparator comp;
    std::mt19937_64 rng(779879);
    std::unique_ptr<Design> des;
    int map_total = 0;
    // A design may fail (no matching of compatible pairs, or no column with both colors): retry with
    // fewer generic windows (32, then 28, without a new assignment the third time), then fall back.
    for (int attempt = 0;; attempt++) {
        A = originalA;
        for (u64& a : A) a &= kActiveWindows;
        std::iota(permutation.begin(), permutation.end(), 0);
        comp.init(M, G, rng);
        if (attempt < 2) {

            const int map_iters = map_env ? map_env : attempt == 0 ? kMapIters : kMapRetryIters;
            // the greedy matching climb on the first assignment only
            const int gsteps = attempt ? 0 : gopt_env ? std::max(0, gopt_env) : kGoptSteps;
            auto ws = assign_windows(A, M, G, comp.edge, comp.polarity, permutation, 1e300, map_iters, gsteps, 0.0);
            map_total += ws.iterations;
            if (!attempt)
                std::cerr << "gobj_before = " << ws.gobj_before << "\ngobj_after = " << ws.gobj_after
                          << "\ngopt_steps = " << ws.climb_steps << '\n';
        }
        comp.rebuild();
        des = std::make_unique<Design>(A, M, G);
        // gcost: the exact mean number of moves of the generic layer from a uniform order, averaged over
        // the two targets of the pair (the legal distance is asymmetric; b reverses a's relations): PosetSums::both_of / 1440
        auto estimate = [&](u64 a, u64 b) {
            const auto reach = comp.closure(a, a ^ b);
            u64 r = 0;
            for (int s = 0; s < M; s++) r |= u64(reach[s]) << (8 * s);
            return PosetSums::get().both_of(r) / 1440.0;
        };

        if (des->initialize([&](u64 a, u64 b) { return comp.compatible(a, b); }, estimate, []() { return false; }))
            break;
        if (attempt >= 2) {
            state.emergency = true;
            return state;
        }
        G = attempt == 0 ? 32 : 28;
    }
    std::cerr << "map_iters = " << map_total << "\nmap_end_sec = " << elapsed_sec() << '\n';

    // ==== design_papers: finish each candidate and select by V ====
    DesignState warm_state;
    auto finish = [&](Design* des,bool raw=false,int extra=0) {
        DesignState state;
        auto A=des->A;
    if(!raw && extra!=2) {
    if (climb_iters > 0) des->filler_climb(1e300, extra?25000:climb_iters);
    std::cerr << "climb_iters = " << des->climb_iters << "\nclimb_accepted = " << des->climb_accepted
              << "\nclimb_evaluated = " << des->climb_evaluated << "\nclimb_cached = " << des->climb_cached
              << "\nproxy_before = " << des->proxy_before / P << "\nproxy_after = " << des->proxy_after / P
              << "\nclimb_end_sec = " << elapsed_sec() << '\n';
    const auto match = rematch_probability(*des, extra?1:2, 1.0, 2.0);
    std::cerr << "match_iterations = " << match.iterations << "\nmatch_cycles = " << match.accepted_cycles
              << "\nmatch_changed = " << match.changed << "\nmatch_decrease = " << match.decrease
              << "\nmatch_sec = " << match.seconds << "\nmatch_end_sec = " << elapsed_sec() << '\n';
    }
    // Restore the cap bit only for the physical papers and online targets.
    // Assignment never moves index 63, and all design calculations used 63 bits.
    for (int u = 0; u < P; ++u) A[u] |= originalA[u] & kCapBit;
    double model_col = 0.0, model_hole = 0.0, model_gc = 0.0;
    for (int c = 0; c < des->H; ++c) model_col += des->colcost(c), model_hole += des->hcost(c);
    for (const auto& u : des->unit) model_gc += des->gc(u);
    std::cerr << "cap_window = " << kCapWindow << "\nmodel_cost = " << (model_col + model_hole + model_gc) / P
              << "\nmodel_col = " << model_col / P << "\nmodel_hole = " << model_hole / P
              << "\nmodel_gc = " << model_gc / P << '\n';

    // ==== design_papers: printing the papers ====

    // Papers: six generic sheets, the cap, then the columns 0, 1, ... (colors alternate,
    // the more numerous first; singles before pairs within a color).
    std::vector<Paper> papers(K);
    std::vector<int> columns(K, -1), ded(P, -1);
    for (int i = 0; i < M; i++) papers[i] = {comp.opq[i], comp.black[i]};
    papers[kCapPaper] = {kCapBit, kCapBit};
    u64 opaque = low_bits(G) | kCapBit;
    int next = M + 1;
    // Start each column with its handle-demand majority color, then the other color.
    // Demand comes from targets in shallower columns; a pair differing here asks for both colors.
    std::vector<std::array<int, 2>> demand(des->H, {0, 0});
    for (const auto& u : des->unit)
        for (int c = u.c + 1; c < des->H; c++) {
            demand[c][des->hb[u.a] >> c & 1]++;
            if (u.b >= 0) demand[c][des->hb[u.b] >> c & 1]++;
        }
    for (int c = 0; c < des->H; c++) {
        opaque |= 1ULL << des->handle[c];
        std::array<std::vector<int>, 2> members;
        for (int x = 0; x < des->U; x++)
            if (des->unit[x].c == c) members[des->color(des->unit[x], c)].push_back(x);
        for (auto& group : members)
            std::stable_sort(group.begin(), group.end(),
                             [&](int x, int y) { return des->weight(des->unit[x]) < des->weight(des->unit[y]); });
        const int majority = demand[c][1] > demand[c][0];
        for (int step = 0; !members[0].empty() || !members[1].empty(); step++) {
            int color = members[1].size() > members[0].size();
            if (step < 2 && !members[majority ^ step].empty()) color = majority ^ step;
            int x = members[color].back();
            members[color].pop_back();
            const auto& u = des->unit[x];
            u64 mask = opaque;
            if (u.b >= 0) mask &= ~(A[u.a] ^ A[u.b]);
            mask |= kCapBit;
            u64 black = A[u.a] & mask;
            if (u.b >= 0 && ((A[u.a] ^ A[u.b]) & kCapBit)) black &= ~kCapBit;
            papers[next] = {mask, black};
            columns[next] = c;
            ded[u.a] = next;
            if (u.b >= 0) ded[u.b] = next;
            next++;
        }
    }
    if (next != K || std::find(ded.begin(), ded.end(), -1) != ded.end()) {
        state.emergency = true;
        return state;
    }
    state.M = M;
    state.G = G;
    state.H = des->H;
    state.permutation = permutation;
    state.A = A;
    state.edge = comp.edge;
    state.polarity = comp.polarity;
    state.papers = papers;
    state.columns = columns;
    state.ded = ded;
    state.handle = des->handle;
    if(raw)return state;
    // ==== design_papers: handle perforation ====

    // The solver of the papers as printed, for the perforation only (main builds the one of the requests).
    Solver solver = make_solver(state);
    const auto natural_opacity=solver.h_opq;
    if(extra==2 && !warm_state.papers.empty()) {
        for(const auto& unit:des->unit) {
            const int k=state.ded[unit.a],old=warm_state.ded[unit.a];
            // Keep the natural physical mask/color as the restoration source.
            // Only the initial opacity of the perforation model has the old holes.
            solver.h_opq[k]=solver.handle_bits(warm_state.papers[old].opaque);
        }
    }
    // Sacrifice a few printed handles when that makes a common donor
    // repair several other products more efficiently. Its own handle stays.
    const double perforation_start = elapsed_sec();
    // Only the H live entries are read. Specialize the common 25-handle layout;
    // the full capacity also supports the retry designs and experimental maps.
    auto perforate = [&]<int Capacity>() {
        Perforation<Capacity> perforation(solver);
        if(extra==2)perforation.allowed=natural_opacity;
        perforation.run(0.7);
        std::cerr << "perf_owner_bound_checks = " << perforation.owner_bound_checks
                  << "\nperf_owner_bound_skips = " << perforation.owner_bound_skips << '\n';
        std::cerr << "perf_owner_raw = " << perforation.accepted_owner_raw / P
                  << "\nperf_owner_conditioned = " << perforation.accepted_owner_corrected / P
                  << "\nperf_donor_gain = " << perforation.accepted_donor / P << '\n';
        std::cerr << "perf_cache_rows = " << perforation.cache_rows
                  << "\nperf_cache_skips = " << perforation.cache_skips << '\n';
        perforation.install();
        state.papers = solver.paper;
        std::cerr << "perforation_holes = " << perforation.holes() << "\nperforation_trials = " << perforation.trials
                  << "\nperforation_accepts = " << perforation.accepted
                  << "\nperforation_sec = " << elapsed_sec() - perforation_start
                  << "\nperforation_end_sec = " << elapsed_sec() << '\n';
    };
    if (solver.H <= 25) perforate.template operator()<25>();
    else perforate.template operator()<64>();

    // ==== design_papers: perforation-aware reassignment ====

    // Extra holes stay attached to physical paper slots. The Hungarian step can
    // change the targets, so their colors, natural pair holes and head probabilities
    // must all be evaluated again. Columns and each slot's own handle stay fixed.
    const int late_iterations = int(env_real("ARGON_D2_LATE_ITERS", 1));
    if (late_iterations > 0) {
        const double late_start = elapsed_sec();
        std::vector<u64> extra(des->U);
        std::vector<int> slot_paper(des->U);
        for (int x = 0; x < des->U; ++x) {
            const auto& u = des->unit[x];
            const int k = slot_paper[x] = state.ded[u.a];
            extra[x] = low_bits(des->H) & ~des->holes(u) & ~solver.h_opq[k];
            assert(!(extra[x] & ~low_bits(u.c)));
        }
        const auto late = rematch_probability(*des, late_iterations, 1.05, 2.0, &extra);
        int remaining = 0;
        for (int x = 0; x < des->U; ++x) {
            const auto& u = des->unit[x];
            const int k = slot_paper[x];
            assert(state.columns[k] == u.c);
            u64 mask = low_bits(G) | kCapBit;
            for (int c = 0; c <= u.c; ++c) mask |= u64(1) << des->handle[c];
            if (u.b >= 0) mask &= ~(A[u.a] ^ A[u.b]);
            mask |= kCapBit;
            for (u64 z = extra[x]; z; z &= z - 1) mask &= ~(u64(1) << des->handle[__builtin_ctzll(z)]);
            u64 black = A[u.a] & mask;
            if (u.b >= 0 && ((A[u.a] ^ A[u.b]) & kCapBit)) black &= ~kCapBit;
            state.papers[k] = {mask, black};
            state.ded[u.a] = k;
            if (u.b >= 0) state.ded[u.b] = k;
            remaining += __builtin_popcountll(extra[x] & ~des->holes(u));
        }
        std::cerr << "d2_rematch_iterations = " << late.iterations
                  << "\nd2_rematch_cycles = " << late.accepted_cycles
                  << "\nd2_rematch_changed = " << late.changed
                  << "\nd2_rematch_decrease = " << late.decrease
                  << "\nd2_model_initial = " << late.initial_model
                  << "\nd2_model_final = " << late.final_model
                  << "\nd2_filler_initial = " << late.initial_filler
                  << "\nd2_filler_final = " << late.final_filler
                  << "\nd2_extra_remaining = " << remaining
                  << "\nd2_rematch_sec = " << elapsed_sec() - late_start
                  << "\nd2_rematch_end_sec = " << elapsed_sec() << '\n';
    }
    return state;
    };
    deval::DesignValue value;
    double best=1e100,first=0,anneal_sec=0,finish_sec=0,eval_sec=0;
    int chosen=-1,finished=0,total_iters=0;
    std::string chosen_log;
    // Share the first segments. Every branch starts from this same
    // best state, with a deterministic salt for its remaining random moves.
    const double prefix_begin=elapsed_sec();
    des->anneal(1e300,anneal_iters,0,shared);
    anneal_sec+=elapsed_sec()-prefix_begin;
    total_iters+=des->anneal_iters;
    const auto prefix=std::make_unique<Design>(*des);
    std::unique_ptr<Design> best_assignment;
    auto complete=[&](int id,int extra) {
        std::ostringstream log;auto* old=std::cerr.rdbuf(log.rdbuf());
        Design::kClimbProxyWeight=.5;
        std::cerr<<"colswap_tried = "<<des->colswap_tried<<"\ncolswap_accepted = "<<des->colswap_accepted
                 <<"\nreplace_tried = "<<des->replace_tried<<"\nreplace_accepted = "<<des->replace_accepted<<'\n';
        double begin=elapsed_sec();auto candidate=finish(des.get(),false,extra);
        finish_sec+=elapsed_sec()-begin;std::cerr.rdbuf(old);
        if(candidate.emergency)return 1e100;
        begin=elapsed_sec();const double v=value.from_design(candidate);eval_sec+=elapsed_sec()-begin;
        if(env_int("DEVAL_DUMP_FEATURES"))std::cerr<<"@deval_final "<<id<<' '<<v<<'\n';
        if(!finished)first=v;
        ++finished;
        if(v<best){best=v;chosen=id;state=std::move(candidate);chosen_log=log.str();best_assignment=std::make_unique<Design>(*des);}
        return v;
    };
    for(int i=0;i<candidates;++i) {
        deval_salt=first_salt+i;
        des=std::make_unique<Design>(*prefix);
        if(i)des->rng.x^=u64(i)*0x9E3779B97F4A7C15ULL;
        double begin=elapsed_sec();des->anneal_reheat=i?2:1.;des->reheat_start=shared/4.;
        des->anneal(1e300,int(anneal_iters*branch_scale),shared,4);
        anneal_sec+=elapsed_sec()-begin;total_iters+=des->anneal_iters;
        complete(i,0);
    }
    // Repeat the full native finishing from the best completed assignment.
    // The original four candidates remain eligible throughout the search.
    for(int j=0;j<4;++j) {
        const int repeat=1+j/2,id=candidates+j;
        deval_salt=first_salt+id;
        if(!best_assignment)break;
        des=std::make_unique<Design>(*best_assignment);
        des->rng.x^=u64(repeat)*0x9E3779B97F4A7C15ULL;
        const bool warm=j%2==1;
        if(warm)warm_state=state;
        complete(id,warm?2:1);
    }
    if(!finished)state.emergency=true;
    if(finished)improve_initial_columns(state);
    std::cerr << chosen_log;
    std::cerr << "anneal_iters = " << total_iters << "\nanneal_end_sec = " << elapsed_sec()
              << "\ndv_candidates = " << finished << "\ndv_chosen = " << chosen
              << "\ndv_first = " << first << "\ndv_best = " << best
              << "\ndv_anneal_sec = " << anneal_sec << "\ndv_finish_sec = " << finish_sec
              << "\ndv_eval_sec = " << eval_sec << '\n';
    return state;
}

#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC pop_options
#endif
#ifdef LOCAL_BENCH
// ==== Saving and loading the design state (LOCAL_BENCH: DesignStore) ====

// LOCAL_BENCH stores designs by FNV-1a hash of the barcodes, shared by alternate order sequences.
// DESIGN_SAVE_DIR saves the state, captured stderr, helper readiness, and raw clock ticks.
// DESIGN_LOAD_DIR loads it, replays stderr verbatim, and restores the clock offset after rebuilding
// the helper tables. Loading fails if the file is missing or inconsistent with the input.
struct DesignStore {
    static constexpr int kVersion = 1;
    std::string save_path, load_path;  // empty: not saving / not loading
    std::ostringstream captured;       // the stderr of design_papers (saving)
    std::streambuf* real_cerr = nullptr;
    bool helpers_ready = false;  // loaded: the saved run completed the helper tables
    long long end_ticks = 0;     // loaded: Clock ticks from the start to the end of the design

    [[noreturn]] static void fail(const std::string& message) {
        std::cerr << "design_store_error: " << message << std::endl;
        std::exit(1);
    }
    static u64 barcode_hash(const std::vector<u64>& a) {  // FNV-1a of the barcodes' bytes (bit j: window j)
        u64 h = 0xcbf29ce484222325ULL;
        for (u64 x : a)
            for (int byte = 0; byte < 8; byte++) h = (h ^ (x >> (8 * byte) & 255)) * 0x100000001b3ULL;
        return h;
    }
    explicit DesignStore(const std::vector<u64>& originalA) {
        char name[32];
        std::snprintf(name, sizeof name, "%016llx.txt", (unsigned long long)barcode_hash(originalA));
        const char* save = std::getenv("DESIGN_SAVE_DIR");
        const char* load = std::getenv("DESIGN_LOAD_DIR");
        if (save && *save) save_path = std::string(save) + "/" + name;
        if (load && *load) load_path = std::string(load) + "/" + name;
        if (!save_path.empty() && !load_path.empty()) fail("DESIGN_SAVE_DIR and DESIGN_LOAD_DIR are both set");
    }
    bool loading() const { return !load_path.empty(); }

    // Saving: the stderr of design_papers goes to `captured` (and to the real stderr at the end).
    void begin_capture() {
        if (!save_path.empty()) real_cerr = std::cerr.rdbuf(captured.rdbuf());
    }
    void end_capture() {
        if (!real_cerr) return;
        std::cerr.rdbuf(real_cerr);
        real_cerr = nullptr;
        std::cerr << captured.str();
    }

    // The end of the design (after the helper tables, before the papers are printed).
    void design_end(const DesignState& state, bool ready) {
        if (loading()) {
            kStartTime = Clock::now() - Clock::duration(end_ticks);
            return;
        }
        if (save_path.empty()) return;
        const long long ticks = (Clock::now() - kStartTime).count();
        std::ostringstream out;
        out.precision(17);
        auto list = [&](const char* key, const auto& values) {
            out << key << ' ' << values.size();
            for (const auto& v : values) out << ' ' << v;
            out << '\n';
        };
        out << "design_state " << kVersion << '\n'
            << "emergency " << state.emergency << '\n'
            << "end_ticks " << ticks << '\n'
            << "end_sec " << CLOCK_SCALE * std::chrono::duration<double>(Clock::duration(ticks)).count() << '\n'
            << "helpers_ready " << ready << '\n'
            << "M " << state.M << "\nG " << state.G << "\nH " << state.H << '\n';
        list("permutation", state.permutation);
        list("A", state.A);
        std::vector<int> pairs;
        for (auto [a, b] : state.edge) pairs.push_back(a), pairs.push_back(b);
        list("edge", pairs);
        list("polarity", state.polarity);
        std::vector<u64> bits;
        for (const auto& p : state.papers) bits.push_back(p.opaque), bits.push_back(p.black);
        list("papers", bits);
        list("columns", state.columns);
        list("ded", state.ded);
        list("handle", state.handle);
        const std::string text = captured.str();
        out << "stderr " << text.size() << '\n' << text;
        const std::string tmp = save_path + ".tmp";
        {
            std::ofstream file(tmp, std::ios::binary);
            file << out.str();
            if (!file) fail("cannot write " + tmp);
        }
        if (std::rename(tmp.c_str(), save_path.c_str()) != 0) fail("cannot rename " + tmp);
    }

    // Loading: the design state of the input (originalA: the targets as read).
    DesignState load(const std::vector<u64>& originalA) {
        std::ifstream in(load_path, std::ios::binary);
        if (!in) fail("no saved design " + load_path);
        auto expect = [&](const char* key) {
            std::string word;
            if (!(in >> word) || word != key) fail(load_path + ": expected " + key);
        };
        auto number = [&](const char* key, auto& value) {
            expect(key);
            if (!(in >> value)) fail(load_path + ": bad " + key);
        };
        auto list = [&](const char* key, auto& values, size_t size) {
            expect(key);
            size_t n = 0;
            if (!(in >> n) || n != size) fail(load_path + ": bad size of " + key);
            values.resize(n);
            for (auto& v : values)
                if (!(in >> v)) fail(load_path + ": bad " + key);
        };
        DesignState state;
        int version = 0;
        double end_sec = 0;
        number("design_state", version);
        if (version != kVersion) fail(load_path + ": version " + std::to_string(version));
        number("emergency", state.emergency);
        number("end_ticks", end_ticks);
        number("end_sec", end_sec);
        number("helpers_ready", helpers_ready);
        number("M", state.M);
        number("G", state.G);
        number("H", state.H);
        if (!state.emergency) {
            if (state.M < 2 || state.M > 12 || state.G < 1 || state.G > 63 || state.H < 1 || state.G + state.H > 63)
                fail(load_path + ": bad M, G or H");
            list("permutation", state.permutation, N);
            list("A", state.A, P);
            std::vector<int> pairs;
            list("edge", pairs, 2 * state.G);
            for (int j = 0; j < state.G; j++) state.edge.emplace_back(pairs[2 * j], pairs[2 * j + 1]);
            list("polarity", state.polarity, state.G);
            std::vector<u64> bits;
            list("papers", bits, 2 * K);
            for (int k = 0; k < K; k++) state.papers.push_back({bits[2 * k], bits[2 * k + 1]});
            list("columns", state.columns, K);
            list("ded", state.ded, P);
            list("handle", state.handle, state.H);
            // The saved targets must be those read, on the saved windows (a file of another input).
            for (int u = 0; u < P; u++) {
                u64 a = 0;
                for (int j = 0; j < N; j++) a |= (originalA[u] >> state.permutation[j] & 1) << j;
                if (a != state.A[u]) fail(load_path + ": the targets differ from the input");
            }
        } else {
            for (const char* key : {"permutation", "A", "edge", "polarity", "papers", "columns", "ded", "handle"}) {
                std::vector<long long> skip;
                expect(key);
                size_t n = 0;
                in >> n;
                skip.resize(n);
                for (auto& v : skip) in >> v;
            }
        }
        size_t length = 0;
        number("stderr", length);
        in.get();  // the newline after the length
        std::string text(length, '\0');
        if (!in.read(text.data(), length)) fail(load_path + ": short stderr");
        std::cerr << text << "design_loaded = 1\n";
        return state;
    }
};
#endif

#ifdef LOCAL_BENCH
// ==== Analysis output (LOCAL_BENCH): paper attributes ====

// Local evaluation only (AGENTS.md, the analysis section; README): one line
// `@paper <name> = <value of output paper 0> ... <value of output paper K-1>` per attribute ('-': no
// value), from the design state (never from the patterns):
//   role     cap (the black cap on window 63), generic (a sheet of the comparator), pair / single (a
//            column paper serving two targets / one target);
//   col      the column c of a column paper (its handle is h_c);
//   depth0   its depth in its column at the start (0: the column top);
//   hcolor   its color on its own handle h_c;
//   perf     the handles that the handle perforation made holes: the printed paper of column c is opaque
//            on h_0..h_c except where the two targets of a pair differ (design_papers: printing);
//   targets  the targets it serves (a or a,b: the barcode numbers of the input).
// initial_order: the stack before the first request (top first, internal numbers); out_index: the
// output number of an internal paper number.
template <class OutIndex>
void print_paper_attributes(const DesignState& state, const std::array<uint8_t, K>& initial_order, OutIndex out_index) {
    std::vector<std::string> role(K, "-"), col(K, "-"), depth0(K, "-"), hcolor(K, "-"), perf(K, "-"), targets(K, "-");
    std::vector<std::vector<int>> served(K);
    for (int u = 0; u < P; u++)
        if (state.ded[u] >= 0) served[state.ded[u]].push_back(u);
    std::vector<int> rank(state.H, 0);
    for (int k : initial_order)
        if (state.columns[k] >= 0) depth0[k] = std::to_string(rank[state.columns[k]]++);
    for (int k = 0; k < K; k++) {
        const int c = state.columns[k];
        if (k == kCapPaper)
            role[k] = "cap";
        else if (k < state.M)
            role[k] = "generic";
        else
            role[k] = served[k].size() == 2 ? "pair" : served[k].size() == 1 ? "single" : "none";
        if (c < 0) continue;
        col[k] = std::to_string(c);
        hcolor[k] = std::to_string(state.papers[k].black >> state.handle[c] & 1);
        u64 printed = 0;
        for (int j = 0; j <= c; j++) printed |= 1ULL << state.handle[j];
        if (served[k].size() == 2) printed &= ~(state.A[served[k][0]] ^ state.A[served[k][1]]);
        perf[k] = std::to_string(__builtin_popcountll(printed & ~state.papers[k].opaque));
        std::string t;
        for (int u : served[k]) t += (t.empty() ? "" : ",") + std::to_string(u);
        if (!t.empty()) targets[k] = t;
    }
    std::vector<int> internal(K);
    for (int k = 0; k < K; k++) internal[out_index(k)] = k;
    std::string out;
    auto line = [&](const char* name, const std::vector<std::string>& values) {
        out += "@paper ";
        out += name;
        out += " =";
        for (int o = 0; o < K; o++) out += ' ' + values[internal[o]];
        out += '\n';
    };
    line("role", role);
    line("col", col);
    line("depth0", depth0);
    line("hcolor", hcolor);
    line("perf", perf);
    line("targets", targets);
    std::cerr << out;
}
#endif

}  // namespace

int main() {
    // ==== main: input ====

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

    // ==== main: the design (designed, or loaded under LOCAL_BENCH) ====

#ifdef LOCAL_BENCH
    DesignStore store(originalA);  // DESIGN_SAVE_DIR / DESIGN_LOAD_DIR
    DesignState state;
    if (store.loading())
        state = store.load(originalA);
    else {
        store.begin_capture();
        state = design_papers(originalA);
        store.end_capture();
    }
#else
    const DesignState state = design_papers(originalA);
#endif
    if (state.emergency) {
#ifdef LOCAL_BENCH
        store.design_end(state, false);
#endif
        return emergency_design(originalA, R);
    }
    Solver solver = make_solver(state);
    const int M = state.M, G = state.G;

    // ==== main: helper tables and the generic look-ahead ====

    double helper_limit = 1e300;
#ifdef LOCAL_BENCH
    // a loaded design: the helper tables are complete, or given up at once, as in the saved run
    if (store.loading()) helper_limit = store.helpers_ready ? 1e300 : -1e300;
#endif
    { AF_SCOPE(adaptive, 1); solver.init_adaptive(); }
    if (M == Interleave::GM && solver.comparator.complete) {
        solver.interleave = std::make_shared<Interleave>();
        { AF_SCOPE(comparator_tables, 1); solver.comparator.build_tables(); }
        solver.interleave->init(solver.comparator, state.papers, state.A, state.ded, state.columns, solver.gmask,
                                solver.hmask, helper_limit);
        { AF_SCOPE(lookahead, 1); solver.init_lookahead(); }
    }
#ifdef LOCAL_BENCH
    store.design_end(state, solver.interleave && solver.interleave->ready);
#endif
    std::cerr << "helper_end_sec = " << elapsed_sec() << '\n';
    std::cerr << "colmdp_columns = " << solver.colmdp_columns << "\ncolmdp_full_states = " << solver.colmdp_full_states
              << "\ncolmdp_sequences = " << solver.colmdp_sequences << "\ncolmdp_sec = " << solver.colmdp_sec << '\n';

#if AF_PROFILE
    AFProfile::report();
#endif

    // ==== main: simulation harness (SIM_HARNESS) ====

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
                wr += sim.display() != state.A[u];
            }
        }
        std::cerr << "sim_moves = " << tot / (double(ns) * R) << "\nsim_wrong = " << double(wr) / ns << '\n';
        return 0;
    }
#endif

    // ==== main: output of the papers ====

    // Output the cap as paper 0, with generic sheets shifted to 1..6, so it starts on top.
    // Internal indices remain unchanged; out_index translates papers and moves.
    auto out_index = [](int k) { return k == kCapPaper ? 0 : k < kCapPaper ? k + 1 : k; };
    std::vector<int> out_order(K);
    for (int k = 0; k < K; k++) out_order[out_index(k)] = k;
    std::string output;
    for (int o = 0; o < K; o++) {
        const auto& pp = state.papers[out_order[o]];
        std::string row(N, '.');
        for (int j = 0; j < N; j++)
            row[state.permutation[j]] = !(pp.opaque >> j & 1) ? '.' : (pp.black >> j & 1) ? '1' : '0';
        output += row + '\n';
    }
    std::cout << output << std::flush;
#ifdef LOCAL_BENCH
    print_paper_attributes(state, solver.order, out_index);
    std::string op_labels;  // the `@ops` lines, printed after the requests
    int op_label_errors = 0;
#endif

    // ==== main: requests ====

    long long total = 0, generic = 0, wrong = 0;
    double req_sec = 0;  // time spent planning the requests (without waiting for them)
    for (int r = 0; r < R; r++) {
        int u;
        if (!(std::cin >> u) || u == -1) return 0;
        const double t_req = elapsed_sec();
        auto moves = solver.process(u);
        req_sec += elapsed_sec() - t_req;
        wrong += solver.display() != state.A[u];
        output = std::to_string(moves.size()) + '\n';
        for (auto [x, d] : moves) {
            output += std::to_string(out_index(x)) + ' ' + std::to_string(d) + '\n';
            generic += x < M;
        }
        std::cout << output << std::flush;
#ifdef LOCAL_BENCH
        // the labels of the moves (an error of the labels: none at all for this request), after the
        // output so that the tester gets the moves first
        if (solver.op_tags.size() != moves.size()) op_label_errors++, solver.op_tags.clear();
        append_op_labels(op_labels, r, solver.op_tags);
#endif
        total += moves.size();
    }

    // ==== main: statistics ====
    std::cerr << "value_seed_trials = " << solver.value_seed_trials
              << "\nvalue_seed_valid = " << solver.value_seed_valid
              << "\nvalue_seed_accepts = " << solver.value_seed_accepts
              << "\nvalue_seed_gain = " << solver.value_seed_gain
              << "\nvalue_seed_saved = " << solver.value_seed_saved << '\n';
    std::cerr << "complete_value_duplicates = " << solver.complete_value_duplicates << '\n';
    std::cerr << "complete_value_calls = " << solver.complete_value_calls
              << "\ncomplete_value_invalid = " << solver.complete_value_invalid
              << "\ncomplete_value_plans = " << solver.complete_value_plans << '\n';
    std::cerr << "value_filler_trials = " << solver.value_filler_trials
              << "\nvalue_filler_plans = " << solver.value_filler_plans
              << "\nvalue_filler_better = " << solver.value_filler_better
              << "\nvalue_filler_gain = " << solver.value_filler_gain << '\n';
    cf_report();
    std::cerr << "cf_value_hits = " << solver.cf_value_hits << "\ncf_value_misses = " << solver.cf_value_misses << '\n';

#ifdef LOCAL_BENCH
    std::cerr << solver.heavy_log;
    std::cerr << op_labels << "op_label_errors = " << op_label_errors << '\n';
#endif
    std::cerr << "eject_pairs = " << solver.eject_pairs << "\neject_trials = " << solver.eject_trials
              << "\neject_accepts = " << solver.eject_accepts << "\neject_inside = " << solver.eject_inside << '\n';
    std::cerr << "triple_trials = " << solver.triple_trials << "\ntriple_repairs = " << solver.triple_repairs
              << "\ntriple_accepts = " << solver.triple_accepts << '\n';
    std::cerr << "neutral_total = " << solver.neutral_total << "\nneutral_accepted = " << solver.neutral_accepted
              << "\nneutral_direct_saved = " << solver.neutral_direct_saved
              << "\nneutral_escape_saved = " << solver.neutral_escape_saved << '\n';
    std::cerr << "ns_rounds = " << solver.ns_rounds << "\nns_plan_calls = " << solver.ns_plan_calls
              << "\nns_one_trials = " << solver.ns_one_trials << "\nns_one_accepts = " << solver.ns_one_accepts
              << "\nns_three_trials = " << solver.ns_three_trials << "\nns_three_accepts = " << solver.ns_three_accepts
              << "\nns_changed = " << solver.ns_changed << "\nns_saved = " << solver.ns_saved << '\n';
    std::cerr << "f2_plan_reused = " << solver.f2_plan_reused << "\nf2_plan_skipped = " << solver.f2_plan_skipped
              << "\nf2_plan_wins = " << solver.f2_plan_wins << "\nf2_plan_screens = " << solver.f2_plan_screens << '\n';
    std::cerr << "f2_memo_hits = " << solver.f2_memo_hits << "\nf2_memo_misses = " << solver.f2_memo_misses << '\n';
    std::cerr << "f2_prefix_steps = " << solver.f2_prefix_steps << "\nf2_replay_steps = " << solver.f2_replay_steps << '\n';
    std::cerr << "f2_refine_calls = " << solver.f2_refine_calls << "\nf2_refine_saved = " << solver.f2_refine_saved << '\n';
    std::cerr << "post_alternate = " << solver.post_alternate
              << "\npost_candidate_calls = " << solver.post_candidate_calls
              << "\npost_secondary_saved = " << solver.post_secondary_saved << '\n';
    std::cerr << "self_wrong = " << wrong << "\ngeneric_moves = " << generic << "\ntotal_moves = " << total
              << "\nG = " << G << "\nplan_failures = " << solver.plan_failures
              << "\npost_saved = " << solver.post_saved
              << "\nrewrite_trials = " << solver.rewrite_trials
              << "\nrewrite_accepts = " << solver.rewrite_accepts
              << "\nrewrite_same_column = " << solver.rewrite_same_column
              << "\nhelper_papers = " << (solver.interleave ? solver.interleave->helper_papers : 0)
              << "\ninterleave_trials = " << solver.interleave_trials
              << "\ninterleave_selected = " << solver.interleave_selected << "\ntail_hits = " << solver.tail_hits
              << "\nchain_trials = " << solver.chain_trials << "\nchain_selected = " << solver.chain_selected
              << "\nchain_papers = " << solver.chain_papers << "\nunsafe_plans = " << solver.unsafe_plans
              << "\nfiller_demand_spread = " << solver.filler_demand_spread << "\nreq_sec = " << req_sec
              << "\nend_sec = " << elapsed_sec() << '\n';
    return 0;
}
