// tiny: exact evaluation of paper designs in a reduced model of AHC074, and simulated annealing
// over designs (an analysis tool, not a submission).
//
// Model: N windows, K papers (K <= 9), T distinct random targets with floor(N/2) ones, the same
// move rule as the real problem (take a visible paper, insert it below d of the others). Requests
// are uniform over the targets other than the one shown. The cost of a design is the optimal
// long-run average number of moves per request, computed exactly by relative value iteration on
// the MDP whose states are the permutations showing a target ("rest states"):
//     h(s) + g = mean_{t != shown(s)} min_{s' shows t} [dist(s, s') + h(s')]
// where dist is the shortest number of moves between permutations. For every target t one
// multi-source Dijkstra on the reversed move graph (sources s' with labels h(s'), unit edges, done
// with a sorted source list merged with a FIFO queue) gives F_t(s) = min_{s'} dist(s, s') + h(s')
// for every state. A target that no permutation shows costs PEN (an error, no move).
//
// Usage: tiny mode=sa|eval N=8 K=8 T=10 seed=1 [design=file] [iters=..] [out=file] ...
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
#include <sstream>
#include <string>
#include <vector>

using u64 = std::uint64_t;

static std::map<std::string, std::string> g_args;
static int g_code = 0;  // number of locked code windows (handle sub-model), 0 = plain model
static int g_zcode = -1;  // code of the generic paper K-1 (zcode=1), -1 if none
static std::string arg_s(const std::string& k, const std::string& d) {
    auto it = g_args.find(k);
    return it == g_args.end() ? d : it->second;
}
static long arg_i(const std::string& k, long d) {
    auto it = g_args.find(k);
    return it == g_args.end() ? d : std::atol(it->second.c_str());
}
static double arg_d(const std::string& k, double d) {
    auto it = g_args.find(k);
    return it == g_args.end() ? d : std::atof(it->second.c_str());
}
static double now_sec() {
    static auto t0 = std::chrono::steady_clock::now();
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
}

struct Model {
    int N = 0, K = 0, T = 0, S = 0;
    std::vector<std::uint8_t> perm;  // perm[s*K + pos] = paper at position pos (0 = top)
    std::vector<std::int32_t> succ;  // succ[(s*K + q)*K + p] = state after moving position q to p
    std::vector<u64> tg;             // targets

    static int rank_perm(const std::uint8_t* p, int K) {
        int r = 0;
        unsigned used = 0;
        for (int i = 0; i < K; i++) {
            int c = __builtin_popcount(((1u << p[i]) - 1) & ~used);
            r = r * (K - i) + c;
            used |= 1u << p[i];
        }
        return r;
    }

    void build(int n, int k) {
        N = n;
        K = k;
        S = 1;
        for (int i = 2; i <= K; i++) S *= i;
        perm.resize((size_t)S * K);
        std::vector<std::uint8_t> p(K);
        std::iota(p.begin(), p.end(), 0);
        int s = 0;
        do {
            std::copy(p.begin(), p.end(), perm.begin() + (size_t)s * K);
            s++;
        } while (std::next_permutation(p.begin(), p.end()));
        succ.resize((size_t)S * K * K);
        std::vector<std::uint8_t> q(K);
        for (int st = 0; st < S; st++) {
            const std::uint8_t* pp = &perm[(size_t)st * K];
            for (int a = 0; a < K; a++) {
                for (int b = 0; b < K; b++) {
                    if (a == b) {
                        succ[((size_t)st * K + a) * K + b] = st;
                        continue;
                    }
                    // remove position a, insert at position b
                    int m = 0;
                    std::uint8_t x = pp[a];
                    for (int i = 0; i < K; i++)
                        if (i != a) q[m++] = pp[i];
                    // q has K-1 elements; insert x at b
                    for (int i = K - 1; i > b; i--) q[i] = q[i - 1];
                    q[b] = x;
                    succ[((size_t)st * K + a) * K + b] = rank_perm(q.data(), K);
                }
            }
        }
    }
};

struct Design {
    std::vector<u64> op, bk;  // opaque and black masks per paper
    std::string str(int N) const {
        std::string out;
        for (size_t k = 0; k < op.size(); k++) {
            for (int w = 0; w < N; w++) out += (op[k] >> w & 1) ? ((bk[k] >> w & 1) ? '1' : '0') : '.';
            out += '\n';
        }
        return out;
    }
    int cell(int k, int w) const { return (op[k] >> w & 1) ? int(bk[k] >> w & 1) : 2; }
    void set(int k, int w, int v) {
        u64 b = 1ULL << w;
        op[k] &= ~b;
        bk[k] &= ~b;
        if (v == 0) op[k] |= b;
        if (v == 1) op[k] |= b, bk[k] |= b;
    }
};

struct Evaluator {
    const Model& M;
    double PEN;
    std::vector<std::uint16_t> vis;  // visible positions of each state
    std::vector<std::int16_t> tgt;   // target shown by each state, -1 if none
    std::vector<std::vector<int>> rest;
    std::vector<float> h, Th, dist;
    std::vector<int> que;
    std::vector<std::uint8_t> done;
    std::vector<std::vector<float>> F;  // F[t][s], kept only when keepF
    bool keepF = false;
    double g_lo = 0, g_hi = 0;
    int infeasible = 0;

