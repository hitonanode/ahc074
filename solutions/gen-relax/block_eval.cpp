// Offline (not a solution): evaluates and searches block designs for the generic layer.
// A block of s windows has its own base (Y on every window) and m papers with any pattern of
// hole / Y / ~Y per window. States are the stack orders of the m + 1 papers; the display (relative
// to Y, bit = ~Y) is the topmost opaque paper per window. A pair with differing windows D (each
// window with probability p) and u's relative pattern B on D is consistent iff some state shows B
// on D and some state shows D & ~B on D. Requests: each order draws a random consistent pair side
// (D, B) (D may be empty: untouched); the block moves to the nearest state showing B on D (BFS
// over single moves of a visible paper, random tie-break).
// Reports: consistency probability and moves per touched request.
//   block_eval check S P ORDERS pat1 pat2 ...      (patterns over '.', '0' = Y, '1' = ~Y)
//   block_eval search S M P ITERS SEED LAMBDA     (hill climbing on consistency - LAMBDA * moves)
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <numeric>
#include <random>
#include <string>
#include <vector>

struct Design {
    int s, m;
    std::vector<int> op, col;  // papers 0..m-1, paper m = base
};

struct Eval {
    double cons = 0, moves = 0;
};

static int fact(int n) { return n <= 1 ? 1 : n * fact(n - 1); }

Eval evaluate(const Design& d, double p, int orders, std::mt19937_64& rng) {
    int s = d.s, m = d.m, n = m + 1, T = 1 << s;
    std::vector<int> op(d.op), col(d.col);
    op.push_back(T - 1);
    col.push_back(0);
    // enumerate states
    std::vector<std::vector<int>> st;
    std::map<std::vector<int>, int> id;
    std::vector<int> perm(n);
    std::iota(perm.begin(), perm.end(), 0);
    do {
        id[perm] = st.size();
        st.push_back(perm);
    } while (std::next_permutation(perm.begin(), perm.end()));
    int S = st.size();
    std::vector<int> disp(S);
    std::vector<std::vector<int>> adj(S);
    for (int i = 0; i < S; i++) {
        int cov = 0, c = 0;
        for (int k : st[i]) {
            c |= col[k] & ~cov;
            cov |= op[k];
        }
        disp[i] = c;
        cov = 0;
        for (int pos = 0; pos < n; pos++) {
            int k = st[i][pos];
            bool vis = (op[k] & ~cov) != 0;
            cov |= op[k];
            if (!vis) continue;
            for (int np = 0; np < n; np++) {
                if (np == pos) continue;
                std::vector<int> r = st[i];
                r.erase(r.begin() + pos);
                r.insert(r.begin() + np, k);
                adj[i].push_back(id[r]);
            }
        }
    }
    std::vector<char> dsp(T, 0);
    for (int i = 0; i < S; i++) dsp[disp[i]] = 1;
    // consistency per (D, B)
    std::vector<std::vector<char>> okB(T, std::vector<char>(T, 0));
    double cons = 0;
    for (int D = 0; D < T; D++) {
        std::vector<char> proj(T, 0);
        for (int X = 0; X < T; X++) if (dsp[X]) proj[X & D] = 1;
        double w = 1;
        for (int i = 0; i < s; i++) w *= (D >> i & 1) ? p : 1 - p;
        int c = __builtin_popcount(D), ok = 0;
        for (int B = D;; B = (B - 1) & D) {
            if (proj[B] && proj[D & ~B]) okB[D][B] = 1, ok++;
            if (B == 0) break;
        }
        cons += w * ok / (double)(1 << c);
    }
    Eval e;
    e.cons = cons;
    if (orders <= 0) return e;
    int cur = 0;
    long long moves = 0, touched = 0;
    std::vector<int> dist(S);
    for (int o = 0; o < orders; o++) {
        int D = 0;
        for (int i = 0; i < s; i++) if ((rng() >> 11) * 0x1.0p-53 < p) D |= 1 << i;
        if (!D) continue;
        int B;
        int tries = 0;
        do {
            B = (int)(rng() & (T - 1)) & D;
        } while (!okB[D][B] && ++tries < 1000);
        if (!okB[D][B]) continue;
        touched++;
        // BFS from cur
        std::fill(dist.begin(), dist.end(), -1);
        std::vector<int> q = {cur};
        dist[cur] = 0;
        std::vector<int> goals;
        for (size_t h = 0; h < q.size(); h++) {
            int u = q[h];
            if (!goals.empty() && dist[u] > dist[goals[0]]) break;
            if ((disp[u] & D) == B) {
                goals.push_back(u);
                continue;
            }
            for (int v : adj[u]) if (dist[v] < 0) dist[v] = dist[u] + 1, q.push_back(v);
        }
        int g = goals[rng() % goals.size()];
        moves += dist[g];
        cur = g;
    }
    e.moves = touched ? (double)moves / touched : 0;
    return e;
}

std::string show(const Design& d) {
    std::string r;
    for (int k = 0; k < d.m; k++) {
        if (k) r += ' ';
        for (int i = 0; i < d.s; i++) r += !(d.op[k] >> i & 1) ? '.' : (d.col[k] >> i & 1) ? '1' : '0';
    }
    return r;
}

int main(int argc, char** argv) {
    std::mt19937_64 rng(1);
    if (!std::strcmp(argv[1], "check")) {
        Design d;
        d.s = std::atoi(argv[2]);
        double p = std::atof(argv[3]);
        int orders = std::atoi(argv[4]);
        d.m = argc - 5;
        for (int k = 0; k < d.m; k++) {
            int o = 0, c = 0;
            for (int i = 0; i < d.s; i++) {
                if (argv[5 + k][i] != '.') o |= 1 << i;
                if (argv[5 + k][i] == '1') c |= 1 << i;
            }
            d.op.push_back(o);
            d.col.push_back(c);
        }
        Eval e = evaluate(d, p, orders, rng);
        std::printf("s=%d m=%d [%s]: consistency %.4f, moves/touched %.4f\n", d.s, d.m, show(d).c_str(), e.cons, e.moves);
        return 0;
    }
    // search
    Design d;
    d.s = std::atoi(argv[2]);
    d.m = std::atoi(argv[3]);
    double p = std::atof(argv[4]);
    int iters = std::atoi(argv[5]);
    rng.seed(std::atoi(argv[6]));
    double lambda = std::atof(argv[7]);
    int T = 1 << d.s;
    for (int k = 0; k < d.m; k++) {
        int o = (int)(rng() % (T - 1)) + 1;
        d.op.push_back(o);
        d.col.push_back((int)rng() & o);
    }
    auto score = [&](const Design& x, Eval& e) {
        e = evaluate(x, p, 3000, rng);
        return e.cons - lambda * e.moves;
    };
    Eval be;
    double best = score(d, be);
    for (int it = 0; it < iters; it++) {
        Design x = d;
        int k = rng() % x.m, i = rng() % x.s;
        int st = rng() % 3;  // 0 hole, 1 Y, 2 ~Y
        x.op[k] &= ~(1 << i);
        x.col[k] &= ~(1 << i);
        if (st) x.op[k] |= 1 << i;
        if (st == 2) x.col[k] |= 1 << i;
        if (!x.op[k]) continue;
        Eval e;
        double v = score(x, e);
        if (v >= best) {
            best = v, d = x, be = e;
        }
    }
    Eval fin = evaluate(d, p, 50000, rng);
    std::printf("s=%d m=%d lambda=%.3f [%s]: consistency %.4f, moves/touched %.4f\n", d.s, d.m, lambda, show(d).c_str(), fin.cons, fin.moves);
}
