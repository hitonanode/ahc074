// Generic-layer codes: feasibility of close pairs and expected cost for sheet designs.
// usage: codes <input file>
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>
using u64 = uint64_t;
#ifndef MM
#define MM 6
#endif
#ifndef GG
#define GG 36
#endif
const int M = MM, G = GG;
std::vector<std::array<int, M>> perms;
std::vector<uint8_t> D;  // perm distance
int NP;
struct Design { std::array<u64, M> opq{}, blk{}; };
std::vector<u64> displays(const Design& d) {
    std::vector<u64> out(NP);
    for (int i = 0; i < NP; i++) {
        u64 cov = 0, b = 0;
        for (int s : perms[i]) { b |= d.blk[s] & ~cov; cov |= d.opq[s]; }
        out[i] = b;
    }
    return out;
}
Design comparator(std::mt19937& rng) {
    std::vector<std::pair<int, int>> ps;
    for (int a = 0; a < M; a++) for (int b = a + 1; b < M; b++) ps.push_back({a, b});
    std::shuffle(ps.begin(), ps.end(), rng);
    Design d;
    for (int j = 0; j < G; j++) {
        auto [a, b] = ps[j % ps.size()];
        if (rng() & 1) std::swap(a, b);
        d.opq[a] |= 1ULL << j; d.opq[b] |= 1ULL << j; d.blk[a] |= 1ULL << j;
    }
    return d;
}
Design kdesign(std::mt19937& rng, std::vector<int> ks) {
    Design d;
    for (int j = 0; j < G; j++) {
        int k = ks[rng() % ks.size()];
        std::array<int, M> s; std::iota(s.begin(), s.end(), 0); std::shuffle(s.begin(), s.end(), rng);
        std::vector<int> col(k);
        for (int t = 0; t < k; t++) col[t] = rng() & 1;
        if (std::count(col.begin(), col.end(), 1) == 0) col[0] = 1;
        if (std::count(col.begin(), col.end(), 0) == 0) col[0] = 0;
        for (int t = 0; t < k; t++) { d.opq[s[t]] |= 1ULL << j; if (col[t]) d.blk[s[t]] |= 1ULL << j; }
    }
    return d;
}
struct Res { double feas, sat, cost; };
Res eval(const Design& d, const std::vector<std::pair<u64, u64>>& pairs) {
    auto disp = displays(d);
    int feas = 0; double sat = 0, cost = 0;
    std::vector<int> su, sv;
    for (auto [u, v] : pairs) {
        u64 dm = (u ^ v) & ((1ULL << G) - 1);
        su.clear(); sv.clear();
        for (int i = 0; i < NP; i++) {
            if ((disp[i] & dm) == (u & dm)) su.push_back(i);
            if ((disp[i] & dm) == (v & dm)) sv.push_back(i);
        }
        if (su.empty() || sv.empty()) continue;
        feas++;
        sat += (su.size() + sv.size()) / 2.0;
        double c = 0;
        for (auto* s : {&su, &sv}) {
            double tot = 0;
            for (int a = 0; a < NP; a++) {
                int m = 99;
                for (int b : *s) m = std::min(m, int(D[a * NP + b]));
                tot += m;
            }
            c += tot / NP / 2;
        }
        cost += c;
    }
    return {double(feas) / pairs.size(), feas ? sat / feas : 0, feas ? cost / feas : 0};
}
int main(int argc, char** argv) {
    std::array<int, M> p; std::iota(p.begin(), p.end(), 0);
    do perms.push_back(p); while (std::next_permutation(p.begin(), p.end()));
    NP = perms.size();
    D.resize(NP * NP);
    for (int a = 0; a < NP; a++) for (int b = 0; b < NP; b++) {
        int dp[M + 1][M + 1] = {};
        for (int i = 1; i <= M; i++) for (int j = 1; j <= M; j++)
            dp[i][j] = perms[a][i - 1] == perms[b][j - 1] ? dp[i - 1][j - 1] + 1 : std::max(dp[i - 1][j], dp[i][j - 1]);
        D[a * NP + b] = M - dp[M][M];
    }
    std::ifstream in(argv[1]);
    int n, k, P, R; in >> n >> k >> P >> R;
    std::vector<u64> A(P);
    for (auto& a : A) { std::string s; in >> s; a = 0; for (int j = 0; j < 64; j++) if (s[j] == '1') a |= 1ULL << j; }
    std::mt19937 rng(1);
    std::vector<int> win(64); std::iota(win.begin(), win.end(), 0); std::shuffle(win.begin(), win.end(), rng);
    auto proj = [&](u64 a) { u64 r = 0; for (int j = 0; j < G; j++) r |= ((a >> win[j]) & 1) << j; return r; };
    std::vector<std::pair<u64, u64>> pairs;
    for (int a = 0; a < P; a++) for (int b = a + 1; b < P; b++)
        if (__builtin_popcountll(A[a] ^ A[b]) <= 26) pairs.push_back({proj(A[a]), proj(A[b])});
    printf("close pairs %zu\n", pairs.size());
    struct C { const char* name; std::vector<int> ks; };
    std::vector<C> cs = {{"comparator", {}}};
    for (auto& c : cs) {
        double f = 0, s = 0, co = 0;
        for (int t = 0; t < 4; t++) {
            std::mt19937 r(100 + t);
            Design d = c.ks.empty() ? comparator(r) : kdesign(r, c.ks);
            auto res = eval(d, pairs);
            f += res.feas; s += res.sat; co += res.cost;
        }
        printf("%-11s feasible %.3f  sat %.1f  cost %.3f\n", c.name, f / 4, s / 4, co / 4);
    }
}