    Evaluator(const Model& m, double pen) : M(m), PEN(pen), tg(m.tg) {
        vis.resize(M.S);
        tgt.resize(M.S);
        h.assign(M.S, 0.f);
        Th.assign(M.S, 0.f);
        dist.resize(M.S);
        que.resize(M.S + 8);
        done.resize(M.S);
    }

    std::vector<u64> tg;  // targets of this evaluator (M.tg unless replaced)
    int target_index(u64 d) const {
        for (int t = 0; t < M.T; t++)
            if (tg[t] == d) return t;
        return -1;
    }

    void prepare(const Design& D) {
        rest.assign(M.T, {});
        const int K = M.K;
        for (int s = 0; s < M.S; s++) {
            const std::uint8_t* p = &M.perm[(size_t)s * K];
            u64 cov = 0, disp = 0;
            unsigned v = 0;
            for (int i = 0; i < K; i++) {
                int k = p[i];
                u64 o = D.op[k] & ~cov;
                if (o) v |= 1u << i;
                disp |= D.bk[k] & o;
                cov |= D.op[k];
            }
            vis[s] = (std::uint16_t)v;
            int t = target_index(disp);
            tgt[s] = (std::int16_t)t;
            if (t >= 0) rest[t].push_back(s);
        }
        infeasible = 0;
        for (int t = 0; t < M.T; t++)
            if (rest[t].empty()) infeasible++;
        // Reverse adjacency (CSR) of the legal moves: pred of x = states y with a move y -> x.
        pstart.assign(M.S + 1, 0);
        for (int y = 0; y < M.S; y++) {
            int c = __builtin_popcount(vis[y]) * (K - 1);
            const std::int32_t* row = &M.succ[(size_t)y * K * K];
            for (unsigned v = vis[y]; v; v &= v - 1) {
                int p = __builtin_ctz(v);
                for (int q = 0; q < K; q++)
                    if (q != p) pstart[row[p * K + q] + 1]++;
            }
            (void)c;
        }
        for (int s = 0; s < M.S; s++) pstart[s + 1] += pstart[s];
        pred.resize(pstart[M.S]);
        fillp.assign(pstart.begin(), pstart.end() - 1);
        for (int y = 0; y < M.S; y++) {
            const std::int32_t* row = &M.succ[(size_t)y * K * K];
            for (unsigned v = vis[y]; v; v &= v - 1) {
                int p = __builtin_ctz(v);
                for (int q = 0; q < K; q++)
                    if (q != p) pred[fillp[row[p * K + q]]++] = y;
            }
        }
    }
    std::vector<int> pstart, pred, fillp;

    // dist[s] = min_{s' in rest[t]} dist(s, s') + h(s') for all s.
    void dijkstra(int t) {
        const float INF = 1e30f;
        std::fill(dist.begin(), dist.end(), INF);
        std::fill(done.begin(), done.end(), 0);
        auto& src = rest[t];
        std::sort(src.begin(), src.end(), [&](int a, int b) { return h[a] < h[b]; });
        for (int s : src) dist[s] = h[s];
        size_t si = 0;
        int qh = 0, qt = 0;
        while (si < src.size() || qh < qt) {
            int x;
            if (qh < qt && (si >= src.size() || dist[que[qh]] <= h[src[si]])) {
                x = que[qh++];
            } else {
                x = src[si++];
                if (dist[x] < h[x]) continue;  // improved through the queue
            }
            if (done[x]) continue;
            done[x] = 1;
            float L = dist[x] + 1.f;
            for (int e = pstart[x]; e < pstart[x + 1]; e++) {
                int y = pred[e];
                if (dist[y] > L) {
                    dist[y] = L;
                    que[qt++] = y;
                }
            }
        }
    }

    // One step of value iteration: Th(s) = mean over t != tgt(s) of min(F_t(s), PEN + h(s)).
    void step() {
        std::fill(Th.begin(), Th.end(), 0.f);
        if (keepF) F.assign(M.T, {});
        for (int t = 0; t < M.T; t++) {
            if (rest[t].empty()) {
                for (int s = 0; s < M.S; s++)
                    if (tgt[s] != t) Th[s] += (float)PEN + h[s];
                if (keepF) F[t].assign(M.S, 1e30f);
                continue;
            }
            dijkstra(t);
            for (int s = 0; s < M.S; s++)
                if (tgt[s] != t) Th[s] += std::min(dist[s], (float)PEN + h[s]);
            if (keepF) F[t] = dist;
        }
        for (int s = 0; s < M.S; s++) Th[s] /= (float)(tgt[s] >= 0 ? M.T - 1 : M.T);
    }

    // Relative value iteration. Returns the estimate of the average cost g (midpoint of the
    // bounds min/max over rest states of Th - h).
    double solve(int max_iter, double tol, double alpha = 1.0) {
        for (int it = 0; it < max_iter; it++) {
            step();
            double lo = 1e30, hi = -1e30;
            for (int s = 0; s < M.S; s++)
                if (tgt[s] >= 0) {
                    double d = Th[s] - h[s];
                    lo = std::min(lo, d);
                    hi = std::max(hi, d);
                }
            if (lo > hi) lo = hi = PEN;  // no rest state at all
            g_lo = lo;
            g_hi = hi;
            // normalize by the mean over rest states
            double mean = 0;
            int cnt = 0;
            for (int s = 0; s < M.S; s++)
                if (tgt[s] >= 0) mean += Th[s], cnt++;
            mean = cnt ? mean / cnt : 0;
            for (int s = 0; s < M.S; s++) h[s] = (float)((1 - alpha) * h[s] + alpha * (Th[s] - mean));
            if (hi - lo < tol) break;
        }
        return 0.5 * (g_lo + g_hi);
    }
};

