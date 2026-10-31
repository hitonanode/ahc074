// Audit tool: replays an output and, for every request, looks for moves that can be dropped.
// A move is re-expressed as "insert paper k just below paper a" (a = -1: at the top), with a taken
// from the original replay, so that dropping earlier moves keeps the intended placement.
//   drop1: requests where dropping one move keeps every move legal and the display correct.
//   drop2: same with two moves (only counted if no single move can be dropped).
//   twice: papers moved twice or more within one request.
// Usage: redundant <input> <output>   (prints `name = value` lines)
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using u64 = std::uint64_t;
int N, K, P, R;
std::vector<u64> A, opq, blk;
std::vector<int> req;

struct Mv {
    int k, anchor;  // anchor: paper just above k after the move, -1 = top
};

static bool visible(const std::vector<int>& order, int k) {
    u64 cov = 0;
    for (int x : order) {
        if (x == k) return (opq[k] & ~cov) != 0;
        cov |= opq[x];
    }
    return false;
}
static u64 display(const std::vector<int>& order) {
    u64 cov = 0, b = 0;
    for (int x : order) {
        b |= blk[x] & ~cov;
        cov |= opq[x];
    }
    return b;
}
static void apply_mv(std::vector<int>& order, const Mv& m) {
    order.erase(std::find(order.begin(), order.end(), m.k));
    if (m.anchor < 0) order.insert(order.begin(), m.k);
    else order.insert(std::find(order.begin(), order.end(), m.anchor) + 1, m.k);
}
// Runs the moves except those flagged; true if all legal and the display is the target.
static bool check(std::vector<int> order, const std::vector<Mv>& mv, const std::vector<char>& skip, u64 target) {
    for (size_t i = 0; i < mv.size(); i++) {
        if (skip[i]) continue;
        if (mv[i].anchor == mv[i].k) return false;
        if (!visible(order, mv[i].k)) return false;
        apply_mv(order, mv[i]);
    }
    return display(order) == target;
}

int main(int argc, char** argv) {
    std::ifstream fin(argv[1]), fout(argv[2]);
    fin >> N >> K >> P >> R;
    A.resize(P);
    for (auto& a : A) {
        std::string s;
        fin >> s;
        a = 0;
        for (int j = 0; j < N; j++) if (s[j] == '1') a |= 1ULL << j;
    }
    req.resize(R);
    for (auto& x : req) fin >> x;
    opq.resize(K), blk.resize(K);
    for (int k = 0; k < K; k++) {
        std::string s;
        fout >> s;
        opq[k] = blk[k] = 0;
        for (int j = 0; j < N; j++) {
            if (s[j] != '.') opq[k] |= 1ULL << j;
            if (s[j] == '1') blk[k] |= 1ULL << j;
        }
    }
    std::vector<int> order(K);
    for (int i = 0; i < K; i++) order[i] = i;
    long long total = 0, drop1_req = 0, drop1_moves = 0, drop2_req = 0, twice_req = 0, twice_extra = 0;
    for (int r = 0; r < R; r++) {
        int m;
        fout >> m;
        std::vector<Mv> mv(m);
        std::vector<int> o = order;
        for (int i = 0; i < m; i++) {
            int k, d;
            fout >> k >> d;
            o.erase(std::find(o.begin(), o.end(), k));
            mv[i] = {k, d == 0 ? -1 : o[d - 1]};
            o.insert(o.begin() + d, k);
        }
        total += m;
        u64 target = A[req[r]];
        std::vector<char> skip(m, 0);
        int best1 = 0;
        for (int i = 0; i < m; i++) {
            skip[i] = 1;
            if (check(order, mv, skip, target)) {
                best1++;
                if (getenv("VERBOSE")) std::cout << "  r=" << r << " drop move " << i << " paper " << mv[i].k << " of " << m << '\n';
            }
            skip[i] = 0;
        }
        if (best1) {
            drop1_req++;
            drop1_moves += best1;
        } else if (m <= 30) {
            bool f = false;
            for (int i = 0; i < m && !f; i++)
                for (int j = i + 1; j < m && !f; j++) {
                    skip[i] = skip[j] = 1;
                    f = check(order, mv, skip, target);
                    skip[i] = skip[j] = 0;
                }
            drop2_req += f;
        }
        std::vector<int> cnt(K, 0);
        bool tw = false;
        for (auto& x : mv) if (++cnt[x.k] >= 2) tw = true, twice_extra++;
        twice_req += tw;
        if ((best1 || tw) && getenv("VERBOSE")) {
            std::cout << "r=" << r << " m=" << m << " drop1=" << best1 << " twice=" << tw << '\n';
        }
        order = o;
    }
    std::cout << "moves = " << total << "\ndrop1_req = " << drop1_req << "\ndrop1_moves = " << drop1_moves
              << "\ndrop2_req = " << drop2_req << "\ntwice_req = " << twice_req << "\ntwice_extra = " << twice_extra << '\n';
}
