// Offline estimate (not a solution): flip papers that cover other blocks with patterns other than
// the base colors Y, to relax the consistency of the pairs without new papers (flipz-).
// Generic layer of cons-flip: base (Y on every block) and the flips f_0..f_4 (~Y_b on block b). A
// design gives act[b][c] for every flip b and other block c (20 chars, b = 0..4, c = 0..4, c != b):
// '.' hole, '0' Y_c, '1' ~Y_c, 'z' Z_c, 'Z' ~Z_c (Z_c: an extra pattern of block c, chosen to
// maximize the target pairs nested relative to Y_c or Z_c). Block c shows the value of the topmost
// paper covering it; a paper can move iff a block it covers is not covered above it (the general
// rule of cons-flip). cons-flip itself is "....0...00..000.0000".
// A pair (u, v) is consistent iff some order of the 6 papers shows A_u on the differing G windows
// and some order shows A_v (joint displays, not block by block). For one input (blocks and Y as
// cons-flip computes them before its annealing: H = 34, 5 blocks of 6), prints per design
//   - |R| (distinct joint displays), consistent partners per target (and targets with none),
//   - a greedy matching of 70 pairs among the consistent ones by handle distance (all 34 handle
//     windows) then G distance: mean handle / G distance of the pairs (a proxy of what the
//     annealing can reach; cons-flip ~13.4, no constraint ~8.3),
//   - generic moves per pair request of the lookahead policy on those pairs (random requests).
// "free" = no consistency constraint, "idealZ" = every block shows Y, ~Y, Z, ~Z independently of
// the other blocks (what splitting every block would give; not reachable with 6 papers).
// usage: zsim INPUT DESIGN [DESIGN...]
//        zsim INPUT search ITERS LAMBDA SEED [START|rand [TEMP]]
//          simulated annealing over designs; objective = handle distance + LAMBDA x moves
//          (LAMBDA < 0: maximize the consistent partners instead); "noz" after TEMP: values ., 0, 1 only
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

using u64 = std::uint64_t;
constexpr int N = 64, P = 256, NB = 5, NP = 6;
using Perm = std::array<int8_t, NP>;

std::vector<u64> A;
std::vector<u64> bmask(NB), by(NB), bz(NB);
std::vector<int> handle;
u64 gmask = 0;