static std::vector<u64> gen_targets(int N, int T, std::uint64_t seed) {
    std::mt19937_64 rng(seed);
    std::vector<u64> out;
    int ones = N / 2;
    while ((int)out.size() < T) {
        std::vector<int> idx(N);
        std::iota(idx.begin(), idx.end(), 0);
        std::shuffle(idx.begin(), idx.end(), rng);
        u64 x = 0;
        for (int i = 0; i < ones; i++) x |= 1ULL << idx[i];
        if (std::find(out.begin(), out.end(), x) == out.end()) out.push_back(x);
    }
    return out;
}

static std::string pat(u64 x, int N) {
    std::string s;
    for (int w = 0; w < N; w++) s += (x >> w & 1) ? '1' : '0';
    return s;
}

static Design read_design(const std::string& file, int N, int K) {
    std::ifstream in(file);
    Design D;
    D.op.assign(K, 0);
    D.bk.assign(K, 0);
    std::string line;
    int k = 0;
    while (k < K && std::getline(in, line)) {
        if (line.empty() || line[0] == '#') continue;
        for (int w = 0; w < N && w < (int)line.size(); w++) {
            if (line[w] == '0') D.set(k, w, 0);
            else if (line[w] == '1') D.set(k, w, 1);
        }
        k++;
    }
    return D;
}

// Describes which targets each paper agrees with (all opaque cells equal to the target).
static void describe(const Model& M, const Design& D) {
    for (int k = 0; k < M.K; k++) {
        std::printf("  P%d ", k);
        for (int w = 0; w < M.N; w++) std::putchar(D.cell(k, w) == 2 ? '.' : char('0' + D.cell(k, w)));
        int nop = __builtin_popcountll(D.op[k]);
        std::printf("  opaque %2d  agrees with:", nop);
        for (int t = 0; t < M.T; t++)
            if (((D.bk[k] ^ M.tg[t]) & D.op[k]) == 0) std::printf(" t%d", t);
        std::printf("\n");
    }
}

