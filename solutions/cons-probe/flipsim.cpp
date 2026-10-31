// Offline (not a solution): generic layer designs where a flip paper also covers other blocks.
// Papers: 0 = base (every block "off"), 1 + b = flip of block b ("on" on block b). A design gives,
// for every flip b and every other block c, an action: hole, "off" (Y_c, resets c) or "on" (~Y_c).
// A state is the order of the 6 papers (top first); block c shows the value of the topmost paper
// covering it. A paper can be moved iff some block it covers is not covered by a paper above it.
// Requests: 70 pairs with a touched set and an orientation vector x (u wants x, v wants ~x), drawn
// to match the request mix of solutions/cons-tab (touched 5: 70%, 4: 20%, 3: 7%, 2: 3%; uniform /
// one minority block / two: 18 / 41 / 41%); singles (no want) make 46% of the requests. Policy as
// in left-ap's set_blocks: a shortest path to a satisfying state, among those the end state with
// the least expected moves for the next pair target. Prints moves per pair request and whether
// every want of the pairs is reachable.
// usage: flipsim DESIGN [SEED]   DESIGN = 20 chars (b = 0..4, c = 0..4, c != b) of '.', '0', '1'
//        flipsim search ITERS SEED  (hill climbing over designs)
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <numeric>
#include <random>
#include <string>
#include <vector>

constexpr int NB = 5, NP = 6;
using Perm = std::array<int8_t, NP>;

struct Design {
    int act[NB][NB];  // act[b][c]: -1 hole, 0 off, 1 on (c != b); act[b][b] = 1
};

struct Sim {
    Design d;
    std::vector<Perm> st;
    std::vector<int> code_to_id;
    std::vector<int> disp;  // bit c = block c on
    std::vector<std::vector<int>> adj;
    std::vector<int16_t> dist;  // S x S
    int S = 0;
    static int encode(const Perm& p) {
        int c = 0;
        for (int i = NP - 1; i >= 0; i--) c = c * NP + p[i];
        return c;
    }
    int cover(int k, int c) const {  // value of paper k on block c, -1 hole
        if (k == 0) return 0;
        return d.act[k - 1][c];
    }
    void build() {
        Perm p;
        for (int i = 0; i < NP; i++) p[i] = i;
        int pw = 1;
        for (int i = 0; i < NP; i++) pw *= NP;
        code_to_id.assign(pw, -1);
        st.clear();
        do {
            code_to_id[encode(p)] = st.size();
            st.push_back(p);
        } while (std::next_permutation(p.begin(), p.end()));
        S = st.size();
        disp.assign(S, 0);
        adj.assign(S, {});
        for (int s = 0; s < S; s++) {
            const Perm& q = st[s];
            int dv = 0;
            for (int c = 0; c < NB; c++)
                for (int i = 0; i < NP; i++) {
                    int v = cover(q[i], c);
                    if (v >= 0) {
                        dv |= v << c;
                        break;
                    }
                }
            disp[s] = dv;
            int covered = 0;
            for (int i = 0; i < NP; i++) {
                int k = q[i], mine = 0;
                for (int c = 0; c < NB; c++) if (cover(k, c) >= 0) mine |= 1 << c;
                bool vis = (mine & ~covered) != 0;
                covered |= mine;
                if (!vis) continue;
                for (int dpos = 0; dpos < NP; dpos++) {
                    if (dpos == i) continue;
                    Perm r = q;
                    for (int j = i; j + 1 < NP; j++) r[j] = r[j + 1];
                    for (int j = NP - 1; j > dpos; j--) r[j] = r[j - 1];
                    r[dpos] = k;
                    adj[s].push_back(code_to_id[encode(r)]);
                }
            }
        }
        dist.assign((size_t)S * S, 1000);
        std::vector<int> qu;
        for (int s = 0; s < S; s++) {
            int16_t* ds = &dist[(size_t)s * S];
            qu.assign(1, s);
            ds[s] = 0;
            for (size_t h = 0; h < qu.size(); h++) {
                int x = qu[h];
                for (int t : adj[x])
                    if (ds[t] > ds[x] + 1) ds[t] = ds[x] + 1, qu.push_back(t);
            }
        }
    }
    bool sat(int s, int mask, int val) const { return (disp[s] & mask) == val; }
};

struct Want {
    int mask, val;
};

// Pairs matching the request mix of cons-tab.
std::vector<std::array<Want, 2>> make_pairs(std::mt19937_64& rng) {
    std::vector<std::array<Want, 2>> pr;
    for (int i = 0; i < 70; i++) {
        double r = (rng() >> 11) * 0x1.0p-53;
        int t = r < 0.70 ? 5 : r < 0.90 ? 4 : r < 0.97 ? 3 : 2;
        std::vector<int> bl(NB);
        std::iota(bl.begin(), bl.end(), 0);
        std::shuffle(bl.begin(), bl.end(), rng);
        int mask = 0;
        for (int j = 0; j < t; j++) mask |= 1 << bl[j];
        double r2 = (rng() >> 11) * 0x1.0p-53;
        int minority = r2 < 0.18 ? 0 : r2 < 0.59 ? 1 : 2;
        if (minority > t / 2) minority = t / 2;
        int val = 0;
        for (int j = 0; j < minority; j++) val |= 1 << bl[j];
        if (rng() & 1) val = mask & ~val;
        pr.push_back({Want{mask, val}, Want{mask, mask & ~val}});
    }
    return pr;
}