void make_blocks() {
    int H = 34, G = N - H, s = 6, nb = NB;
    std::mt19937_64 rng(12345);
    std::vector<std::vector<int>> bw(nb);
    for (int j = 0, b = 0; b < nb; b++) {
        int sz = G / nb + (b < G % nb ? 1 : 0);
        for (int i = 0; i < sz; i++) bw[b].push_back(j++);
    }
    (void)s;
    auto best_y = [&](const std::vector<int>& w, int& ybest) {
        int sz = w.size(), T = 1 << sz;
        std::vector<long long> cnt(T, 0);
        for (int u = 0; u < P; u++) {
            int x = 0;
            for (int i = 0; i < sz; i++) x |= (int)(A[u] >> w[i] & 1) << i;
            cnt[x]++;
        }
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
    std::vector<int> hw;
    for (int j = G; j < N; j++) hw.push_back(j);
    const double gh_rate = 0.3, pmove_rate = 0.0;
    for (int it = 0; it < 3000; it++) {
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
        if ((rng() >> 11) * 0x1.0p-53 < pmove_rate) continue;
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
    for (int b = 0; b < nb; b++) {
        bmask[b] = by[b] = 0;
        for (int i = 0; i < (int)bw[b].size(); i++) {
            bmask[b] |= 1ULL << bw[b][i];
            if (yb[b] >> i & 1) by[b] |= 1ULL << bw[b][i];
        }
        gmask |= bmask[b];
    }
    std::sort(hw.begin(), hw.end());
    handle = hw;
}

// Pattern of value v on block c.
u64 pat(int c, int v) {
    switch (v) {
        case 0: return by[c];
        case 1: return bmask[c] & ~by[c];
        case 2: return bz[c];
        default: return bmask[c] & ~bz[c];
    }
}

// Z_c maximizing the pairs nested relative to Y_c or Z_c (per block).
void choose_z(int c) {
    std::vector<int> w;
    for (int j = 0; j < N; j++) if (bmask[c] >> j & 1) w.push_back(j);
    int sz = w.size(), T = 1 << sz;
    std::vector<long long> cnt(T, 0);
    for (int u = 0; u < P; u++) {
        int x = 0;
        for (int i = 0; i < sz; i++) x |= (int)(A[u] >> w[i] & 1) << i;
        cnt[x]++;
    }
    int y = 0;
    for (int i = 0; i < sz; i++) y |= (int)(by[c] >> w[i] & 1) << i;
    auto nested = [&](int a, int b, int r) {
        int x1 = a ^ r, x2 = b ^ r;
        return (x1 & ~x2) == 0 || (x2 & ~x1) == 0;
    };
    long long best = -1;
    int bzl = 0;
    for (int z = 0; z < T; z++) {
        long long tot = 0;
        for (int a = 0; a < T; a++) {
            if (!cnt[a]) continue;
            for (int b = 0; b < T; b++) {
                if (!cnt[b]) continue;
                if (nested(a, b, y) || nested(a, b, z)) tot += cnt[a] * cnt[b];
            }
        }
        if (tot > best) best = tot, bzl = z;
    }
    bz[c] = 0;
    for (int i = 0; i < sz; i++) if (bzl >> i & 1) bz[c] |= 1ULL << w[i];
}

struct Design {
    int act[NB][NB];  // value of flip b on block c: -1 hole, 0..3; act[b][b] = 1
};

Design parse(const char* s) {
    Design d;
    int i = 0;
    for (int b = 0; b < NB; b++)
        for (int c = 0; c < NB; c++) {
            if (c == b) { d.act[b][c] = 1; continue; }
            char ch = s[i++];
            d.act[b][c] = ch == '.' ? -1 : ch == '0' ? 0 : ch == '1' ? 1 : ch == 'z' ? 2 : 3;
        }
    return d;
}

struct Space {
    Design d;
    std::vector<Perm> st;
    std::vector<int> code_to_id;
    std::vector<int> disp;  // 2 bits per block
    std::vector<std::vector<int>> adj, radj;
    std::vector<int16_t> dist;
    int S = 0;
    static int encode(const Perm& p) {
        int c = 0;
        for (int i = NP - 1; i >= 0; i--) c = c * NP + p[i];
        return c;
    }
    int cover(int k, int c) const { return k == 0 ? 0 : d.act[k - 1][c]; }
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
        radj.assign(S, {});
        for (int s = 0; s < S; s++) {
            const Perm& q = st[s];
            int dv = 0;
            for (int c = 0; c < NB; c++)
                for (int i = 0; i < NP; i++) {
                    int v = cover(q[i], c);
                    if (v >= 0) {
                        dv |= v << (2 * c);
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
                    int t = code_to_id[encode(r)];
                    adj[s].push_back(t);
                    radj[t].push_back(s);
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
};

// Want of target u for the differing windows diff: per block a 4-bit mask of acceptable values
// (15 if untouched).
std::array<int, NB> want_of(int u, u64 diff) {
    std::array<int, NB> w{};
    for (int c = 0; c < NB; c++) {
        u64 dm = diff & bmask[c];
        if (!dm) { w[c] = 15; continue; }
        int m = 0;
        for (int v = 0; v < 4; v++)
            if (((A[u] ^ pat(c, v)) & dm) == 0) m |= 1 << v;
        w[c] = m;
    }
    return w;
}
bool sat_disp(int dv, const std::array<int, NB>& w) {
    for (int c = 0; c < NB; c++)
        if (!(w[c] >> (dv >> (2 * c) & 3) & 1)) return false;
    return true;
}


// Pairs (u < v) with their wants (20 bits: 4-bit masks per block for u, then for v).
struct PairW { int u, v, dh, dg; int wu, wv; };
std::vector<PairW> pairs_all;
int pack(const std::array<int, NB>& w) {
    int x = 0;
    for (int c = 0; c < NB; c++) x |= w[c] << (4 * c);
    return x;
}
bool sat_packed(int dv, int w) {
    for (int c = 0; c < NB; c++)
        if (!(w >> (4 * c) >> (dv >> (2 * c) & 3) & 1)) return false;
    return true;
}
struct Eval {
    double partners = 0, gh = 0, gg = 0, moves = 0, nopart = 0;
    int npairs = 0, R = 0, plain = 0;  // plain: displays of Y / ~Y only (32 = every orientation)
};
// Consistent pairs under the display set rl; greedy matching (70 pairs) by handle distance; moves.
Eval evaluate(const Design& d, bool with_moves, bool free_mode = false, bool ideal = false) {
    Space sp;
    sp.d = d;
    sp.build();
    std::vector<char> rset(1 << (2 * NB), 0);
    std::vector<int> rl;
    for (int s = 0; s < sp.S; s++)
        if (!rset[sp.disp[s]]) rset[sp.disp[s]] = 1, rl.push_back(sp.disp[s]);
    Eval ev;
    ev.R = rl.size();
    for (int dv : rl) {
        bool pl = true;
        for (int c = 0; c < NB; c++) if ((dv >> (2 * c) & 3) >= 2) pl = false;
        ev.plain += pl;
    }
    std::vector<int> ok;
    std::vector<int> pc(P, 0);
    for (int i = 0; i < (int)pairs_all.size(); i++) {
        const auto& p = pairs_all[i];
        bool good = free_mode;
        if (ideal) {
            good = true;
            for (int c = 0; c < NB; c++) if (((p.wu >> (4 * c)) & 15) == 0) good = false;
        } else if (!good) {
            bool ou = false, ov = false;
            for (int dv : rl) {
                if (!ou && sat_packed(dv, p.wu)) ou = true;
                if (!ov && sat_packed(dv, p.wv)) ov = true;
                if (ou && ov) break;
            }
            good = ou && ov;
        }
        if (good) ok.push_back(i), pc[p.u]++, pc[p.v]++;
    }
    for (int u = 0; u < P; u++) ev.partners += pc[u], ev.nopart += pc[u] == 0;
    ev.partners /= P;
    // greedy matching by (handle distance, G distance)
    std::sort(ok.begin(), ok.end(), [&](int a, int b) {
        const auto &x = pairs_all[a], &y = pairs_all[b];
        return x.dh * 64 + x.dg < y.dh * 64 + y.dg;
    });
    std::vector<char> used(P, 0);
    std::vector<int> chosen;
    for (int i : ok) {
        if ((int)chosen.size() >= 70) break;
        const auto& p = pairs_all[i];
        if (used[p.u] || used[p.v]) continue;
        used[p.u] = used[p.v] = 1;
        chosen.push_back(i);
        ev.gh += p.dh, ev.gg += p.dg;
    }
    ev.npairs = chosen.size();
    ev.gh /= std::max(1, ev.npairs);
    ev.gg /= std::max(1, ev.npairs);
    if (!with_moves || free_mode) return ev;
    std::vector<int> wants;
    std::vector<int> want_id(P, -1);
    for (int i : chosen) {
        const auto& p = pairs_all[i];
        want_id[p.u] = wants.size();
        wants.push_back(p.wu);
        want_id[p.v] = wants.size();
        wants.push_back(p.wv);
    }
    const int S = sp.S;
    std::vector<std::vector<int>> satl(wants.size());
    std::vector<std::vector<uint8_t>> dsat(wants.size(), std::vector<uint8_t>(S, 255));
    for (size_t w = 0; w < wants.size(); w++) {
        std::vector<int> q;
        for (int s = 0; s < S; s++)
            if (sat_packed(sp.disp[s], wants[w])) satl[w].push_back(s), dsat[w][s] = 0, q.push_back(s);
        for (size_t h = 0; h < q.size(); h++) {
            int x = q[h];
            for (int pp : sp.radj[x])
                if (dsat[w][pp] > dsat[w][x] + 1) dsat[w][pp] = dsat[w][x] + 1, q.push_back(pp);
        }
    }
    std::vector<double> V(S, 0);
    for (int s = 0; s < S; s++) {
        for (size_t w = 0; w < wants.size(); w++) V[s] += dsat[w][s];
        V[s] /= wants.size();
    }
    double tot = 0;
    long long cnt = 0;
    std::mt19937_64 rng(777);
    int cur = 0;
    for (int r = 0; r < 100000; r++) {
        int u = rng() % P;
        if (want_id[u] < 0) continue;
        int w = want_id[u];
        int best = -1;
        for (int t : satl[w]) {
            if (best < 0) { best = t; continue; }
            int dt = sp.dist[(size_t)cur * S + t], db = sp.dist[(size_t)cur * S + best];
            if (dt < db || (dt == db && V[t] < V[best] - 1e-12)) best = t;
        }
        tot += sp.dist[(size_t)cur * S + best];
        cnt++;
        cur = best;
    }
    ev.moves = tot / cnt;
    return ev;
}

std::string show(const Design& d) {
    std::string s;
    const char* ch = ".01zZ";
    for (int b = 0; b < NB; b++)
        for (int c = 0; c < NB; c++)
            if (c != b) s += ch[d.act[b][c] + 1];
    return s;
}

int main(int argc, char** argv) {
    {
        std::ifstream in(argv[1]);
        int n, k, p, r;
        in >> n >> k >> p >> r;
        A.assign(P, 0);
        for (int u = 0; u < P; u++) {
            std::string s;
            in >> s;
            for (int j = 0; j < N; j++) if (s[j] == '1') A[u] |= 1ULL << j;
        }
    }
    make_blocks();
    u64 hmask = 0;
    for (int h : handle) hmask |= 1ULL << h;
    for (int c = 0; c < NB; c++) choose_z(c);
    for (int u = 0; u < P; u++)
        for (int v = u + 1; v < P; v++) {
            u64 x = A[u] ^ A[v], diff = x & gmask;
            pairs_all.push_back({u, v, __builtin_popcountll(x & hmask), __builtin_popcountll(diff),
                                 pack(want_of(u, diff)), pack(want_of(v, diff))});
        }
    auto print = [&](const char* tag, const Design& d, const Eval& e) {
        std::printf("%-6s %s |R|=%3d (plain %2d) partners %.2f (none %.0f) pairs %d handle-dist %.2f G-dist %.2f moves %.4f\n", tag,
                    show(d).c_str(), e.R, e.plain, e.partners, e.nopart, e.npairs, e.gh, e.gg, e.moves);
    };
    if (!std::strcmp(argv[2], "search")) {
        int iters = std::atoi(argv[3]);
        double lam = std::atof(argv[4]);  // objective: handle distance + lam * moves
        std::mt19937_64 rng(std::atoi(argv[5]));
        Design d = parse(argc > 6 && std::strcmp(argv[6], "rand") ? argv[6] : "....0...00..000.0000");
        if (argc > 6 && !std::strcmp(argv[6], "rand"))
            for (int b = 0; b < NB; b++)
                for (int c = 0; c < NB; c++)
                    if (c != b) d.act[b][c] = (int)(rng() % 5) - 1;
        const double temp0 = argc > 7 ? std::atof(argv[7]) : 0.0;
        const int nval = argc > 8 && !std::strcmp(argv[8], "noz") ? 3 : 5;  // noz: values ., 0, 1 only
        Design bestd = d;
        double bestobj = 1e18;
        auto obj = [&](const Eval& e) {
            // pairs missing (fewer than 70) are heavily penalized
            if (lam < 0) return -e.partners;  // partners only
            return e.gh + lam * e.moves + 10.0 * (70 - e.npairs);
        };
        Eval be = evaluate(d, lam > 0);
        double bo = obj(be);
        print("start", d, be);
        for (int it = 0; it < iters; it++) {
            Design e = d;
            int b = rng() % NB, c = rng() % (NB - 1);
            if (c >= b) c++;
            e.act[b][c] = (int)(rng() % nval) - 1;
            if (rng() % 2) {
                int b2 = rng() % NB, c2 = rng() % (NB - 1);
                if (c2 >= b2) c2++;
                e.act[b2][c2] = (int)(rng() % nval) - 1;
            }
            Eval ee = evaluate(e, lam > 0);
            double o = obj(ee);
            double temp = temp0 * (1.0 - (double)it / iters);
            if (o < bo - 1e-9 || (temp > 0 && (rng() >> 11) * 0x1.0p-53 < std::exp((bo - o) / temp))) {
                d = e, be = ee, bo = o;
                if (bo < bestobj) {
                    bestobj = bo, bestd = d;
                    print("it", d, be);
                    std::fflush(stdout);
                }
            }
        }
        print("final", bestd, evaluate(bestd, true));
        return 0;
    }
    Design dummy = parse("....0...00..000.0000");
    print("free", dummy, evaluate(dummy, false, true));
    print("idealZ", dummy, evaluate(dummy, false, false, true));
    for (int ai = 2; ai < argc; ai++) {
        Design d = parse(argv[ai]);
        print("design", d, evaluate(d, true));
    }
}