// Follows the optimal policy (from ev.F, ev.h) for R random requests and prints statistics.
static void simulate(const Model& M, Evaluator& ev, const Design& D, int R, std::uint64_t seed,
                     int show) {
    std::mt19937_64 rng(seed);
    const int K = M.K;
    // start: the best rest state of a random target
    int cur = -1;
    {
        int t0 = 0;
        float best = 1e30f;
        for (int s : ev.rest[t0])
            if (ev.h[s] < best) best = ev.h[s], cur = s;
    }
    if (cur < 0) {
        std::printf("target 0 infeasible\n");
        return;
    }
    long total = 0, errors = 0;
    std::vector<long> hist(2 * K + 2, 0);
    std::vector<long> moved_paper(K, 0), from_pos(K, 0), to_pos(K, 0);
    std::vector<std::vector<long>> fromto(K, std::vector<long>(K, 0));
    int prev = ev.tgt[cur];
    std::vector<int> colp(K, -1);
    std::array<long, 4> mclass{};
    if (g_code > 0) {
        u64 hm = 0;
        for (int w = g_code; w < M.N; w++) hm |= 1ULL << w;
        for (int k = 0; k < M.T; k++) colp[k] = __builtin_popcountll(D.op[k] & hm) - 1;
    }
    double st_nvis = 0, st_topw = 0, st_maxw = 0, st_agree = 0;
    for (int r = 0; r < R; r++) {
        int t;
        do t = (int)(rng() % M.T);
        while (t == prev);
        const auto& Ft = ev.F[t];
        std::string trace;
        int x = cur;
        int moves = 0;
        if (ev.PEN + ev.h[x] < Ft[x] - 1e-4) {
            errors++;
            prev = t;
            if (r < show) std::printf("req %d t%d: ERROR\n", r, t);
            continue;
        }
        while (true) {
            if (ev.tgt[x] == t && ev.h[x] <= Ft[x] + 1e-4) break;
            // find a move x -> y with Ft[y] + 1 == Ft[x]
            const std::uint8_t* p = &M.perm[(size_t)x * K];
            int by = -1, bq = -1, bp = -1;
            std::vector<std::array<int, 3>> cands;
            for (int q = 0; q < K; q++) {
                if (!(ev.vis[x] >> q & 1)) continue;
                for (int pp = 0; pp < K; pp++) {
                    if (pp == q) continue;
                    int y = M.succ[((size_t)x * K + q) * K + pp];
                    if (std::fabs(Ft[y] + 1.f - Ft[x]) < 1e-3) cands.push_back({y, q, pp});
                }
            }
            if (cands.empty()) {
                std::printf("policy error at req %d\n", r);
                return;
            }
            auto c = cands[rng() % cands.size()];
            by = c[0], bq = c[1], bp = c[2];
            int paper = p[bq];
            moved_paper[paper]++;
            if (g_code > 0) {
                // move classes for designs of the handle sub-model: lift (the target's paper to
                // the top), return (the previous target's paper), dig (a paper of column c from
                // the top to the bottom of the papers of column c), other
                int cls = 3;
                if (paper == t && bp == 0) cls = 0;
                else if (paper == prev) cls = 1;
                else if (paper < M.T) {
                    int c = colp[paper];
                    int first = -1, last = -1;
                    for (int i = 0; i < K; i++)
                        if (p[i] < M.T && colp[p[i]] == c && p[i] != prev && p[i] != t) {
                            if (first < 0) first = i;
                            last = i;
                        }
                    if (bq == first && bp == last) cls = 2;
                }
                mclass[cls]++;
            }
            from_pos[bq]++;
            to_pos[bp]++;
            fromto[bq][bp]++;
            if (r < show) trace += " P" + std::to_string(paper) + "@" + std::to_string(bq) + ">" + std::to_string(bp);
            x = by;
            moves++;
            if (moves > 2 * K) {
                std::printf("too many moves\n");
                return;
            }
        }
        {
            // shape of the rest state reached: how many papers are visible, how many windows the
            // top paper shows, whether the paper showing the most windows agrees with t everywhere
            const std::uint8_t* p = &M.perm[(size_t)x * K];
            u64 cov = 0;
            int nvis = 0, topw = -1, maxw = 0, maxk = -1;
            std::string vw;
            for (int i = 0; i < K; i++) {
                int k = p[i];
                u64 o = D.op[k] & ~cov;
                cov |= D.op[k];
                int c = __builtin_popcountll(o);
                if (c) nvis++;
                if (i == 0) topw = c;
                if (c > maxw) maxw = c, maxk = k;
                if (r < show && c) vw += " P" + std::to_string(k) + ":" + std::to_string(c);
            }
            st_nvis += nvis;
            st_topw += topw;
            st_maxw += maxw;
            if (((D.bk[maxk] ^ M.tg[t]) & D.op[maxk]) == 0) st_agree++;
            if (r < show) {
                std::printf("req %3d t%-2d %d moves:%-28s order:", r, t, moves, trace.c_str());
                for (int i = 0; i < K; i++) std::printf(" %d", p[i]);
                std::printf("  shows:%s\n", vw.c_str());
            }
        }
        total += moves;
        hist[moves]++;
        cur = x;
        prev = t;
    }
    std::printf("simulated %d requests: %.4f moves/request, errors %ld\n", R, (double)total / R, errors);
    std::printf("rest states: visible papers %.3f, windows of the top paper %.3f (of %d), max windows of "
                "one paper %.3f, that paper agrees with the target %.3f\n",
                st_nvis / R, st_topw / R, M.N, st_maxw / R, st_agree / R);
    std::printf("moves histogram:");
    for (int i = 0; i <= 2 * K; i++)
        if (hist[i]) std::printf(" %d:%.3f", i, (double)hist[i] / R);
    if (g_code > 0)
        std::printf("\nmove classes per request: lift %.3f return %.3f dig %.3f other %.3f",
                    (double)mclass[0] / R, (double)mclass[1] / R, (double)mclass[2] / R,
                    (double)mclass[3] / R);
    std::printf("\nmoves per paper:");
    for (int k = 0; k < K; k++) std::printf(" P%d:%.3f", k, (double)moved_paper[k] / R);
    std::printf("\nfrom position:");
    for (int k = 0; k < K; k++) std::printf(" %d:%.3f", k, (double)from_pos[k] / R);
    std::printf("\nto position:");
    for (int k = 0; k < K; k++) std::printf(" %d:%.3f", k, (double)to_pos[k] / R);
    std::printf("\n");
}