struct Result {
    double moves = 0;
    bool ok = true;
};
double g_tab[NB + 1][NB + 1];  // moves by (touched, wanted on), summed over the last evaluations
long long g_cnt[NB + 1][NB + 1];

Result evaluate(const Design& d, int seeds, int reqs) {
    Sim sim;
    sim.d = d;
    sim.build();
    Result res;
    double tot = 0;
    long long cnt = 0;
    for (int sd = 0; sd < seeds; sd++) {
        std::mt19937_64 rng(1000 + sd);
        auto pairs = make_pairs(rng);
        std::vector<Want> wants;
        for (auto& p : pairs) wants.push_back(p[0]), wants.push_back(p[1]);
        // satisfying sets and V
        std::vector<std::vector<int>> satl(wants.size());
        for (size_t w = 0; w < wants.size(); w++)
            for (int s = 0; s < sim.S; s++)
                if (sim.sat(s, wants[w].mask, wants[w].val)) satl[w].push_back(s);
        for (auto& l : satl)
            if (l.empty()) res.ok = false;
        if (!res.ok) return res;
        std::vector<double> V(sim.S, 0);
        for (int s = 0; s < sim.S; s++) {
            double v = 0;
            for (size_t w = 0; w < wants.size(); w++) {
                int m = 1000;
                for (int t : satl[w]) m = std::min<int>(m, sim.dist[(size_t)s * sim.S + t]);
                v += m;
            }
            V[s] = v / wants.size();
        }
        int cur = 0;
        for (int r = 0; r < reqs; r++) {
            if ((rng() >> 11) * 0x1.0p-53 < 0.46) continue;  // a single: no want
            int w = rng() % wants.size();
            int best = -1;
            for (int t : satl[w]) {
                if (best < 0) { best = t; continue; }
                int dt = sim.dist[(size_t)cur * sim.S + t], db = sim.dist[(size_t)cur * sim.S + best];
                if (dt < db || (dt == db && V[t] < V[best] - 1e-12)) best = t;
            }
            int dd = sim.dist[(size_t)cur * sim.S + best];
            tot += dd;
            cnt++;
            {
                int t = __builtin_popcount(wants[w].mask), k = __builtin_popcount(wants[w].val);
                g_tab[t][k] += dd;
                g_cnt[t][k]++;
            }
            cur = best;
        }
    }
    res.moves = tot / cnt;
    return res;
}

std::string show(const Design& d) {
    std::string s;
    for (int b = 0; b < NB; b++) {
        if (b) s += ' ';
        for (int c = 0; c < NB; c++) s += c == b ? 'F' : d.act[b][c] < 0 ? '.' : d.act[b][c] ? '1' : '0';
    }
    return s;
}

Design parse(const char* str) {
    Design d;
    int i = 0;
    for (int b = 0; b < NB; b++)
        for (int c = 0; c < NB; c++) {
            if (c == b) { d.act[b][c] = 1; continue; }
            char ch = str[i++];
            d.act[b][c] = ch == '.' ? -1 : ch == '1' ? 1 : 0;
        }
    return d;
}

int main(int argc, char** argv) {
    if (!std::strcmp(argv[1], "search")) {
        int iters = std::atoi(argv[2]);
        std::mt19937_64 rng(std::atoi(argv[3]));
        Design d = parse(argc > 4 ? argv[4] : "....................");
        Result br = evaluate(d, 4, 4000);
        std::printf("start %s %.4f\n", show(d).c_str(), br.moves);
        for (int it = 0; it < iters; it++) {
            Design e = d;
            int b = rng() % NB, c = rng() % (NB - 1);
            if (c >= b) c++;
            e.act[b][c] = (int)(rng() % 3) - 1;
            Result r = evaluate(e, 4, 4000);
            if (r.ok && r.moves < br.moves - 1e-9) {
                d = e, br = r;
                std::printf("it %d %s %.4f\n", it, show(d).c_str(), br.moves);
                std::fflush(stdout);
            }
        }
        Result fin = evaluate(d, 16, 20000);
        std::printf("final %s %.4f (plain %.4f)\n", show(d).c_str(), fin.moves,
                    evaluate(parse("...................."), 16, 20000).moves);
        return 0;
    }
    Design d = parse(argv[1]);
    Result r = evaluate(d, 16, 20000);
    std::printf("%s ok=%d moves/pair request %.4f\n", show(d).c_str(), (int)r.ok, r.moves);
    for (int t = 2; t <= NB; t++) {
        std::printf("  t=%d:", t);
        for (int k = 0; k <= t; k++)
            if (g_cnt[t][k]) std::printf(" on%d %.2f", k, g_tab[t][k] / g_cnt[t][k]);
        std::printf("\n");
    }
}
