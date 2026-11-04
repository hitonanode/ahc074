// Analyze a saved design, never used as an interactive solver.
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

using U = std::uint64_t;
struct Paper { U op = 0, black = 0; };
U bits(const std::string& s, char value) {
    U r = 0;
    for (int j = 0; j < int(s.size()); ++j) if (s[j] == value) r |= U(1) << j;
    return r;
}

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    std::ifstream input(argv[1]), saved(argv[2]);
    int n, k, p, r;
    input >> n >> k >> p >> r;
    std::vector<U> A(p);
    std::string row;
    for (auto& a : A) { input >> row; a = bits(row, '1'); }
    std::vector<Paper> papers(k);
    for (auto& q : papers) {
        saved >> row;
        q = {~bits(row, '.'), bits(row, '1')};
    }
    if (n != 64 || k != 192 || p != 256 || !input || !saved) return 3;
    const U cap = papers[0].op;
    U gm = 0;
    for (int x = 1; x <= 6; ++x) gm |= papers[x].op;
    const U hm = ~(gm | cap);
    std::array<int, 64> e0{}, e1{}, col{};
    col.fill(-1);
    std::vector<int> handles;
    for (int x = 7; x < k; ++x) {
        U m = papers[x].op & hm;
        while (m) {
            int j = std::countr_zero(m); m &= m - 1;
            if (col[j] < 0) { col[j] = int(handles.size()); handles.push_back(j); }
        }
    }
    for (int j = 0; j < 64; ++j) if (gm >> j & 1) {
        std::vector<int> support;
        for (int x = 1; x <= 6; ++x) if (papers[x].op >> j & 1) support.push_back(x - 1);
        if (support.size() != 2) return 4;
        e0[j] = support[0]; e1[j] = support[1];
    }
    const int H = int(handles.size());
    std::vector<int> pc(k, -1), nc(H), owner(p, -1), single;
    for (int x = 7; x < k; ++x) {
        for (int j : handles) if (papers[x].op >> j & 1) pc[x] = std::max(pc[x], col[j]);
        if (pc[x] < 0) return 5;
        ++nc[pc[x]];
        for (int a = 0; a < p; ++a) if (!((A[a] ^ papers[x].black) & papers[x].op & ~cap)) {
            if (owner[a] >= 0) return 6;
            owner[a] = x;
        }
        if ((papers[x].op & gm) == gm) single.push_back(x);
    }
    if (std::find(owner.begin(), owner.end(), -1) != owner.end()) return 7;

    // Above a fully opaque helper one may remove only sources of the target's
    // comparison graph. Kahn removal has a unique remainder, independent of order.
    // Its edges are exactly the windows the helper must repair.
    auto residue = [&](U target, U holes) {
        std::array<unsigned, 6> pred{};
        U scan = holes & gm;
        while (scan) {
            int j = std::countr_zero(scan); scan &= scan - 1;
            int a = e0[j], b = e1[j];
            if (((papers[a + 1].black ^ target) >> j) & 1) std::swap(a, b);
            pred[b] |= 1U << a;
        }
        unsigned remain = 63;
        while (true) {
            unsigned sources = 0;
            for (int a = 0; a < 6; ++a)
                if ((remain >> a & 1) && !(pred[a] & remain)) sources |= 1U << a;
            if (!sources) break;
            remain &= ~sources;
        }
        U result = 0;
        scan = holes & gm;
        while (scan) {
            int j = std::countr_zero(scan); scan &= scan - 1;
            if ((remain >> e0[j] & 1) && (remain >> e1[j] & 1)) result |= U(1) << j;
        }
        return result;
    };
    std::vector<U> hp(H);
    for (int c = 0; c < H; ++c) hp[c] = (c ? hp[c - 1] : 0) | (U(1) << handles[c]);
    std::vector<std::array<U, 256>> res(256);
    std::array<long long, 39> residual_hist{};
    long long near = 0, compat = 0, possible = 0, available4 = 0, available8 = 0, available16 = 0;
    double best_donor_count = 0, best_donor_proxy = 0;
    struct Candidate { int a, b, c, na, nb, ra, rb; double fee; };
    std::vector<Candidate> cand;
    for (int a = 0; a < p; ++a) for (int b = a + 1; b < p; ++b) {
        const U diff = A[a] ^ A[b], gh = diff & gm;
        const U ra = residue(A[a], gh), rb = residue(A[b], gh);
        res[a][b] = ra; res[b][a] = rb;
        if (std::popcount(diff & ~cap) > 26) continue;
        ++near;
        if (!ra) { ++compat; continue; }
        ++residual_hist[std::popcount(ra)];
        ++residual_hist[std::popcount(rb)];
        int best_n = 0;
        double best_fee = 1e9;
        Candidate best{};
        for (int c = 0; c < H; ++c) {
            if (diff >> handles[c] & 1) continue;
            const U hh = hm & ~(hp[c] & ~diff);
            int na = 0, nb = 0;
            double sa = 0, sb = 0;
            for (int x = 7; x < k; ++x) {
                if (x == owner[a] || x == owner[b] || pc[x] == c) continue;
                const U required_a = papers[x].op & (ra | hh);
                const U required_b = papers[x].op & (rb | hh);
                // A helper with holes leaves an induced comparison problem below
                // itself. It is usable exactly when that problem is acyclic.
                if (!((papers[x].black ^ A[a]) & required_a) && !residue(A[a], ra & ~papers[x].op)) { ++na; sa += 1.0 / nc[pc[x]]; }
                if (!((papers[x].black ^ A[b]) & required_b) && !residue(A[b], rb & ~papers[x].op)) { ++nb; sb += 1.0 / nc[pc[x]]; }
            }
            best_n = std::max(best_n, std::min(na, nb));
            if (na && nb) {
                // Only a screening proxy: independent random column orders, plus
                // one helper placement and an eventual return, per target.
                const double fee = 1.8 + 0.5 * (1.0 / sa + 1.0 / sb) - 1.0;
                if (fee < best_fee) { best_fee = fee; best = {a,b,c,na,nb,std::popcount(ra),std::popcount(rb),fee}; }
            }
        }
        possible += best_n > 0;
        available4 += best_n >= 4;
        available8 += best_n >= 8;
        available16 += best_n >= 16;
        best_donor_count += best_n;
        if (best_n) { best_donor_proxy += best_fee; cand.push_back(best); }
    }
    long long triangles = 0, triples = 0;
    std::vector<std::array<int, 3>> triple_ids;
    for (int a = 0; a < p; ++a) for (int b = a + 1; b < p; ++b) if (!res[a][b])
        for (int c = b + 1; c < p; ++c) if (!res[a][c] && !res[b][c]) {
            ++triangles;
            U holes = (A[a] ^ A[b]) | (A[a] ^ A[c]);
            if (!residue(A[a], holes) && !residue(A[b], holes) && !residue(A[c], holes)) {
                ++triples; triple_ids.push_back({a,b,c});
            }
        }
    std::sort(cand.begin(), cand.end(), [](auto a, auto b) { return a.fee < b.fee; });
    std::cout << "{\"near\":" << near << ",\"compatible\":" << compat
              << ",\"single_donors\":" << single.size() << ",\"rescued\":" << possible
              << ",\"donors4\":" << available4 << ",\"donors8\":" << available8
              << ",\"donors16\":" << available16 << ",\"mean_min_donors\":" << best_donor_count / (near-compat)
              << ",\"mean_proxy\":" << (possible ? best_donor_proxy / possible : 0)
              << ",\"triangles\":" << triangles << ",\"triples\":" << triples << ",\"residual_hist\":[";
    for (int j = 0; j < 39; ++j) std::cout << (j ? "," : "") << residual_hist[j];
    std::cout << "],\"best\":[";
    for (int i = 0; i < std::min(20, int(cand.size())); ++i) {
        const auto& q = cand[i];
        std::cout << (i ? "," : "") << "[" << q.a << ',' << q.b << ',' << q.c << ',' << q.na << ',' << q.nb << ',' << q.ra << ',' << q.rb << ',' << q.fee << ']';
    }
    std::cout << "],\"triple_ids\":[";
    for (int i = 0; i < int(triple_ids.size()); ++i) {
        const auto& q = triple_ids[i];
        std::cout << (i ? "," : "") << '[' << q[0] << ',' << q[1] << ',' << q[2] << ']';
    }
    std::cout << "]}\n";
}