// The hub policy on a hub design of the handle sub-model (paper k < T dedicated to target k, in
// column popcount(handle cells) - 1): return the previous paper to the top or the bottom of its
// column (whichever ends cheaper), dig the column of the new paper until it is the column top,
// lift it to the top, then rotate every deeper column whose handle shows the wrong color.
// Returns the average cost per request (moves + PEN per error).
static double simulate_hub(const Model& M, const Design& D, int R, std::uint64_t seed, double PEN) {
    const int K = M.K, T = M.T, Hc = M.N - g_code;
    std::vector<int> col(K, -1);
    u64 hmask = 0;
    for (int w = g_code; w < M.N; w++) hmask |= 1ULL << w;
    for (int k = 0; k < T; k++) col[k] = __builtin_popcountll(D.op[k] & hmask) - 1;
    // initial order: free papers first (they are holes on the code), then columns 0, 1, ...
    std::vector<int> order;
    for (int k = T; k < K; k++) order.push_back(k);
    for (int l = 0; l < Hc; l++)
        for (int k = 0; k < T; k++)
            if (col[k] == l) order.push_back(k);
    auto display = [&](const std::vector<int>& o, unsigned* vis) {
        u64 cov = 0, disp = 0;
        unsigned v = 0;
        for (int i = 0; i < K; i++) {
            u64 x = D.op[o[i]] & ~cov;
            if (x) v |= 1u << i;
            disp |= D.bk[o[i]] & x;
            cov |= D.op[o[i]];
        }
        if (vis) *vis = v;
        return disp;
    };
    auto pos_of = [&](const std::vector<int>& o, int k) {
        return (int)(std::find(o.begin(), o.end(), k) - o.begin());
    };
    // moves paper k to position p (0 = top); returns false if k is not visible
    auto mv = [&](std::vector<int>& o, int k, int p) {
        unsigned vis;
        display(o, &vis);
        int q = pos_of(o, k);
        if (!(vis >> q & 1)) return false;
        o.erase(o.begin() + q);
        o.insert(o.begin() + p, k);
        return true;
    };
    // range [a, b) of the papers of column l in place (contiguous), skipping the lifted paper
    auto col_range = [&](const std::vector<int>& o, int l, int skip) {
        int a = -1, b = -1;
        for (int i = 0; i < K; i++)
            if (o[i] != skip && col[o[i]] == l) {
                if (a < 0) a = i;
                b = i + 1;
            }
        return std::make_pair(a, b);
    };
    std::mt19937_64 rng(seed);
    int up = -1, prev = -1;
    long total = 0, errors = 0;
    for (int r = 0; r < R; r++) {
        int v;
        do v = (int)(rng() % T);
        while (v == prev);
        prev = v;
        int best_cost = 1 << 30;
        std::vector<int> best_order;
        for (int mode = 0; mode < (up >= 0 ? 2 : 1); mode++) {
            std::vector<int> o = order;
            int moves = 0;
            bool ok = true;
            if (up >= 0) {
                // return up to the top (mode 0) or the bottom (mode 1) of its column
                auto [a, b] = col_range(o, col[up], up);
                int target_pos;
                if (a < 0) {  // empty column: just after the previous columns
                    target_pos = 1;
                    for (int i = 1; i < K; i++)
                        if (col[o[i]] < col[up]) target_pos = i + 1;
                } else {
                    target_pos = mode == 0 ? a : b;
                }
                // positions are counted with up removed
                int q = pos_of(o, up);
                if (target_pos > q) target_pos--;
                if (target_pos != q) {  // a paper of column 0 may already be in place
                    ok &= mv(o, up, target_pos);
                    moves++;
                }
            }
            // dig column col[v] until v is its top
            for (int guard = 0; ok && guard < K; guard++) {
                auto [a, b] = col_range(o, col[v], -1);
                if (o[a] == v) break;
                ok &= mv(o, o[a], b - 1);
                moves++;
            }
            if (o[0] != v) {
                ok &= mv(o, v, 0);
                moves++;
            }
            // rotate deeper columns whose handle shows the wrong color
            for (int m = col[v] + 1; ok && m < Hc; m++) {
                int w = g_code + m;
                auto [a, b] = col_range(o, m, v);
                int tries = 0;
                while (((display(o, nullptr) ^ M.tg[v]) >> w & 1) && tries < b - a - 1) {
                    ok &= mv(o, o[a], b - 1);
                    moves++;
                    tries++;
                }
            }
            int cost = moves;
            if (!ok || display(o, nullptr) != M.tg[v]) cost += (int)PEN;
            if (cost < best_cost) best_cost = cost, best_order = o;
        }
        if (best_cost >= PEN) errors++;
        total += best_cost;
        order = best_order;
        up = v;
    }
    std::printf("hub policy: %.4f per request (errors %.4f per request)\n", (double)total / R,
                (double)errors / R);
    return (double)total / R;
}

static double eval_full(const Model& M, Evaluator& ev, const Design& D, int iters = 200,
                        double tol = 1e-4) {
    ev.prepare(D);
    std::fill(ev.h.begin(), ev.h.end(), 0.f);
    double g = ev.solve(iters, tol, 0.5);
    return g;
}

// Initial design: paper k gets the pattern of target k % T, cells made holes with prob ph.
static Design init_design(const Model& M, std::mt19937_64& rng, const std::string& kind, double ph) {
    Design D;
    D.op.assign(M.K, 0);
    D.bk.assign(M.K, 0);
    std::uniform_real_distribution<double> U(0, 1);
    for (int k = 0; k < M.K; k++) {
        for (int w = 0; w < M.N; w++) {
            if (w < g_code) {
                if (k < M.T) D.set(k, w, (int)(M.tg[k] >> w & 1));
                else if (k == M.K - 1 && g_zcode >= 0) D.set(k, w, g_zcode >> w & 1);
                else D.set(k, w, 2);
                continue;
            }
            if (k == M.K - 1 && g_zcode >= 0) {
                D.set(k, w, 2);
                continue;
            }
            if (g_code > 0 && k >= M.T) {
                D.set(k, w, U(rng) < 0.5 ? 2 : (int)(rng() % 2));
                continue;
            }
            if (kind == "random") {
                D.set(k, w, (int)(rng() % 3));
            } else {
                int t = k % M.T;
                if (U(rng) < ph && !(g_code > 0 && w == g_code + k % (M.N - g_code))) D.set(k, w, 2);
                else D.set(k, w, (int)(M.tg[t] >> w & 1));
            }
        }
    }
    return D;
}

