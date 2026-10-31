// Audit tool: requests where a paper is moved twice (steps i < j). Tries to replace the two moves
// by one: step i moves the paper to any position p, step j is dropped, every other move keeps its
// anchor ("just below paper a"). Counts the requests where some p keeps every move legal and gives
// exactly the same final order (so the rest of the game is unchanged): a pure saving.
// Usage: twice <input> <output>   (prints `name = value` lines; VERBOSE=1 lists the requests)
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using u64 = std::uint64_t;
int N, K, P, R;
std::vector<u64> A, opq, blk;
std::vector<int> req;

struct Mv {
    int k, anchor;  // anchor: paper just above k after the move, -1 = top; -2: absolute position pos
    int pos = 0;
};
static bool visible(const std::vector<int>& order, int k) {
    u64 cov = 0;
    for (int x : order) {
        if (x == k) return (opq[k] & ~cov) != 0;
        cov |= opq[x];
    }
    return false;
}
static void apply_mv(std::vector<int>& order, const Mv& m) {
    order.erase(std::find(order.begin(), order.end(), m.k));
    if (m.anchor == -2) order.insert(order.begin() + m.pos, m.k);
    else if (m.anchor < 0) order.insert(order.begin(), m.k);
    else order.insert(std::find(order.begin(), order.end(), m.anchor) + 1, m.k);
}
static bool run(std::vector<int> order, const std::vector<Mv>& mv, int skip, const std::vector<int>& want) {
    for (size_t i = 0; i < mv.size(); i++) {
        if ((int)i == skip) continue;
        if (mv[i].anchor == mv[i].k) return false;
        if (!visible(order, mv[i].k)) return false;
        apply_mv(order, mv[i]);
    }
    return order == want;
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
    long long total = 0, twice_req = 0, saved = 0, gap_total = 0, gap_req = 0, noop_moves = 0, hit_dj = 0, hit_aj = 0, hit_any = 0;
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
        {  // lower bound for the same final order without visibility: K - LIS(positions in o of order)
            std::vector<int> posn(K);
            for (int i = 0; i < K; i++) posn[o[i]] = i;
            std::vector<int> tails;
            for (int x : order) {
                int v = posn[x];
                auto it = std::lower_bound(tails.begin(), tails.end(), v);
                if (it == tails.end()) tails.push_back(v);
                else *it = v;
            }
            int lb = K - (int)tails.size();
            gap_total += m - lb;
            gap_req += m > lb;
            if (getenv("VERBOSE") && m > lb) std::cout << "r=" << r << " m=" << m << " lb=" << lb << '\n';
        }
        for (int i = 0; i < m; i++)  // a move whose removal keeps the exact final order
            if (run(order, mv, i, o)) {
                noop_moves++;
                if (getenv("VERBOSE")) std::cout << "r=" << r << " noop step " << i << " paper " << mv[i].k << '\n';
            }
        // Greedy: repeatedly merge one pair of moves of the same paper while possible.
        bool any = false;
        for (bool again = true; again;) {
            again = false;
            for (int i = 0; i < (int)mv.size() && !again; i++)
                for (int j = i + 1; j < (int)mv.size() && !again; j++) {
                    if (mv[j].k != mv[i].k) continue;
                    any = true;
                    // State before step i (with the current list of moves).
                    std::vector<int> st = order;
                    for (int t = 0; t < i; t++) apply_mv(st, mv[t]);
                    // Candidate positions: step j's absolute depth, just below step j's anchor.
                    int cand_dj = -1, cand_aj = -1;
                    {
                        std::vector<int> s2 = st;
                        for (int t = i; t < j; t++) apply_mv(s2, mv[t]);
                        apply_mv(s2, mv[j]);
                        cand_dj = std::find(s2.begin(), s2.end(), mv[j].k) - s2.begin();
                        std::vector<int> s3 = st;
                        s3.erase(std::find(s3.begin(), s3.end(), mv[i].k));
                        cand_aj = mv[j].anchor < 0 ? 0 : (int)(std::find(s3.begin(), s3.end(), mv[j].anchor) - s3.begin()) + 1;
                    }
                    std::vector<int> ps = {cand_dj, cand_aj};
                    for (int q = 0; q < K; q++) ps.push_back(q);
                    for (int p : ps) {
                        if (again || p < 0 || p >= K) continue;
                        auto mv2 = mv;
                        mv2[i] = {mv[i].k, -2, p};
                        if (run(order, mv2, j, o)) {
                            hit_dj += p == cand_dj;
                            hit_aj += p == cand_aj;
                            hit_any += p == cand_dj || p == cand_aj;
                            // Re-anchor step i on the paper above position p (as the solver would output).
                            mv.erase(mv.begin() + j);
                            mv[i] = mv2[i];
                            saved++;
                            again = true;
                            if (getenv("VERBOSE")) std::cout << "r=" << r << " paper " << mv[i].k << " steps " << i << "," << j << " -> pos " << p << '\n';
                        }
                    }
                    break;
                }
        }
        twice_req += any;
        order = o;
    }
    std::cout << "moves = " << total << "\ntwice_req = " << twice_req << "\ntwice_saved = " << saved << "\ngap_moves = " << gap_total << "\ngap_req = " << gap_req << "\nnoop_moves = " << noop_moves << "\nhit_dj = " << hit_dj << "\nhit_aj = " << hit_aj << "\nhit_any = " << hit_any << '\n';
}