int main(int argc, char** argv) {
    for (int i = 1; i < argc; i++) {
        std::string a = argv[i];
        auto e = a.find('=');
        if (e == std::string::npos) g_args[a] = "1";
        else g_args[a.substr(0, e)] = a.substr(e + 1);
    }
    std::string mode = arg_s("mode", "sa");
    Model M;
    int N = (int)arg_i("N", 8), K = (int)arg_i("K", 7), T = (int)arg_i("T", 9);
    std::uint64_t seed = (std::uint64_t)arg_i("seed", 1);
    double PEN = arg_d("pen", 100.0);
    // Handle sub-model (code=c > 0): windows 0..c-1 carry a distinct code per target, and paper
    // k < T is dedicated to target k: opaque with the code of target k there (locked), so the
    // topmost dedicated paper must be the target's own one (like the G windows of the real
    // problem). Windows c..c+H-1 are random bits; the K - T other papers ("free") are holes on
    // the code windows. Only the cells of windows >= c are searched.
    int code = (int)arg_i("code", 0);
    if (code > 0) {
        int Hw = (int)arg_i("H", 4);
        N = code + Hw;
        T = K - (int)arg_i("free", 0);
    }
    M.T = T;
    M.tg = gen_targets(N, T, seed * 7919 + 17);
    if (code > 0) {
        std::mt19937_64 r2(seed * 31337 + 5);
        std::vector<int> codes(1 << code);
        std::iota(codes.begin(), codes.end(), 0);
        std::shuffle(codes.begin(), codes.end(), r2);
        for (int t = 0; t < T; t++) {
            u64 x = (u64)codes[t];
            for (int w = code; w < N; w++)
                if (r2() & 1) x |= 1ULL << w;
            M.tg[t] = x;
        }
    }
    g_code = code;
    if (code > 0 && arg_i("zcode", 0)) {
        // paper K-1 is a generic paper Z, opaque on the code windows with a code no target has
        // (like the generic layer of the real problem, which the lifted paper must be above)
        std::vector<int> used;
        for (int t = 0; t < T; t++) used.push_back((int)(M.tg[t] & ((1ULL << code) - 1)));
        for (int c = 0; c < (1 << code); c++)
            if (std::find(used.begin(), used.end(), c) == used.end()) {
                g_zcode = c;
                break;
            }
    }
    if (g_args.count("targets")) {  // explicit targets file (one 0/1 string per line)
        std::ifstream in(arg_s("targets", ""));
        M.tg.clear();
        std::string line;
        while (std::getline(in, line))
            if (!line.empty()) {
                u64 x = 0;
                for (int w = 0; w < N; w++)
                    if (line[w] == '1') x |= 1ULL << w;
                M.tg.push_back(x);
            }
        M.T = T = (int)M.tg.size();
    }
    M.build(N, K);
    std::printf("model N=%d K=%d T=%d seed=%llu states=%d (built %.2fs)\n", N, K, T,
                (unsigned long long)seed, M.S, now_sec());
    for (int t = 0; t < T; t++) std::printf("  t%-2d %s\n", t, pat(M.tg[t], N).c_str());
    Evaluator ev(M, PEN);
    std::mt19937_64 rng(seed * 1000003 + arg_i("sa_seed", 0));

    if (mode == "eval") {
        Design D = read_design(arg_s("design", "design.txt"), N, K);
        double g = eval_full(M, ev, D, (int)arg_i("vi", 300), arg_d("tol", 1e-5));
        std::printf("g = %.5f [%.5f, %.5f] infeasible %d (%.2fs)\n", g, ev.g_lo, ev.g_hi, ev.infeasible,
                    now_sec());
        describe(M, D);
        if (g_args.count("hubpol")) simulate_hub(M, D, (int)arg_i("R", 20000), seed + 99, PEN);
        ev.keepF = true;
        ev.step();
        simulate(M, ev, D, (int)arg_i("R", 20000), seed + 99, (int)arg_i("show", 30));
        return 0;
    }

    if (mode == "ssa") {
        // Structural search in the handle sub-model: a dedicated paper k < T is opaque on the
        // code and on the handle windows of its mask open[k] (where it takes the color of its
        // target), a hole elsewhere; the free papers k >= T have fixed cells. The cost of a
        // structure is the exact optimal cost averaged over `sets` random draws of the handle
        // colors of the targets, so that the search cannot exploit coincidences of one draw.
        int sets = (int)arg_i("sets", 8);
        std::vector<Evaluator> evs;
        for (int i = 0; i < sets; i++) {
            evs.emplace_back(M, PEN);
            std::mt19937_64 r3(seed * 977 + i * 131 + 7);
            for (int t = 0; t < T; t++) {
                u64 x = M.tg[t] & ((1ULL << code) - 1);
                for (int w = code; w < N; w++)
                    if (r3() & 1) x |= 1ULL << w;
                evs[i].tg[t] = x;
            }
        }
        u64 hm = 0;
        for (int w = code; w < N; w++) hm |= 1ULL << w;
        std::vector<u64> open(T, hm);
        Design freeD;  // cells of the free papers
        freeD.op.assign(K, 0);
        freeD.bk.assign(K, 0);
        if (g_zcode >= 0)
            for (int w = 0; w < code; w++) freeD.set(K - 1, w, g_zcode >> w & 1);
        std::string init = arg_s("init", "cols");
        if (init == "cols") {  // triangle with the given column sizes
            std::vector<int> cols;
            std::stringstream ss(arg_s("cols", "2,2,2,2"));
            std::string x;
            while (std::getline(ss, x, ',')) cols.push_back(std::atoi(x.c_str()));
            int idx = 0;
            for (int l = 0; l < (int)cols.size(); l++)
                for (int j = 0; j < cols[l]; j++) {
                    u64 o = 0;
                    for (int m = 0; m <= l; m++) o |= 1ULL << (code + m);
                    open[idx++] = o;
                }
        } else if (init == "file") {
            Design D0 = read_design(arg_s("design", ""), N, K);
            for (int k = 0; k < T; k++) open[k] = D0.op[k] & hm;
            for (int k = T; k < K; k++) freeD.op[k] = D0.op[k], freeD.bk[k] = D0.bk[k];
        } else {
            for (int k = 0; k < T; k++) open[k] = rng() & hm;
        }
        auto build = [&](int i, const std::vector<u64>& op_, const Design& fr) {
            Design D;
            D.op.assign(K, 0);
            D.bk.assign(K, 0);
            u64 cm = (1ULL << code) - 1;
            for (int k = 0; k < T; k++) {
                D.op[k] = cm | op_[k];
                D.bk[k] = evs[i].tg[k] & D.op[k];
            }
            for (int k = T; k < K; k++) D.op[k] = fr.op[k], D.bk[k] = fr.bk[k];
            return D;
        };
        int vi = (int)arg_i("vi", 6);
        double tol = arg_d("tol", 2e-3);
        auto eval_all = [&](const std::vector<u64>& op_, const Design& fr, bool full, double* spread) {
            double sum = 0, lo = 1e30, hi = -1e30;
            for (int i = 0; i < sets; i++) {
                Design D = build(i, op_, fr);
                evs[i].prepare(D);
                double g;
                if (full) {
                    std::fill(evs[i].h.begin(), evs[i].h.end(), 0.f);
                    g = evs[i].solve(300, 1e-5, 0.5);
                } else {
                    g = evs[i].solve(vi, tol, 0.5);
                }
                sum += g;
                lo = std::min(lo, g);
                hi = std::max(hi, g);
            }
            if (spread) *spread = hi - lo;
            return sum / sets;
        };
        auto show = [&](const std::vector<u64>& op_, const Design& fr) {
            for (int k = 0; k < K; k++) {
                std::printf("  P%d ", k);
                for (int w = 0; w < N; w++) {
                    if (k < T) std::putchar(w < code ? 'c' : ((op_[k] >> w & 1) ? 'X' : '.'));
                    else std::putchar(fr.cell(k, w) == 2 ? '.' : char('0' + fr.cell(k, w)));
                }
                std::printf("\n");
            }
        };
        double spread;
        double cc = eval_all(open, freeD, true, &spread);
        std::printf("init structure g = %.5f (spread over sets %.3f)\n", cc, spread);
        show(open, freeD);
        long iters = arg_i("iters", 0);
        double T0 = arg_d("T0", 0.05), T1 = arg_d("T1", 0.002);
        std::uniform_real_distribution<double> U(0, 1);
        auto best = open;
        Design bestF = freeD;
        double bc = cc;
        std::vector<std::vector<float>> saved(sets);
        for (long it = 0; it < iters; it++) {
            double temp = T0 * std::pow(T1 / T0, (double)it / iters);
            auto no = open;
            Design nf = freeD;
            int k = (int)(rng() % K);
            int w = code + (int)(rng() % (N - code));
            if (k < T) {
                no[k] ^= 1ULL << w;
                if (rng() % 3 == 0) {  // a second cell of the same paper
                    int w2 = code + (int)(rng() % (N - code));
                    if (w2 != w) no[k] ^= 1ULL << w2;
                }
            } else {
                if (g_zcode >= 0 && k == K - 1 && w < code) continue;
                int v = nf.cell(k, w);
                nf.set(k, w, (v + 1 + (int)(rng() % 2)) % 3);
            }
            for (int i = 0; i < sets; i++) saved[i] = evs[i].h;
            double nc = eval_all(no, nf, false, nullptr);
            if (nc <= cc || U(rng) < std::exp((cc - nc) / temp)) {
                open = no;
                freeD = nf;
                cc = nc;
                if (nc < bc) bc = nc, best = no, bestF = nf;
            } else {
                for (int i = 0; i < sets; i++) {
                    evs[i].h = saved[i];
                }
            }
            if ((it + 1) % arg_i("log", 200) == 0)
                std::printf("it %ld temp %.4f cur %.4f best %.4f (%.1fs)\n", it + 1, temp, cc, bc, now_sec());
        }
        if (iters > 0) {
            double g = eval_all(best, bestF, true, &spread);
            std::printf("best structure g = %.5f (spread over sets %.3f)\n", g, spread);
            show(best, bestF);
            if (g_args.count("out")) {
                std::ofstream o(arg_s("out", ""));
                o << build(0, best, bestF).str(N);
            }
        }
        return 0;
    }

    if (mode == "hub") {
        // Hub family in the handle sub-model: column l (0 = shallowest) owns handle window c + l;
        // a paper of column l shows its target on handles 0..l and is a hole on the deeper
        // handles (the triangle). Random assignments of the targets to the columns (sizes from
        // cols=...) are evaluated exactly; the best is kept. Free papers: all holes.
        std::vector<int> cols;
        {
            std::stringstream ss(arg_s("cols", "2,2,2,2"));
            std::string x;
            while (std::getline(ss, x, ',')) cols.push_back(std::atoi(x.c_str()));
        }
        int Hc = (int)cols.size();
        int tries = (int)arg_i("tries", 30);
        Design best;
        double bc = 1e30;
        std::vector<int> ord(T);
        std::iota(ord.begin(), ord.end(), 0);
        for (int tr = 0; tr < tries; tr++) {
            std::shuffle(ord.begin(), ord.end(), rng);
            Design D;
            D.op.assign(K, 0);
            D.bk.assign(K, 0);
            int idx = 0;
            for (int l = 0; l < Hc; l++)
                for (int j = 0; j < cols[l]; j++) {
                    int k = ord[idx++];
                    for (int w = 0; w < code; w++) D.set(k, w, (int)(M.tg[k] >> w & 1));
                    for (int m = 0; m <= l; m++) D.set(k, code + m, (int)(M.tg[k] >> (code + m) & 1));
                }
            if (g_zcode >= 0)
                for (int w = 0; w < code; w++) D.set(K - 1, w, g_zcode >> w & 1);
            double g = eval_full(M, ev, D, 300, 1e-4);
            if (g < bc) bc = g, best = D;
        }
        double g = eval_full(M, ev, best, 300, 1e-5);
        std::printf("hub best g = %.5f [%.5f, %.5f] infeasible %d\n", g, ev.g_lo, ev.g_hi, ev.infeasible);
        std::printf("design:\n%s", best.str(N).c_str());
        describe(M, best);
        if (g_args.count("out")) {
            std::ofstream o(arg_s("out", ""));
            o << best.str(N);
        }
        simulate_hub(M, best, (int)arg_i("R", 20000), seed + 99, PEN);
        ev.keepF = true;
        ev.step();
        simulate(M, ev, best, (int)arg_i("R", 20000), seed + 99, (int)arg_i("show", 20));
        return 0;
    }

    // Simulated annealing.
    long iters = arg_i("iters", 20000);
    double T0 = arg_d("T0", 0.3), T1 = arg_d("T1", 0.003);
    int vi = (int)arg_i("vi", 6);
    double tol = arg_d("tol", 2e-3);
    Design cur;
    if (g_args.count("design")) cur = read_design(arg_s("design", ""), N, K);
    else cur = init_design(M, rng, arg_s("init", "targets"), arg_d("ph", 0.2));
    double cc = eval_full(M, ev, cur, 100, 1e-3);
    std::printf("init g = %.4f infeasible %d\n", cc, ev.infeasible);
    Design best = cur;
    double bc = cc;
    std::vector<float> saved_h;
    std::uniform_real_distribution<double> U(0, 1);
    long acc = 0;
    double tlim = arg_d("time", 1e9);
    for (long it = 0; it < iters; it++) {
        if (now_sec() > tlim) break;
        double frac = (double)it / iters;
        double temp = T0 * std::pow(T1 / T0, frac);
        Design nd = cur;
        int kind = (int)(rng() % 10);
        auto rw = [&]() { return g_code + (int)(rng() % (N - g_code)); };
        if (kind < 7) {
            int k = (int)(rng() % K), w = rw();
            int v = nd.cell(k, w);
            int nv = (v + 1 + (int)(rng() % 2)) % 3;
            nd.set(k, w, nv);
        } else if (kind < 9) {
            // two cells of one paper
            int k = (int)(rng() % K);
            for (int r = 0; r < 2; r++) {
                int w = rw();
                int v = nd.cell(k, w);
                nd.set(k, w, (v + 1 + (int)(rng() % 2)) % 3);
            }
        } else {
            // paper k takes target t's colors on its opaque cells (or everywhere)
            int k = (int)(rng() % K), t = (int)(rng() % T);
            if (g_code > 0 && k < T) t = k;
            for (int w = g_code; w < N; w++) {
                if (nd.cell(k, w) != 2 || rng() % 4 == 0) nd.set(k, w, (int)(M.tg[t] >> w & 1));
            }
        }
        saved_h = ev.h;
        ev.prepare(nd);
        double nc = ev.solve(vi, tol, 0.5);
        if (nc <= cc || U(rng) < std::exp((cc - nc) / temp)) {
            cur = nd;
            cc = nc;
            acc++;
            if (nc < bc - 1e-9 && ev.g_hi - ev.g_lo < 0.05) {
                bc = nc;
                best = nd;
            }
        } else {
            ev.h = saved_h;
            ev.prepare(cur);  // restore rest lists for the warm start
        }
        if ((it + 1) % (long)arg_i("log", 1000) == 0)
            std::printf("it %ld temp %.4f cur %.4f best %.4f acc %.3f (%.1fs)\n", it + 1, temp, cc, bc,
                        (double)acc / (it + 1), now_sec());
    }
    double g = eval_full(M, ev, best, 300, 1e-5);
    std::printf("best g = %.5f [%.5f, %.5f] infeasible %d (%.1fs)\n", g, ev.g_lo, ev.g_hi, ev.infeasible,
                now_sec());
    std::string ds = best.str(N);
    std::printf("design:\n%s", ds.c_str());
    describe(M, best);
    if (g_args.count("out")) {
        std::ofstream o(arg_s("out", ""));
        o << ds;
    }
    ev.keepF = true;
    ev.step();
    simulate(M, ev, best, (int)arg_i("R", 20000), seed + 99, (int)arg_i("show", 20));
    return 0;
}
